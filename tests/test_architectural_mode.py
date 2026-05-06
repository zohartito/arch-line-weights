from __future__ import annotations

import pytest
from shapely.geometry import LineString

from arch_line_weights.architectural import classify_architectural_layer
from arch_line_weights.poche import _try_structural_open_loop, polygonize_layer
from arch_line_weights.poche_saas import _is_cut_layer


@pytest.mark.parametrize(
    "layer,tier,weight,poche,closure",
    [
        (
            "axon::Visible::ClippingPlaneIntersections::TEC_CONCRETE_BASE",
            "cut",
            1.0,
            True,
            True,
        ),
        (
            "axon::Visible::ClippingPlaneIntersections::TEC_ROOF_CLT",
            "cut",
            1.0,
            True,
            True,
        ),
        (
            "axon::Visible::ClippingPlaneIntersections::26_CLT_GAP_ROOF_CAP",
            "cut",
            1.0,
            True,
            True,
        ),
        (
            "axon::Visible::ClippingPlaneIntersections::15_CU_PUNCH_RETURNS_SOUTH_BAY_ALIGNED_V44",
            "cladding",
            0.18,
            False,
            False,
        ),
        (
            "axon::Visible::ClippingPlaneIntersections::23_WINDOW_FRAMES_REMAP",
            "frames",
            0.3,
            False,
            False,
        ),
        (
            "axon::Visible::Curves::TEC_STEEL_CONNECTOR_L-BRACKET",
            "connectors",
            0.25,
            False,
            False,
        ),
        (
            "axon::Visible::Curves::05_RHS_STL_FRAME",
            "structure_secondary",
            0.35,
            False,
            False,
        ),
        (
            "axon::Visible::ClippingPlaneIntersections::Entourage::People",
            "entourage",
            0.13,
            False,
            False,
        ),
    ],
)
def test_architectural_section_axon_semantics(layer, tier, weight, poche, closure):
    assignment = classify_architectural_layer(layer, preset="section")

    assert assignment.tier == tier
    assert assignment.weight_pt == weight
    assert assignment.poche is poche
    assert assignment.open_loop_closure is closure


def test_architectural_poche_filter_uses_semantics():
    assert _is_cut_layer(
        "axon::Visible::ClippingPlaneIntersections::TEC_CONCRETE_BASE",
        architectural=True,
    )
    assert not _is_cut_layer(
        "axon::Visible::ClippingPlaneIntersections::15_CU_PUNCH_RETURNS_SOUTH_BAY_ALIGNED_V44",
        architectural=True,
    )
    assert not _is_cut_layer(
        "axon::Visible::ClippingPlaneIntersections::WINDOW_IGU_GLASS",
        architectural=True,
    )


@pytest.mark.parametrize(
    "layer",
    [
        "axon::Visible::ClippingPlaneIntersections::15_CU_PUNCH_RETURNS_SOUTH_BAY_ALIGNED_V44",
        "axon::Visible::ClippingPlaneIntersections::WINDOW_IGU_GLASS",
        "axon::Visible::ClippingPlaneIntersections::HELPER_TANGENT_CURVE",
        "axon::Visible::Curves::TEC_CONCRETE_BASE_HELPER_TANGENT",
    ],
)
def test_cladding_glass_and_helper_layers_are_not_poche_eligible(layer):
    assignment = classify_architectural_layer(layer, preset="section")

    assert assignment.poche is False
    assert _is_cut_layer(layer, architectural=True) is False


def test_view_name_section_cut_does_not_make_visible_curves_poche():
    assignment = classify_architectural_layer(
        "axon iso section cut::Visible::Curves::TEC_TIMBER_BEAMS",
        preset="section",
    )

    assert assignment.tier == "structure_primary"
    assert assignment.weight_pt == 0.5
    assert assignment.poche is False


def test_structural_open_loop_closes_three_sided_cut_chain():
    lines = [
        LineString([(0, 0), (100, 0), (100, 20), (0, 20)]),
    ]

    polys = _try_structural_open_loop(
        "axon::Visible::ClippingPlaneIntersections::TEC_CONCRETE_BASE",
        lines,
    )

    assert len(polys) == 1
    assert round(polys[0].area) == 2000


def test_structural_open_loop_rejects_cladding_layer():
    lines = [
        LineString([(0, 0), (100, 0), (100, 20), (0, 20)]),
    ]

    polys = _try_structural_open_loop(
        "axon::Visible::ClippingPlaneIntersections::15_CU_PUNCH_RETURNS_SOUTH_BAY_ALIGNED_V44",
        lines,
    )

    assert polys == []


def test_polygonize_reports_structural_open_loop_when_bridge_fails(monkeypatch):
    monkeypatch.setattr(
        "arch_line_weights.poche.infer_bridges_best",
        lambda *_args, **_kwargs: ([], 0.0, "none"),
    )

    polys, result = polygonize_layer(
        "axon::Visible::ClippingPlaneIntersections::TEC_CONCRETE_BASE",
        [[[0, 0], [100, 0], [100, 20], [0, 20]]],
        bridge_strategy="best",
    )

    assert len(polys) == 1
    assert result.strategy == "structural_open_loop"
    assert result.confidence >= 0.85


def test_structural_open_loop_can_add_missing_regions_to_existing_closed_loops():
    polys, result = polygonize_layer(
        "axon::Visible::ClippingPlaneIntersections::TEC_CONCRETE_BASE",
        [
            [[0, 0], [20, 0], [20, 20], [0, 20], [0, 0]],
            [[40, 0], [100, 0], [100, 20], [40, 20]],
        ],
        bridge_strategy="greedy",
    )

    assert result.strategy == "structural_open_loop"
    assert len(polys) == 2


def test_polygonize_uses_helper_tangents_to_close_parallel_structural_edges(monkeypatch):
    monkeypatch.setattr(
        "arch_line_weights.poche.infer_bridges_best",
        lambda *_args, **_kwargs: ([], 0.0, "none"),
    )

    polys, result = polygonize_layer(
        "axon::Visible::ClippingPlaneIntersections::TEC_CONCRETE_BASE",
        [
            [[0, 0], [100, 0]],
            [[100, 90], [0, 90]],
        ],
        bridge_strategy="best",
        structural_helper_lines=[
            LineString([(100, 0), (100, 45), (100, 90)]),
        ],
    )

    assert len(polys) == 1
    assert result.strategy == "structural_open_loop"
    assert result.confidence >= 0.85
    assert round(polys[0].area) == 9000
