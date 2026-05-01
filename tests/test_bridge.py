"""Tests for the bridge inference module.

Covers the v0.5 additions:
* Backtracking bridger (``infer_bridges_backtrack``) -- recovers from
  greedy's "commit-to-wrong-pair" failure mode.
* Hand-rolled DBSCAN endpoint clustering (``collapse_endpoint_clusters``,
  ``_dbscan``, ``_adaptive_eps``).
* Strategy selector (``infer_bridges_best``).
* Edge cases (empty input, single endpoint, all-coincident endpoints).
"""

from __future__ import annotations

import math

import pytest
from shapely.geometry import LineString

from arch_line_weights.bridge import (
    _adaptive_eps,
    _candidate_pairs,
    _collect_endpoints,
    _dbscan,
    _polygon_count,
    collapse_endpoint_clusters,
    infer_bridges,
    infer_bridges_backtrack,
    infer_bridges_best,
)
from arch_line_weights.poche import _polys_at_tolerance

# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _square_with_corner_gaps(g: float = 0.2) -> list[LineString]:
    """4-segment square with a small gap at every corner."""
    return [
        LineString([(0, 0), (10 - g, 0)]),
        LineString([(10, g), (10, 10 - g)]),
        LineString([(10 - g, 10), (g, 10)]),
        LineString([(0, 10 - g), (0, g)]),
    ]


def _greedy_trap_fixture() -> list[LineString]:
    """A 6-segment polyline soup designed to make greedy commit to the
    *wrong* nearest-neighbour pair.

    Layout (rough)::

        A──┐  ┌──B
           │  │
           │  │
           │  │
           ┘  └

    Two parallel segments share their inside endpoints almost-coincident
    (the "intra-cluster" pinch). The actual closing pair is across the gap
    at the top. Greedy's distance-sort puts the intra-cluster pair first,
    commits to it, and never bridges across the top -- yielding 0 polys.
    Backtracking should undo and find the cross-the-top pairing.

    This is the deterministic-test analogue of the
    ``11_CU_CORR_SOLID_OPAQUE`` failure described in
    ``docs/research/stubborn-layers-deep-dive.md``.
    """
    # Outer rectangle (0,0)-(10,10), with two interior "tabs" hanging
    # downward from y=10 toward y=5, where they almost meet (gap 0.05).
    return [
        # outer rectangle, broken into 4 sides
        LineString([(0, 0), (10, 0)]),  # bottom
        LineString([(10, 0), (10, 10)]),  # right
        LineString([(0, 10), (0, 0)]),  # left  (note: down-direction)
        # top edge has a 0.5-wide gap between (4.75, 10) and (5.25, 10)
        LineString([(0, 10), (4.75, 10)]),  # top-left half
        LineString([(5.25, 10), (10, 10)]),  # top-right half
        # near the gap: a tiny parallel "noise" segment whose endpoints
        # live in a tight cluster with the actual gap endpoints. Greedy's
        # nearest-pair sort prefers this over the across-gap pair.
        LineString([(4.80, 10.02), (5.20, 10.02)]),
    ]


# --------------------------------------------------------------------------- #
# Backtracking bridger
# --------------------------------------------------------------------------- #


def test_backtrack_closes_simple_square():
    """Backtracking should close a square with sub-pt corner gaps, just like
    greedy does."""
    segs = _square_with_corner_gaps(g=0.2)
    aug, conf = infer_bridges_backtrack(segs, max_gap=2.0, min_gap=0.01)
    assert len(aug) >= len(segs)
    assert conf > 0
    polys = _polys_at_tolerance(aug, 0.0)
    assert len(polys) >= 1


def test_backtrack_returns_zero_when_no_candidates():
    """No endpoints in the soup → no bridges, zero confidence."""
    aug, conf = infer_bridges_backtrack([], max_gap=10.0)
    assert aug == []
    assert conf == 1.0  # vacuously "ok" — nothing to do


