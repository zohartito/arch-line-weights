"""Architectural semantic layer interpretation.

This is a higher-level overlay on top of the source-specific layer classifier.
It is intentionally conservative: it lets layer names drive hierarchy and
poché eligibility before color luminance gets a vote.
"""

from __future__ import annotations

from dataclasses import dataclass

from .layer_classify import Source
from .presets import mm, select_preset


@dataclass(frozen=True)
class ArchitecturalAssignment:
    tier: str
    weight_pt: float
    semantic: str
    poche: bool
    open_loop_closure: bool
    confidence: float
    why: str


_CUT_MARKERS = ("CLIPPINGPLANEINTERSECTIONS", "SECTION_CUT")

_ENTOURAGE = (
    "ENTOURAGE",
    "SCALE_FIGURE",
    "SCALEFIGURE",
    "PEOPLE",
    "PERSON",
    "HUMAN",
    "FIGURE",
)

_REFERENCE = ("FLOOR_DATUMS", "_DATUM", "_GRID", "_REF", "REFERENCE")
_ANNOTATION = ("_DIM", "_TEXT", "_TAG", "ANNOTATION", "NOTES")

_GLASS = ("WINDOW_IGU_GLASS", "WINDOW_GLASS", "GLASS", "IGU", "GLAZING")
_WINDOW_FRAME = (
    "WINDOW_FRAME",
    "WINDOW_ALUM_FRAME",
    "FRAMES_REMAP",
    "MULLION",
    "SASH",
    "JAMB",
    "WINDOW_HEAD",
    "WINDOW_SILL",
)

_MEMBRANE = ("EPDM", "_MEM_", "_WP_", "MEMBRANE", "SEALANT", "FLASHING", "TPO")
_INSULATION = ("_INS_", "_MW_", "_RW_", "_XPS_", "_PIR_", "INSULATION")

_CONNECTOR = (
    "TEC_STEEL_CONNECTOR",
    "CONNECTOR",
    "L-BRACKET",
    "BRACKET",
    "CLEAT",
    "CLEAT_PLATE",
    "_CLIP_",
    "CLIP_",
    "_CLIP",
    "CLIPS",
    "FASTENER",
    "BOLT",
    "SCREW",
    "STRAP",
    "ANCHOR",
)

_CLADDING = (
    "_CU_CORR_",
    "_CU_FLAT_",
    "_CU_PUNCH_",
    "CU_CORR",
    "CU_FLAT",
    "CU_PUNCH",
    "PUNCH_RETURNS",
    "PERF_SCREEN",
    "SCREEN",
    "CLADDING",
    "RAINSCREEN",
    "FACADE",
    "FACADE_PANEL",
    "COPPER_PANEL",
    "METAL_PANEL",
    "SPANDREL",
)

_STRUCTURAL_SOLID = (
    "TEC_FOUNDATION",
    "FOUNDATION",
    "FOOTING",
    "TEC_CONCRETE_BASE",
    "CONCRETE",
    "TEC_CLT_SLABS",
    "TEC_ROOF_CLT",
    "CLT_BACKUP",
    "_CLT_BACKUP_",
    "CLT_THICK",
    "_CLT_THICK_",
    "CLT_GAP_ROOF",
    "_CLT_GAP_ROOF_",
    "TEC_TIMBER",
    "TIMBER_BEAM",
    "TIMBER_COLUMN",
    "TIMBER",
    "SLAB",
)

_SECONDARY_STEEL = ("_SHS_", "_RHS_", "_CHS_", "_UC_", "_UB_", "_STL_", "HSS", "STEEL_FRAME")


_SECTION_SCREEN_WEIGHTS = {
    "cut": 1.0,
    "profile": 0.5,
    "structure_primary": 0.5,
    "structure_secondary": 0.25,
    "frames": 0.3,
    "edges_secondary": 0.3,
    "connectors": 0.18,
    "glazing": 0.25,
    "cladding": 0.18,
    "material_minor": 0.13,
    "insulation": 0.13,
    "reference": 0.13,
    "annotation": 0.13,
    "entourage": 0.13,
    "texture": 0.08,
    "default": 0.25,
}

