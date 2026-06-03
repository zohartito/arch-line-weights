from __future__ import annotations

import pytest
from shapely.geometry import LineString

from arch_line_weights.architectural import (
    architectural_layer_color_resolver,
    architectural_stroke_style_for_layer,
    classify_architectural_layer,
)
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
            0.18,
            False,
            False,
        ),
        (
            "axon::Visible::Curves::05_RHS_STL_FRAME",
            "structure_secondary",
            0.25,
            False,
            False,
        ),
        (
            "axon iso section cut::Visible::Curves::FIXED_STAIR_COHESIVE",
            "structure_primary",
            0.5,
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
    "layer,tier",
    [
        (
            "axon::Visible::ClippingPlaneIntersections::CONCRETE_RAINSCREEN_PANEL",
            "cladding",
        ),
        (
            "axon::Visible::ClippingPlaneIntersections::CLT_WINDOW_IGU_GLASS",
            "glazing",
        ),
        (
            "axon::Visible::ClippingPlaneIntersections::FOUNDATION_EPDM_FLASHING",
            "material_minor",
        ),
        (
            "axon::Visible::ClippingPlaneIntersections::TEC_CONCRETE_CONNECTOR_CLIP",
            "connectors",
        ),
    ],
)
def test_architectural_blacklist_wins_over_structural_cut_tokens(layer, tier):
    assignment = classify_architectural_layer(layer, preset="section")

    assert assignment.tier == tier
    assert assignment.poche is False
    assert _is_cut_layer(layer, architectural=True) is False


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


def test_visible_fixed_stair_is_structural_but_not_poche():
    assignment = classify_architectural_layer(
        "axon iso section cut::Visible::Curves::FIXED_STAIR_COHESIVE",
        preset="section",
    )

    assert assignment.tier == "structure_primary"
    assert assignment.weight_pt == 0.5
    assert assignment.poche is False


def test_architectural_cut_color_resolver_makes_non_poche_cuts_read_as_cut():
    resolve = architectural_layer_color_resolver(preset="section")

    assert (
        resolve(
            "axon::Visible::ClippingPlaneIntersections::15_CU_PUNCH_RETURNS_SOUTH_BAY_ALIGNED_V44"
        )
        == (0, 0, 0)
    )
    assert (
        resolve("axon::Visible::ClippingPlaneIntersections::24_SHS_100_OUTRIGGERS_REMAP")
        == (0, 0, 0)
    )
    assert (
        resolve("axon::Visible::ClippingPlaneIntersections::03c_WINDOW_IGU_GLASS")
        == (0, 76, 160)
    )
    assert resolve("axon::Visible::Curves::15_CU_PUNCH_RETURNS_SOUTH_BAY_ALIGNED_V44") is None


def test_architectural_cut_style_is_separate_from_poche_semantics():
    style = architectural_stroke_style_for_layer(
        "axon::Visible::ClippingPlaneIntersections::15_CU_PUNCH_RETURNS_SOUTH_BAY_ALIGNED_V44"
    )

    assert style.weight_pt == 0.18
    assert style.stroke_rgb == (0, 0, 0)
    assert style.solid_line is True

    visible_style = architectural_stroke_style_for_layer(
        "axon::Visible::Curves::15_CU_PUNCH_RETURNS_SOUTH_BAY_ALIGNED_V44"
    )
    assert visible_style.weight_pt == 0.18
    assert visible_style.stroke_rgb is None
    assert visible_style.solid_line is False


def test_generic_clipping_plane_is_cut_line_not_poche_fill():
    layer = "axon::Visible::ClippingPlaneIntersections::UNRESOLVED_PANEL_EDGE"

    assignment = classify_architectural_layer(layer, preset="section")
    style = architectural_stroke_style_for_layer(layer, preset="section")

    assert assignment.tier == "cut"
    assert assignment.poche is False
    assert style.weight_pt == 0.3
    assert style.stroke_rgb == (0, 0, 0)
    assert style.solid_line is True


@pytest.mark.parametrize(
    "layer,expected_weight",
    [
        (
            "axon::Visible::ClippingPlaneIntersections::TEC_STEEL_CONNECTOR_L-BRACKET",
            0.18,
        ),
        (
            "axon::Visible::ClippingPlaneIntersections::CLEAT_PLATE",
            0.18,
        ),
        (
            "axon::Visible::ClippingPlaneIntersections::24_SHS_100_OUTRIGGERS_REMAP",
            0.25,
        ),
        (
            "axon::Visible::ClippingPlaneIntersections::15_CU_PUNCH_RETURNS_SOUTH_BAY_ALIGNED_V44",
            0.18,
        ),
    ],
)
def test_non_solid_cut_layers_stay_subordinate(layer, expected_weight):
    style = architectural_stroke_style_for_layer(layer, preset="section")
    assignment = classify_architectural_layer(layer, preset="section")

    assert assignment.poche is False
    assert style.weight_pt == expected_weight
    assert style.stroke_rgb == (0, 0, 0)
    assert style.solid_line is True


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


