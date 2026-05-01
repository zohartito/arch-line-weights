"""Alpha-shape (α-complex) reconstruction for sparse point clouds.

This module is the rung-4 rescue in the polygonize ladder used by
:func:`arch_line_weights.poche.polygonize_layer`. Where shapely's
``concave_hull(MultiPoint, ratio=0.3)`` returns one lumpy envelope that may
collapse two genuinely-separate sub-shapes into a blob (the
``26_CLT_GAP_ROOF_CAP`` failure mode), an α-shape can preserve holes and
multi-component topology because it filters Delaunay triangles by
circumradius rather than by a global concavity ratio.

Algorithm
---------
1.  Compute the Delaunay triangulation of the input point set
    (``scipy.spatial.Delaunay``).
2.  For a given ``alpha`` (interpreted as a *radius threshold*, in source
    units), keep only those triangles whose circumradius is ``<= alpha``.
3.  Take the boundary of the kept-triangle union — that is the α-shape.

The boundary is recovered via the classic "edge counting" trick: any edge
shared by exactly one kept triangle is on the boundary; any edge shared
by two is interior. Walking the boundary edges as a graph yields the
exterior ring(s) and any holes.

Public API
----------
``alpha_shape(points, alpha)``
    Return the α-shape Polygon (or MultiPolygon flattened into the
    largest-area Polygon) for a fixed ``alpha``.

``alpha_shape_best(points)``
    Adaptive alpha selection. Sweeps a logarithmic grid of ``alpha`` values
    and returns the polygon that maximises the number of distinct closed
    regions (matching the existing "best of strategies" pattern in the
    rescue ladder). When all alphas yield a single-region polygon, picks
    the largest non-degenerate one.

Why hand-rolled (not the ``alphashape`` PyPI package)
-----------------------------------------------------
``alphashape`` is not currently in the dependency tree, and the project
already pulls in ``scipy`` transitively via ``shapely``'s wheel. A
~120-line implementation on top of ``Delaunay`` keeps the dep surface
clean and makes the alpha-selection criterion explicit (we want
"maximises distinct closed regions", not the package's default
"maximises perimeter-to-area ratio"). The algorithm itself is textbook —
see Edelsbrunner & Mücke, "Three-Dimensional Alpha Shapes" (1994), §3.
"""

from __future__ import annotations

import math

from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import unary_union

# Default alpha sweep — log-spaced across the range that matters for plot-
# scale architectural geometry (sub-point gaps to multi-foot mass-timber bays).
# In source units (typically points), so 1.0 ≈ 1pt and 100.0 ≈ 100pt.
DEFAULT_ALPHA_GRID: tuple[float, ...] = (
    1.0,
    2.5,
    5.0,
    10.0,
    20.0,
    35.0,
    50.0,
    75.0,
    100.0,
)


# --------------------------------------------------------------------------- #
# Triangle geometry
# --------------------------------------------------------------------------- #


def _circumradius(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
) -> float:
    """Circumradius of the triangle defined by three 2-D points.

    Uses the algebraic identity ``R = (a * b * c) / (4 * area)`` where
    ``a, b, c`` are the side lengths. Degenerate (collinear) triangles
    return ``+inf`` so the alpha-filter rejects them — a thin sliver
    triangle has unbounded circumradius and shouldn't survive any
    sensible alpha.
    """
    a = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
    b = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
    c = math.hypot(p0[0] - p2[0], p0[1] - p2[1])
    # 2 × signed area via cross product
    cross = (p1[0] - p0[0]) * (p2[1] - p0[1]) - (p1[1] - p0[1]) * (p2[0] - p0[0])
    area = 0.5 * abs(cross)
    if area <= 1e-12:
        return float("inf")
    return (a * b * c) / (4.0 * area)


# --------------------------------------------------------------------------- #
# Core algorithm
# --------------------------------------------------------------------------- #