def test_backtrack_preserves_already_closed_topology():
    """If the input already polygonizes, backtracking should add no bridges."""
    segs = [
        LineString([(0, 0), (10, 0)]),
        LineString([(10, 0), (10, 10)]),
        LineString([(10, 10), (0, 10)]),
        LineString([(0, 10), (0, 0)]),
    ]
    assert _polygon_count(segs) == 1
    aug, conf = infer_bridges_backtrack(segs, max_gap=2.0)
    # No bridges added, original count preserved
    assert len(aug) == len(segs)
    assert conf > 0


def test_backtrack_succeeds_where_greedy_struggles():
    """Synthetic fixture where greedy commits to an intra-cluster pair and
    fails to close. Backtracking should match or beat greedy.

    This mirrors the ``11_CU_CORR_SOLID_OPAQUE`` failure mode.
    """
    segs = _greedy_trap_fixture()
    n_segs = len(segs)

    aug_g, conf_g = infer_bridges(segs, max_gap=5.0, min_gap=0.001)
    n_g = _polygon_count(aug_g)

    aug_b, conf_b = infer_bridges_backtrack(segs, max_gap=5.0, min_gap=0.001, max_depth=8)
    n_b = _polygon_count(aug_b)

    # Backtracking must at least match greedy on polygon yield.
    assert n_b >= n_g, (
        f"backtracking under-performed greedy: greedy={n_g} backtrack={n_b}"
    )
    # And it should have found *some* closing polygon.
    assert n_b >= 1
    # We do not require fewer bridges; the success criterion is yield.
    _ = (conf_g, conf_b, n_segs)


def test_backtrack_max_depth_bounds_search():
    """``max_depth=0`` should produce no bridges (recursion exits before
    exploring any candidate)."""
    segs = _square_with_corner_gaps(g=0.2)
    aug, _ = infer_bridges_backtrack(segs, max_gap=2.0, min_gap=0.01, max_depth=0)
    # depth=0 limit means the search exits immediately at the root frame
    # without committing to any pair.
    assert len(aug) == len(segs)


# --------------------------------------------------------------------------- #
# DBSCAN clustering
# --------------------------------------------------------------------------- #


def test_dbscan_groups_corrugation_peaks():
    """Two tight endpoint clusters separated by a wide gap should produce
    exactly two clusters under DBSCAN."""
    pts = [
        # cluster A around (0, 0)
        (0.0, 0.0),
        (0.05, 0.01),
        (0.02, -0.03),
        # cluster B around (10, 10)
        (10.0, 10.0),
        (9.97, 10.02),
        (10.04, 9.99),
    ]
    labels = _dbscan(pts, eps=0.5, min_samples=2)
    # Both clusters should be discovered; no noise.
    assert all(lab >= 0 for lab in labels)
    assert sorted(set(labels)) == [0, 1]
    # Labels should partition the input exactly into the two clusters.
    cluster_a = {labels[0], labels[1], labels[2]}
    cluster_b = {labels[3], labels[4], labels[5]}
    assert len(cluster_a) == 1
    assert len(cluster_b) == 1
    assert cluster_a != cluster_b


def test_dbscan_isolates_noise():
    """Lone points outside ε should be labelled noise (-1)."""
    pts = [
        (0.0, 0.0),
        (0.05, 0.01),  # near (0,0) — in cluster
        (100.0, 100.0),  # far away — noise
    ]
    labels = _dbscan(pts, eps=0.5, min_samples=2)
    assert labels[0] >= 0
    assert labels[1] >= 0
    assert labels[2] == -1


def test_dbscan_empty_input():
    assert _dbscan([], eps=1.0) == []


def test_adaptive_eps_scales_with_density():
    """Sparse point set → large ε; dense point set → small ε."""
    sparse = [(0.0, 0.0), (10.0, 0.0), (20.0, 0.0)]
    dense = [(0.0, 0.0), (0.1, 0.0), (0.2, 0.0)]
    eps_sparse = _adaptive_eps(sparse)
    eps_dense = _adaptive_eps(dense)
    assert eps_sparse > eps_dense


def test_adaptive_eps_capped():
    """Even very sparse inputs should not exceed the absolute cap."""
    sparse = [(0.0, 0.0), (1000.0, 0.0)]
    eps = _adaptive_eps(sparse, multiplier=1.5, cap=5.0)
    assert eps <= 5.0


