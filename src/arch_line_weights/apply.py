"""Rewrite a PDF/AI content stream so each stroke gets a per-color weight.

Strategy:
  * Parse the page's content stream into (operands, operator) instructions
  * Track the current stroke RGB (set by `RG`)
  * Before every stroke operator (S, s, B, B*, b, b*) inject `<width> w`
  * For .ai files, strip /PieceInfo so Illustrator re-parses from the modified
    PDF stream instead of its now-stale private cache

Only RGB stroke colors are supported. CMYK / Gray strokes pass through with
the default weight.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from decimal import Decimal

import pikepdf
from pikepdf import Operator

from .input_format import raise_if_unsupported
from .linetypes import DASH_PATTERNS_PT, LineType

STROKE_OPS = {"S", "s", "B", "B*", "b", "b*"}


@dataclass
class ApplyResult:
    rg_seen: int = 0
    strokes_processed: int = 0
    weights_applied: dict[float, int] = field(default_factory=dict)
    unmatched_colors: dict[tuple[int, int, int], int] = field(default_factory=dict)
    output_size: int = 0
    input_size: int = 0
    pieceinfo_stripped: bool = False
    linetypes_applied: dict[str, int] = field(default_factory=dict)
    excluded_strokes: int = 0
    layer_weight_overrides: int = 0
    layer_color_overrides: int = 0
    layer_dash_overrides: int = 0
    marked_content_ops_seen: int = 0
    marked_content_layers_seen: int = 0
    marked_content_malformed: int = 0
    warnings: list[str] = field(default_factory=list)


def apply_to_file(
    src: str,
    dst: str,
    rgb_to_weight: dict[tuple[int, int, int], float],
    *,
    default_width: float = 0.25,
    strip_pieceinfo: bool = True,
    rgb_to_linetype: dict[tuple[int, int, int], LineType] | None = None,
    layer_weight_resolver: Callable[[str], float | None] | None = None,
    layer_color_resolver: Callable[[str], tuple[int, int, int] | None] | None = None,
    layer_solid_line_resolver: Callable[[str], bool] | None = None,
) -> ApplyResult:
    """Apply per-color stroke widths to `src`, save to `dst`.

    When ``rgb_to_linetype`` is given, a PDF dash operator is injected before
    each matching stroke (CONTINUOUS emits nothing; NON_PLOTTING is counted in
    ``result.excluded_strokes`` but not deleted — dropping a paint op can orphan
    `q`/clip state, so true exclusion is deferred to the marked-content path).
    With no ``rgb_to_linetype`` the output is byte-identical to a weight-only run.
    """
    if os.path.abspath(src) == os.path.abspath(dst):
        raise ValueError("dst must differ from src to keep the original safe")
    raise_if_unsupported(src, "apply")

    pdf = pikepdf.open(src)
    result = ApplyResult(input_size=os.path.getsize(src))

    for page in pdf.pages:
        instructions = list(pikepdf.parse_content_stream(page))
        property_layers = _page_property_layers(page)
        new_inst = _rewrite(
            instructions,
            rgb_to_weight,
            default_width,
            result,
            rgb_to_linetype,
            property_layers=property_layers,
            layer_weight_resolver=layer_weight_resolver,
            layer_color_resolver=layer_color_resolver,
            layer_solid_line_resolver=layer_solid_line_resolver,
        )
        new_bytes = pikepdf.unparse_content_stream(new_inst)
        page.Contents = pdf.make_stream(new_bytes)

        if strip_pieceinfo and "/PieceInfo" in page.obj:
            del page.obj["/PieceInfo"]
            result.pieceinfo_stripped = True
        for k in ("/LastModified", "/Thumb"):
            if k in page.obj:
                del page.obj[k]

    if (
        layer_weight_resolver is not None
        or layer_color_resolver is not None
        or layer_solid_line_resolver is not None
    ) and result.marked_content_layers_seen == 0:
        if result.marked_content_ops_seen == 0:
            _warn_once(
                result, "no marked-content OCG layer bindings found; using color/default stroke mapping"
            )
        else:
            _warn_once(
                result,
                "marked-content OCG layer bindings were present but unresolved; using color/default stroke mapping",
            )

    pdf.save(dst)
    result.output_size = os.path.getsize(dst)
    return result


def _dash_operands(linetype: LineType) -> list | None:
    """Build pikepdf operands for a `d` (dash) op, or None for a solid line."""
    pattern = DASH_PATTERNS_PT.get(linetype)
    if pattern is None:
        return None
    on_off, phase = pattern
    return [pikepdf.Array([Decimal(f"{n:g}") for n in on_off]), Decimal(f"{phase:g}")]


def _solid_dash_operands() -> list:
    """Operands for `[] 0 d` — reset the dash state to a solid line."""
    return [pikepdf.Array([]), Decimal("0")]


def _rgb_operands(rgb: tuple[int, int, int]) -> list[Decimal]:
    return [Decimal(f"{max(0, min(255, channel)) / 255:g}") for channel in rgb]


def _warn_once(result: ApplyResult, message: str) -> None:
    if message not in result.warnings:
        result.warnings.append(message)


def _ocg_name(value) -> str | None:
    try:
        name = value.get("/Name")
    except Exception:
        return None
    if name is None:
        return None
    text = str(name).strip()
    return text or None


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
        name = _ocg_name(value)
        if name:
            out[str(key)] = name
    return out


def _layer_from_property_object(prop, property_layers: dict[str, str]) -> str | None:
    if isinstance(prop, pikepdf.Name):
        return property_layers.get(str(prop))
    direct = _ocg_name(prop)
    if direct:
        return direct
    try:
        nested = prop.get("/OC")
    except Exception:
        return None
    if isinstance(nested, pikepdf.Name):
        return property_layers.get(str(nested))
    return _ocg_name(nested)


def _layer_from_bdc_operands(
    operands,
    property_layers: dict[str, str],
    result: ApplyResult,
) -> str | None:
    tag = str(operands[0]) if operands else ""
    if tag != "/OC":
        return None
    if len(operands) < 2:
        result.marked_content_malformed += 1
        _warn_once(result, "BDC /OC without a property operand; using color/default stroke mapping")
        return None
    prop = operands[1]
    layer = _layer_from_property_object(prop, property_layers)
    if layer:
        result.marked_content_layers_seen += 1
        return layer
    prop_name = str(prop) if isinstance(prop, pikepdf.Name) else "<inline>"
    _warn_once(
        result,
        f"unresolved marked-content OCG property {prop_name}; using color/default stroke mapping",
    )
    return None


def _current_layer(layer_stack: list[str | None]) -> str | None:
    for layer_name in reversed(layer_stack):
        if layer_name:
            return layer_name
    return None


def _rewrite(
    instructions: Iterable,
    rgb_to_weight: dict[tuple[int, int, int], float],
    default_width: float,
    result: ApplyResult,
    rgb_to_linetype: dict[tuple[int, int, int], LineType] | None = None,
    *,
    property_layers: dict[str, str] | None = None,
    layer_weight_resolver: Callable[[str], float | None] | None = None,
    layer_color_resolver: Callable[[str], tuple[int, int, int] | None] | None = None,
    layer_solid_line_resolver: Callable[[str], bool] | None = None,
) -> list:
    out: list = []
    current_rgb: tuple[int, int, int] | None = None
    layer_stack: list[str | None] = []
    property_layers = property_layers or {}
    # Only touch the dash state when at least one real dash pattern is requested;
    # then set it on EVERY stroke (solid `[] 0 d` reset by default) so a pattern
    # never leaks into later strokes via persistent graphics state.
    emit_dashes = (
        rgb_to_linetype is not None and any(lt in DASH_PATTERNS_PT for lt in rgb_to_linetype.values())
    ) or layer_solid_line_resolver is not None

    def layer_weight(layer_name: str | None) -> float | None:
        if not layer_name or layer_weight_resolver is None:
            return None
        weight = layer_weight_resolver(layer_name)
        if weight is not None:
            result.layer_weight_overrides += 1
        return weight

    def layer_color(layer_name: str | None) -> tuple[int, int, int] | None:
        if not layer_name or layer_color_resolver is None:
            return None
        color = layer_color_resolver(layer_name)
        if color is not None:
            result.layer_color_overrides += 1
        return color

    def layer_solid_line(layer_name: str | None) -> bool:
        if not layer_name or layer_solid_line_resolver is None:
            return False
        solid = bool(layer_solid_line_resolver(layer_name))
        if solid:
            result.layer_dash_overrides += 1
        return solid

    for operands, op in instructions:
        op_str = str(op)

        if op_str == "BDC":
            result.marked_content_ops_seen += 1
            layer_stack.append(_layer_from_bdc_operands(operands, property_layers, result))
            out.append((operands, op))
            continue
        if op_str == "BMC":
            result.marked_content_ops_seen += 1
            layer_stack.append(None)
            out.append((operands, op))
            continue
        if op_str == "EMC":
            if layer_stack:
                layer_stack.pop()
            else:
                result.marked_content_malformed += 1
                _warn_once(result, "EMC without matching BDC/BMC; using color/default stroke mapping")
            out.append((operands, op))
            continue

        active_layer = _current_layer(layer_stack)

        if op_str == "RG" and len(operands) >= 3:
            try:
                r, g, b = (float(o) for o in operands[:3])
                current_rgb = (round(r * 255), round(g * 255), round(b * 255))
                result.rg_seen += 1
            except Exception:
                current_rgb = None
            out.append((operands, op))

        elif op_str in STROKE_OPS:
            semantic_weight = layer_weight(active_layer)
            if semantic_weight is not None:
                w = semantic_weight
            elif current_rgb is not None:
                w = rgb_to_weight.get(current_rgb, default_width)
                if current_rgb not in rgb_to_weight:
                    result.unmatched_colors[current_rgb] = result.unmatched_colors.get(current_rgb, 0) + 1
            else:
                w = default_width

            semantic_color = layer_color(active_layer)
            if semantic_color is not None:
                out.append((_rgb_operands(semantic_color), Operator("RG")))

            linetype = (
                rgb_to_linetype.get(current_rgb)
                if rgb_to_linetype is not None and current_rgb is not None
                else None
            )
            if linetype is LineType.NON_PLOTTING:
                # v1: count + surface, never delete (dropping a paint op can
                # orphan q/clip state — deferred to the marked-content path).
                result.excluded_strokes += 1
            solid_line = layer_solid_line(active_layer)
            if emit_dashes:
                dash = _dash_operands(linetype) if linetype is not None and not solid_line else None
                out.append((dash if dash is not None else _solid_dash_operands(), Operator("d")))
                if dash is not None:
                    result.linetypes_applied[linetype.value] = (
                        result.linetypes_applied.get(linetype.value, 0) + 1
                    )

            result.weights_applied[w] = result.weights_applied.get(w, 0) + 1
            result.strokes_processed += 1
            out.append(([Decimal(f"{w:g}")], Operator("w")))
            out.append((operands, op))

        elif op_str == "w":
            # Drop pre-existing line-width ops: a `<width> w` is injected before
            # every stroke above, so passing the old one through would accumulate a
            # redundant `w` on each re-apply and break byte-idempotency.
            continue

        else:
            out.append((operands, op))

    if layer_stack:
        result.marked_content_malformed += len(layer_stack)
        _warn_once(
            result,
            "marked-content sequence ended with unclosed BDC/BMC; using resolved layers only where available",
        )

    return out
