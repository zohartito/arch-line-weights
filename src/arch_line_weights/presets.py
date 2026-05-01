"""Built-in tier presets for common architectural drawing types.

A preset is just a list of tier definitions: name, target weight (pt), and a
human description of what belongs there.

Presets do NOT auto-assign colors — they only define the weight ladder.
The color → tier mapping is the job of `classify` (auto) or a user JSON file.

v0.5 (2026-04-30): the legacy four hand-tuned lists are retained for
backward-compatibility, but `select_preset()` now resolves to ISO-128-aligned
ladders per drawing type (section / plan / elevation / detail) and per scale.
The research informing this is `docs/research/preset-families.md`.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Tier:
    name: str
    weight_pt: float
    description: str


# ---------------------------------------------------------------------------- #
# Legacy hand-tuned presets (v0.3 — preserved for back-compat)
# ---------------------------------------------------------------------------- #

SECTION = [
    Tier(
        "cut", 1.0, "Section cut line — what the section plane slices through (walls, floors, roof, ground)."
    ),
    Tier("profile", 0.5, "Foreground object profiles in elevation behind the cut."),
    Tier("edges", 0.3, "Object edges, surface changes, structural members."),
    Tier("material", 0.18, "Material indication, surface tone, dashed/dotted accents."),
    Tier("texture", 0.08, "Hatch / pattern / wood grain / poché — densest line work."),
    Tier("special", 0.25, "Glazing, water, sky — non-architectural elements."),
]

PLAN = [
    Tier("walls_cut", 1.0, "Walls cut by the plan slice (typically ~4' above floor)."),
    Tier("walls_full", 0.5, "Walls in full elevation behind the cut."),
    Tier("furniture", 0.3, "Furniture, fixtures, equipment outlines."),
    Tier("texture", 0.18, "Floor pattern, tile, surface texture."),
    Tier("background", 0.08, "Beyond — distant context."),
    Tier("special", 0.25, "Glazing, water."),
]

ELEVATION = [
    Tier("silhouette", 1.0, "Outermost edge of the building."),
    Tier("major", 0.5, "Major surface breaks, building corners."),
    Tier("openings", 0.3, "Windows, doors, balconies."),
    Tier("material", 0.18, "Material breaks, panel joints."),
    Tier("texture", 0.08, "Surface texture, shadow lines."),
    Tier("special", 0.25, "Glazing reflections."),
]

DETAIL = [
    Tier("cut", 1.5, "Section cut at detail scale — extra heavy."),
    Tier("profile", 0.7, "Profile of foreground objects."),
    Tier("edges", 0.4, "Edges and material breaks."),
    Tier("material", 0.25, "Material indication."),
    Tier("texture", 0.13, "Hatching, fastener detail."),
    Tier("special", 0.3, "Special elements."),
]

PRESETS: dict[str, list[Tier]] = {
    "section": SECTION,
    "plan": PLAN,
    "elevation": ELEVATION,
    "detail": DETAIL,
}


def get_preset(name: str) -> list[Tier]:
    if name not in PRESETS:
        raise KeyError(f"unknown preset {name!r}; available: {sorted(PRESETS)}")
    return PRESETS[name]


# ---------------------------------------------------------------------------- #
# ISO 128 / standards-aligned weights (v0.4 + v0.5 expansion)
# ---------------------------------------------------------------------------- #
#
# Per ISO 128-20, line widths follow a √2 geometric series:
#     0.13, 0.18, 0.25, 0.35, 0.50, 0.70, 1.00, 1.40, 2.00 mm
# Conversion: pt = mm × 2.835 (PostScript points)
#
# v0.5: each drawing type has its own ladder anchored to its conventional
# "heaviest line" role:
#   - section.cut      = 0.70 mm  (the slice plane is the heaviest line)
#   - plan.walls_cut   = 0.50 mm  (1 ISO step lighter than section per
#                                  Ramsey/Sleeper §1.4 + Ching p.60)
#   - elevation.silhouette = 0.70 mm (no cut tier; silhouette is heaviest)
#   - detail.cut_primary = 1.00 mm (1 step heavier than section per Ching p.27)
#
# Per Ramsey/Sleeper, Ching, and NCS, plot scale shifts the tier values
# uniformly. v0.5 anchors at 1/4"=1' baseline (offset = 0):
#   1/16"=1' → -2 ISO steps
#   1/8"=1'  → -1 ISO step
#   1/4"=1'  →  0 (baseline)
#   1/2"=1'  → +1 ISO step
#   1"=1'    → +2 ISO steps
#
# Screen weights are computed from print weights × 1.7 (per ISO 128 +
# Adobe Acrobat rendering thresholds), clamped at 0.5 pt visual minimum.
#
# See docs/research/preset-families.md for full citations.

MM_TO_PT = 2.835


def mm(x: float) -> float:
    """Convert millimetres to PostScript points (rounded to 3 dp)."""
    return round(x * MM_TO_PT, 3)


# ISO 128 √2 ladder (mm), used for scale-shift offsets
_ISO_LADDER_MM = [0.13, 0.18, 0.25, 0.35, 0.50, 0.70, 1.00, 1.40, 2.00]
_ISO_LADDER_PT = [mm(x) for x in _ISO_LADDER_MM]


# ---------------------------------------------------------------------------- #
# Section preset family
# ---------------------------------------------------------------------------- #

SECTION_ISO_PRINT = [
    Tier("cut", mm(0.70), "Section cut at 1/4\"=1' — Ramsey/Sleeper / NCS v6"),
    Tier("profile", mm(0.50), "Profile / foreground silhouette"),
    Tier("edges", mm(0.35), "Object edges, plane intersections"),
    Tier("hidden", mm(0.25), "Hidden / centerline / dashed"),
    Tier("material", mm(0.18), "Material indication, hatching"),
    Tier("texture", mm(0.13), "Texture, very light poché, background"),
    Tier("special", mm(0.25), "Glazing, water, sky"),
]

SECTION_ISO_SCREEN = [
    Tier("cut", 1.0, "Section cut, screen-review weight"),
    Tier("profile", 0.5, "Profile / foreground silhouette"),
    Tier("edges", 0.3, "Object edges"),
    Tier("hidden", 0.18, "Hidden / centerline"),
    Tier("material", 0.13, "Material indication"),
    Tier("texture", 0.08, "Texture / hatch"),
    Tier("special", 0.25, "Glazing"),
]


# ---------------------------------------------------------------------------- #
# Plan preset family — cut is 1 ISO step lighter than section
# (Ramsey/Sleeper §1.4, Ching p.60)
# ---------------------------------------------------------------------------- #

PLAN_ISO_PRINT = [
    Tier("walls_cut", mm(0.50), "Walls cut by plan slice (~4' AFF) — 1 step lighter than section"),
    Tier("casework", mm(0.35), "Built-in millwork, counters, stairs"),
    Tier("furniture", mm(0.25), "Loose furniture, fixtures, equipment, plumbing"),
    Tier("pattern", mm(0.18), "Floor pattern (tile, hardwood seams), door swings"),
    Tier("site", mm(0.18), "Trees, parking, landscape, contours"),
    Tier("texture", mm(0.13), "Floor poché tone, ground pattern"),
    Tier("special", mm(0.25), "Glazing in plan, water features"),
]

PLAN_ISO_SCREEN = [
    Tier("walls_cut", 0.71, "Walls cut, screen weight"),
    Tier("casework", 0.5, "Built-in millwork"),
    Tier("furniture", 0.35, "Furniture, fixtures"),
    Tier("pattern", 0.25, "Floor pattern, door swings"),
    Tier("site", 0.25, "Site context"),
    Tier("texture", 0.18, "Floor poché"),
    Tier("special", 0.35, "Glazing"),
]


# ---------------------------------------------------------------------------- #
# Elevation preset family — no cut tier; silhouette is heaviest
# (ISO 128-30:2001 §4.2)
# ---------------------------------------------------------------------------- #

ELEVATION_ISO_PRINT = [
    Tier("silhouette", mm(0.70), "Outermost edge of the building against sky/ground"),
    Tier("profile", mm(0.50), "Major form breaks, building corners, roof eave"),
    Tier("openings", mm(0.35), "Windows, doors, balcony rails, recessed elements"),
    Tier("joints", mm(0.25), "Material joints, panel breaks, control joints, reveals"),
    Tier("material", mm(0.18), "Material patterning (brick coursing, siding, panel grid)"),
    Tier("texture", mm(0.13), "Surface texture, shadow lines, light reveal"),
    Tier("special", mm(0.25), "Glazing, glazing reflections, water"),
]

ELEVATION_ISO_SCREEN = [
    Tier("silhouette", 1.0, "Building silhouette, screen weight"),
    Tier("profile", 0.71, "Major breaks"),
    Tier("openings", 0.5, "Windows, doors"),
    Tier("joints", 0.35, "Joints, reveals"),
    Tier("material", 0.25, "Material pattern"),
    Tier("texture", 0.18, "Surface texture"),
    Tier("special", 0.35, "Glazing"),
]


# ---------------------------------------------------------------------------- #
# Detail preset family — 1 ISO step heavier than section (Ching p.27)
# Includes extra sub-tiers because annotation density is higher at detail scale
# ---------------------------------------------------------------------------- #

DETAIL_ISO_PRINT = [
    Tier("cut_primary", mm(1.00), "Primary section cut (structural, masonry, concrete)"),
    Tier("cut_secondary", mm(0.70), "Secondary cut (insulation outline, panel layer)"),
    Tier("profile", mm(0.50), "Profile / foreground silhouette in elevation behind cut"),
    Tier("edges", mm(0.35), "Material edges, fastener heads, gasket compression"),
    Tier("hidden", mm(0.25), "Hidden / centerline / dashed"),
    Tier("material", mm(0.25), "Material indication (more visible at detail scale)"),
    Tier("texture", mm(0.18), "Hatching, fastener thread detail"),
    Tier("annotation", mm(0.18), "Dimension lines, leader lines, callouts"),
    Tier("special", mm(0.30), "Glazing, gaskets shown distinctly"),
]

DETAIL_ISO_SCREEN = [
    Tier("cut_primary", 1.5, "Primary cut at detail scale, screen weight"),
    Tier("cut_secondary", 1.0, "Secondary cut"),
    Tier("profile", 0.71, "Profile"),
    Tier("edges", 0.5, "Material edges"),
    Tier("hidden", 0.35, "Hidden / centerline"),
    Tier("material", 0.35, "Material indication"),
    Tier("texture", 0.25, "Hatching"),
    Tier("annotation", 0.25, "Dimensions"),
    Tier("special", 0.42, "Glazing"),
]


# ---------------------------------------------------------------------------- #
# Scale-shift table — anchored at 1/4" baseline (offset 0)
# Per Ching p.27 + NCS v6 Plotting Guidelines §5.3
# ---------------------------------------------------------------------------- #

_SCALE_SHIFTS: dict[str, int] = {
    # 1/16" → -2 (cut: 0.70 → 0.35 mm)
    "1/16": -2,
    "1/16\"=1'": -2,
    "1/16=1'": -2,
    # 1/8" → -1 (cut: 0.70 → 0.50 mm)
    "1/8": -1,
    "1/8\"=1'": -1,
    "1/8=1'": -1,
    # 1/4" → 0 (baseline; cut: 0.70 mm)
    "1/4": 0,
    "1/4\"=1'": 0,
    "1/4=1'": 0,
    # 1/2" → +1 (cut: 0.70 → 1.00 mm)
    "1/2": 1,
    "1/2\"=1'": 1,
    "1/2=1'": 1,
    # 1" → +2 (cut: 0.70 → 1.40 mm)
    "1": 2,
    "1\"=1'": 2,
    "1=1'": 2,
    # 3" → +3 (cut: 0.70 → 2.00 mm)
    "3": 3,
    "3\"=1'": 3,
    "3=1'": 3,
    # full → +4 (clamped at 2.00 mm)
    "full": 4,
}


_ISO_PRINT_FAMILIES: dict[str, list[Tier]] = {
    "section": SECTION_ISO_PRINT,
    "plan": PLAN_ISO_PRINT,
    "elevation": ELEVATION_ISO_PRINT,
    "detail": DETAIL_ISO_PRINT,
}

_ISO_SCREEN_FAMILIES: dict[str, list[Tier]] = {
    "section": SECTION_ISO_SCREEN,
    "plan": PLAN_ISO_SCREEN,
    "elevation": ELEVATION_ISO_SCREEN,
    "detail": DETAIL_ISO_SCREEN,
}


def _shift_tier_iso(tier: Tier, shift: int) -> Tier:
    """Shift a tier's weight along the ISO 128 √2 ladder by `shift` steps.

    Positive shift = heavier (e.g. +1 = 0.50 → 0.70 mm).
    Negative shift = lighter (e.g. -1 = 0.50 → 0.35 mm).
    Clamped to ladder bounds.
    """
    if shift == 0 or not _ISO_LADDER_PT:
        return tier
    # Find nearest ladder index to current weight
    nearest_idx = min(
        range(len(_ISO_LADDER_PT)),
        key=lambda i: abs(_ISO_LADDER_PT[i] - tier.weight_pt),
    )
    new_idx = max(0, min(len(_ISO_LADDER_PT) - 1, nearest_idx + shift))
    return Tier(tier.name, _ISO_LADDER_PT[new_idx], tier.description)


def select_preset(
    drawing_type: str = "section",
    scale: str = "1/4",
    for_print: bool = False,
) -> list[Tier]:
    """Return the right tier ladder for drawing type, scale, and print/screen.

    Examples:
        select_preset("section",   "1/4", for_print=True)  → SECTION_ISO_PRINT (cut: 0.70 mm)
        select_preset("plan",      "1/8", for_print=True)  → PLAN_ISO_PRINT shifted -1 (cut: 0.35 mm)
        select_preset("elevation", "1/4", for_print=False) → ELEVATION_ISO_SCREEN
        select_preset("detail",    "1/2", for_print=True)  → DETAIL_ISO_PRINT shifted +1 (cut_primary: 1.40 mm)

    Unknown drawing types fall back to section.
    Unknown scales fall back to the 1/4 baseline (offset 0).
    """
    drawing_type = drawing_type.lower().strip()
    families = _ISO_PRINT_FAMILIES if for_print else _ISO_SCREEN_FAMILIES
    base = families.get(drawing_type, families["section"])

    if not for_print:
        # Screen ladders are not scale-shifted (screen review is at fixed zoom).
        return base

    shift = _SCALE_SHIFTS.get(scale, 0)
    if shift == 0:
        return base

    return [_shift_tier_iso(tier, shift) for tier in base]


__all__ = [
    "DETAIL",
    "DETAIL_ISO_PRINT",
    "DETAIL_ISO_SCREEN",
    "ELEVATION",
    "ELEVATION_ISO_PRINT",
    "ELEVATION_ISO_SCREEN",
    "MM_TO_PT",
    "PLAN",
    "PLAN_ISO_PRINT",
    "PLAN_ISO_SCREEN",
    "PRESETS",
    "SECTION",
    "SECTION_ISO_PRINT",
    "SECTION_ISO_SCREEN",
    "Tier",
    "get_preset",
    "mm",
    "select_preset",
]
