"""Built-in tier presets for common architectural drawing types.

A preset is just a list of tier definitions: name, target weight (pt), and a
human description of what belongs there.

Presets do NOT auto-assign colors — they only define the weight ladder.
The color → tier mapping is the job of `classify` (auto) or a user JSON file.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Tier:
    name: str
    weight_pt: float
    description: str


SECTION = [
    Tier("cut",      1.0,  "Section cut line — what the section plane slices through (walls, floors, roof, ground)."),
    Tier("profile",  0.5,  "Foreground object profiles in elevation behind the cut."),
    Tier("edges",    0.3,  "Object edges, surface changes, structural members."),
    Tier("material", 0.18, "Material indication, surface tone, dashed/dotted accents."),
    Tier("texture",  0.08, "Hatch / pattern / wood grain / poché — densest line work."),
    Tier("special",  0.25, "Glazing, water, sky — non-architectural elements."),
]

PLAN = [
    Tier("walls_cut",  1.0,  "Walls cut by the plan slice (typically ~4' above floor)."),
    Tier("walls_full", 0.5,  "Walls in full elevation behind the cut."),
    Tier("furniture",  0.3,  "Furniture, fixtures, equipment outlines."),
    Tier("texture",    0.18, "Floor pattern, tile, surface texture."),
    Tier("background", 0.08, "Beyond — distant context."),
    Tier("special",    0.25, "Glazing, water."),
]

ELEVATION = [
    Tier("silhouette", 1.0,  "Outermost edge of the building."),
    Tier("major",      0.5,  "Major surface breaks, building corners."),
    Tier("openings",   0.3,  "Windows, doors, balconies."),
    Tier("material",   0.18, "Material breaks, panel joints."),
    Tier("texture",    0.08, "Surface texture, shadow lines."),
    Tier("special",    0.25, "Glazing reflections."),
]

DETAIL = [
    Tier("cut",      1.5,  "Section cut at detail scale — extra heavy."),
    Tier("profile",  0.7,  "Profile of foreground objects."),
    Tier("edges",    0.4,  "Edges and material breaks."),
    Tier("material", 0.25, "Material indication."),
    Tier("texture",  0.13, "Hatching, fastener detail."),
    Tier("special",  0.3,  "Special elements."),
]

PRESETS: dict[str, list[Tier]] = {
    "section":   SECTION,
    "plan":      PLAN,
    "elevation": ELEVATION,
    "detail":    DETAIL,
}


def get_preset(name: str) -> list[Tier]:
    if name not in PRESETS:
        raise KeyError(f"unknown preset {name!r}; available: {sorted(PRESETS)}")
    return PRESETS[name]


# ---------------------------------------------------------------------------- #
# ISO 128 / standards-aligned weights (v0.4)
# ---------------------------------------------------------------------------- #
#
# Per ISO 128-20, line widths follow a √2 geometric series:
#     0.13, 0.18, 0.25, 0.35, 0.50, 0.70, 1.00, 1.40, 2.00 mm
# Conversion: pt = mm × 2.835 (PostScript points)
#
# Per Ramsey/Sleeper, Ching, and NCS, plot scale shifts the tier values:
#   1/16"=1' → one ISO step thinner than 1/8"
#   1/8"=1'  → baseline offset
#   1/4"=1'  → one step heavier
#   1/2"=1'  → two steps heavier
#
# Screen review can stay at the lighter end since fine lines vanish on screens
# below ~96 dpi; print needs heavier weights to read at full size.
#
# See docs/research/standards.md for full citations.

MM_TO_PT = 2.835


def mm(x: float) -> float:
    """Convert millimetres to PostScript points (rounded to 3 dp)."""
    return round(x * MM_TO_PT, 3)


# Section preset following NCS / Ramsey-Sleeper at 1/4"=1'-0", PRINT
SECTION_ISO_PRINT = [
    Tier("cut",      mm(0.70), "Section cut at 1/4\"=1' — Ramsey/Sleeper"),
    Tier("profile",  mm(0.50), "Profile / foreground silhouette"),
    Tier("edges",    mm(0.35), "Object edges, plane intersections"),
    Tier("hidden",   mm(0.25), "Hidden / centerline / dashed"),
    Tier("material", mm(0.18), "Material indication, hatching"),
    Tier("texture",  mm(0.13), "Texture, very light poché, background"),
    Tier("special",  mm(0.25), "Glazing, water, sky"),
]

# Same set, screen-review (1.5× lighter so they don't dominate at 100% zoom)
SECTION_ISO_SCREEN = [
    Tier("cut",      1.0,  "Section cut, screen-review weight"),
    Tier("profile",  0.5,  "Profile / foreground silhouette"),
    Tier("edges",    0.3,  "Object edges"),
    Tier("hidden",   0.18, "Hidden / centerline"),
    Tier("material", 0.13, "Material indication"),
    Tier("texture",  0.08, "Texture / hatch"),
    Tier("special",  0.25, "Glazing"),
]

DETAIL_ISO_PRINT = [
    Tier("cut",      mm(1.00), "Section cut at detail scale"),
    Tier("profile",  mm(0.70), "Profile / foreground"),
    Tier("edges",    mm(0.50), "Edges"),
    Tier("hidden",   mm(0.35), "Hidden"),
    Tier("material", mm(0.25), "Material hatch"),
    Tier("texture",  mm(0.18), "Texture"),
    Tier("special",  mm(0.30), "Glazing"),
]


_SCALE_SHIFTS = {
    "1/16": -1, "1/16\"=1'": -1, "1/16=1'": -1,
    "1/8":   0, "1/8\"=1'":   0, "1/8=1'":   0,
    "1/4":   1, "1/4\"=1'":   1, "1/4=1'":   1,
    "1/2":   2, "1/2\"=1'":   2, "1/2=1'":   2,
    "1\"=1'": 3, "1=1'": 3,
}


def select_preset(
    drawing_type: str = "section",
    scale: str = "1/4",
    for_print: bool = False,
) -> list[Tier]:
    """Return the right tier ladder for drawing type, scale, and print/screen.

    Examples:
        select_preset("section", "1/4", for_print=True)  → SECTION_ISO_PRINT
        select_preset("section", "1/4", for_print=False) → SECTION_ISO_SCREEN
        select_preset("section", "1/8", for_print=True)  → SECTION_ISO_PRINT shifted lighter
    """
    if not for_print:
        # Screen review uses the lighter end across scales
        base = SECTION_ISO_SCREEN if drawing_type == "section" else PRESETS.get(drawing_type, SECTION_ISO_SCREEN)
        return base

    base = SECTION_ISO_PRINT if drawing_type != "detail" else DETAIL_ISO_PRINT
    shift = _SCALE_SHIFTS.get(scale, 1)  # default 1/4" baseline
    if shift == 1:
        return base

    # Shift each tier on the ISO ladder
    iso_pt = [mm(0.13), mm(0.18), mm(0.25), mm(0.35), mm(0.50), mm(0.70), mm(1.00), mm(1.40), mm(2.00)]
    shifted = []
    for tier in base:
        try:
            idx = iso_pt.index(min(iso_pt, key=lambda v: abs(v - tier.weight_pt)))
        except ValueError:
            shifted.append(tier)
            continue
        new_idx = max(0, min(len(iso_pt) - 1, idx + (shift - 1)))
        shifted.append(Tier(tier.name, iso_pt[new_idx], tier.description))
    return shifted