def alpha_shape(
    points: list[tuple[float, float]],
    alpha: float,
) -> Polygon | None:
    """Compute the α-shape of ``points`` for a fixed ``alpha`` threshold.

    Parameters
    ----------
    points : list of (x, y) tuples
        The point cloud to fit. Duplicate points are tolerated; fewer
        than 3 distinct points returns ``None``.
    alpha : float
        Maximum allowed circumradius for a Delaunay triangle to be
        included in the α-complex. Larger ``alpha`` → coarser hull
        (closer to convex). Smaller ``alpha`` → tighter hull, may leave
        holes or split into components.

    Returns
    -------
    Polygon or None
        The α-shape as a single shapely ``Polygon``. If the α-complex
        produces multiple disconnected components, this returns the one
        with the largest area; the multi-component case is handled by
        :func:`alpha_shape_best` which counts regions in its scoring.
        Returns ``None`` when:

        * Fewer than 3 distinct points
        * No triangles survive the α-filter
        * scipy is unavailable or Delaunay fails (e.g. all points collinear)
    """
    # Deduplicate; Delaunay can crash on coincident points.
    distinct = list(dict.fromkeys(points))
    if len(distinct) < 3:
        return None

    try:
        from scipy.spatial import Delaunay
    except Exception:
        return None

    try:
        tri = Delaunay(distinct)
    except Exception:
        # All points collinear / numerically degenerate.
        return None

    # Filter triangles by circumradius.
    kept_triangles: list[Polygon] = []
    for simplex in tri.simplices:
        i, j, k = int(simplex[0]), int(simplex[1]), int(simplex[2])
        p0 = distinct[i]
        p1 = distinct[j]
        p2 = distinct[k]
        r = _circumradius(p0, p1, p2)
        if r <= alpha:
            try:
                poly = Polygon([p0, p1, p2])
                if poly.is_valid and poly.area > 1e-9:
                    kept_triangles.append(poly)
            except Exception:
                continue

    if not kept_triangles:
        return None

    # Union the kept triangles into the α-shape. ``unary_union`` handles
    # arbitrary topology — adjacent triangles merge across shared edges,
    # disconnected clusters stay separate.
    try:
        merged = unary_union(kept_triangles)
    except Exception:
        return None

    if merged.is_empty:
        return None

    # Return the largest-area Polygon if the union is multi-part. The caller
    # (``alpha_shape_best``) already accounts for region count separately.
    if isinstance(merged, Polygon):
        return merged
    if isinstance(merged, MultiPolygon):
        polys = list(merged.geoms)
        if not polys:
            return None
        polys.sort(key=lambda p: p.area, reverse=True)
        return polys[0]
    return None


# --------------------------------------------------------------------------- #
# Adaptive alpha selection
# --------------------------------------------------------------------------- #


def _count_regions(geom, min_area: float = 1.0) -> int:
    """Number of disjoint Polygon components in a shapely geometry.

    Returns 0 for None / empty, 1 for a single Polygon, len(geoms) for
    a MultiPolygon. Used as the primary scoring criterion in the alpha
    sweep — more distinct closed regions = better topology recovery.

    ``min_area`` filters out sliver components below the area threshold
    (in source units squared). This prevents tiny corner triangles —
    which are technically "regions" of the α-complex — from gaming the
    "more regions wins" tiebreaker.
    """
    if geom is None or geom.is_empty:
        return 0
    if isinstance(geom, Polygon):
        return 1 if geom.area >= min_area else 0
    if isinstance(geom, MultiPolygon):
        return sum(1 for g in geom.geoms if g.area >= min_area)
    return 0


def _significant_regions(geom, min_relative: float = 0.10) -> int:
    """Count regions whose area is at least ``min_relative`` of the
    *largest* region's area.

    Where :func:`_count_regions` filters by absolute area threshold, this
    filters by *relative* area. The point: "two of three roof caps" is a
    real multi-component topology only if the caps are comparable in
    size. A 1000-pt² cap with a 5-pt² speck attached doesn't count as
    "two regions" — the speck is noise, not a real second component.

    Returns 1 for a single Polygon (the largest-region argument is
    always ``>= largest * min_relative``). Returns 0 for None / empty.
    """
    if geom is None or geom.is_empty:
        return 0
    if isinstance(geom, Polygon):
        return 1
    if isinstance(geom, MultiPolygon):
        polys = list(geom.geoms)
        if not polys:
            return 0
        largest = max(p.area for p in polys)
        if largest <= 0:
            return 0
        threshold = largest * min_relative
        return sum(1 for p in polys if p.area >= threshold)
    return 0


