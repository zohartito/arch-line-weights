"""Tests for the §1.1 role ladder and §1.4 assignment procedure.

Expected pt weights are the authoritative values from the real
``select_preset(..., for_print=True, scale="1/4")`` output, NOT hand-coded ISO
rungs — see spec doc 49 and the module docstring.
"""

from __future__ import annotations

import dataclasses

import pytest

from arch_line_weights.role_ladder import (
    Role,
    RoleAssignment,
    assign_role,
    enforce_integrity,
    modulate_by_depth,
    weight_for_role,
)

# Lightest non-special rung per preset at 1/4", for_print=True. Used as the
# floor that depth recession and clamping must never cross.
_TEXTURE_FLOOR_PT = {
    "section": 0.369,
    "usc": 0.369,
    "plan": 0.369,
    "elevation": 0.369,
    "detail": 0.51,
}


def test_cut_is_continuous_and_integrity_protected() -> None:
    a = assign_role(is_cut=True, preset="section", for_print=True)
    assert a.role is Role.CUT_PROFILE
    assert a.weight_pt == 1.984
    assert a.continuous is True
    assert a.integrity_protected is True


def test_spatial_edge_takes_heaviest_when_no_cut_tier() -> None:
    a = assign_role(separates_solid_void=True, preset="elevation", for_print=True)
    assert a.role is Role.SPATIAL_EDGE
    assert a.preset_tier == "silhouette"
    assert a.weight_pt == 1.984
    assert a.integrity_protected is True


def test_planar_corner_maps_to_edges() -> None:
    a = assign_role(is_planar_corner=True, preset="section", for_print=True)
    assert a.role is Role.PLANAR_CORNER
    assert a.weight_pt == 0.992


def test_too_dark_surface_demotes_style_not_weight() -> None:
    a = assign_role(
        is_surface_change=True,
        too_dark_for_surface=True,
        preset="section",
        for_print=True,
    )
    assert a.role is Role.SURFACE
    assert a.dashed_demote is True
    # Ladder is NOT broken: weight stays on the SURFACE rung.
    assert a.weight_pt == 0.51


def test_depth_recedes_surface_but_not_below_floor() -> None:
    near = assign_role(is_surface_change=True, depth_rank=0, depth_total=3, preset="section", for_print=True)
    far = assign_role(is_surface_change=True, depth_rank=2, depth_total=3, preset="section", for_print=True)
    assert far.weight_pt <= near.weight_pt
    assert far.weight_pt >= _TEXTURE_FLOOR_PT["section"]


def test_modulate_by_depth_exempts_integrity_protected() -> None:
    cut = weight_for_role(Role.CUT_PROFILE, preset="section", for_print=True)
    receded = modulate_by_depth(Role.CUT_PROFILE, cut, 5, 6, "section", "1/4", True)
    # Integrity-protected lines never recede with depth.
    assert receded.weight_pt == cut.weight_pt
    assert receded == cut


def test_cut_wins_precedence_over_surface() -> None:
    a = assign_role(is_cut=True, is_surface_change=True, preset="section", for_print=True)
    assert a.role is Role.CUT_PROFILE


def test_enforce_integrity_flags_layout_at_cut_weight() -> None:
    cut = weight_for_role(Role.CUT_PROFILE, preset="section", for_print=True)
    layout = weight_for_role(Role.LAYOUT, preset="section", for_print=True)
    # Hand-build a LAYOUT line illegally sitting at the cut weight.
    offender = dataclasses.replace(
        layout,
        weight_pt=cut.weight_pt,
        weight_mm=cut.weight_mm,
        preset_tier="cut",
    )
    warnings = enforce_integrity([cut, offender])
    assert warnings
    assert len(warnings) == 1
    assert "integrity violation" in warnings[0]


def test_enforce_integrity_clean_when_below_protected() -> None:
    cut = weight_for_role(Role.CUT_PROFILE, preset="section", for_print=True)
    layout = weight_for_role(Role.LAYOUT, preset="section", for_print=True)
    assert enforce_integrity([cut, layout]) == []


def test_enforce_integrity_empty_without_protected_line() -> None:
    layout = weight_for_role(Role.LAYOUT, preset="section", for_print=True)
    surface = weight_for_role(Role.SURFACE, preset="section", for_print=True)
    assert enforce_integrity([layout, surface]) == []


def test_emphasis_never_passes_integrity_protected_weight() -> None:
    # PLANAR_CORNER (edges, 0.992) with emphasis would bump toward profile
    # (1.417); profile is the SPATIAL_EDGE rung but is below the cut. The bump
    # must never exceed an integrity-protected line's weight on the page.
    cut = weight_for_role(Role.CUT_PROFILE, preset="section", for_print=True)
    bumped = assign_role(is_planar_corner=True, emphasis=True, preset="section", for_print=True)
    assert bumped.weight_pt < cut.weight_pt


def test_unknown_preset_falls_back_to_section() -> None:
    a = assign_role(is_cut=True, preset="does-not-exist", for_print=True)
    assert a.role is Role.CUT_PROFILE
    # section cut weight
    assert a.weight_pt == 1.984


def test_layout_role_values() -> None:
    assert Role.CUT_PROFILE.value == "cut-profile"
    assert Role.SPATIAL_EDGE.value == "spatial-edge"
    assert Role.PLANAR_CORNER.value == "planar-corner"
    assert Role.SURFACE.value == "surface"
    assert Role.LAYOUT.value == "layout"


def test_weight_mm_is_snapped_to_iso_rung() -> None:
    a = weight_for_role(Role.CUT_PROFILE, preset="section", for_print=True)
    # 1.984 pt -> 0.70 mm exactly on the ISO ladder.
    assert a.weight_mm == 0.70


@pytest.mark.parametrize("preset", ["section", "usc", "plan", "elevation", "detail"])
def test_role_ladder_is_monotonic(preset: str) -> None:
    cut = weight_for_role(Role.CUT_PROFILE, preset=preset, for_print=True).weight_pt
    corner = weight_for_role(Role.PLANAR_CORNER, preset=preset, for_print=True).weight_pt
    surface = weight_for_role(Role.SURFACE, preset=preset, for_print=True).weight_pt
    layout = weight_for_role(Role.LAYOUT, preset=preset, for_print=True).weight_pt
    assert cut >= corner >= surface >= layout


@pytest.mark.parametrize("preset", ["section", "usc", "plan", "elevation", "detail"])
@pytest.mark.parametrize("depth_rank", [0, 1, 2, 3])
def test_depth_monotonic_and_floored(preset: str, depth_rank: int) -> None:
    base = weight_for_role(Role.SURFACE, preset=preset, for_print=True)
    receded = modulate_by_depth(Role.SURFACE, base, depth_rank, depth_rank + 1, preset, "1/4", True)
    # Receding never gets heavier, and never drops below the texture floor.
    assert receded.weight_pt <= base.weight_pt
    assert receded.weight_pt >= _TEXTURE_FLOOR_PT[preset]


def test_role_assignment_is_frozen() -> None:
    a = weight_for_role(Role.SURFACE, preset="section", for_print=True)
    assert isinstance(a, RoleAssignment)
    with pytest.raises(dataclasses.FrozenInstanceError):
        a.weight_pt = 9.9  # type: ignore[misc]
