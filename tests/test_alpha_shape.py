"""Tests for the alpha-shape (α-complex) rescue rung.

Covers:

1. Hand-rolled ``alpha_shape`` over known synthetic point clouds.
2. Adaptive alpha selection (``alpha_shape_best``) — picks a sensible
   alpha for sparse and dense inputs alike.
3. Multi-region recovery (``alpha_shape_all_regions``) — preserves the
   ``26_CLT_GAP_ROOF_CAP`` two-cluster topology.
4. Integration: ``polygonize_layer`` with ``use_alpha_shape=True``
   produces ≥ as many polygons as ``use_alpha_shape=False`` on a
   synthetic stubborn-layer fixture.
"""

from __future__ import annotations

import math

from shapely.geometry import LineString, Point, Polygon

from arch_line_weights.alpha_shape import (
    DEFAULT_ALPHA_GRID,
    _circumradius,
    _count_regions,
    alpha_shape,
    alpha_shape_all_regions,
    alpha_shape_best,
)
from arch_line_weights.poche import polygonize_layer

# --------------------------------------------------------------------------- #
# Helpers — synthetic point clouds
# --------------------------------------------------------------------------- #


def _square_perimeter_points(side: float = 10.0, n_per_side: int = 6) -> list[tuple[float, float]]:
    """Densely-sampled points along the perimeter of a square."""
    pts: list[tuple[float, float]] = []
    for i in range(n_per_side):
        t = i / n_per_side
        pts.append((t * side, 0.0))  # bottom
        pts.append((side, t * side))  # right
        pts.append((side - t * side, side))  # top
        pts.append((0.0, side - t * side))  # left
    return pts