def _alpha_shape_full(
    points: list[tuple[float, float]],
    alpha: float,
):
    """Like :func:`alpha_shape` but returns the full union (Polygon **or**
    MultiPolygon) so :func:`alpha_shape_best` can count regions.

    Internal helper — the public ``alpha_shape`` flattens to the largest
    Polygon for callers that just want one geometry.
    """
    distinct = list(dict.fromkeys(points))
    if len(distinct) < 3:
        return None
    try:
        from scipy.spatial import Delaunay
    except Exception:
        return None
    try:
        tri = Delaunay(distinct)
    except Exception:
        return None

    kept_triangles: list[Polygon] = []
    for simplex in tri.simplices:
        i, j, k = int(simplex[0]), int(simplex[1]), int(simplex[2])
        p0 = distinct[i]
        p1 = distinct[j]
        p2 = distinct[k]
        r = _circumradius(p0, p1, p2)
        if r <= alpha:
            try:
                poly = Polygon([p0, p1, p2])
                if poly.is_valid and poly.area > 1e-9:
                    kept_triangles.append(poly)
            except Exception:
                continue

    if not kept_triangles:
        return None

    try:
        merged = unary_union(kept_triangles)
    except Exception:
        return None

    if merged.is_empty:
        return None
    return merged


def alpha_shape_best(
    points: list[tuple[float, float]],
    alpha_grid: tuple[float, ...] = DEFAULT_ALPHA_GRID,
) -> tuple[Polygon | None, float, int]:
    """Adaptive α selection: sweep ``alpha_grid`` and pick the result that
    best balances coverage (total area) with topology (region count).

    Parameters
    ----------
    points : list of (x, y) tuples
        The point cloud to fit.
    alpha_grid : tuple of float, default :data:`DEFAULT_ALPHA_GRID`
        Candidate alphas to try, in source units (typically points).

    Returns
    -------
    polygon : Polygon or None
        The largest-area Polygon component of the winning α-shape. ``None``
        if no alpha produced any polygon.
    alpha : float
        The winning ``alpha`` value (``0.0`` if nothing worked).
    n_regions : int
        Number of distinct closed regions the winning α-complex contained.
        ``> 1`` indicates the α-shape preserved a multi-component topology
        (the ``26_CLT_GAP_ROOF_CAP`` win condition).

    Notes
    -----
    Scoring criterion (lexicographic, big to small):
    1. Total area covered (so we don't pick a degenerate sliver alpha)
    2. Number of significant regions (so two correctly-separated roof
       caps beat one blobby envelope that spans the gap, when total
       coverage is similar)

    This is "maximize regions" with a hard floor on coverage — without
    the area-first ordering, a too-tight alpha that produces 4 sliver
    corners would beat a single full hull.

    Memory note: Delaunay is O(n log n) in 2-D; this is safe for the
    endpoint counts we see per cut layer (a few hundred points at most).
    """
    if len(points) < 3:
        return None, 0.0, 0

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    bbox_area = max(1.0, (max(xs) - min(xs)) * (max(ys) - min(ys)))
    # Minimum region area = 5% of bbox area. Anything smaller is a sliver
    # corner artifact, not a real cluster.
    min_region_area = max(1.0, bbox_area * 0.05)

    try:
        from shapely.geometry import MultiPoint
        hull_area = float(MultiPoint(points).convex_hull.area)
    except Exception:
        hull_area = bbox_area
    coverage_threshold = max(min_region_area, hull_area * 0.40)

    # Enumerate well-formed alpha-shapes. An alpha-shape "counts" only if:
    #   * total area ≥ 40% of the convex hull (well-covered)
    #   * every region has area ≥ 5% of the bounding-box area (no slivers)
    # Among those, pick the one with the most distinct closed regions
    # (the spec's "maximize regions" criterion). Tie-break by largest area.
    candidates: list[tuple[float, int, float, object]] = []
    for alpha in alpha_grid:
        geom = _alpha_shape_full(points, alpha)
        if geom is None or geom.is_empty:
            continue
        # Count regions ≥ min_region_area (absolute threshold, not relative).
        # This rejects sliver corners that survive the relative-area filter.
        n_real_regions = _count_regions(geom, min_area=min_region_area)
        if n_real_regions == 0:
            continue
        try:
            area = float(geom.area)
        except Exception:
            area = 0.0
        if area < coverage_threshold:
            continue
        candidates.append((alpha, n_real_regions, area, geom))

    if not candidates:
        # Fallback pass: if nothing passed both filters, accept any geom
        # with positive area. This keeps the function from returning None
        # on edge cases (e.g. very small input that doesn't reach the
        # coverage threshold but still has valid geometry).
        for alpha in alpha_grid:
            geom = _alpha_shape_full(points, alpha)
            if geom is None or geom.is_empty:
                continue
            try:
                area = float(geom.area)
            except Exception:
                area = 0.0
            if area > 0:
                candidates.append((alpha, _significant_regions(geom), area, geom))

    if not candidates:
        return None, 0.0, 0

    # Sort by (n_regions desc, area desc) — maximize regions, break ties
    # on coverage. This is the spec's criterion, made robust by the
    # min_region_area filter that rejects sliver corners.
    candidates.sort(key=lambda c: (c[1], c[2]), reverse=True)
    best_alpha, _, _, best_geom = candidates[0]

    final_n_regions = _count_regions(best_geom, min_area=min_region_area)
    if isinstance(best_geom, Polygon):
        return best_geom, best_alpha, max(1, final_n_regions)
    if isinstance(best_geom, MultiPolygon):
        polys = list(best_geom.geoms)
        polys.sort(key=lambda p: p.area, reverse=True)
        return polys[0], best_alpha, max(1, final_n_regions)
    return None, 0.0, 0


