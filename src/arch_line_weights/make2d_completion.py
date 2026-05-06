"""Architectural Make2D completion helpers.

The completion stage sits between raw layer/path extraction and final styling.
Its job is to turn Rhino/Illustrator layer evidence into bounded repair
candidates that both line-weight hierarchy and poché can consume.

This first slice is intentionally conservative: it only auto-accepts structural
cut-face completion candidates that are anchored to the target clipping-plane
layer. Same-component visible/tangent geometry can help close a face, but a
helper-only closed shape is diagnostic evidence, not automatic black fill.
"""

from __future__ import annotations

import contextlib
import warnings
from dataclasses import dataclass
from typing import Literal

from shapely.geometry import LineString, MultiLineString, Polygon, box
from shapely.ops import linemerge, polygonize, unary_union

from .architectural import ArchitecturalAssignment, classify_architectural_layer
from .layer_classify import Source

Path2D = list[list[float]]
LayerRole = Literal["cut", "visible_curve", "visible_tangent", "other"]

_CUT_MARKER = "::CLIPPINGPLANEINTERSECTIONS::"
_VISIBLE_CURVES_MARKER = "::VISIBLE::CURVES::"
_VISIBLE_TANGENTS_MARKER = "::VISIBLE::TANGENTS::"

_MIN_COMPLETION_AREA = 20.0
_CUT_ANCHOR_BUFFER = 0.75
_CUT_ANCHOR_MIN = 8.0
_CUT_ANCHOR_PERIMETER_RATIO = 0.08
_BOUNDS_MARGIN = 80.0


@dataclass(frozen=True)
class DrawingLayer:
    """A parsed AI/Rhino drawing layer with architectural semantics attached."""

    name: str
    paths: list[Path2D]
    assignment: ArchitecturalAssignment
    role: LayerRole
    component_key: str


@dataclass(frozen=True)
class CompletionCandidate:
    """One proposed Make2D repair with acceptance metadata."""

    component_key: str
    target_layer: str
    source_role: LayerRole
    polygon: Polygon
    confidence: float
    provenance: str
    accepted: bool
    reason: str
    cut_shared_length: float


def component_key(layer_name: str) -> str:
    """Return the Rhino leaf/component key for a layer name."""
    return layer_name.rsplit("::", 1)[-1].upper()


def layer_role(layer_name: str) -> LayerRole:
    upper = layer_name.upper()
    if _CUT_MARKER in upper:
        return "cut"
    if _VISIBLE_CURVES_MARKER in upper:
        return "visible_curve"
    if _VISIBLE_TANGENTS_MARKER in upper:
        return "visible_tangent"
    return "other"


def build_drawing_layers(
    paths_by_layer: dict[str, list[Path2D]],
    *,
    preset: str = "section",
    scale: str = "1/4",
    for_print: bool = False,
    source: Source = Source.RHINO,
) -> list[DrawingLayer]:
    """Attach semantic classification and component keys to parsed layers."""
    return [
        DrawingLayer(
            name=name,
            paths=paths,
            assignment=classify_architectural_layer(
                name,
                preset=preset,
                scale=scale,
                for_print=for_print,
                source=source,
            ),
            role=layer_role(name),
            component_key=component_key(name),
        )
        for name, paths in paths_by_layer.items()
    ]


def _lines_from_paths(paths: list[Path2D]) -> list[LineString]:
    lines: list[LineString] = []
    for pts in paths:
        if len(pts) < 2:
            continue
        with contextlib.suppress(Exception):
            lines.append(LineString([(p[0], p[1]) for p in pts]))
    return lines


def _expanded_bounds(lines: list[LineString], margin: float = _BOUNDS_MARGIN) -> Polygon | None:
    if not lines:
        return None
    minx, miny, maxx, maxy = MultiLineString(lines).bounds
    if maxx <= minx or maxy <= miny:
        return None
    return box(minx - margin, miny - margin, maxx + margin, maxy + margin)


def _candidate_polygons(lines: list[LineString]) -> list[Polygon]:
    if not lines:
        return []
    try:
        merged = linemerge(MultiLineString(lines))
    except Exception:
        return []
    try:
        raw = list(polygonize(merged))
    except Exception:
        return []
    valid = [
        p
        for p in raw
        if isinstance(p, Polygon)
        and not p.is_empty
        and p.is_valid
        and p.area >= _MIN_COMPLETION_AREA
    ]
    if not valid:
        return []
    try:
        merged_polys = unary_union(valid)
    except Exception:
        return valid
    if isinstance(merged_polys, Polygon):
        return [merged_polys] if merged_polys.area >= _MIN_COMPLETION_AREA else []
    try:
        return [
            p
            for p in merged_polys.geoms
            if isinstance(p, Polygon)
            and not p.is_empty
            and p.is_valid
            and p.area >= _MIN_COMPLETION_AREA
        ]
    except AttributeError:
        return valid