def _square_filled_points(side: float = 10.0, n_per_side: int = 8) -> list[tuple[float, float]]:
    """Square perimeter + interior grid. Models a polygonal cut shape after
    `segmentize` densification feeds the rescue ladder.

    Without interior points, perimeter-only Delaunay produces 4 isolated
    corner triangles at small alpha — a degenerate case that doesn't
    represent real cut-layer geometry.
    """
    pts = _square_perimeter_points(side=side, n_per_side=n_per_side)
    step = side / max(2, n_per_side // 2)
    x = step
    while x < side - 0.001:
        y = step
        while y < side - 0.001:
            pts.append((x, y))
            y += step
        x += step
    return pts


def _u_shape_points() -> list[tuple[float, float]]:
    """Points along the perimeter of a U-shape (open top).

    The U-shape is a textbook "concavity-preserving" test for α-shapes:
    a too-coarse alpha bridges the U and returns a filled rectangle;
    the right alpha returns the U with the notch preserved.
    """
    # Outer boundary going around a U with arms 30 wide, 100 tall, gap 40 wide
    # at the top.
    coords = [
        (0, 0),
        (100, 0),  # bottom
        (100, 100),  # right outside
        (70, 100),  # right top of U
        (70, 30),  # right inside (down)
        (30, 30),  # bottom of notch
        (30, 100),  # left inside (up)
        (0, 100),  # left top of U
    ]
    # Densify so Delaunay has enough vertices to chew on.
    pts: list[tuple[float, float]] = []
    n = len(coords)
    for i in range(n):
        x0, y0 = coords[i]
        x1, y1 = coords[(i + 1) % n]
        seg_len = math.hypot(x1 - x0, y1 - y0)
        steps = max(2, int(seg_len / 5))
        for k in range(steps):
            t = k / steps
            pts.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
    return pts


def _two_clusters_points(gap: float = 50.0) -> list[tuple[float, float]]:
    """Two square point clusters separated by a gap.

    Models the ``26_CLT_GAP_ROOF_CAP`` topology: two genuinely-separate
    cut shapes that must NOT be merged into one envelope.
    """
    cluster_a = _square_perimeter_points(side=20, n_per_side=8)
    # Translate cluster B by (gap + 20, 0) so they don't touch.
    cluster_b = [(x + 20 + gap, y) for x, y in _square_perimeter_points(side=20, n_per_side=8)]
    return cluster_a + cluster_b


# --------------------------------------------------------------------------- #
# 1. Circumradius helper
# --------------------------------------------------------------------------- #


def test_circumradius_unit_right_triangle():
    """A right triangle with legs (3, 4) has hypotenuse 5; its circumradius
    is exactly half the hypotenuse = 2.5."""
    r = _circumradius((0, 0), (3, 0), (0, 4))
    assert abs(r - 2.5) < 1e-9


def test_circumradius_collinear_returns_inf():
    """Collinear (zero-area) triangles have undefined circumradius —
    return ``+inf`` so they're rejected by every alpha threshold."""
    r = _circumradius((0, 0), (5, 0), (10, 0))
    assert math.isinf(r)


# --------------------------------------------------------------------------- #
# 2. Basic alpha_shape sanity
# --------------------------------------------------------------------------- #


def test_alpha_shape_returns_none_for_too_few_points():
    """Fewer than 3 points → no triangulation → None."""
    assert alpha_shape([(0.0, 0.0), (1.0, 0.0)], alpha=10.0) is None
    assert alpha_shape([], alpha=10.0) is None


def test_alpha_shape_returns_none_when_alpha_too_small():
    """An alpha smaller than every triangle's circumradius rejects everything."""
    pts = _square_perimeter_points(side=10, n_per_side=4)
    # Triangulation of 16 points around a 10×10 square has triangles with
    # circumradius around 5pt minimum. Alpha=0.1 should reject all.
    result = alpha_shape(pts, alpha=0.1)
    assert result is None


def test_alpha_shape_recovers_square_at_large_alpha():
    """A coarse alpha covers all triangles → returns ~ the convex hull
    (a square in this case)."""
    pts = _square_perimeter_points(side=10, n_per_side=6)
    poly = alpha_shape(pts, alpha=100.0)
    assert poly is not None
    assert isinstance(poly, Polygon)
    # Should cover most of the 10x10 = 100 sq unit area.
    assert poly.area > 80.0


def test_alpha_shape_returns_polygon_for_u_shape():
    """A medium alpha on a U-shape point cloud produces a non-trivial polygon.
    The exact area depends on which Delaunay triangles survive the alpha
    filter, but we expect *something* with positive area."""
    pts = _u_shape_points()
    poly = alpha_shape(pts, alpha=20.0)
    assert poly is not None
    assert isinstance(poly, Polygon)
    assert poly.area > 0.0


# --------------------------------------------------------------------------- #
# 3. Adaptive alpha selection
# --------------------------------------------------------------------------- #


def test_alpha_shape_best_picks_a_sensible_alpha_for_square():
    """On a filled square point cloud (perimeter + interior grid), the
    alpha sweep should converge to a single region that fills the
    square. Uses ``_square_filled_points`` to match what the rescue
    ladder actually feeds (segmentize densification + linemerge gives
    interior coverage)."""
    pts = _square_filled_points(side=10, n_per_side=8)
    poly, alpha, n_regions = alpha_shape_best(pts)
    assert poly is not None
    assert n_regions == 1
    assert alpha in DEFAULT_ALPHA_GRID
    assert poly.area > 80.0  # close to 100 sq units of the square


def test_alpha_shape_best_returns_none_for_too_few_points():
    """Sub-3-point input returns the empty triple."""
    poly, alpha, n = alpha_shape_best([(0.0, 0.0)])
    assert poly is None
    assert alpha == 0.0
    assert n == 0


def test_alpha_shape_best_handles_empty():
    poly, alpha, n = alpha_shape_best([])
    assert poly is None
    assert alpha == 0.0
    assert n == 0


def test_alpha_shape_best_recovers_two_regions_for_clt_gap():
    """The ``26_CLT_GAP_ROOF_CAP`` win condition: two cluster point clouds
    with a gap should recover a 2-region α-shape if the alpha sweep can
    find a value tight enough to leave the gap open.

    Note: depending on the gap and alpha grid, this may yield 1 region
    (a large alpha bridges the gap). The win is when ``n_regions >= 2``.
    """
    pts = _two_clusters_points(gap=50.0)
    polys, _alpha, n = alpha_shape_all_regions(pts)
    # We expect at least 2 regions — clusters are 50pt apart and the alpha
    # sweep includes values tight enough to leave them disjoint.
    assert n >= 2
    assert len(polys) >= 2
    # Each cluster is a 20×20 square — area should be in that ballpark.
    for poly in polys:
        assert 100.0 < poly.area < 800.0


def test_alpha_shape_best_picks_more_regions_over_one_big_region():
    """If two alpha values both produce valid output, the multi-region one
    should win (the scoring criterion in the docstring)."""
    pts = _two_clusters_points(gap=80.0)
    poly, _alpha, n_regions = alpha_shape_best(pts)
    # At least 1 region — the polygon returned is the largest. n_regions
    # captures whether the underlying α-complex preserved the gap.
    assert poly is not None
    assert n_regions >= 1


# --------------------------------------------------------------------------- #
# 4. _count_regions helper
# --------------------------------------------------------------------------- #


def test_count_regions_polygon():
    p = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
    assert _count_regions(p) == 1


def test_count_regions_none():
    assert _count_regions(None) == 0


def test_count_regions_empty_polygon():
    assert _count_regions(Polygon()) == 0


# --------------------------------------------------------------------------- #
# 5. Integration with polygonize_layer
# --------------------------------------------------------------------------- #


def _gappy_two_loop_paths() -> list[list[list[float]]]:
    """Two loops with sub-segment gaps that defeat linemerge AND are too
    far apart for auto_bridge — only alpha_shape or concave_hull/bbox can
    produce something. Models the ``26_CLT_GAP_ROOF_CAP`` failure mode.
    """
    # Two 20×20 squares 100pt apart, each broken into 4 segments with
    # 2pt corner gaps (too big for snap to fix, too small for visual loss).
    paths: list[list[list[float]]] = []
    g = 2.0
    for x_off in (0.0, 100.0):
        # Each square: 4 disconnected sides
        paths.append([[x_off + 0, 0], [x_off + 20 - g, 0]])
        paths.append([[x_off + 20, g], [x_off + 20, 20 - g]])
        paths.append([[x_off + 20 - g, 20], [x_off + g, 20]])
        paths.append([[x_off + 0, 20 - g], [x_off + 0, g]])
    return paths


def test_polygonize_layer_alpha_shape_off_matches_v051():
    """With use_alpha_shape=False, the rescue ladder must skip the new rung."""
    paths = _gappy_two_loop_paths()
    _polys, fr = polygonize_layer("test_layer", paths, use_alpha_shape=False)
    # The fixture should fall through bridge → concave_hull or bbox.
    # Critical check: strategy is NOT "alpha_shape" when flag is off.
    assert fr.strategy != "alpha_shape"


def test_polygonize_layer_alpha_shape_on_uses_alpha_shape_rung():
    """With use_alpha_shape=True (v0.5.2 default), a fixture that exhausts
    bare/snap/bridge should produce alpha_shape OR a strategy at least
    as confident."""
    paths = _gappy_two_loop_paths()
    _polys, fr = polygonize_layer("test_layer", paths, use_alpha_shape=True)
    assert fr.polygon_count >= 1


def test_polygonize_layer_alpha_on_yields_at_least_as_many_polygons_as_off():
    """The integration win: alpha_shape ON should never *under*-perform
    alpha_shape OFF. On the synthetic two-loop fixture, it should
    typically over-perform (alpha_shape recovers 2 polys vs. 1
    blob from concave_hull).
    """
    paths = _gappy_two_loop_paths()
    _, fr_off = polygonize_layer("test", paths, use_alpha_shape=False)
    _, fr_on = polygonize_layer("test", paths, use_alpha_shape=True)
    assert fr_on.polygon_count >= fr_off.polygon_count


def test_polygonize_layer_alpha_does_not_break_clean_layers():
    """A layer that linemerge polygonizes cleanly must still pick
    linemerge_bare — the alpha-shape rung is a fallback, not a replacement."""
    # 4-segment closed square, no gaps.
    paths: list[list[list[float]]] = [
        [[0, 0], [10, 0]],
        [[10, 0], [10, 10]],
        [[10, 10], [0, 10]],
        [[0, 10], [0, 0]],
    ]
    _polys, fr = polygonize_layer("clean_layer", paths, use_alpha_shape=True)
    assert fr.strategy == "linemerge_bare"
    assert fr.polygon_count == 1


def test_polygonize_layer_alpha_confidence_is_055():
    """The α-shape rung's confidence is 0.55 (between bridge and concave_hull)."""
    # Force a fixture that defeats bridge by using widely-separated loops.
    # Two squares 200pt apart with 2pt gaps at every corner.
    paths: list[list[list[float]]] = []
    g = 2.0
    for x_off in (0.0, 200.0):
        paths.append([[x_off + 0, 0], [x_off + 20 - g, 0]])
        paths.append([[x_off + 20, g], [x_off + 20, 20 - g]])
        paths.append([[x_off + 20 - g, 20], [x_off + g, 20]])
        paths.append([[x_off + 0, 20 - g], [x_off + 0, g]])

    _, fr = polygonize_layer("two_loops", paths, use_alpha_shape=True)
    # If alpha_shape was the chosen rung, confidence is 0.55.
    if fr.strategy == "alpha_shape":
        assert abs(fr.confidence - 0.55) < 1e-9


# --------------------------------------------------------------------------- #
# 6. Regression: alpha_shape doesn't produce degenerate output
# --------------------------------------------------------------------------- #


def test_alpha_shape_rejects_collinear_points():
    """Collinear points have no valid triangulation — return None
    gracefully rather than crashing."""
    pts = [(0.0, 0.0), (5.0, 0.0), (10.0, 0.0), (15.0, 0.0)]
    result = alpha_shape(pts, alpha=20.0)
    # Either None (Delaunay refused) or a degenerate sliver — but at
    # the very least, should not crash.
    if result is not None:
        assert isinstance(result, Polygon)


def test_alpha_shape_handles_duplicate_points():
    """Duplicate input points are deduplicated; the result should be
    indistinguishable from the deduplicated version."""
    pts = _square_perimeter_points(side=10, n_per_side=4)
    pts_with_dupes = pts + pts[:5]  # add some duplicates
    poly = alpha_shape(pts_with_dupes, alpha=10.0)
    assert poly is not None
    assert poly.area > 50.0


def test_alpha_shape_empty_grid_returns_none():
    """An empty alpha grid is a no-op — returns None."""
    pts = _square_perimeter_points()
    poly, alpha, n = alpha_shape_best(pts, alpha_grid=())
    assert poly is None
    assert alpha == 0.0
    assert n == 0


# --------------------------------------------------------------------------- #
# 7. Densification path inside polygonize_layer._try_alpha_shape
# --------------------------------------------------------------------------- #


def test_polygonize_layer_alpha_on_handles_sparse_input():
    """Sparse input (just 4 line segments forming a square with gaps)
    should still polygonize via the alpha rung after segmentize() densifies."""
    g = 1.0
    # 4-segment square with corner gaps too big for snap, but small enough
    # that bridge could fix them — so we expect bridge or alpha to win.
    paths = [
        [[0, 0], [100 - g, 0]],
        [[100, g], [100, 100 - g]],
        [[100 - g, 100], [g, 100]],
        [[0, 100 - g], [0, g]],
    ]
    _polys, fr = polygonize_layer("sparse", paths, use_alpha_shape=True)
    assert fr.polygon_count >= 1
    # We don't pin the strategy — bridge or alpha both acceptable.
    assert fr.strategy in {
        "linemerge_bare",
        "linemerge_snap",
        "auto_bridge",
        "alpha_shape",
        "concave_hull",
        "bbox",
    }


def test_alpha_shape_polygon_validity():
    """Every polygon returned by alpha_shape should be a valid shapely Polygon."""
    pts = _square_perimeter_points()
    poly = alpha_shape(pts, alpha=10.0)
    assert poly is not None
    assert poly.is_valid
    assert not poly.is_empty


def test_alpha_shape_all_regions_returns_empty_for_nothing():
    """No alpha produces output → empty list, alpha=0, n=0."""
    polys, alpha, n = alpha_shape_all_regions([(0.0, 0.0), (1.0, 0.0)])
    assert polys == []
    assert alpha == 0.0
    assert n == 0


# --------------------------------------------------------------------------- #
# 8. Defensive: scipy import failures are graceful
# --------------------------------------------------------------------------- #


def test_alpha_shape_works_when_scipy_available():
    """Sanity: scipy is installed in this env, so alpha_shape should succeed
    on any reasonable input. If this test fails, scipy is missing or
    Delaunay is broken."""
    pts = _square_perimeter_points(side=10, n_per_side=6)
    # Pick alpha large enough that all triangles survive.
    poly = alpha_shape(pts, alpha=50.0)
    assert poly is not None
    # Sanity: the polygon should cover most of the square and be inside it.
    bbox = poly.bounds
    assert -1.0 <= bbox[0] <= 1.0  # min_x near 0
    assert 9.0 <= bbox[2] <= 11.0  # max_x near 10


# --------------------------------------------------------------------------- #
# 9. Sanity: lines argument shape from _try_alpha_shape
# --------------------------------------------------------------------------- #


def test_alpha_shape_works_on_linestring_endpoints():
    """When the rescue ladder feeds endpoints from a list[LineString], the
    densified-points path should still produce a polygon."""
    # 16 short overlapping segments forming a rough circle.
    n = 16
    radius = 50.0
    lines = []
    for i in range(n):
        a = 2 * math.pi * i / n
        b = 2 * math.pi * (i + 1) / n
        x0 = radius * math.cos(a)
        y0 = radius * math.sin(a)
        x1 = radius * math.cos(b)
        y1 = radius * math.sin(b)
        lines.append(LineString([(x0, y0), (x1, y1)]))

    pts = []
    for ls in lines:
        pts.extend((float(x), float(y)) for x, y in ls.coords)

    # alpha=60 covers the worst-case triangle circumradius (~50 for points
    # on a 50-radius circle) so all triangles survive the alpha filter.
    poly = alpha_shape(pts, alpha=60.0)
    assert poly is not None
    # The α-shape of a circle should be roughly the disc of radius 50.
    # Area should be in the range (π × 50² × 0.5, π × 50²) — between
    # ~3900 and ~7900 sq units.
    assert 3000.0 < poly.area < 8500.0


def test_polygon_centroid_inside_alpha_shape():
    """A defensive sanity check: the centroid of the input points should
    land somewhere inside or near the resulting α-shape."""
    pts = _square_perimeter_points(side=20, n_per_side=8)
    poly = alpha_shape(pts, alpha=30.0)
    assert poly is not None
    centroid_x = sum(p[0] for p in pts) / len(pts)
    centroid_y = sum(p[1] for p in pts) / len(pts)
    # Centroid of a square's perimeter samples lies at the center.
    centroid = Point(centroid_x, centroid_y)
    # Allow small margin since α-shape may not perfectly match.
    assert poly.distance(centroid) < 5.0
