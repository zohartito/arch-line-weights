"""Pure-pikepdf poché: fill closed cut loops from PDF OCG marked content.

No Illustrator, no JSX. Extracts stroked paths from
``Visible::ClippingPlaneIntersections::*`` OCG blocks, runs the existing
shapely ladder in ``poche.polygonize_layer``, and injects solid-black fill
(and optional material hatch strokes) into the page content stream.

Conservative policy is unchanged: only ``should_inject_fill`` polygons are
drawn; low-confidence layers stay report-only.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

import pikepdf
from pikepdf import Operator
from shapely.geometry import LineString, Polygon

from .hatch import MATERIALS, hatch_polygon, material_for_layer
from .input_format import raise_if_unsupported
from .poche import (
    PocheReport,
    _is_poche_cut_layer_name,
    polygonize_layer,
    should_inject_fill,
)
from .run_report import build_poche_report

_PATH_OPS = {"m", "l", "c", "v", "y", "h", "re"}
_STROKE_CLOSE_OPS = {"S", "s", "B", "B*", "b", "b*", "f", "f*", "F", "n"}

# DETAIL hatch grammar prefers patterned recipes over the solid-cut defaults
# used by the Illustrator poché path at small scales.
_PATTERNED_MATERIAL = {
    "concrete_solid": "concrete",
    "clt_solid": "clt_cross_grain",
    "board_formed_concrete": "board_formed_concrete",
}


def _hatch_material_for_layer(layer_name: str) -> str:
    material = material_for_layer(layer_name)
    return _PATTERNED_MATERIAL.get(material, material)


@dataclass
class PochePdfResult:
    report: PocheReport
    report_json: dict
    output_size: int = 0
    fills_injected: int = 0
    hatch_segments_injected: int = 0
    cut_layers_seen: int = 0
    non_cut_layers_seen: int = 0
    warnings: list[str] = field(default_factory=list)


def _page_property_layers(page) -> dict[str, str]:
    try:
        resources = page.obj.get("/Resources", {})
        properties = resources.get("/Properties", {})
    except Exception:
        return {}
    out: dict[str, str] = {}
    try:
        items = properties.items()
    except Exception:
        return out
    for key, value in items:
        try:
            name = value.get("/Name")
        except Exception:
            continue
        if name is None:
            continue
        text = str(name).strip()
        if text:
            out[str(key)] = text
    return out


def _layer_from_bdc(operands, property_layers: dict[str, str]) -> str | None:
    if not operands or str(operands[0]) != "/OC":
        return None
    if len(operands) < 2:
        return None
    prop = operands[1]
    if isinstance(prop, pikepdf.Name):
        return property_layers.get(str(prop))
    try:
        name = prop.get("/Name")
    except Exception:
        return None
    return str(name).strip() if name is not None else None


def _float(op) -> float:
    return float(op)


def enumerate_cut_layer_paths_from_page(page) -> tuple[dict[str, list[list[list[float]]]], dict[str, int]]:
    """Parse one page's content stream into per-OCG path lists.

    Returns ``(cut_layer_paths, layer_kind_counts)`` where cut layers match
    ClippingPlaneIntersections (non-glass) and ``layer_kind_counts`` maps
    ``cut`` / ``non_cut`` to distinct layer name counts.
    """
    property_layers = _page_property_layers(page)
    instructions = list(pikepdf.parse_content_stream(page))
    layer_stack: list[str | None] = []
    current_path: list[tuple[float, float]] = []
    subpaths: list[list[tuple[float, float]]] = []
    by_layer: dict[str, list[list[list[float]]]] = {}
    seen_cut: set[str] = set()
    seen_non_cut: set[str] = set()

    def flush_path(*, close: bool = False) -> None:
        nonlocal current_path, subpaths
        if current_path:
            pts = list(current_path)
            if close and len(pts) >= 2 and pts[0] != pts[-1]:
                pts.append(pts[0])
            subpaths.append(pts)
            current_path = []
        active = next((name for name in reversed(layer_stack) if name), None)
        if not active or not subpaths:
            subpaths = []
            return
        if _is_poche_cut_layer_name(active):
            seen_cut.add(active)
            bucket = by_layer.setdefault(active, [])
            for pts in subpaths:
                if len(pts) >= 2:
                    bucket.append([[float(x), float(y)] for x, y in pts])
        else:
            seen_non_cut.add(active)
        subpaths = []

    for operands, op in instructions:
        op_str = str(op)
        if op_str == "BDC":
            layer_stack.append(_layer_from_bdc(operands, property_layers))
            continue
        if op_str == "BMC":
            layer_stack.append(None)
            continue
        if op_str == "EMC":
            if layer_stack:
                layer_stack.pop()
            continue

        if op_str == "m" and len(operands) >= 2:
            if current_path:
                subpaths.append(list(current_path))
            current_path = [(_float(operands[0]), _float(operands[1]))]
        elif op_str == "l" and len(operands) >= 2 and current_path:
            current_path.append((_float(operands[0]), _float(operands[1])))
        elif op_str == "re" and len(operands) >= 4:
            if current_path:
                subpaths.append(list(current_path))
                current_path = []
            x, y, w, h = (_float(operands[0]), _float(operands[1]), _float(operands[2]), _float(operands[3]))
            subpaths.append([(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)])
        elif op_str == "h":
            if current_path and current_path[0] != current_path[-1]:
                current_path.append(current_path[0])
        elif op_str in {"c", "v", "y"} and current_path and len(operands) >= 2:
            # Approximate curves by their end point for polygonize input.
            current_path.append((_float(operands[-2]), _float(operands[-1])))
        elif op_str in _STROKE_CLOSE_OPS:
            flush_path(close=op_str in {"s", "b", "b*", "f", "f*", "F"})

    return by_layer, {"cut": len(seen_cut), "non_cut": len(seen_non_cut)}


def _polygon_to_pdf_ops(poly: Polygon) -> list[tuple[list, Operator]]:
    """Emit path construction + fill for one shapely polygon (exterior only)."""
    coords = list(poly.exterior.coords)
    if len(coords) < 4:
        return []
    ops: list[tuple[list, Operator]] = []
    x0, y0 = coords[0]
    ops.append(([Decimal(f"{x0:g}"), Decimal(f"{y0:g}")], Operator("m")))
    for x, y in coords[1:]:
        ops.append(([Decimal(f"{x:g}"), Decimal(f"{y:g}")], Operator("l")))
    ops.append(([], Operator("h")))
    ops.append(([], Operator("f")))
    return ops


def _lines_to_pdf_stroke_ops(lines: list[LineString], width: float = 0.15) -> list[tuple[list, Operator]]:
    ops: list[tuple[list, Operator]] = []
    if not lines:
        return ops
    ops.append(([Decimal("0"), Decimal("0"), Decimal("0")], Operator("RG")))
    ops.append(([Decimal(f"{width:g}")], Operator("w")))
    for line in lines:
        coords = list(line.coords)
        if len(coords) < 2:
            continue
        x0, y0 = coords[0]
        ops.append(([Decimal(f"{x0:g}"), Decimal(f"{y0:g}")], Operator("m")))
        for x, y in coords[1:]:
            ops.append(([Decimal(f"{x:g}"), Decimal(f"{y:g}")], Operator("l")))
        ops.append(([], Operator("S")))
    return ops


def _build_injection_ops(
    report: PocheReport,
    *,
    style: str,
    scale: float,
) -> tuple[list[tuple[list, Operator]], int, int]:
    """Build content-stream ops for injected fills (+ optional hatch)."""
    ops: list[tuple[list, Operator]] = []
    fills = 0
    hatch_segments = 0
    if not report.polygons:
        return ops, fills, hatch_segments

    ops.append(([], Operator("q")))
    ops.append(([Decimal("0"), Decimal("0"), Decimal("0")], Operator("rg")))
    for layer_name, polygons in sorted(report.polygons.items()):
        for ring in polygons:
            if len(ring) < 3:
                continue
            poly = Polygon([(p[0], p[1]) for p in ring])
            if poly.is_empty or not poly.is_valid:
                continue
            layer_ops = _polygon_to_pdf_ops(poly)
            if not layer_ops:
                continue
            ops.extend(layer_ops)
            fills += 1
            if style == "material":
                material = _hatch_material_for_layer(layer_name)
                recipe = MATERIALS.get(material)
                if recipe is not None and recipe.solid:
                    hatch_lines = []
                else:
                    try:
                        hatch_lines = hatch_polygon(poly, material, scale)
                    except Exception:
                        hatch_lines = []
                    # Keep PDF hatch budgets bounded for dense DETAIL recipes.
                    if len(hatch_lines) > 5_000:
                        hatch_lines = hatch_lines[:5_000]
                if hatch_lines:
                    ops.append(([], Operator("Q")))
                    ops.append(([], Operator("q")))
                    stroke_ops = _lines_to_pdf_stroke_ops(hatch_lines)
                    ops.extend(stroke_ops)
                    hatch_segments += len(hatch_lines)
                    ops.append(([], Operator("Q")))
                    ops.append(([], Operator("q")))
                    ops.append(([Decimal("0"), Decimal("0"), Decimal("0")], Operator("rg")))
    ops.append(([], Operator("Q")))
    return ops, fills, hatch_segments


def polygonize_cut_layers(
    cut_paths: dict[str, list[list[list[float]]]],
    *,
    overrides: dict | None = None,
    use_alpha_shape: bool = True,
    bridge_strategy: str | None = None,
) -> PocheReport:
    """Run the shared shapely ladder; only high-confidence polys are injectable."""
    report = PocheReport()
    overrides = overrides or {}
    for layer_name in sorted(cut_paths):
        paths = cut_paths[layer_name]
        ov = overrides.get(layer_name)
        polys, result = polygonize_layer(
            layer_name,
            paths,
            override=ov,
            use_alpha_shape=use_alpha_shape,
            bridge_strategy=bridge_strategy,
        )
        report.fills.append(result)
        if polys and should_inject_fill(result):
            report.polygons[layer_name] = [
                [[round(x, 4), round(y, 4)] for x, y in p.exterior.coords] for p in polys
            ]
    return report


def apply_poche_pdf(
    src: str,
    dst: str | None = None,
    *,
    style: str = "solid",
    scale: float = 1 / 50,
    overrides: dict | None = None,
    use_alpha_shape: bool = True,
    bridge_strategy: str | None = None,
    report_json_path: str | None = None,
) -> PochePdfResult:
    """Inject poché fills into a PDF from OCG cut layers; write optional report."""
    src = os.path.abspath(src)
    if dst is None:
        p = Path(src)
        dst = str(p.with_name(f"{p.stem} POCHE-PDF{p.suffix}"))
    dst = os.path.abspath(dst)
    if dst == src:
        raise ValueError("dst must differ from src to keep the original safe")
    raise_if_unsupported(src, "poche-pdf")

    pdf = pikepdf.open(src)
    all_cut: dict[str, list[list[list[float]]]] = {}
    cut_count = 0
    non_cut_count = 0
    for page in pdf.pages:
        page_paths, kinds = enumerate_cut_layer_paths_from_page(page)
        cut_count += kinds["cut"]
        non_cut_count += kinds["non_cut"]
        for name, paths in page_paths.items():
            all_cut.setdefault(name, []).extend(paths)

    report = polygonize_cut_layers(
        all_cut,
        overrides=overrides,
        use_alpha_shape=use_alpha_shape,
        bridge_strategy=bridge_strategy,
    )
    inject_ops, fills_injected, hatch_segments = _build_injection_ops(
        report, style=style, scale=scale
    )

    # Append fill block once on the first page (section drawings are single-page).
    if inject_ops and pdf.pages:
        page0 = pdf.pages[0]
        existing = list(pikepdf.parse_content_stream(page0))
        new_bytes = pikepdf.unparse_content_stream([*existing, *inject_ops])
        page0.Contents = pdf.make_stream(new_bytes)
        if "/PieceInfo" in page0.obj:
            del page0.obj["/PieceInfo"]
        for k in ("/LastModified", "/Thumb"):
            if k in page0.obj:
                del page0.obj[k]

    pdf.save(dst)
    pdf.close()

    report_json = build_poche_report(
        input_path=src,
        output_path=dst,
        source={
            "mode": "poche-pdf",
            "style": style,
            "scale": scale,
            "engine": "pikepdf",
            "min_inject_confidence": float(os.environ.get("ARCH_LW_POCHE_MIN_INJECT_CONFIDENCE", "0.85")),
        },
        poche_report=report,
        command="poche-pdf",
    )
    if report_json_path:
        Path(report_json_path).write_text(json.dumps(report_json, indent=2, sort_keys=True) + "\n")

    return PochePdfResult(
        report=report,
        report_json=report_json,
        output_size=os.path.getsize(dst),
        fills_injected=fills_injected,
        hatch_segments_injected=hatch_segments,
        cut_layers_seen=cut_count,
        non_cut_layers_seen=non_cut_count,
    )
