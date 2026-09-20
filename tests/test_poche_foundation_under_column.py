"""The foundation/concrete mass under a wood column must poché solid.

Regression cover for the Day-1 proof miss recorded in
``tests/fixtures/make2d_day1_manifest.json`` as
``foundation_concrete_under_wood_column_left_footing``: the left footing
printed as outline only.

Cause: the bridger scored a closure by how MANY bridges it had to add
relative to the segment count. Make2D fragments a cut at its corners, so a
stepped footing -- a spread pad with a pier the wood column bears on -- has
one short bridge per corner and drove ``n_bridges / n_segments`` to 1.0. The
bridge penalty collapsed to zero and the layer landed at confidence 0.62,
below the 0.85 injection threshold, even though the recovered polygon was
~99% real cut line. It was held back as diagnostic-only, so the footing kept
its cut stroke and got no fill.

See ``bridge._confidence`` and ``docs/research/disconnected-loops.md``.
"""

from __future__ import annotations

from itertools import pairwise

from shapely.geometry import Polygon

from arch_line_weights import poche
from arch_line_weights.bridge import _bridged_fraction, _confidence
from arch_line_weights.poche import polygonize_layer, should_inject_fill

FOUNDATION_CUT = "axon::Visible::ClippingPlaneIntersections::TEC_FOUNDATION"

# Spread pad with the pier the wood column bears on: 8 corners, so Make2D
# leaves 8 stub gaps. Point units at the QA plot scale, as the rest of the
# poché gates assume.
STEPPED_FOOTING = [
    (0, 0),
    (240, 0),
    (240, 60),
    (150, 60),
    (150, 200),
    (90, 200),
    (90, 60),
    (0, 60),
    (0, 0),
]
STEPPED_FOOTING_AREA = Polygon(STEPPED_FOOTING).area


def _fragmented(points, shrink: float):
    """Emit the outline as one path per edge, each trimmed at both ends.

    Reproduces how Make2D hands back a clipping-plane cut: every corner is a
    gap rather than a shared vertex.
    """
    paths = []
    for (x0, y0), (x1, y1) in pairwise(points):
        dx, dy = x1 - x0, y1 - y0
        paths.append(
            [
                [x0 + dx * shrink, y0 + dy * shrink],
                [x1 - dx * shrink, y1 - dy * shrink],
            ]
        )
    return paths


def test_stepped_footing_under_column_is_injected_not_outline_only():
    paths = _fragmented(STEPPED_FOOTING, shrink=0.10)

    polys, fill = polygonize_layer(FOUNDATION_CUT, paths)

    assert fill.strategy == "auto_bridge"
    assert should_inject_fill(fill), (
        f"stepped footing held back at confidence {fill.confidence:.2f}; it would print as outline only"
    )
    recovered = sum(p.area for p in polys)
    assert recovered >= STEPPED_FOOTING_AREA * 0.95


def test_stepped_footing_closure_is_mostly_real_cut_line():
    """The promoted closure is evidence, not invention: >=80% drawn length."""
    from arch_line_weights.poche import _lines_from_anchors

    lines = _lines_from_anchors(_fragmented(STEPPED_FOOTING, shrink=0.10))
    drawn = sum(line.length for line in lines)
    assert drawn >= Polygon(STEPPED_FOOTING).length * 0.75


def test_counting_bridges_would_still_hold_the_footing_back():
    """Pin the cause: the old count-based penalty gates this exact closure."""
    # 8 edges, 8 corner stubs, one polygon recovered.
    by_count = _confidence(n_segments=8, n_bridges=8, n_polys=1, expected=1)
    by_length = _confidence(
        n_segments=8,
        n_bridges=8,
        n_polys=1,
        expected=1,
        bridged_fraction=0.20,
    )

    assert 0.75 * by_count + 0.25 < 0.85
    assert 0.75 * by_length + 0.25 >= 0.85


def test_bridged_fraction_measures_inferred_length():
    from shapely.geometry import LineString

    segments = [LineString([(0, 0), (80, 0)])]
    bridges = [LineString([(80, 0), (100, 0)])]

    assert _bridged_fraction(segments, bridges) == 0.2
    assert _bridged_fraction([], []) is None


def test_scattered_fragments_stay_diagnostic_only():
    """A closure that is mostly invented must still be refused."""
    paths = [
        [[0, 0], [40, 0]],
        [[120, 10], [150, 40]],
        [[60, 120], [100, 120]],
        [[10, 90], [10, 130]],
    ]

    _polys, fill = polygonize_layer(FOUNDATION_CUT, paths)

    assert not should_inject_fill(fill), f"scattered fragments injected at confidence {fill.confidence:.2f}"


def test_projected_column_stem_still_never_fills():
    """Length scoring must not open the visible (projected) path."""
    visible = "axon::Visible::Curves::TEC_FOUNDATION"
    stem = [
        [[300, 0], [300, 240]],
        [[340, 0], [340, 240]],
    ]

    polys, _candidates = poche._visible_structural_completion_candidates(visible, stem)

    assert polys == []