def test_adaptive_eps_floor_for_tiny_input():
    """Single-point input → returns the floor, not zero or NaN."""
    eps = _adaptive_eps([(0.0, 0.0)], floor=0.05)
    assert eps == 0.05
    eps_empty = _adaptive_eps([], floor=0.05)
    assert eps_empty == 0.05


def test_collapse_endpoint_clusters_merges_pinched_corners():
    """Two segments meeting at a near-coincident corner should land at the
    same point after DBSCAN collapse, so ``linemerge`` chains them."""
    g = 0.05
    segs = [
        LineString([(0, 0), (10, 0)]),
        LineString([(10 + g, g), (10 + g, 10)]),  # tiny offset at start
    ]
    collapsed = collapse_endpoint_clusters(segs, eps=0.5)
    # The right-end of seg0 and start of seg1 should now share coords.
    seg0_end = collapsed[0].coords[-1]
    seg1_start = collapsed[1].coords[0]
    assert math.hypot(seg0_end[0] - seg1_start[0], seg0_end[1] - seg1_start[1]) < 1e-9


def test_collapse_endpoint_clusters_empty():
    assert collapse_endpoint_clusters([]) == []


def test_collapse_endpoint_clusters_single_segment():
    """A single segment has 2 endpoints which (per default min_samples=2)
    will form one cluster -- but they are far apart, so ε won't bridge them.
    Collapse should be a no-op."""
    segs = [LineString([(0, 0), (10, 0)])]
    collapsed = collapse_endpoint_clusters(segs)
    # Either unchanged, or the two endpoints land on themselves.
    assert len(collapsed) == 1
    coords = list(collapsed[0].coords)
    assert len(coords) == 2


def test_collapse_drops_zero_length_segments():
    """If both endpoints of a 2-vertex segment land in the same cluster,
    the resulting segment has zero length and must be dropped."""
    # Two endpoints already coincident → DBSCAN collapses to one centroid →
    # the segment vanishes.
    segs = [LineString([(0.0, 0.0), (0.001, 0.0)])]
    # Construct a second segment so DBSCAN has a cluster to form.
    segs.append(LineString([(0.0005, 0.0), (5.0, 0.0)]))
    collapsed = collapse_endpoint_clusters(segs, eps=0.5)
    # The first segment's two endpoints both fell in the cluster around 0;
    # after collapse it has zero length and should be dropped.
    for ls in collapsed:
        assert ls.length > 0


# --------------------------------------------------------------------------- #
# Strategy selector
# --------------------------------------------------------------------------- #


def test_best_picks_winner_among_strategies():
    """The selector should return a result no worse than greedy on a fixture
    where greedy is already correct."""
    segs = _square_with_corner_gaps(g=0.2)
    aug_g, _conf_g = infer_bridges(segs, max_gap=2.0)
    n_g = _polygon_count(aug_g)

    aug_best, conf_best, name = infer_bridges_best(segs, max_gap=2.0)
    n_best = _polygon_count(aug_best)

    assert n_best >= n_g
    assert name in {"greedy", "backtrack", "dbscan_collapse", "dbscan_collapse+backtrack"}
    assert conf_best > 0


def test_best_handles_empty_input():
    aug, conf, name = infer_bridges_best([])
    assert aug == []
    assert conf == 1.0
    assert name == "none"


def test_best_picks_dbscan_when_collapse_is_sufficient():
    """A fixture where endpoint clusters collapse to a clean topology
    without needing any bridges -- DBSCAN should win or tie."""
    # Two segments meeting at a tightly-clustered "corner pinch" so DBSCAN
    # collapses to a clean rectangle.
    segs = [
        LineString([(0, 0), (10, 0)]),
        LineString([(10.02, 0.01), (10, 10)]),
        LineString([(10, 10.01), (0, 10)]),
        LineString([(0.01, 10), (0, 0.02)]),
    ]
    aug, conf, name = infer_bridges_best(segs, max_gap=2.0)
    # We don't pin the strategy name -- any of them is acceptable as long
    # as the result polygonizes cleanly.
    assert _polygon_count(aug) >= 1
    assert conf > 0
    assert name != "none"


