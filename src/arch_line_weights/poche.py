"""Poché: turn cut-line geometry into solid black fills.

Pipeline (two-stage; relies on Adobe Illustrator for layer-preserving I/O):

1. **Dump** — JSX walks the open file's `ClippingPlaneIntersections::*` layers
   (and any `__POCHE_CLOSE__` user-marked closing layer) and writes every path's
   anchor points to a JSON file.

2. **Polygonize** — `polygonize_dump()` reads the JSON, runs a sweep of
   tolerances over `shapely.ops.linemerge` + `polygonize`, picks the strategy
   that maximises polygon count per layer, falls back to `concave_hull`,
   `bounding_box`, with a confidence score per fill.

3. **Apply** — JSX (rendered with the polygons baked in) creates new closed
   `pathItem`s in each cut layer with `filled = true; fillColor = black`,
   then `saveAs <src> POCHE.<ext>`.

Per-layer strategy can be overridden via a JSON file:

    {
      "TEC_FOUNDATION":          {"strategy": "bbox"},
      "TEC_CONCRETE_BASE":       {"strategy": "concave_hull", "ratio": 0.4},
      "23_WINDOW_FRAMES_REMAP_*": {"strategy": "skip"}
    }
"""

from __future__ import annotations

import contextlib
import json
import logging
import math
import os
import subprocess
import textwrap
import time
import warnings
from dataclasses import dataclass, field
from itertools import pairwise
from pathlib import Path
from typing import Literal

from shapely import concave_hull, segmentize
from shapely.geometry import LineString, MultiLineString, MultiPoint, Polygon, box
from shapely.geometry import Polygon as _ShPolygon
from shapely.ops import linemerge, polygonize, snap, unary_union

from .bridge import infer_bridges, infer_bridges_best
from .hatch import hatch_polygon, material_for_layer

_log = logging.getLogger(__name__)

POCHE_CLOSE_LAYER = "__POCHE_CLOSE__"
TOLERANCE_SWEEP = (0.0, 0.1, 0.5, 1.0, 2.0, 5.0)  # 0 = bare linemerge, no snap

# Bridge strategy selector — controlled by the ``bridge_strategy`` argument
# or the ``ARCH_LW_BRIDGE_STRATEGY`` environment variable. Default is
# ``"best"`` as of v0.6.7: routes through :func:`bridge.infer_bridges_best`
# which picks the best of 4 strategies (greedy, backtracking, DBSCAN
# endpoint collapse, DBSCAN+backtrack). ``"greedy"`` is preserved for
# backwards compatibility with v0.5.x and is reachable via explicit
# ``bridge_strategy="greedy"`` or ``ARCH_LW_BRIDGE_STRATEGY=greedy``. See
# ``docs/research/bridge-strategy-wire-notes.md`` for the wiring rationale
# and the v0.6.7 default-flip rationale, and
# ``docs/research/stubborn-layers-deep-dive.md`` for the strategy ladder.
BridgeStrategy = Literal["greedy", "best"]
_VALID_BRIDGE_STRATEGIES: tuple[str, ...] = ("greedy", "best")
_DEFAULT_BRIDGE_STRATEGY: BridgeStrategy = "best"
_BRIDGE_STRATEGY_ENV = "ARCH_LW_BRIDGE_STRATEGY"
_BRIDGE_BEST_BUDGET_ENV = "ARCH_LW_BRIDGE_BEST_LAYER_BUDGET_SEC"
_BRIDGE_BEST_MAX_ENDPOINTS_ENV = "ARCH_LW_BRIDGE_BEST_MAX_ENDPOINTS"
_POCHE_MIN_INJECT_CONFIDENCE_ENV = "ARCH_LW_POCHE_MIN_INJECT_CONFIDENCE"
_POCHE_ALLOW_LOW_CONFIDENCE_ENV = "ARCH_LW_POCHE_ALLOW_LOW_CONFIDENCE"
_DEFAULT_BRIDGE_BEST_BUDGET_SEC = 60.0
_DEFAULT_BRIDGE_BEST_MAX_ENDPOINTS = 1000
_DEFAULT_POCHE_MIN_INJECT_CONFIDENCE = 0.85


def _resolve_bridge_strategy(explicit: str | None) -> BridgeStrategy:
    """Resolve the bridge strategy from an explicit argument or env var.

    Order of precedence: explicit argument > ``ARCH_LW_BRIDGE_STRATEGY`` env
    var > default (``"best"``). Unknown values silently fall back to the
    default — this is a runtime tuning knob and a typo shouldn't break the
    pipeline.
    """
    candidate = explicit or os.environ.get(_BRIDGE_STRATEGY_ENV)
    if candidate is None:
        return _DEFAULT_BRIDGE_STRATEGY
    if candidate not in _VALID_BRIDGE_STRATEGIES:
        return _DEFAULT_BRIDGE_STRATEGY
    return candidate  # type: ignore[return-value]


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


# ---------------------------------------------------------------------------- #
# Per-fill result metadata
# ---------------------------------------------------------------------------- #

Strategy = Literal[
    "linemerge_bare",
    "linemerge_snap",
    "auto_bridge",
    "structural_open_loop",
    "structural_parallel_edges",
    "structural_visible_completion",
    "alpha_shape",
    "llm_topology",
    "concave_hull",
    "bbox",
    "user_override",
    "skipped",
    "failed",
]


@dataclass
class FillResult:
    layer: str
    strategy: Strategy
    confidence: float
    polygon_count: int
    segment_count: int
    tolerance: float | None = None
    # Set by the auto_bridge rung when ``bridge_strategy="best"`` is in
    # effect — names the inner strategy that ``infer_bridges_best`` picked
    # ("greedy", "backtrack", "dbscan_collapse", "dbscan_collapse+backtrack",
    # or "none"). ``None`` for the default greedy path so reports for
    # pre-existing runs are unchanged.
    bridge_strategy_name: str | None = None


