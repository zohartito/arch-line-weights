"""v0.5 preset families — distinct ladders for plan / elevation / detail / section.

Per docs/research/preset-families.md, each drawing type uses the same ISO 128
ladder anchored to a different "heaviest line" role.
"""

from __future__ import annotations

from arch_line_weights.presets import (
    DETAIL_ISO_PRINT,
    DETAIL_ISO_SCREEN,
    ELEVATION_ISO_PRINT,
    ELEVATION_ISO_SCREEN,
    PLAN_ISO_PRINT,
    PLAN_ISO_SCREEN,
    SECTION_ISO_PRINT,
    SECTION_ISO_SCREEN,
    mm,
    select_preset,
)

# --------------------------------------------------------------------------- #
# Per-drawing-type ladders exist and are non-empty
# --------------------------------------------------------------------------- #


def test_all_four_print_families_exist_and_nonempty():
    for fam in (SECTION_ISO_PRINT, PLAN_ISO_PRINT, ELEVATION_ISO_PRINT, DETAIL_ISO_PRINT):
        assert fam, "preset family is empty"
        assert all(t.weight_pt > 0 for t in fam), "non-positive tier weight"


def test_all_four_screen_families_exist_and_nonempty():
    for fam in (SECTION_ISO_SCREEN, PLAN_ISO_SCREEN, ELEVATION_ISO_SCREEN, DETAIL_ISO_SCREEN):
        assert fam, "preset family is empty"
        assert all(t.weight_pt > 0 for t in fam), "non-positive tier weight"


# --------------------------------------------------------------------------- #
# Drawing-type-specific role conventions
# --------------------------------------------------------------------------- #


def test_section_cut_is_0_70_mm():
    """Section cut at 1/4\"=1' is 0.70 mm = 1.98 pt per Ramsey/Sleeper §1.4."""
    cut = next(t for t in SECTION_ISO_PRINT if t.name == "cut")
    assert abs(cut.weight_pt - mm(0.70)) < 0.01


def test_plan_cut_is_one_step_lighter_than_section():
    """Plan walls_cut is 0.50 mm = 1 ISO step lighter than section cut.

    Per Ramsey/Sleeper §1.4 + Ching p.60 — plans show more linework per area
    so cut is conventionally 0.50 mm at 1/4".
    """
    section_cut = next(t for t in SECTION_ISO_PRINT if t.name == "cut").weight_pt
    plan_cut = next(t for t in PLAN_ISO_PRINT if t.name == "walls_cut").weight_pt
    assert plan_cut < section_cut, "plan cut should be lighter than section cut"
    assert abs(plan_cut - mm(0.50)) < 0.01


def test_elevation_has_no_cut_tier():
    """Per ISO 128-30:2001 §4.2, elevations have no cut tier."""
    tier_names = {t.name for t in ELEVATION_ISO_PRINT}
    assert "cut" not in tier_names
    assert "walls_cut" not in tier_names
    assert "cut_primary" not in tier_names
    # but it does have a silhouette
    assert "silhouette" in tier_names


def test_elevation_silhouette_is_heaviest():
    """Silhouette is the heaviest tier in elevation."""
    weights = {t.name: t.weight_pt for t in ELEVATION_ISO_PRINT}
    silhouette = weights["silhouette"]
    other_max = max(w for n, w in weights.items() if n != "silhouette")
    assert silhouette >= other_max


def test_elevation_has_joints_not_hidden():
    """Per the research recommendation, elevations replace `hidden` with `joints`.

    Elevations almost never use hidden lines — what they need is a tier for
    material joint / panel break / control joint / reveal lines.
    """
    tier_names = {t.name for t in ELEVATION_ISO_PRINT}
    assert "joints" in tier_names
    assert "hidden" not in tier_names


def test_detail_cut_primary_is_one_step_heavier_than_section():
    """Detail cut_primary is 1.00 mm = 1 ISO step heavier than section per Ching p.27."""
    section_cut = next(t for t in SECTION_ISO_PRINT if t.name == "cut").weight_pt
    detail_cut = next(t for t in DETAIL_ISO_PRINT if t.name == "cut_primary").weight_pt
    assert detail_cut > section_cut
    assert abs(detail_cut - mm(1.00)) < 0.01


def test_detail_has_extra_subtiers():
    """Detail has more sub-tiers than section because annotation density is higher."""
    assert len(DETAIL_ISO_PRINT) >= len(SECTION_ISO_PRINT)
    detail_names = {t.name for t in DETAIL_ISO_PRINT}
    # Required new sub-tiers per the research doc
    assert "cut_primary" in detail_names
    assert "cut_secondary" in detail_names
    assert "annotation" in detail_names


# --------------------------------------------------------------------------- #
# select_preset() routing
# --------------------------------------------------------------------------- #