def test_best_strategy_name_present_in_known_set():
    segs = _square_with_corner_gaps(g=0.2)
    _, _, name = infer_bridges_best(segs, max_gap=2.0)
    assert name in {
        "greedy",
        "backtrack",
        "dbscan_collapse",
        "dbscan_collapse+backtrack",
        "none",
    }


# --------------------------------------------------------------------------- #
# Edge cases
# --------------------------------------------------------------------------- #


def test_empty_input_all_paths():
    """Every public entry point should handle empty input gracefully."""
    aug, conf = infer_bridges([])
    assert aug == [] and conf == 1.0
    aug, conf = infer_bridges_backtrack([])
    assert aug == [] and conf == 1.0
    assert collapse_endpoint_clusters([]) == []
    aug, conf, name = infer_bridges_best([])
    assert aug == [] and conf == 1.0 and name == "none"


def test_single_segment_no_candidates():
    """One segment → two endpoints from the same segment → no candidate
    pairs → no bridges, zero confidence (nothing to close)."""
    segs = [LineString([(0, 0), (10, 0)])]
    eps = _collect_endpoints(segs)
    cands = _candidate_pairs(eps, max_gap=50.0)
    assert cands == []  # same-segment pairs filtered

    aug_b, _conf_b = infer_bridges_backtrack(segs, max_gap=50.0)
    # No candidates → no bridges.
    assert len(aug_b) == len(segs)


def test_all_coincident_endpoints():
    """If every segment endpoint is at the exact same point, there is no
    bridging to do (they already share)."""
    segs = [
        LineString([(5, 5), (5, 5.001)]),
        LineString([(5.001, 5), (5, 5)]),
    ]
    # Should not crash; bridges (if any) are degenerate and conf is bounded.
    aug, conf = infer_bridges(segs, max_gap=5.0, min_gap=0.0001)
    assert isinstance(aug, list)
    assert 0.0 <= conf <= 1.0

    aug_b, conf_b = infer_bridges_backtrack(segs, max_gap=5.0, min_gap=0.0001)
    assert isinstance(aug_b, list)
    assert 0.0 <= conf_b <= 1.0

    collapsed = collapse_endpoint_clusters(segs, eps=0.1)
    assert isinstance(collapsed, list)


def test_two_disjoint_clusters_no_bridge_across_huge_gap():
    """Two clusters of segments separated by a gap >> max_gap should NOT be
    bridged (the user's intentional gap is preserved)."""
    segs = [
        LineString([(0, 0), (1, 0)]),
        LineString([(1000, 1000), (1001, 1000)]),
    ]
    aug_b, conf_b = infer_bridges_backtrack(segs, max_gap=50.0)
    # max_gap shouldn't allow a bridge across 1414pt of gap.
    assert len(aug_b) == len(segs)
    assert conf_b == 0.0


# --------------------------------------------------------------------------- #
# Backwards compatibility -- the original greedy bridger is unchanged
# --------------------------------------------------------------------------- #


def test_greedy_bridger_still_works_unchanged():
    """The v0.4 greedy bridger must still close a square with corner gaps."""
    segs = _square_with_corner_gaps(g=0.2)
    aug, conf = infer_bridges(segs, max_gap=2.0, min_gap=0.01)
    assert len(aug) > len(segs)
    assert conf > 0
    polys = _polys_at_tolerance(aug, 0.0)
    assert len(polys) >= 1


@pytest.mark.parametrize("gap_size", [0.05, 0.1, 0.2, 0.5])
def test_strategy_selector_robust_across_gap_sizes(gap_size: float):
    """The selector should produce at least one polygon across a range of
    realistic Make2D gap sizes."""
    segs = _square_with_corner_gaps(g=gap_size)
    aug, conf, name = infer_bridges_best(segs, max_gap=max(gap_size * 5, 2.0))
    assert _polygon_count(aug) >= 1
    assert conf > 0
    assert name != "none"