@dataclass
class PocheReport:
    fills: list[FillResult] = field(default_factory=list)
    polygons: dict[str, list[list[list[float]]]] = field(default_factory=dict)
    completion_candidates: list[object] = field(default_factory=list)

    @property
    def total_polygons(self) -> int:
        return sum(f.polygon_count for f in self.fills)

    @property
    def working_layers(self) -> int:
        return sum(1 for f in self.fills if f.confidence >= 0.85)

    @property
    def imperfect_layers(self) -> int:
        return sum(1 for f in self.fills if 0 < f.confidence < 0.85)

    @property
    def failed_layers(self) -> int:
        return sum(1 for f in self.fills if f.confidence == 0)

    @property
    def injected_polygons(self) -> int:
        return sum(len(polys) for polys in self.polygons.values())


def should_inject_fill(result: FillResult) -> bool:
    """Return True when a polygonize result is trustworthy enough to draw.

    Low-confidence rescue geometry (alpha-shape, concave hull, bbox, LLM) is
    useful diagnostic information, but painting it solid black can create
    visually convincing false poché. Default to conservative output; users
    can still opt into the old behavior with ARCH_LW_POCHE_ALLOW_LOW_CONFIDENCE=1.
    """
    if result.strategy in {"failed", "skipped"} or result.polygon_count <= 0:
        return False
    if result.strategy == "user_override":
        return True
    if os.environ.get(_POCHE_ALLOW_LOW_CONFIDENCE_ENV) == "1":
        return True
    min_conf = _env_float(
        _POCHE_MIN_INJECT_CONFIDENCE_ENV,
        _DEFAULT_POCHE_MIN_INJECT_CONFIDENCE,
    )
    return result.confidence >= min_conf


# ---------------------------------------------------------------------------- #
# Polygonize
# ---------------------------------------------------------------------------- #


def _lines_from_anchors(paths: list[list[list[float]]]) -> list[LineString]:
    out = []
    for pts in paths:
        if len(pts) >= 2:
            with contextlib.suppress(Exception):
                out.append(LineString([(p[0], p[1]) for p in pts]))
    return out


def _polys_at_tolerance(lines: list[LineString], tol: float) -> list[Polygon]:
    if not lines:
        return []
    if tol > 0:
        all_geom = unary_union(lines)
        snapped = [snap(ls, all_geom, tol) for ls in lines]
    else:
        snapped = lines
    mls = MultiLineString(snapped)
    merged = linemerge(mls)
    if isinstance(merged, LineString):
        merged_lines = [merged]
    else:
        try:
            merged_lines = list(merged.geoms)
        except AttributeError:
            merged_lines = [merged]
    return list(polygonize(merged_lines))


def _try_concave_hull(lines: list[LineString], ratio: float = 0.3) -> Polygon | None:
    densified = []
    for ls in lines:
        try:
            densified.append(segmentize(ls, max_segment_length=2.0))
        except Exception:
            densified.append(ls)
    pts: list[tuple[float, float]] = []
    for ls in densified:
        pts.extend(list(ls.coords))
    if len(pts) < 3:
        return None
    try:
        h = concave_hull(MultiPoint(pts), ratio=ratio)
    except Exception:
        return None
    if isinstance(h, Polygon) and h.area > 1.0:
        return h
    return None


def _bbox(lines: list[LineString]) -> Polygon | None:
    if not lines:
        return None
    mls = MultiLineString(lines)
    minx, miny, maxx, maxy = mls.bounds
    if maxx - minx < 1 or maxy - miny < 1:
        return None
    return box(minx, miny, maxx, maxy)


def _is_structural_poche_layer(layer_name: str) -> bool:
    try:
        from .architectural import classify_architectural_layer

        return classify_architectural_layer(layer_name).poche
    except Exception:
        return False


def _segment_lengths(lines: list[LineString]) -> list[float]:
    lengths: list[float] = []
    for line in lines:
        coords = list(line.coords)
        for a, b in pairwise(coords):
            seg = LineString([a, b])
            if seg.length > 0:
                lengths.append(float(seg.length))
    return lengths


def _clean_structural_polygons(polys: list[Polygon]) -> list[Polygon]:
    """Merge overlapping inferred cut fills and drop degenerate fragments."""
    valid = [p for p in polys if p is not None and p.is_valid and p.area > 1.0]
    if not valid:
        return []
    try:
        merged = unary_union(valid)
    except Exception:
        merged = valid
    if isinstance(merged, Polygon):
        return [merged] if merged.is_valid and merged.area > 1.0 else []
    try:
        return [
            p
            for p in merged.geoms
            if isinstance(p, Polygon) and p.is_valid and p.area > 1.0
        ]
    except AttributeError:
        return valid


def _expanded_bounds_polygon(lines: list[LineString], margin: float) -> Polygon | None:
    if not lines:
        return None
    minx, miny, maxx, maxy = MultiLineString(lines).bounds
    if maxx <= minx or maxy <= miny:
        return None
    return box(minx - margin, miny - margin, maxx + margin, maxy + margin)


def _polygon_uses_cut_edge(poly: Polygon, cut_lines: list[LineString]) -> bool:
    """Return True when an inferred helper polygon is anchored to cut geometry."""
    required = max(8.0, 0.08 * poly.length)
    shared_total = 0.0
    boundary = poly.boundary
    for line in cut_lines:
        if line.length <= 2.0:
            continue
        try:
            shared = boundary.buffer(0.75).intersection(line).length
            shared_total += shared
            if shared_total >= required:
                return True
        except Exception:
            continue
    return False


def _helper_expansion_limit(layer_name: str) -> float:
    upper = layer_name.upper()
    if "TEC_CONCRETE_BASE" in upper or "TEC_FOUNDATION" in upper:
        return 1.85
    return 4.0


def _helper_candidate_overexpands_cut(
    layer_name: str,
    helper_poly: Polygon,
    cut_only_polys: list[Polygon],
) -> bool:
    """Reject helper candidates that mostly widen an existing cut-only face."""
    if helper_poly.is_empty or not cut_only_polys:
        return False
    limit = _helper_expansion_limit(layer_name)
    for cut_poly in cut_only_polys:
        if cut_poly.is_empty or cut_poly.area <= 1.0:
            continue
        try:
            overlap = helper_poly.intersection(cut_poly).area
        except Exception:
            continue
        if overlap >= cut_poly.area * 0.75 and helper_poly.area > cut_poly.area * limit:
            return True
    return False