_PRESET_TIER = {
    "cut": {"section": "cut", "plan": "walls_cut", "elevation": "silhouette", "detail": "cut_primary"},
    "profile": {"section": "profile", "plan": "casework", "elevation": "profile", "detail": "profile"},
    "structure_primary": {"section": "profile", "plan": "casework", "elevation": "profile", "detail": "cut_secondary"},
    "structure_secondary": {"section": None, "plan": "furniture", "elevation": "openings", "detail": "profile"},
    "frames": {"section": "edges", "plan": "furniture", "elevation": "openings", "detail": "profile"},
    "edges_secondary": {"section": "edges", "plan": "furniture", "elevation": "openings", "detail": "edges"},
    "connectors": {"section": "special", "plan": "pattern", "elevation": "joints", "detail": "edges"},
    "glazing": {"section": "special", "plan": "special", "elevation": "special", "detail": "special"},
    "cladding": {"section": "hidden", "plan": "site", "elevation": "material", "detail": "material"},
    "material_minor": {"section": "material", "plan": "texture", "elevation": "texture", "detail": "texture"},
    "insulation": {"section": "material", "plan": "texture", "elevation": "texture", "detail": "texture"},
    "reference": {"section": "material", "plan": "pattern", "elevation": "joints", "detail": "hidden"},
    "annotation": {"section": "material", "plan": "texture", "elevation": "texture", "detail": "annotation"},
    "entourage": {"section": "material", "plan": "texture", "elevation": "texture", "detail": "annotation"},
    "texture": {"section": "texture", "plan": "texture", "elevation": "texture", "detail": "texture"},
    "default": {"section": "special", "plan": "furniture", "elevation": "openings", "detail": "edges"},
}


def _has(haystack: str, patterns: tuple[str, ...]) -> bool:
    return any(pattern in haystack for pattern in patterns)


def _is_cut_context(haystack: str) -> bool:
    return _has(haystack, _CUT_MARKERS)


def architectural_weight_for_tier(
    tier: str,
    *,
    preset: str = "section",
    scale: str = "1/4",
    for_print: bool = False,
) -> float:
    """Return the architectural-mode weight for a semantic tier."""
    preset_key = preset.lower().strip()
    if not for_print and preset_key == "section":
        return _SECTION_SCREEN_WEIGHTS.get(tier, _SECTION_SCREEN_WEIGHTS["default"])

    tiers = select_preset(preset_key, scale=scale, for_print=for_print)
    by_name = {t.name: t.weight_pt for t in tiers}
    preset_tier_name = _PRESET_TIER.get(tier, {}).get(preset_key)
    if preset_tier_name and preset_tier_name in by_name:
        return by_name[preset_tier_name]

    if for_print and tier == "structure_secondary":
        return mm(0.35)
    return _SECTION_SCREEN_WEIGHTS.get(tier, _SECTION_SCREEN_WEIGHTS["default"])


def _assignment(
    tier: str,
    semantic: str,
    *,
    preset: str,
    scale: str,
    for_print: bool,
    poche: bool = False,
    open_loop_closure: bool = False,
    confidence: float = 0.95,
    why: str,
) -> ArchitecturalAssignment:
    return ArchitecturalAssignment(
        tier=tier,
        weight_pt=architectural_weight_for_tier(
            tier,
            preset=preset,
            scale=scale,
            for_print=for_print,
        ),
        semantic=semantic,
        poche=poche,
        open_loop_closure=open_loop_closure,
        confidence=confidence,
        why=why,
    )


