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
