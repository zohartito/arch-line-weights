"""Visible-structural completion candidate recording.

The visible auto-fill path must record which loops it considered and which gate
each one passed or missed, so ambiguous/rejected candidates are reported rather
than silently dropped.
"""

from __future__ import annotations

from shapely.geometry import Polygon

from arch_line_weights import poche

FOUNDATION_LAYER = "axon::Visible::Curves::TEC_FOUNDATION"


def _patch_open_loop(monkeypatch, polys: list[Polygon]) -> None:
    monkeypatch.setattr(poche, "_try_structural_open_loop", lambda *a, **k: list(polys))


def test_visible_completion_records_accepted_candidate(monkeypatch):
    # Wide footing strip: area 8000 >= 800 and width 200 >= 1.5 * height 40.
    poly = Polygon([(0, 0), (200, 0), (200, 40), (0, 40)])
    _patch_open_loop(monkeypatch, [poly])
    paths = [[[0, 0], [200, 0], [200, 40], [0, 40], [0, 0]]]

    polys, candidates = poche._visible_structural_completion_candidates(FOUNDATION_LAYER, paths)

    assert len(polys) == 1
    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.accepted is True
    assert candidate.confidence == 0.88
    assert candidate.target_layer == FOUNDATION_LAYER
    assert candidate.component_key == "TEC_FOUNDATION"
    assert candidate.source_role == "visible_curve"
    assert candidate.provenance == "visible-structural-open-loop"
    assert candidate.reason.startswith("accepted:")


def test_visible_completion_records_rejected_below_min_area(monkeypatch):
    # Area 200 is below the 800 min_area gate for foundation layers.
    poly = Polygon([(0, 0), (20, 0), (20, 10), (0, 10)])
    _patch_open_loop(monkeypatch, [poly])
    paths = [[[0, 0], [200, 0]]]  # path length 200 clears min_path_length 100

    polys, candidates = poche._visible_structural_completion_candidates(FOUNDATION_LAYER, paths)

    assert polys == []
    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.accepted is False
    assert candidate.confidence == 0.0
    assert "below visible min_area" in candidate.reason
    assert candidate.polygon.bounds == (0.0, 0.0, 20.0, 10.0)


def test_visible_completion_records_rejected_implausible_ratio(monkeypatch):
    # Area 8000 clears min_area, but width 40 < 1.5 * height 200 fails plausibility.
    poly = Polygon([(0, 0), (40, 0), (40, 200), (0, 200)])
    _patch_open_loop(monkeypatch, [poly])
    paths = [[[0, 0], [200, 0]]]

    polys, candidates = poche._visible_structural_completion_candidates(FOUNDATION_LAYER, paths)

    assert polys == []
    assert candidates[0].accepted is False
    assert "1.5x height" in candidates[0].reason


def test_visible_completion_reports_rejections_even_with_accepted(monkeypatch):
    accepted = Polygon([(0, 0), (200, 0), (200, 40), (0, 40)])
    rejected = Polygon([(0, 0), (20, 0), (20, 10), (0, 10)])
    _patch_open_loop(monkeypatch, [accepted, rejected])
    paths = [[[0, 0], [200, 0], [200, 40], [0, 40], [0, 0]]]

    polys, candidates = poche._visible_structural_completion_candidates(FOUNDATION_LAYER, paths)

    assert len(polys) == 1
    assert [candidate.accepted for candidate in candidates] == [True, False]