def cut_shared_length(poly: Polygon, cut_lines: list[LineString]) -> float:
    """Measure how much of a candidate boundary coincides with real cut lines."""
    if poly.is_empty or not cut_lines:
        return 0.0
    boundary = poly.boundary
    shared = 0.0
    for line in cut_lines:
        if line.length <= 2.0:
            continue
        try:
            shared += boundary.buffer(_CUT_ANCHOR_BUFFER).intersection(line).length
        except Exception:
            continue
    return float(shared)


def has_cut_anchor(poly: Polygon, cut_lines: list[LineString]) -> bool:
    """Return True when a helper-derived polygon is sufficiently cut-anchored."""
    required = max(_CUT_ANCHOR_MIN, _CUT_ANCHOR_PERIMETER_RATIO * poly.length)
    return cut_shared_length(poly, cut_lines) >= required


def _completion_area_limit(layer_name: str) -> float:
    upper = layer_name.upper()
    if "TEC_CLT_SLABS" in upper:
        return 7000.0
    if "TEC_ROOF_CLT" in upper or "ROOF_CAP" in upper:
        return 3500.0
    if "TEC_FOUNDATION" in upper or "TEC_CONCRETE_BASE" in upper:
        return 2500.0
    if "CLT_THICK" in upper or "BACKUP_WALL" in upper:
        return 1800.0
    return 1200.0


def _oriented_dimensions(poly: Polygon) -> tuple[float, float] | None:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            rect = poly.minimum_rotated_rectangle
        coords = list(rect.exterior.coords)
    except Exception:
        return None
    if len(coords) < 4:
        return None
    lengths = [
        LineString([coords[i], coords[i + 1]]).length
        for i in range(min(4, len(coords) - 1))
    ]
    lengths = [length for length in lengths if length > 1e-6]
    if len(lengths) < 2:
        return None
    short = min(lengths)
    long = max(lengths)
    return short, long


def _rectangularity(poly: Polygon, short: float, long: float) -> float:
    rect_area = short * long
    if rect_area <= 1e-6:
        return 0.0
    return min(1.0, poly.area / rect_area)


def _large_candidate_is_plausible(
    layer_name: str,
    poly: Polygon,
    shared: float,
    required: float,
) -> bool:
    """Allow large repairs only when they look like strongly anchored cut strips."""
    upper = layer_name.upper()
    if "TEC_CONCRETE_BASE" in upper or "ROOF_CAP" in upper:
        return False
    dims = _oriented_dimensions(poly)
    if dims is None:
        return False
    short, long = dims
    aspect = long / max(short, 1e-6)
    rectangularity = _rectangularity(poly, short, long)
    if "TEC_FOUNDATION" in upper:
        return (
            poly.area <= 5000.0
            and aspect >= 2.0
            and short <= 90.0
            and rectangularity >= 0.65
            and shared >= max(35.0, required * 1.5)
        )
    if "TEC_ROOF_CLT" in upper or "TEC_CLT_SLABS" in upper:
        return (
            poly.area <= 45000.0
            and aspect >= 2.0
            and short <= 260.0
            and rectangularity >= 0.60
            and shared >= max(200.0, required * 1.5)
        )
    return False


def _timber_beam_candidate_is_plausible(
    poly: Polygon,
    shared: float,
    required: float,
) -> bool:
    """Allow only small, repeated beam-end rectangles from helper completion."""
    dims = _oriented_dimensions(poly)
    if dims is None:
        return False
    short, long = dims
    aspect = long / max(short, 1e-6)
    return (
        80.0 <= poly.area <= 450.0
        and 4.0 <= short <= 18.0
        and long <= 45.0
        and 1.2 <= aspect <= 6.0
        and _rectangularity(poly, short, long) >= 0.65
        and shared >= max(required, 20.0)
    )


def _duplicates_existing(poly: Polygon, existing: list[Polygon]) -> bool:
    for current in existing:
        if current.is_empty or current.area <= 0:
            continue
        try:
            overlap = poly.intersection(current).area
        except Exception:
            continue
        if overlap >= min(poly.area, current.area) * 0.80:
            return True
    return False


def _accepted_candidate(
    *,
    target_layer: str,
    component: str,
    source_role: LayerRole,
    polygon: Polygon,
    confidence: float,
    provenance: str,
    cut_shared: float,
) -> CompletionCandidate:
    return CompletionCandidate(
        component_key=component,
        target_layer=target_layer,
        source_role=source_role,
        polygon=polygon,
        confidence=confidence,
        provenance=provenance,
        accepted=True,
        reason="accepted: bounded and anchored to clipping-plane edge",
        cut_shared_length=cut_shared,
    )


def _rejected_candidate(
    *,
    target_layer: str,
    component: str,
    source_role: LayerRole,
    polygon: Polygon,
    provenance: str,
    reason: str,
    cut_shared: float = 0.0,
) -> CompletionCandidate:
    return CompletionCandidate(
        component_key=component,
        target_layer=target_layer,
        source_role=source_role,
        polygon=polygon,
        confidence=0.0,
        provenance=provenance,
        accepted=False,
        reason=reason,
        cut_shared_length=cut_shared,
    )