def _polygon_rectangularity(poly: Polygon) -> float:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            rect = poly.minimum_rotated_rectangle
        coords = list(rect.exterior.coords)
    except Exception:
        return 0.0
    if len(coords) < 4:
        return 0.0
    lengths = [
        LineString([coords[i], coords[i + 1]]).length
        for i in range(min(4, len(coords) - 1))
    ]
    lengths = [length for length in lengths if length > 1e-6]
    if len(lengths) < 2:
        return 0.0
    rect_area = min(lengths) * max(lengths)
    if rect_area <= 1e-6:
        return 0.0
    return min(1.0, poly.area / rect_area)


def _structural_open_loop_candidates(
    lines: list[LineString],
    *,
    max_gap: float,
) -> list[Polygon]:
    """Close individual open chains by joining their endpoints."""
    try:
        merged = linemerge(MultiLineString(lines))
    except Exception:
        return []
    if isinstance(merged, LineString):
        chains = [merged]
    else:
        try:
            chains = [g for g in merged.geoms if isinstance(g, LineString)]
        except AttributeError:
            chains = []

    candidates: list[Polygon] = []
    for chain in chains:
        coords = list(chain.coords)
        if len(coords) < 3 or chain.is_ring:
            continue
        start = coords[0]
        end = coords[-1]
        gap = LineString([start, end]).length
        if gap <= 0.1 or gap > max_gap:
            continue
        if chain.length <= 0 or gap > chain.length:
            continue
        candidate = Polygon([*coords, start])
        if candidate.is_empty or not candidate.is_valid or candidate.area <= 1.0:
            continue
        unique_vertices = {
            (round(float(x), 6), round(float(y), 6))
            for x, y in candidate.exterior.coords[:-1]
        }
        if len(unique_vertices) < 4:
            continue
        if _polygon_rectangularity(candidate) < 0.55:
            continue
        minx, miny, maxx, maxy = candidate.bounds
        width = maxx - minx
        height = maxy - miny
        if width <= 1.0 or height <= 1.0:
            continue
        aspect = max(width, height) / max(1e-6, min(width, height))
        if aspect > 35.0:
            continue
        candidates.append(candidate)

    return candidates


def _segments_from_lines(lines: list[LineString]) -> list[LineString]:
    segments: list[LineString] = []
    for line in lines:
        coords = list(line.coords)
        for start, end in pairwise(coords):
            seg = LineString([start, end])
            if seg.length > 2.0:
                segments.append(seg)
    return segments


def _normalized_direction(line: LineString) -> tuple[float, float] | None:
    coords = list(line.coords)
    if len(coords) < 2:
        return None
    start = coords[0]
    end = coords[-1]
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = math.hypot(dx, dy)
    if length <= 0:
        return None
    ux = dx / length
    uy = dy / length
    if ux < -1e-9 or (abs(ux) < 1e-9 and uy < 0):
        ux = -ux
        uy = -uy
    return ux, uy