def classify_architectural_layer(
    name: str,
    *,
    preset: str = "section",
    scale: str = "1/4",
    for_print: bool = False,
    source: Source = Source.RHINO,
) -> ArchitecturalAssignment:
    """Classify one layer using architectural semantics.

    The rule order is deliberate: non-structural layers such as glass,
    connectors, cladding, membranes, and entourage win before generic
    clipping-plane rules. That prevents dark source colors or cut-layer
    placement from turning facade details into heavy poché.
    """
    del source  # Reserved for future source-specific architectural overlays.
    upper = name.upper()
    cut_context = _is_cut_context(upper)

    if _has(upper, _ENTOURAGE):
        return _assignment(
            "entourage",
            "scale/context figure",
            preset=preset,
            scale=scale,
            for_print=for_print,
            confidence=0.98,
            why="entourage is presentation context, never cut",
        )
    if _has(upper, _REFERENCE):
        return _assignment(
            "reference",
            "datum/reference",
            preset=preset,
            scale=scale,
            for_print=for_print,
            confidence=0.95,
            why="datum/grid/reference layer",
        )
    if _has(upper, _ANNOTATION):
        return _assignment(
            "annotation",
            "annotation",
            preset=preset,
            scale=scale,
            for_print=for_print,
            confidence=0.95,
            why="annotation/dimension layer",
        )
    if _has(upper, _GLASS):
        return _assignment(
            "glazing",
            "glass/glazing",
            preset=preset,
            scale=scale,
            for_print=for_print,
            confidence=0.97,
            why="glass is transparent enclosure, never poché",
        )
    if _has(upper, _WINDOW_FRAME):
        return _assignment(
            "frames",
            "window/frame edge",
            preset=preset,
            scale=scale,
            for_print=for_print,
            confidence=0.95,
            why="window/frame layer is outline detail, not solid cut mass",
        )
    if _has(upper, _MEMBRANE):
        return _assignment(
            "material_minor",
            "membrane/sealant/flashing",
            preset=preset,
            scale=scale,
            for_print=for_print,
            confidence=0.95,
            why="membrane/sealant layer is material indication",
        )
    if _has(upper, _INSULATION):
        return _assignment(
            "insulation",
            "insulation/material hatch",
            preset=preset,
            scale=scale,
            for_print=for_print,
            confidence=0.95,
            why="insulation layer is material indication",
        )
    if _has(upper, _CONNECTOR):
        return _assignment(
            "connectors",
            "connector/detail hardware",
            preset=preset,
            scale=scale,
            for_print=for_print,
            confidence=0.95,
            why="connector/bracket/hardware stays subordinate to cut mass",
        )
    if _has(upper, _CLADDING):
        return _assignment(
            "cladding",
            "facade/cladding/screen",
            preset=preset,
            scale=scale,
            for_print=for_print,
            confidence=0.95,
            why="facade screen/cladding is enclosure surface, not poché",
        )
    if cut_context and _has(upper, _STRUCTURAL_SOLID):
        return _assignment(
            "cut",
            "structural cut solid",
            preset=preset,
            scale=scale,
            for_print=for_print,
            poche=True,
            open_loop_closure=True,
            confidence=0.96,
            why="structural solid in clipping-plane context",
        )
    if _has(upper, _STRUCTURAL_SOLID):
        return _assignment(
            "structure_primary",
            "primary structural profile",
            preset=preset,
            scale=scale,
            for_print=for_print,
            confidence=0.90,
            why="primary structural layer seen beyond cut",
        )
    if _has(upper, _SECONDARY_STEEL):
        return _assignment(
            "structure_secondary",
            "secondary steel framing",
            preset=preset,
            scale=scale,
            for_print=for_print,
            confidence=0.90,
            why="secondary steel frame layer",
        )
    if cut_context:
        return _assignment(
            "cut",
            "generic clipping-plane intersection",
            preset=preset,
            scale=scale,
            for_print=for_print,
            confidence=0.45,
            why="generic clipped layer; not poché-eligible without structural material evidence",
        )
    return _assignment(
        "default",
        "unclassified architectural layer",
        preset=preset,
        scale=scale,
        for_print=for_print,
        confidence=0.20,
        why="no architectural pattern match",
    )


def architectural_layer_weight_resolver(
    *,
    preset: str = "section",
    scale: str = "1/4",
    for_print: bool = False,
    source: Source = Source.RHINO,
):
    """Return a callback suitable for apply_saas.rewrite_payload."""

    def _resolve(layer_name: str) -> float | None:
        assignment = classify_architectural_layer(
            layer_name,
            preset=preset,
            scale=scale,
            for_print=for_print,
            source=source,
        )
        if assignment.confidence < 0.80 and assignment.tier == "default":
            return None
        return assignment.weight_pt

    return _resolve


__all__ = [
    "ArchitecturalAssignment",
    "architectural_layer_weight_resolver",
    "architectural_weight_for_tier",
    "classify_architectural_layer",
]
