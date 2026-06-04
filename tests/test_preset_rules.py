from __future__ import annotations

import pytest

from arch_line_weights.preset_rules import (
    PRESET_RULES,
    DepthModel,
    figure_ground_rule,
    ladder_for_preset,
    rule_for_axon,
    rule_for_preset,
)
from arch_line_weights.role_ladder import Role

_CUT_DRIVEN_PRESETS = ["section", "usc", "plan", "detail"]


def test_section_is_cut_driven_behind_cut() -> None:
    rule = rule_for_preset("section")
    assert rule.cut_driven is True
    assert rule.depth_model is DepthModel.BEHIND_CUT
    assert rule.heaviest_role is Role.CUT_PROFILE


def test_plan_drops_below_cut() -> None:
    rule = rule_for_preset("plan")
    assert rule.depth_model is DepthModel.DROP_BELOW_CUT
    assert rule.cut_driven is True


def test_elevation_is_no_cut_figure_ground_with_groundline() -> None:
    rule = rule_for_preset("elevation")
    assert rule.cut_driven is False
    assert rule.heaviest_role is Role.SPATIAL_EDGE
    assert rule.depth_model is DepthModel.FIGURE_GROUND
    assert rule.integrity_enforced is False
    assert rule.has_groundline is True


def test_axon_is_no_cut_figure_ground_without_groundline() -> None:
    rule = rule_for_axon()
    assert rule.preset == "axon"
    assert rule.cut_driven is False
    assert rule.heaviest_role is Role.SPATIAL_EDGE
    assert rule.depth_model is DepthModel.FIGURE_GROUND
    assert rule.integrity_enforced is False
    # A floating axon has NO groundline.
    assert rule.has_groundline is False


def test_axon_reuses_elevation_weights() -> None:
    # Axon adopts elevation's figure-ground ladder verbatim, groundline aside.
    assert ladder_for_preset("axon") == ladder_for_preset("elevation")


def test_figure_ground_rule_is_pure_three_tier() -> None:
    assert figure_ground_rule() == (
        Role.SPATIAL_EDGE,
        Role.PLANAR_CORNER,
        Role.SURFACE,
    )


def test_figure_ground_rule_has_no_groundline_role() -> None:
    # The reusable order must never smuggle in a cut/groundline tier.
    assert Role.CUT_PROFILE not in figure_ground_rule()


def test_elevation_heaviest_is_silhouette_weight() -> None:
    # No-cut heaviest = silhouette = 0.70 mm print = 1.984 pt.
    ladder = ladder_for_preset("elevation", for_print=True)
    assert ladder[Role.SPATIAL_EDGE] == 1.984


def test_detail_spread_wider_than_section() -> None:
    detail = ladder_for_preset("detail", for_print=True).values()
    section = ladder_for_preset("section", for_print=True).values()
    detail_spread = max(detail) - min(detail)
    section_spread = max(section) - min(section)
    assert detail_spread > section_spread


def test_unknown_preset_falls_back_to_section() -> None:
    assert rule_for_preset("does-not-exist") == PRESET_RULES["section"]
    assert rule_for_preset("does-not-exist").cut_driven is True


@pytest.mark.parametrize("preset", _CUT_DRIVEN_PRESETS)
def test_cut_driven_ladder_descends_cut_to_surface(preset: str) -> None:
    ladder = ladder_for_preset(preset, for_print=True)
    assert ladder[Role.CUT_PROFILE] >= ladder[Role.PLANAR_CORNER]
    assert ladder[Role.PLANAR_CORNER] >= ladder[Role.SURFACE]


@pytest.mark.parametrize("preset", _CUT_DRIVEN_PRESETS)
def test_cut_driven_presets_enforce_integrity(preset: str) -> None:
    rule = rule_for_preset(preset)
    assert rule.cut_driven is True
    assert rule.integrity_enforced is True
    assert rule.heaviest_role is Role.CUT_PROFILE


@pytest.mark.parametrize("preset", ["section", "usc", "plan", "elevation", "detail", "axon"])
def test_ladder_for_preset_never_raises_on_screen_default(preset: str) -> None:
    # Default for_print=False must resolve every role without raising.
    ladder = ladder_for_preset(preset)
    assert set(ladder) == set(Role)
    assert all(isinstance(w, float) and w > 0 for w in ladder.values())


def test_preset_rules_are_self_consistent() -> None:
    # Every entry's .preset key matches its dict key (cheap invariant guard).
    for key, rule in PRESET_RULES.items():
        assert rule.preset == key