def structural_completion_paths_for_layers(
    cut_paths: dict[str, list[Path2D]],
    all_paths: dict[str, list[Path2D]],
    *,
    preset: str = "section",
    scale: str = "1/4",
    for_print: bool = False,
    source: Source = Source.RHINO,
) -> dict[str, list[Path2D]]:
    """Collect same-component visible/tangent paths for structural cut layers.

    The returned paths are only repair evidence. Callers must still validate
    generated geometry before drawing it.
    """
    layers = build_drawing_layers(
        all_paths,
        preset=preset,
        scale=scale,
        for_print=for_print,
        source=source,
    )
    by_component: dict[str, list[Path2D]] = {}
    for layer in layers:
        if layer.role not in {"visible_curve", "visible_tangent"}:
            continue
        if layer.assignment.tier != "structure_primary" or layer.assignment.poche:
            continue
        by_component.setdefault(layer.component_key, []).extend(layer.paths)

    out: dict[str, list[Path2D]] = {}
    for name in cut_paths:
        assignment = classify_architectural_layer(
            name,
            preset=preset,
            scale=scale,
            for_print=for_print,
            source=source,
        )
        if not assignment.poche:
            continue
        paths = by_component.get(component_key(name))
        if paths:
            out[name] = paths
    return out


def complete_structural_cut_polygons(
    layer_name: str,
    cut_paths: list[Path2D],
    completion_paths: list[Path2D],
    existing_polygons: list[Polygon],
) -> tuple[list[Polygon], list[CompletionCandidate]]:
    """Infer extra structural cut-face polygons from bounded Make2D evidence."""
    if not cut_paths or not completion_paths:
        return [], []
    assignment = classify_architectural_layer(layer_name)
    if not assignment.poche:
        return [], []

    cut_lines = _lines_from_paths(cut_paths)
    helper_lines = _lines_from_paths(completion_paths)
    bounds_gate = _expanded_bounds(cut_lines)
    if not cut_lines or not helper_lines or bounds_gate is None:
        return [], []

    limit = _completion_area_limit(layer_name)
    component = component_key(layer_name)
    candidates: list[CompletionCandidate] = []
    accepted: list[Polygon] = []
    for poly in _candidate_polygons(cut_lines + helper_lines):
        shared = cut_shared_length(poly, cut_lines)
        required = max(_CUT_ANCHOR_MIN, _CUT_ANCHOR_PERIMETER_RATIO * poly.length)
        if not bounds_gate.covers(poly.centroid):
            candidates.append(
                _rejected_candidate(
                    target_layer=layer_name,
                    component=component,
                    source_role="visible_curve",
                    polygon=poly,
                    provenance="cut+same-component-visible/tangent",
                    reason="rejected: centroid outside target cut-layer bounds",
                    cut_shared=shared,
                )
            )
            continue
        if shared < required:
            candidates.append(
                _rejected_candidate(
                    target_layer=layer_name,
                    component=component,
                    source_role="visible_curve",
                    polygon=poly,
                    provenance="cut+same-component-visible/tangent",
                    reason=(
                        f"rejected: cut anchor {shared:.1f} below required "
                        f"{required:.1f}"
                    ),
                    cut_shared=shared,
                )
            )
            continue
        if "TEC_TIMBER_BEAMS" in layer_name.upper() and not _timber_beam_candidate_is_plausible(
            poly,
            shared,
            required,
        ):
            candidates.append(
                _rejected_candidate(
                    target_layer=layer_name,
                    component=component,
                    source_role="visible_curve",
                    polygon=poly,
                    provenance="cut+same-component-visible/tangent",
                    reason="rejected: timber beam completion is not a small cut rectangle",
                    cut_shared=shared,
                )
            )
            continue
        if _duplicates_existing(poly, existing_polygons + accepted):
            candidates.append(
                _rejected_candidate(
                    target_layer=layer_name,
                    component=component,
                    source_role="visible_curve",
                    polygon=poly,
                    provenance="cut+same-component-visible/tangent",
                    reason="rejected: duplicates existing cut polygon",
                    cut_shared=shared,
                )
            )
            continue
        if poly.area > limit and not _large_candidate_is_plausible(
            layer_name,
            poly,
            shared,
            required,
        ):
            candidates.append(
                _rejected_candidate(
                    target_layer=layer_name,
                    component=component,
                    source_role="visible_curve",
                    polygon=poly,
                    provenance="cut+same-component-visible/tangent",
                    reason=f"rejected: area {poly.area:.1f} exceeds layer limit {limit:.1f}",
                    cut_shared=shared,
                )
            )
            continue

        accepted.append(poly)
        candidates.append(
            _accepted_candidate(
                target_layer=layer_name,
                component=component,
                source_role="visible_curve",
                polygon=poly,
                confidence=0.88,
                provenance="cut+same-component-visible/tangent",
                cut_shared=shared,
            )
        )

    return accepted, candidates


__all__ = [
    "CompletionCandidate",
    "DrawingLayer",
    "build_drawing_layers",
    "complete_structural_cut_polygons",
    "component_key",
    "cut_shared_length",
    "has_cut_anchor",
    "layer_role",
    "structural_completion_paths_for_layers",
]
