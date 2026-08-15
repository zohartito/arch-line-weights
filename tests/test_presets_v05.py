"""v0.5 preset families — distinct ladders for plan / elevation / detail / section.

Per docs/research/preset-families.md, each drawing type uses the same ISO 128
ladder anchored to a different "heaviest line" role.
"""

from __future__ import annotations

from arch_line_weights.presets import (
    DETAIL_ISO_PRINT,
    DETAIL_ISO_SCREEN,
    ELEVATION,
    ELEVATION_ISO_PRINT,
    ELEVATION_ISO_SCREEN,
    PLAN_ISO_PRINT,
    PLAN_ISO_SCREEN,
    PRESETS,
    SECTION_ISO_PRINT,
    SECTION_ISO_SCREEN,
    STUDIO,
    STUDIO_PRINT,
    STUDIO_SCREEN,
    USC,
    USC_STUDIO_PRINT,
    USC_STUDIO_SCREEN,
    get_preset,
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


def test_studio_preset_exists_for_reference_studio_workflow():
    """Studio preset keeps the reference screen-review hierarchy explicit."""
    assert "studio" in PRESETS
    tiers = {t.name: t.weight_pt for t in get_preset("studio")}
    assert tiers["cut"] == 1.0
    assert tiers["profile"] == 0.5
    assert tiers["edges"] == 0.3
    assert tiers["material"] == 0.18
    assert tiers["texture"] == 0.08
    assert tiers["special"] == 0.25


def test_studio_print_table_documents_studio_convention():
    """Studio 1/4-inch print convention uses 0.13 mm for hatch/texture."""
    tiers = {t.name: t.weight_pt for t in select_preset("studio", "1/4", for_print=True)}
    assert tiers["cut"] == mm(0.70)
    assert tiers["profile"] == mm(0.50)
    assert tiers["edges"] == mm(0.35)
    assert tiers["material"] == mm(0.18)
    assert tiers["texture"] == mm(0.13)
    assert tiers["special"] == mm(0.25)


def test_studio_screen_and_print_families_are_routed_directly():
    assert select_preset("studio", "1/4", for_print=False) == STUDIO_SCREEN
    assert select_preset("studio", "1/4", for_print=True) == STUDIO_PRINT


def test_usc_is_a_deprecated_working_alias_for_studio():
    """`usc` continues to resolve to the exact same tier data as `studio`."""
    assert "usc" in PRESETS
    # Same registered preset object as studio.
    assert PRESETS["usc"] == PRESETS["studio"]
    assert get_preset("usc") == get_preset("studio")
    # select_preset() routes usc identically to studio, screen and print.
    for scale in ("1/16", "1/8", "1/4", "1/2"):
        for for_print in (False, True):
            assert select_preset("usc", scale, for_print=for_print) == select_preset(
                "studio", scale, for_print=for_print
            )


def test_deprecated_usc_studio_import_names_still_resolve():
    """The pre-rename module-level names remain importable as aliases."""
    assert USC is STUDIO
    assert USC_STUDIO_PRINT is STUDIO_PRINT
    assert USC_STUDIO_SCREEN is STUDIO_SCREEN


def test_studio_and_usc_resolve_identical_role_weight_mappings():
    """The role→weight ladder (the path --auto uses) is identical for both."""
    from arch_line_weights.preset_rules import ladder_for_preset

    for scale in ("1/16", "1/8", "1/4", "1/2"):
        for for_print in (False, True):
            assert ladder_for_preset("studio", scale=scale, for_print=for_print) == ladder_for_preset(
                "usc", scale=scale, for_print=for_print
            )


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


def test_axon_and_paraline_presets_are_registered_as_elevation_no_cut_family():
    """Axon/paraline are first-class presets that reuse elevation's no-cut ladder."""
    assert "axon" in PRESETS
    assert "paraline" in PRESETS
    assert get_preset("axon") == ELEVATION
    assert get_preset("paraline") == ELEVATION
    assert select_preset("axon", "1/4", for_print=False) == ELEVATION_ISO_SCREEN
    assert select_preset("paraline", "1/4", for_print=False) == ELEVATION_ISO_SCREEN
    assert select_preset("axon", "1/4", for_print=True) == ELEVATION_ISO_PRINT
    assert select_preset("paraline", "1/4", for_print=True) == ELEVATION_ISO_PRINT


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