def test_select_preset_routes_each_drawing_type():
    """Each drawing-type string resolves to its own ladder."""
    section = select_preset("section", "1/4", for_print=True)
    plan = select_preset("plan", "1/4", for_print=True)
    elevation = select_preset("elevation", "1/4", for_print=True)
    detail = select_preset("detail", "1/4", for_print=True)

    assert {t.name for t in section} != {t.name for t in plan}
    assert {t.name for t in plan} != {t.name for t in elevation}
    assert {t.name for t in elevation} != {t.name for t in detail}


def test_select_preset_unknown_drawing_type_falls_back_to_section():
    """Unknown drawing types fall back gracefully to section."""
    p = select_preset("nonexistent", "1/4", for_print=True)
    section = select_preset("section", "1/4", for_print=True)
    assert {t.name for t in p} == {t.name for t in section}


def test_select_preset_screen_is_lighter_for_each_type():
    """Screen weights are uniformly lighter than print across all drawing types."""
    for dtype in ("section", "plan", "elevation", "detail"):
        screen = select_preset(dtype, "1/4", for_print=False)
        print_ = select_preset(dtype, "1/4", for_print=True)
        # Heaviest tier on print is heavier than heaviest on screen
        max_print = max(t.weight_pt for t in print_)
        max_screen = max(t.weight_pt for t in screen)
        assert max_print > max_screen, f"{dtype}: print should be heavier than screen"


# --------------------------------------------------------------------------- #
# Scale shifts — anchored at 1/4" baseline (offset 0)
# --------------------------------------------------------------------------- #


def test_scale_baseline_at_quarter_inch():
    """Scale 1/4 returns the unshifted print ladder."""
    baseline = select_preset("section", "1/4", for_print=True)
    section_print = SECTION_ISO_PRINT
    for a, b in zip(baseline, section_print, strict=True):
        assert abs(a.weight_pt - b.weight_pt) < 0.001


def test_scale_eighth_inch_is_one_step_lighter():
    """1/8 scale shifts everything 1 ISO step lighter."""
    quarter = select_preset("section", "1/4", for_print=True)
    eighth = select_preset("section", "1/8", for_print=True)
    cut_quarter = next(t for t in quarter if t.name == "cut").weight_pt
    cut_eighth = next(t for t in eighth if t.name == "cut").weight_pt
    assert cut_eighth < cut_quarter
    # 0.70 → 0.50 mm
    assert abs(cut_eighth - mm(0.50)) < 0.05


def test_scale_half_inch_is_one_step_heavier():
    """1/2 scale shifts everything 1 ISO step heavier."""
    quarter = select_preset("section", "1/4", for_print=True)
    half = select_preset("section", "1/2", for_print=True)
    cut_quarter = next(t for t in quarter if t.name == "cut").weight_pt
    cut_half = next(t for t in half if t.name == "cut").weight_pt
    assert cut_half > cut_quarter
    # 0.70 → 1.00 mm
    assert abs(cut_half - mm(1.00)) < 0.05


def test_scale_sixteenth_inch_is_two_steps_lighter():
    """1/16 scale shifts everything 2 ISO steps lighter."""
    quarter = select_preset("section", "1/4", for_print=True)
    sixteenth = select_preset("section", "1/16", for_print=True)
    cut_quarter = next(t for t in quarter if t.name == "cut").weight_pt
    cut_sixteenth = next(t for t in sixteenth if t.name == "cut").weight_pt
    assert cut_sixteenth < cut_quarter
    # 0.70 → 0.35 mm (2 ISO steps lighter)
    assert abs(cut_sixteenth - mm(0.35)) < 0.05


def test_scale_full_clamps_at_top():
    """Full scale clamps at the top of the ISO ladder (2.00 mm)."""
    full = select_preset("section", "full", for_print=True)
    cut = next(t for t in full if t.name == "cut").weight_pt
    # 0.70 mm + 4 steps would overshoot; clamp to 2.00 mm
    assert abs(cut - mm(2.00)) < 0.05


# --------------------------------------------------------------------------- #
# Detail at scale — heaviest possible
# --------------------------------------------------------------------------- #


def test_detail_at_half_scale_is_extra_heavy():
    """Detail cut_primary at 1/2 scale shifts to 1.40 mm."""
    half_detail = select_preset("detail", "1/2", for_print=True)
    cut_primary = next(t for t in half_detail if t.name == "cut_primary").weight_pt
    # 1.00 mm + 1 step = 1.40 mm
    assert abs(cut_primary - mm(1.40)) < 0.05


def test_plan_at_sixteenth_is_very_light():
    """Plan walls_cut at 1/16 scale shifts to 0.25 mm."""
    sixteenth_plan = select_preset("plan", "1/16", for_print=True)
    walls_cut = next(t for t in sixteenth_plan if t.name == "walls_cut").weight_pt
    # 0.50 mm − 2 steps = 0.25 mm
    assert abs(walls_cut - mm(0.25)) < 0.05