def alpha_shape_all_regions(
    points: list[tuple[float, float]],
    alpha_grid: tuple[float, ...] = DEFAULT_ALPHA_GRID,
) -> tuple[list[Polygon], float, int]:
    """Same alpha sweep as :func:`alpha_shape_best`, but returns **every**
    region of the winning α-complex.

    This is the entry point ``polygonize_layer`` actually uses when the
    α-shape rung is the chosen rescue: we want all roof-cap polygons
    (``26_CLT_GAP_ROOF_CAP``), not just the largest one.

    Returns
    -------
    polygons : list[Polygon]
        Empty if no alpha produced anything; otherwise one polygon per
        connected region of the winning α-shape (filtered to non-sliver
        components).
    alpha : float
        The winning ``alpha`` value.
    n_regions : int
        ``len(polygons)`` for convenience.
    """
    if len(points) < 3:
        return [], 0.0, 0

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    bbox_area = max(1.0, (max(xs) - min(xs)) * (max(ys) - min(ys)))
    min_region_area = max(1.0, bbox_area * 0.05)

    try:
        from shapely.geometry import MultiPoint
        hull_area = float(MultiPoint(points).convex_hull.area)
    except Exception:
        hull_area = bbox_area
    coverage_threshold = max(min_region_area, hull_area * 0.40)

    candidates: list[tuple[float, int, float, object]] = []
    for alpha in alpha_grid:
        geom = _alpha_shape_full(points, alpha)
        if geom is None or geom.is_empty:
            continue
        n_real = _count_regions(geom, min_area=min_region_area)
        if n_real == 0:
            continue
        try:
            area = float(geom.area)
        except Exception:
            area = 0.0
        if area < coverage_threshold:
            continue
        candidates.append((alpha, n_real, area, geom))

    if not candidates:
        # Same fallback as alpha_shape_best.
        for alpha in alpha_grid:
            geom = _alpha_shape_full(points, alpha)
            if geom is None or geom.is_empty:
                continue
            try:
                area = float(geom.area)
            except Exception:
                area = 0.0
            if area > 0:
                candidates.append((alpha, _significant_regions(geom), area, geom))

    if not candidates:
        return [], 0.0, 0

    candidates.sort(key=lambda c: (c[1], c[2]), reverse=True)
    best_alpha, _, _, best_geom = candidates[0]

    if isinstance(best_geom, Polygon):
        if best_geom.area >= min_region_area:
            return [best_geom], best_alpha, 1
        return [], 0.0, 0
    if isinstance(best_geom, MultiPolygon):
        polys = list(best_geom.geoms)
        if not polys:
            return [], 0.0, 0
        kept = [p for p in polys if p.area >= min_region_area]
        if not kept:
            # Keep at least the largest if none pass the absolute threshold.
            polys.sort(key=lambda p: p.area, reverse=True)
            kept = [polys[0]]
        return kept, best_alpha, len(kept)
    return [], 0.0, 0