def _try_structural_parallel_edges(
    layer_name: str,
    lines: list[LineString],
    helper_lines: list[LineString] | None = None,
) -> list[Polygon]:
    """Recover cut faces from opposite parallel structural edges.

    Rhino Make2D often emits slab/wall cut solids as two parallel cut edges
    without reliable end caps. This infers the missing two sides, while
    requiring at least one edge in every pair to come from the real clipping
    intersection layer.
    """
    if not _is_structural_poche_layer(layer_name) or not lines:
        return []

    helper_lines = helper_lines or []
    cut_segments = _segments_from_lines(lines)
    helper_segments = _segments_from_lines(helper_lines)
    if len(cut_segments) + len(helper_segments) > 2500:
        helper_segments = []
    if len(cut_segments) < 2 and not helper_segments:
        return []

    lengths = sorted(seg.length for seg in cut_segments if seg.length > 2.0)
    median_seg = lengths[len(lengths) // 2] if lengths else 20.0
    max_thickness = max(12.0, min(185.0, median_seg * 0.75))
    min_overlap = max(5.0, min(30.0, median_seg * 0.08))
    max_angle_delta = math.cos(math.radians(8.0))
    tagged = [(seg, "cut") for seg in cut_segments] + [
        (seg, "helper") for seg in helper_segments
    ]

    candidates: list[Polygon] = []
    for idx, (a, a_kind) in enumerate(tagged):
        a_dir = _normalized_direction(a)
        if a_dir is None or a.length < 5.0:
            continue
        a_coords = list(a.coords)
        a_mid = (
            (a_coords[0][0] + a_coords[-1][0]) / 2.0,
            (a_coords[0][1] + a_coords[-1][1]) / 2.0,
        )
        for b, b_kind in tagged[idx + 1 :]:
            if a_kind == "helper" and b_kind == "helper":
                continue
            b_dir = _normalized_direction(b)
            if b_dir is None or b.length < 5.0:
                continue
            dot = abs(a_dir[0] * b_dir[0] + a_dir[1] * b_dir[1])
            if dot < max_angle_delta:
                continue

            u = a_dir
            normal = (-u[1], u[0])
            b_coords = list(b.coords)
            b_mid = (
                (b_coords[0][0] + b_coords[-1][0]) / 2.0,
                (b_coords[0][1] + b_coords[-1][1]) / 2.0,
            )
            offset = abs(
                (b_mid[0] - a_mid[0]) * normal[0] + (b_mid[1] - a_mid[1]) * normal[1]
            )
            if offset < 2.0 or offset > max_thickness:
                continue

            def _project(pt: tuple[float, float], direction: tuple[float, float] = u) -> float:
                return pt[0] * direction[0] + pt[1] * direction[1]

            a_interval = sorted(
                [(_project(a_coords[0]), a_coords[0]), (_project(a_coords[-1]), a_coords[-1])]
            )
            b_interval = sorted(
                [(_project(b_coords[0]), b_coords[0]), (_project(b_coords[-1]), b_coords[-1])]
            )
            overlap_start = max(a_interval[0][0], b_interval[0][0])
            overlap_end = min(a_interval[1][0], b_interval[1][0])
            overlap = overlap_end - overlap_start
            min_len = min(a.length, b.length)
            if overlap < min_overlap or overlap < 0.35 * min_len:
                continue
            if max(a.length, b.length) / max(1.0, min_len) > 5.0 and overlap < 0.75 * min_len:
                continue

            def _point_at_projection(line: LineString, projection: float) -> tuple[float, float]:
                coords = list(line.coords)
                start = coords[0]
                end = coords[-1]
                start_proj = _project(start)
                end_proj = _project(end)
                denom = end_proj - start_proj
                if abs(denom) <= 1e-9:
                    return start
                t = max(0.0, min(1.0, (projection - start_proj) / denom))
                return (
                    start[0] + (end[0] - start[0]) * t,
                    start[1] + (end[1] - start[1]) * t,
                )

            candidate = Polygon(
                [
                    _point_at_projection(a, overlap_start),
                    _point_at_projection(a, overlap_end),
                    _point_at_projection(b, overlap_end),
                    _point_at_projection(b, overlap_start),
                ]
            )
            if candidate.is_empty or not candidate.is_valid or candidate.area <= 10.0:
                continue
            minx, miny, maxx, maxy = candidate.bounds
            width = maxx - minx
            height = maxy - miny
            if width <= 1.0 or height <= 1.0:
                continue
            aspect = max(width, height) / max(1e-6, min(width, height))
            if aspect > 90.0:
                continue
            candidates.append(candidate)

    return _clean_structural_polygons(candidates)


def _post_filter_structural_polygons(layer_name: str, polygons: list[Polygon]) -> list[Polygon]:
    """Apply layer-specific cleanup after union/simplification.

    Candidate-level guards catch most bad faces, but ``unary_union`` can merge
    individually plausible rectangles into an architectural nonsense shape. This
    pass mirrors the manual Illustrator workflow: after closing shapes, inspect
    whether the resulting face still looks like cut material.
    """
    upper = layer_name.upper()
    filtered: list[Polygon] = []
    for poly in polygons:
        if poly.is_empty or poly.area <= 1.0:
            continue
        minx, miny, maxx, maxy = poly.bounds
        width = maxx - minx
        height = maxy - miny
        longest = max(width, height)
        if ("BACKUP_WALL" in upper or "CLT_BACKUP" in upper) and (
            poly.area < 120.0 and longest < 20.0
        ):
            continue
        rectangularity = _polygon_rectangularity(poly)
        if "TEC_ROOF_CLT" in upper:
            if poly.area > 45000.0:
                continue
            if poly.area > 12000.0 and rectangularity < 0.55:
                continue
        filtered.append(poly)
    return filtered


def _try_structural_open_loop(
    layer_name: str,
    lines: list[LineString],
    helper_lines: list[LineString] | None = None,
) -> list[Polygon]:
    """Close simple structural cut chains by adding missing sides.

    This is deliberately narrower than alpha-shape/concave-hull/bbox rescue:
    it only runs for architectural structural-poche layers and rejects
    sprawling or invalid polygons. Same-material helper geometry may be used
    as closure evidence, but each helper-derived polygon must remain anchored
    to an actual clipping-plane edge.
    """
    if not _is_structural_poche_layer(layer_name) or not lines:
        return []

    helper_lines = helper_lines or []
    lengths = sorted(_segment_lengths(lines))
    median_seg = lengths[len(lengths) // 2] if lengths else 20.0
    max_gap = max(75.0, min(350.0, median_seg * 24.0))

    cut_only = _clean_structural_polygons(
        _structural_open_loop_candidates(lines, max_gap=max_gap)
        + _try_structural_parallel_edges(layer_name, lines, [])
    )
    candidates = list(cut_only)

    if helper_lines:
        for poly in _try_structural_parallel_edges(layer_name, lines, helper_lines):
            if _helper_candidate_overexpands_cut(layer_name, poly, cut_only):
                continue
            candidates.append(poly)

    if helper_lines:
        bounds_gate = _expanded_bounds_polygon(lines, max_gap)
        helper_candidates = _structural_open_loop_candidates(
            lines + helper_lines,
            max_gap=max_gap,
        )
        for poly in helper_candidates:
            if bounds_gate is not None and not bounds_gate.covers(poly.centroid):
                continue
            if not _polygon_uses_cut_edge(poly, lines):
                continue
            if _helper_candidate_overexpands_cut(layer_name, poly, cut_only):
                continue
            candidates.append(poly)

    return _post_filter_structural_polygons(
        layer_name,
        _clean_structural_polygons(candidates),
    )


def _structural_open_loop_improves(
    layer_name: str,
    lines: list[LineString],
    current: list[Polygon],
    helper_lines: list[LineString] | None = None,
) -> list[Polygon]:
    """Return structural-open-loop polygons only if they add useful coverage."""
    structural = _try_structural_open_loop(layer_name, lines, helper_lines)
    if not structural:
        return []
    structural = _clean_structural_polygons(current + structural)
    current_area = sum(p.area for p in current)
    structural_area = sum(p.area for p in structural)
    if (
        current
        and len(structural) <= len(current)
        and structural_area > current_area * 1.85
    ):
        return []
    if len(structural) > len(current):
        return structural
    if structural_area > current_area * 1.10:
        return structural
    return []


def _try_alpha_shape(lines: list[LineString]) -> list[Polygon]:
    """Run the alpha-shape rescue over the densified endpoint cloud.

    Returns ``[]`` on any failure. Densification matches what the concave
    hull rung does — sparse Make2D output points produce a degenerate
    α-shape just like they produce a degenerate concave hull, so we
    segmentize first to feed enough vertices to scipy's Delaunay.
    """
    from .alpha_shape import alpha_shape_all_regions

    densified = []
    for ls in lines:
        try:
            densified.append(segmentize(ls, max_segment_length=2.0))
        except Exception:
            densified.append(ls)
    pts: list[tuple[float, float]] = []
    for ls in densified:
        pts.extend((float(x), float(y)) for x, y in ls.coords)
    if len(pts) < 3:
        return []
    polys, _alpha, _n = alpha_shape_all_regions(pts)
    return [p for p in polys if p.is_valid and p.area > 1.0]


def polygonize_layer(
    layer_name: str,
    paths: list[list[list[float]]],
    closing_lines: list[LineString] | None = None,
    override: dict | None = None,
    *,
    use_alpha_shape: bool = True,
    bridge_strategy: str | None = None,
    structural_helper_lines: list[LineString] | None = None,
) -> tuple[list[Polygon], FillResult]:
    """Best-effort polygonization of one layer's segments.

    Parameters
    ----------
    layer_name, paths, closing_lines, override
        See module docstring.
    use_alpha_shape : bool, default True
        When True, the alpha-shape rung runs between auto_bridge and
        concave_hull (v0.5.2 behavior). When False, that rung is skipped
        and the rescue ladder matches v0.5.1 exactly.
    bridge_strategy : str | None, default None
        Selector for the auto-bridge rung. ``"best"`` (the default if
        unset, since v0.6.7) calls :func:`bridge.infer_bridges_best` which
        picks the highest-yield among 4 strategies (greedy, backtrack,
        DBSCAN endpoint collapse, DBSCAN+backtrack). ``"greedy"`` calls
        :func:`bridge.infer_bridges` (the v0.4 nearest-neighbour bridger)
        and is preserved for backwards compatibility. When ``None``, the
        env var ``ARCH_LW_BRIDGE_STRATEGY`` is consulted; if that is also
        unset, the default ``"best"`` applies. Unknown values silently fall
        back to ``"best"``.
    """
    strategy = _resolve_bridge_strategy(bridge_strategy)
    lines = _lines_from_anchors(paths)
    if closing_lines:
        lines = lines + closing_lines
    helper_lines = structural_helper_lines or []
    n_segments = len(lines)

    if not lines:
        return [], FillResult(layer_name, "failed", 0.0, 0, 0)

    # User override
    if override:
        strat = override.get("strategy", "")
        if strat == "skip":
            return [], FillResult(layer_name, "skipped", 0.0, 0, n_segments)
        if strat == "bbox":
            bb = _bbox(lines)
            if bb is not None:
                return [bb], FillResult(layer_name, "user_override", 0.8, 1, n_segments)
        if strat == "concave_hull":
            ratio = float(override.get("ratio", 0.3))
            ch = _try_concave_hull(lines, ratio)
            if ch is not None:
                return [ch], FillResult(layer_name, "user_override", 0.8, 1, n_segments)

    # Sweep tolerances, pick best (most polygons)
    best: tuple[list[Polygon], float] = ([], 0.0)
    for tol in TOLERANCE_SWEEP:
        polys = _polys_at_tolerance(lines, tol)
        if len(polys) > len(best[0]):
            best = (polys, tol)

    if best[0]:
        polys, tol = best
        structural_polys = _structural_open_loop_improves(
            layer_name,
            lines,
            polys,
            helper_lines,
        )
        if structural_polys:
            return structural_polys, FillResult(
                layer_name,
                "structural_open_loop",
                0.90,
                len(structural_polys),
                n_segments,
                tol,
            )
        if tol == 0:
            return polys, FillResult(layer_name, "linemerge_bare", 1.0, len(polys), n_segments, tol)
        conf = 0.95 if tol <= 0.5 else (0.85 if tol <= 1.0 else 0.7)
        return polys, FillResult(layer_name, "linemerge_snap", conf, len(polys), n_segments, tol)

    # Auto-bridge: infer missing connecting segments and re-run
    # linemerge+polygonize. Default strategy (v0.6.7+) is ``"best"``, which
    # dispatches to the 4-way strategy selector. ``"greedy"`` retains the
    # v0.4 nearest-neighbour bridger for backwards compatibility.
    #
    # Note on the polygonization gate: greedy only adds bridges
    # (``len(augmented) > len(lines)``). The "best" selector includes
    # ``dbscan_collapse``, which mutates endpoints *in place* without adding
    # segments, so the length stays the same. We still want to polygonize
    # the collapsed segments — the gate has to allow the equal-length case
    # for "best".
    try:
        if strategy == "best":
            endpoint_count = 2 * len(lines)
            max_endpoints = _env_int(
                _BRIDGE_BEST_MAX_ENDPOINTS_ENV,
                _DEFAULT_BRIDGE_BEST_MAX_ENDPOINTS,
            )
            budget_sec = _env_float(
                _BRIDGE_BEST_BUDGET_ENV,
                _DEFAULT_BRIDGE_BEST_BUDGET_SEC,
            )
            if endpoint_count > max_endpoints:
                _log.warning(
                    "poche layer %r has %d endpoints, above %s=%d; "
                    "using greedy bridge strategy for this layer",
                    layer_name,
                    endpoint_count,
                    _BRIDGE_BEST_MAX_ENDPOINTS_ENV,
                    max_endpoints,
                )
                aug_best, bridge_conf = infer_bridges(lines, max_gap=50.0, min_gap=0.01)
                strategy_name = "greedy_endpoint_cap"
            else:
                aug_best, bridge_conf, strategy_name = infer_bridges_best(
                    lines,
                    max_gap=50.0,
                    min_gap=0.01,
                    time_budget_sec=budget_sec,
                    layer_name=layer_name,
                )
            augmented = aug_best
            # "best" returns a usable augmented set (possibly the same
            # length as the input if dbscan_collapse won) — always try
            # polygonization on it.
            should_polygonize = bool(augmented)
        else:
            augmented, bridge_conf = infer_bridges(lines, max_gap=50.0, min_gap=0.01)
            strategy_name = None
            # Greedy: only bridges (never collapses), so length increase is
            # the right gate (preserves v0.5.x bit-exact behaviour).
            should_polygonize = len(augmented) > len(lines)
        if should_polygonize:
            polys_with_bridges = _polys_at_tolerance(augmented, 0.0)
            if polys_with_bridges:
                structural_polys = _structural_open_loop_improves(
                    layer_name,
                    lines,
                    polys_with_bridges,
                    helper_lines,
                )
                if structural_polys:
                    return structural_polys, FillResult(
                        layer_name,
                        "structural_open_loop",
                        0.90,
                        len(structural_polys),
                        n_segments,
                        bridge_strategy_name=strategy_name,
                    )
                return polys_with_bridges, FillResult(
                    layer_name,
                    "auto_bridge",
                    0.75 * bridge_conf + 0.25,
                    len(polys_with_bridges),
                    n_segments,
                    bridge_strategy_name=strategy_name,
                )
    except Exception:
        pass

    # Structural open-loop closure: recover simple 3-sided or partially open
    # cut loops for whitelisted structural layers, without allowing facade,
    # glass, connector, membrane, or generic clipped layers into black fill.
    try:
        structural_polys = _try_structural_open_loop(layer_name, lines, helper_lines)
        if structural_polys:
            return structural_polys, FillResult(
                layer_name,
                "structural_open_loop",
                0.88,
                len(structural_polys),
                n_segments,
            )
    except Exception:
        pass

    # Alpha-shape: better-than-concave_hull fallback that preserves multi-
    # component topology (e.g. two roof caps with an intentional gap).
    # Opt-out via use_alpha_shape=False to match v0.5.1 behavior.
    if use_alpha_shape:
        try:
            alpha_polys = _try_alpha_shape(lines)
            if alpha_polys:
                return alpha_polys, FillResult(
                    layer_name, "alpha_shape", 0.55, len(alpha_polys), n_segments
                )
        except Exception:
            pass

    # LLM topology inference (rung 5): opt-in via ARCH_LW_LLM_FALLBACK=1 +
    # an Anthropic API key. Hands the layer name + raw endpoint
    # coordinates (no filenames, no metadata) to a small LLM and asks for
    # a closure plan. Default OFF — the rung returns None when the gate
    # is closed, the SDK is missing, the API key is missing, the network
    # call fails, or the response fails schema validation. See
    # ``llm_topology.py`` and
    # ``docs/research/llm-topology-impl-notes.md``.
    try:
        from .llm_topology import bridges_from_plan, infer_closing_plan

        anchors_flat: list[tuple[float, float]] = []
        for ls in lines:
            try:
                anchors_flat.extend((float(x), float(y)) for x, y in ls.coords)
            except Exception:
                continue
        plan = infer_closing_plan(layer_name, anchors_flat, lines)
        if plan is not None:
            llm_bridges = bridges_from_plan(plan, anchors_flat)
            if llm_bridges:
                augmented_llm = lines + llm_bridges
                polys_llm = _polys_at_tolerance(augmented_llm, 0.0)
                if polys_llm:
                    return polys_llm, FillResult(
                        layer_name, "llm_topology", 0.65, len(polys_llm), n_segments
                    )
    except Exception:
        pass

    # Concave hull fallback
    ch = _try_concave_hull(lines, ratio=0.3)
    if ch is not None:
        return [ch], FillResult(layer_name, "concave_hull", 0.55, 1, n_segments)

    # Bbox last
    bb = _bbox(lines)
    if bb is not None:
        return [bb], FillResult(layer_name, "bbox", 0.3, 1, n_segments)

    return [], FillResult(layer_name, "failed", 0.0, 0, n_segments)


def polygonize_dump(
    geometry_json_path: str,
    overrides: dict[str, dict] | None = None,
    *,
    use_alpha_shape: bool = True,
    bridge_strategy: str | None = None,
) -> PocheReport:
    """Load a JSON dump from `dump_cut_geometry.jsx`, polygonize each layer."""
    with open(geometry_json_path) as f:
        data = json.load(f)

    closing_lines: list[LineString] = []
    closing_layer_data = None
    for k in list(data.keys()):
        if POCHE_CLOSE_LAYER in k:
            closing_layer_data = data.pop(k)
            break
    if closing_layer_data:
        closing_lines = _lines_from_anchors(closing_layer_data)

    overrides = overrides or {}
    report = PocheReport()
    for layer_name, paths in data.items():
        # Match override: exact layer name or fnmatch-style suffix
        ov = overrides.get(layer_name)
        if ov is None:
            for pattern, val in overrides.items():
                if pattern.endswith("*") and layer_name.endswith(pattern[:-1].split("::")[-1]):
                    ov = val
                    break

        polys, result = polygonize_layer(
            layer_name,
            paths,
            closing_lines,
            ov,
            use_alpha_shape=use_alpha_shape,
            bridge_strategy=bridge_strategy,
        )
        report.fills.append(result)
        if polys and should_inject_fill(result):
            report.polygons[layer_name] = [
                [[round(x, 4), round(y, 4)] for x, y in p.exterior.coords] for p in polys
            ]
    return report


# ---------------------------------------------------------------------------- #
# JSX dump + apply
# ---------------------------------------------------------------------------- #

DUMP_JSX_TEMPLATE = r"""#target illustrator

(function () {
    var TARGET = "__TARGET__";
    var OUT = "__OUT__";

    function jsonEscape(s) {
        s = String(s); var out = '"';
        for (var i = 0; i < s.length; i++) {
            var c = s.charAt(i), code = s.charCodeAt(i);
            if (c === '\\') out += '\\\\';
            else if (c === '"') out += '\\"';
            else if (c === '\n') out += '\\n';
            else if (c === '\r') out += '\\r';
            else if (code < 0x20) out += '\\u' + ('0000' + code.toString(16)).slice(-4);
            else out += c;
        }
        return out + '"';
    }

    function shouldDump(name) {
        var n = String(name).toUpperCase();
        if (n.indexOf("__POCHE_CLOSE__") !== -1) return true;
        if (n.indexOf("CLIPPINGPLANEINTERSECTIONS") === -1) return false;
        if (n.indexOf("GLASS") !== -1 || n.indexOf("IGU") !== -1) return false;
        return true;
    }

    var doc = null;
    for (var di = 0; di < app.documents.length; di++) {
        try { if (app.documents[di].fullName.fsName === TARGET) { doc = app.documents[di]; break; } } catch (e) {}
    }
    if (!doc) { return; }

    var leaves = [];
    function visit(layer, prefix) {
        var fullName = prefix ? (prefix + "::" + layer.name) : layer.name;
        if (layer.layers.length > 0) {
            for (var s = 0; s < layer.layers.length; s++) visit(layer.layers[s], fullName);
        } else {
            leaves.push({layer: layer, fullName: fullName});
        }
    }
    for (var L = 0; L < doc.layers.length; L++) visit(doc.layers[L], "");

    var json = "{"; var first = true;
    for (var i = 0; i < leaves.length; i++) {
        var meta = leaves[i];
        if (!shouldDump(meta.fullName)) continue;
        if (!first) json += ","; first = false;
        json += "\n  " + jsonEscape(meta.fullName) + ": [";
        var paths = meta.layer.pathItems;
        for (var p = 0; p < paths.length; p++) {
            var pi = paths[p];
            var pts = pi.pathPoints;
            var pathArr = "[";
            for (var pp = 0; pp < pts.length; pp++) {
                if (pp > 0) pathArr += ",";
                var a = pts[pp].anchor;
                pathArr += "[" + a[0].toFixed(4) + "," + a[1].toFixed(4) + "]";
            }
            pathArr += "]";
            if (p > 0) json += ",";
            json += "\n    " + pathArr;
        }
        json += "\n  ]";
    }
    json += "\n}";

    var f = new File(OUT); f.encoding = "UTF-8"; f.open("w"); f.write(json); f.close();
})();
"""


APPLY_JSX_TEMPLATE = r"""#target illustrator

(function () {
    var TARGET = "__TARGET__";
    var OUTPUT = "__OUTPUT__";
    var REPORT = "__REPORT__";

    try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch (e) {}

    function writeFile(p, s) { var f = new File(p); f.encoding = "UTF-8"; f.open("w"); f.write(s); f.close(); }

__POLYGONS_BAKED__

    var doc = null;
    for (var di = 0; di < app.documents.length; di++) {
        try { if (app.documents[di].fullName.fsName === TARGET) { doc = app.documents[di]; break; } } catch (e) {}
    }
    if (!doc) { writeFile(REPORT, "ERROR: target doc not open: " + TARGET); return; }
    if (app.activeDocument !== doc) app.activeDocument = doc;

    var BLACK = new RGBColor(); BLACK.red = 0; BLACK.green = 0; BLACK.blue = 0;

    var layerByName = {};
    function visit(layer, prefix) {
        var fullName = prefix ? (prefix + "::" + layer.name) : layer.name;
        layerByName[fullName] = layer;
        for (var s = 0; s < layer.layers.length; s++) visit(layer.layers[s], fullName);
    }
    for (var L = 0; L < doc.layers.length; L++) visit(doc.layers[L], "");

    var totalCreated = 0;
    var totalHatch = 0;
    var perLayer = [];
    for (var name in POLYGONS) {
        var lyr = layerByName[name];
        if (!lyr) { perLayer.push(name + " :: NO MATCHING LAYER"); continue; }
        var polys = POLYGONS[name];
        var created = 0;
        for (var pi = 0; pi < polys.length; pi++) {
            try {
                var coords = polys[pi];
                if (coords.length < 3) continue;
                var pts = coords;
                if (pts.length > 2 && pts[0][0] === pts[pts.length-1][0] && pts[0][1] === pts[pts.length-1][1]) {
                    pts = pts.slice(0, pts.length - 1);
                }
                var newPath = lyr.pathItems.add();
                newPath.setEntirePath(pts);
                newPath.closed = true;
                newPath.filled = true;
                newPath.fillColor = BLACK;
                newPath.stroked = false;
                created++;
            } catch (e) {}
        }
        totalCreated += created;
        // hatch lines on top of fill
        var hatchCount = 0;
        if (typeof HATCH !== "undefined" && HATCH[name]) {
            var hlines = HATCH[name];
            for (var hi = 0; hi < hlines.length; hi++) {
                try {
                    var hpts = hlines[hi];
                    if (hpts.length < 2) continue;
                    var hpath = lyr.pathItems.add();
                    hpath.setEntirePath(hpts);
                    hpath.closed = false;
                    hpath.filled = false;
                    hpath.stroked = true;
                    hpath.strokeColor = BLACK;
                    hpath.strokeWidth = 0.13;
                    hatchCount++;
                } catch (e) {}
            }
            totalHatch += hatchCount;
        }
        perLayer.push(name.split("::").pop() + "  +" + created + " polys" + (hatchCount > 0 ? " +" + hatchCount + " hatch" : ""));
    }

    var saveFile = new File(OUTPUT);
    var saveOpts = new IllustratorSaveOptions();
    saveOpts.pdfCompatible = true;
    doc.saveAs(saveFile, saveOpts);

    var rep = "POCHE DONE\nnew filled polys created: " + totalCreated + "\nhatch lines created: " + totalHatch + "\nper layer:\n";
    for (var i = 0; i < perLayer.length; i++) rep += "  " + perLayer[i] + "\n";
    rep += "saved as: " + OUTPUT + "\n";
    writeFile(REPORT, rep);
})();
"""


def _bake_polygons_jsx(polygons: dict) -> str:
    """Convert polygon dict to a JSX-compatible JS object literal."""

    def js_str(s: str) -> str:
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'

    parts = ["var POLYGONS = {"]
    items = list(polygons.items())
    for i, (layer_name, polys) in enumerate(items):
        sep = "," if i < len(items) - 1 else ""
        poly_strs = []
        for poly in polys:
            coord_strs = [f"[{x:g},{y:g}]" for x, y in poly]
            poly_strs.append("[" + ",".join(coord_strs) + "]")
        parts.append(f"  {js_str(layer_name)}: [" + ",".join(poly_strs) + f"]{sep}")
    parts.append("};")
    return "\n".join(parts)


def render_dump_jsx(target: str, out_json: str) -> str:
    return DUMP_JSX_TEMPLATE.replace("__TARGET__", target).replace("__OUT__", out_json)


def _bake_hatch_jsx(hatch_geometry: dict) -> str:
    """Convert hatch-line dict to a JSX-compatible JS object literal."""

    def js_str(s: str) -> str:
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'

    parts = ["var HATCH = {"]
    items = list(hatch_geometry.items())
    for i, (layer_name, lines) in enumerate(items):
        sep = "," if i < len(items) - 1 else ""
        line_strs = []
        for pts in lines:
            coord_strs = [f"[{x:g},{y:g}]" for x, y in pts]
            line_strs.append("[" + ",".join(coord_strs) + "]")
        parts.append(f"  {js_str(layer_name)}: [" + ",".join(line_strs) + f"]{sep}")
    parts.append("};")
    return "\n".join(parts)


def render_apply_jsx(
    target: str, output: str, report_path: str, polygons: dict, hatch_geometry: dict | None = None
) -> str:
    baked = textwrap.indent(_bake_polygons_jsx(polygons), "    ")
    hatch_baked = textwrap.indent(_bake_hatch_jsx(hatch_geometry or {}), "    ")
    full_baked = baked + "\n\n" + hatch_baked
    return (
        APPLY_JSX_TEMPLATE.replace("__TARGET__", target)
        .replace("__OUTPUT__", output)
        .replace("__REPORT__", report_path)
        .replace("__POLYGONS_BAKED__", full_baked)
    )


def _osascript_run_jsx(jsx_path: str, timeout: int = 1800) -> None:
    applescript = f'''with timeout of {timeout} seconds
        tell application "Adobe Illustrator"
            do javascript (read POSIX file "{jsx_path}" as «class utf8»)
        end tell
    end timeout'''
    subprocess.run(["osascript", "-e", applescript], check=True, timeout=timeout + 60)


def _osascript_open(path: str, timeout: int = 1800) -> None:
    applescript = f'''with timeout of {timeout} seconds
        tell application "Adobe Illustrator"
            activate
            try
                close every document saving no
            end try
            open POSIX file "{path}"
        end tell
    end timeout'''
    subprocess.run(["osascript", "-e", applescript], check=True, timeout=timeout + 60)


def _hatch_lines_for_layer(
    layer_name: str, polygons: list[list[list[float]]], scale: float
) -> list[list[list[float]]]:
    """For each polygon in `polygons`, generate material-specific hatch lines.

    Returns a list of polylines (each polyline = list of [x,y] pairs).
    Used by `--style material` to add hatch geometry on top of the solid fill.
    """
    material = material_for_layer(layer_name)
    out_lines: list[list[list[float]]] = []
    for poly_coords in polygons:
        if len(poly_coords) < 3:
            continue
        poly = _ShPolygon(poly_coords)
        if not poly.is_valid or poly.is_empty:
            continue
        lines = hatch_polygon(poly, material, scale)
        for ls in lines:
            try:
                out_lines.append([[round(x, 4), round(y, 4)] for x, y in ls.coords])
            except Exception:
                continue
    return out_lines


def apply_poche(
    src: str,
    dst: str | None = None,
    *,
    overrides_path: str | None = None,
    style: str = "solid",
    scale: float = 1 / 50,
    workdir: str = "/tmp",
    use_alpha_shape: bool = True,
    bridge_strategy: str | None = None,
    geometry_report_path: str | None = None,
) -> PocheReport:
    """Run the full poché pipeline on `src`, save to `dst`.

    style:
        "solid"    — every cut polygon filled solid black (default; v0.4 behavior)
        "material" — also generate per-material hatch geometry (concrete diagonal,
                     CLT cross-grain, etc.) layered on top of the solid fills.
                     Uses `arch_line_weights.hatch.material_for_layer` to choose.
    scale:
        Plot scale as a fraction (1/50, 1/100). Used only when style="material".
    use_alpha_shape:
        When True (v0.5.2 default), the alpha-shape rung sits between
        auto_bridge and concave_hull in the rescue ladder. When False,
        the ladder reverts to v0.5.1 behavior.
    bridge_strategy:
        ``"best"`` (default if unset since v0.6.7) | ``"greedy"``. Controls
        which bridger the auto_bridge rung uses; ``"best"`` runs the 4-way
        strategy selector (greedy, backtrack, DBSCAN, DBSCAN+backtrack) and
        picks the highest yield. ``"greedy"`` preserves the v0.4 nearest-
        neighbour bridger for backwards compatibility. ``None`` consults
        ``ARCH_LW_BRIDGE_STRATEGY`` env var, then defaults.
    """
    src = os.path.abspath(src)
    if dst is None:
        p = Path(src)
        dst = str(p.with_name(f"{p.stem.replace(' HIERARCHY', '')} POCHE{p.suffix}"))
    dst = os.path.abspath(dst)
    if dst == src:
        raise ValueError("dst must differ from src")

    overrides = {}
    if overrides_path:
        with open(overrides_path) as f:
            overrides = json.load(f)

    geom_json = os.path.join(workdir, "arch_lw_cut_geometry.json")
    dump_jsx = os.path.join(workdir, "arch_lw_dump.jsx")
    apply_jsx = os.path.join(workdir, "arch_lw_apply_poche.jsx")
    report_txt = os.path.join(workdir, "arch_lw_poche_report.txt")

    for f in (geom_json, dump_jsx, apply_jsx, report_txt):
        with contextlib.suppress(FileNotFoundError):
            os.unlink(f)

    # 1. Open source clean
    _osascript_open(src)
    time.sleep(2)

    # 2. Dump geometry
    Path(dump_jsx).write_text(render_dump_jsx(src, geom_json))
    _osascript_run_jsx(dump_jsx)
    if not os.path.exists(geom_json):
        raise RuntimeError(f"dump JSX produced no geometry at {geom_json}")

    # 3. Polygonize
    report = polygonize_dump(
        geom_json,
        overrides,
        use_alpha_shape=use_alpha_shape,
        bridge_strategy=bridge_strategy,
    )
    if geometry_report_path:
        from .run_report import build_poche_geometry_report

        with open(geom_json) as f:
            paths_by_layer = json.load(f)
        geometry_report = build_poche_geometry_report(
            source={
                "style": style,
                "scale": scale,
                "bridge_strategy": _resolve_bridge_strategy(bridge_strategy),
                "min_inject_confidence": _env_float(
                    _POCHE_MIN_INJECT_CONFIDENCE_ENV,
                    _DEFAULT_POCHE_MIN_INJECT_CONFIDENCE,
                ),
            },
            paths_by_layer=paths_by_layer,
            poche_report=report,
            redact_layer_names=True,
        )
        geometry_path = Path(geometry_report_path)
        geometry_path.parent.mkdir(parents=True, exist_ok=True)
        geometry_path.write_text(json.dumps(geometry_report, indent=2, sort_keys=True) + "\n")

    # 4a. Optional: generate per-material hatch geometry on top of the fills
    hatch_geometry: dict[str, list[list[list[float]]]] = {}
    if style == "material" and report.polygons:
        for layer_name, polys in report.polygons.items():
            hatch_lines = _hatch_lines_for_layer(layer_name, polys, scale)
            if hatch_lines:
                hatch_geometry[layer_name] = hatch_lines

    # 4b. Build apply JSX
    Path(apply_jsx).write_text(render_apply_jsx(src, dst, report_txt, report.polygons, hatch_geometry))

    # 5. Apply
    _osascript_run_jsx(apply_jsx)
    if not os.path.exists(report_txt):
        raise RuntimeError(f"apply JSX produced no report at {report_txt}")

    return report