def test_structural_open_loop_rejects_triangular_cap_blob():
    polys = _try_structural_open_loop(
        "axon::Visible::ClippingPlaneIntersections::TEC_CONCRETE_BASE",
        [
            LineString([(0, 0), (40, 0), (20, 25)]),
        ],
    )

    assert polys == []


def test_structural_open_loop_rejects_densified_triangular_cap_blob():
    polys = _try_structural_open_loop(
        "axon::Visible::ClippingPlaneIntersections::TEC_CONCRETE_BASE",
        [
            LineString([(0, 0), (20, 0), (40, 0), (20, 25)]),
        ],
    )

    assert polys == []


def test_structural_open_loop_rejects_tiny_backup_wall_fragment():
    polys = _try_structural_open_loop(
        "axon::Visible::ClippingPlaneIntersections::03b_CLT_BACKUP_WALL_5in",
        [
            LineString([(0, 0), (9, 0), (9, 12), (0, 12)]),
        ],
    )

    assert polys == []


def test_structural_open_loop_keeps_tall_backup_wall_strip():
    polys = _try_structural_open_loop(
        "axon::Visible::ClippingPlaneIntersections::03b_CLT_BACKUP_WALL_5in",
        [
            LineString([(0, 0), (9, 0), (9, 60), (0, 60)]),
        ],
    )

    assert len(polys) == 1
    assert round(polys[0].area) == 540


def test_structural_open_loop_rejects_huge_irregular_roof_after_cleaning():
    polys = _try_structural_open_loop(
        "axon::Visible::ClippingPlaneIntersections::TEC_ROOF_CLT",
        [
            LineString([(0, 0), (900, 0), (450, 80)]),
            LineString([(450, 80), (0, 220), (900, 220)]),
        ],
    )

    assert polys == []


def test_structural_open_loop_keeps_rectangular_roof_strip():
    polys = _try_structural_open_loop(
        "axon::Visible::ClippingPlaneIntersections::TEC_ROOF_CLT",
        [
            LineString([(0, 0), (500, 0), (500, 80), (0, 80)]),
        ],
    )

    assert len(polys) == 1
    assert round(polys[0].area) == 40000


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


def test_structural_open_loop_closes_tiny_collinear_fragment_gaps():
    polys, result = polygonize_layer(
        "axon::Visible::ClippingPlaneIntersections::TEC_CONCRETE_BASE",
        [
            [[0, 0], [48, 0]],
            [[52, 0], [100, 0]],
            [[100, 22], [52, 22]],
            [[48, 22], [0, 22]],
        ],
        bridge_strategy="greedy",
        structural_helper_lines=[
            LineString([(0, 0), (0, 22)]),
            LineString([(100, 0), (100, 22)]),
        ],
    )

    assert result.strategy == "structural_open_loop"
    assert len(polys) == 1
    assert round(polys[0].area) == 2200
    assert polys[0].bounds == (0.0, 0.0, 100.0, 22.0)


def test_structural_open_loop_keeps_larger_collinear_void_open():
    polys, result = polygonize_layer(
        "axon::Visible::ClippingPlaneIntersections::TEC_CONCRETE_BASE",
        [
            [[0, 0], [40, 0]],
            [[60, 0], [100, 0]],
            [[100, 22], [60, 22]],
            [[40, 22], [0, 22]],
        ],
        bridge_strategy="greedy",
        structural_helper_lines=[
            LineString([(0, 0), (0, 22)]),
            LineString([(100, 0), (100, 22)]),
        ],
    )

    assert result.strategy == "structural_open_loop"
    assert len(polys) == 2
    assert [round(poly.area) for poly in polys] == [880, 880]


def test_structural_helper_cannot_wildly_expand_existing_concrete_face():
    polys = _try_structural_open_loop(
        "axon::Visible::ClippingPlaneIntersections::TEC_CONCRETE_BASE",
        [
            LineString([(0, 0), (20, 0), (20, 100), (0, 100)]),
        ],
        helper_lines=[
            LineString([(100, 0), (100, 100)]),
        ],
    )

    assert len(polys) == 1
    assert round(polys[0].area) == 2000
    assert polys[0].bounds == (0.0, 0.0, 20.0, 100.0)
