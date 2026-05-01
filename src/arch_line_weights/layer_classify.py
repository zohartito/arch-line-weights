"""Semantic layer-name classifier with per-source dispatch.

Originally targeted Rhino's Make2D + ClippingPlane export, where the OCG
hierarchy is::

    <view>::Visible|Hidden::Curves|ClippingPlaneIntersections::<src_layer>

Phase E5 extends the classifier to recognize layer-name conventions from
non-Rhino vector sources. The first additional convention covered here is
AutoCAD / DXF, following the AIA *CAD Layer Guidelines* (incorporated into
the U.S. National CAD Standard, NCS) layer-name format::

    <discipline>-<MAJOR>-<MINOR1>-[MINOR2]-[STATUS]
    e.g. A-WALL-FULL-N      A-GLAZ-SILL      S-COLS-FULL

References for the AIA NCS rules below:
  - NCS v5 Layer Name Format (https://www.nationalcadstandard.org/)
  - AIA CAD Layer Guidelines (Duke Facilities mirror)
  - Seidler Studio "AutoCAD Standard Layer Names: Floor Plans"

The classifier still uses substring matching (with a small amount of
hyphen-anchored matching for AIA NCS, since hyphens disambiguate field
boundaries) so the rules can be lifted into ExtendScript.

Behavior contract:
  - `classify_layer(name)` (no `source=` arg) preserves pre-Phase-E5 Rhino
    behavior 1:1. Existing callers and tests don't change.
  - `classify_layer(name, source=Source.AUTOCAD)` dispatches to the AIA NCS
    pattern library.
  - `detect_source(pdf_metadata, layer_names)` returns `(source, confidence)`
    based on PDF Producer/Creator metadata first, then layer-name shape.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum


class Source(StrEnum):
    """The vector-source convention a layer-name pattern library is tuned for."""

    AUTO = "auto"
    RHINO = "rhino"
    AUTOCAD = "autocad"  # AIA NCS / ISO 13567-2


@dataclass(frozen=True)
class TierAssignment:
    weight_pt: float
    tier: str
    why: str
    source: Source = Source.RHINO
    confidence: float = 1.0


# Per-source baseline confidence when a pattern matches. See
# docs/research/layer-name-patterns.md §3.
SOURCE_BASELINE_CONFIDENCE: dict[Source, float] = {
    Source.RHINO: 0.95,
    Source.AUTOCAD: 0.85,
}


# --------------------------------------------------------------------------- #
# Rhino Make2D + ClippingPlane rules (existing behavior — unchanged)
# --------------------------------------------------------------------------- #

# Order matters — first match wins (most specific patterns first).
RHINO_RULES: list[tuple[str | tuple[str, ...], TierAssignment]] = [
    # 1. Cut — section plane intersection (heaviest, regardless of material)
    ("CLIPPINGPLANEINTERSECTIONS", TierAssignment(1.0, "cut", "section plane intersection")),
    # 2. Glazing — special, lighter than profile
    (("WINDOW_IGU_GLASS", "WINDOW_GLASS"), TierAssignment(0.25, "glazing", "transparent material")),
    # 3. Reference / datum lines
    (
        ("FLOOR_DATUMS", "_DATUM", "_GRID", "_REF"),
        TierAssignment(0.13, "reference", "construction reference"),
    ),
    # 4. Structure primary — heavy load-bearing in elevation
    (
        (
            "TEC_TIMBER",
            "TEC_CLT_SLABS",
            "TEC_ROOF_CLT",
            "TEC_CONCRETE_BASE",
            "TEC_FOUNDATION",
            "_CLT_BACKUP_",
            "_CLT_THICK_",
            "_CLT_GAP_ROOF_",
        ),
        TierAssignment(0.5, "structure_primary", "heavy structural assembly in elevation"),
    ),
    # 5. Stairs (excluding risers — finer)
    ("TEC_STAIR", TierAssignment(0.5, "structure_primary", "stair structure in elevation")),
    # 6. Window frames
    (("WINDOW_FRAME", "WINDOW_ALUM_FRAME"), TierAssignment(0.3, "frames", "window frame in elevation")),
    # 7. Stair risers (finer than primary structure)
    ("TEC_STAIR_RISERS", TierAssignment(0.3, "edges_secondary", "stair risers")),
    # 8. Steel framing — secondary structure (SHS, RHS, CHS, UC, UB)
    (
        ("_SHS_", "_RHS_", "_CHS_", "_UC_", "_UB_", "_STL_"),
        TierAssignment(0.35, "structure_secondary", "secondary steel framing"),
    ),
    # 9. Connectors / brackets / cleats — finer
    (
        ("TEC_STEEL_CONNECTOR", "L-BRACKET", "_SS_", "CLEAT_PLATE"),
        TierAssignment(0.25, "connectors", "steel connectors / brackets"),
    ),
    # 10. Cladding panels — material surface
    (
        ("_CU_CORR_", "_CU_FLAT_", "_CU_PUNCH_", "CLADDING"),
        TierAssignment(0.18, "cladding", "cladding / surface panels"),
    ),
    # 11. Membranes / sealants — light material
    (
        ("EPDM", "_MEM_", "_WP_", "MEMBRANE", "SEALANT"),
        TierAssignment(0.13, "material_minor", "membrane / sealant"),
    ),
    # 12. Insulation
    (
        ("_INS_", "_MW_", "_RW_", "_XPS_", "_PIR_", "INSULATION"),
        TierAssignment(0.13, "insulation", "insulation hatch"),
    ),
    # 13. Annotation
    (("_DIM", "_TEXT", "_TAG", "ANNOTATION"), TierAssignment(0.13, "annotation", "dimension / annotation")),
]

# Default for the Rhino source — preserves pre-Phase-E5 behavior.
DEFAULT = TierAssignment(0.25, "default", "no pattern match — assigned middle weight")


# --------------------------------------------------------------------------- #
# AutoCAD / AIA NCS rules
# --------------------------------------------------------------------------- #
#
# Field-anchored matching: AIA NCS layer names are hyphen-delimited. We
# normalize to upper-case and pad with hyphens (`-A-WALL-FULL-`) so prefix
# patterns like `-A-WALL-FULL-` match `A-WALL-FULL`, `A-WALL-FULL-N`, and
# `A-WALL-FULL-DEMO` but NOT `A-WALL-FULL2`. This mirrors the NCS field
# semantics.
#
# Order matters — most specific first. Within each tier we list the most
# specific MAJOR-MINOR combos before bare MAJOR-only patterns. The first
# match wins.
#
# Encoded patterns: 25 distinct AIA NCS field tokens, mapped to 8 tiers.
# Coverage target per docs/research/layer-name-patterns.md §1.1: ~90% of
# typical architectural drawings.

AUTOCAD_RULES: list[tuple[str | tuple[str, ...], TierAssignment]] = [
    # 1. REFERENCE — `*-REFR-` minor group (e.g. A-ANNO-REFR is reference,
    #    not annotation, per the NCS minor-group spec). Must come BEFORE
    #    annotation otherwise `-ANNO-` would consume A-ANNO-REFR.
    (
        ("-GRID-", "-GRID ", "-REFR-", "-REFR "),
        TierAssignment(
            0.13,
            "reference",
            "AIA NCS GRID / REFR — construction reference",
            source=Source.AUTOCAD,
            confidence=0.85,
        ),
    ),
    # 2. ANNOTATION — `*-ANNO*` major group AND `*-IDEN` minor group (tags).
    #    Listed before edges_secondary so `A-DOOR-IDEN` doesn't accidentally
    #    match `A-DOOR` further down.
    (
        ("-ANNO-", "-ANNO ", "-IDEN-", "-IDEN ", "-DIMS-", "-TEXT-", "-NOTE-", "-TTLB-", "-SYMB-"),
        TierAssignment(
            0.13,
            "annotation",
            "AIA NCS ANNO/IDEN/DIMS/TEXT/NOTE/TTLB minor group",
            source=Source.AUTOCAD,
            confidence=0.85,
        ),
    ),
    # 3. MATERIAL_MINOR — insulation + membranes.
    (
        ("-INSL-", "-INSL ", "-MEMB-", "-MEMB "),
        TierAssignment(
            0.13,
            "material_minor",
            "AIA NCS INSL / MEMB — insulation or membrane",
            source=Source.AUTOCAD,
            confidence=0.85,
        ),
    ),
    # 4. CLADDING — `*-PATT` minor group on any major (wall/floor/roof/clng).
    (
        ("-PATT-", "-PATT "),
        TierAssignment(
            0.18,
            "cladding",
            "AIA NCS PATT minor — surface pattern / hatch",
            source=Source.AUTOCAD,
            confidence=0.85,
        ),
    ),
    # 5. GLAZING — A-GLAZ-* (must come before WALL/FRAME because A-WALL-GLAZ
    #    contains both `WALL` and `GLAZ`).
    (
        ("-GLAZ-", "-GLAZ ", "-WALL-GLAZ-", "-WALL-GLAZ "),
        TierAssignment(
            0.25,
            "glazing",
            "AIA NCS GLAZ — windows + curtain wall glass",
            source=Source.AUTOCAD,
            confidence=0.85,
        ),
    ),
    # 6. FRAMES — door + window jambs, heads, sills, frames.
    (
        ("-JAMB-", "-JAMB ", "-HEAD-", "-HEAD ", "-FRAM-", "-FRAM ", "-WALL-SILL-", "-WALL-SILL "),
        TierAssignment(
            0.3,
            "frames",
            "AIA NCS JAMB / HEAD / FRAM — door & window frames",
            source=Source.AUTOCAD,
            confidence=0.85,
        ),
    ),
    # 7. CUT — heavy section profile in plan: full-height structural walls,
    #    columns, foundations, slab edges. NCS doesn't tag a "cut" tier
    #    explicitly, so we infer from FULL minor + structural disciplines.
    (
        (
            "-WALL-FULL-",
            "-WALL-FULL ",
            "-WALL-CONC-",
            "-WALL-CONC ",
            "-FLOR-DECK-",
            "-FLOR-DECK ",
            "-ROOF-OTLN-",
            "-ROOF-OTLN ",
            "-S-COLS-",
            "-S-COLS ",
            "-S-FNDN-",
            "-S-FNDN ",
        ),
        TierAssignment(
            1.0,
            "cut",
            "AIA NCS section cut: structural full-height + slab edge + column",
            source=Source.AUTOCAD,
            confidence=0.85,
        ),
    ),
    # 8. STRUCTURE_PRIMARY — beams, joists, decks, roof structure.
    (
        (
            "-S-BEAM-",
            "-S-BEAM ",
            "-S-JOIS-",
            "-S-JOIS ",
            "-S-DECK-",
            "-S-DECK ",
            "-ROOF-STRC-",
            "-ROOF-STRC ",
            "-CLNG-STRC-",
            "-CLNG-STRC ",
        ),
        TierAssignment(
            0.5,
            "structure_primary",
            "AIA NCS BEAM / JOIS / DECK / STRC — primary framing",
            source=Source.AUTOCAD,
            confidence=0.85,
        ),
    ),
    # 9. EDGES_SECONDARY — door leaves, stairs, equipment outlines, furniture,
    #    floor outlines (fall-through after frames + glazing have matched).
    (
        (
            "-DOOR-",
            "-DOOR ",
            "-FLOR-",
            "-FLOR ",
            "-EQPM-",
            "-EQPM ",
            "-FURN-",
            "-FURN ",
            "-STRS-",
            "-STRS ",
        ),
        TierAssignment(
            0.3,
            "edges_secondary",
            "AIA NCS DOOR / FLOR / EQPM / FURN / STRS — secondary edges",
            source=Source.AUTOCAD,
            confidence=0.85,
        ),
    ),
]

# Default for the AutoCAD source — also 0.25pt to align with Rhino default
# (the user's `--default-width` knob), but with low confidence.
AUTOCAD_DEFAULT = TierAssignment(
    0.25,
    "default",
    "AIA NCS pattern library: no recognized MAJOR/MINOR field",
    source=Source.AUTOCAD,
    confidence=0.20,
)


DISPATCH: dict[Source, list[tuple[str | tuple[str, ...], TierAssignment]]] = {
    Source.RHINO: RHINO_RULES,
    Source.AUTOCAD: AUTOCAD_RULES,
}

DEFAULTS: dict[Source, TierAssignment] = {
    Source.RHINO: DEFAULT,
    Source.AUTOCAD: AUTOCAD_DEFAULT,
}


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #


def classify_layer(name: str, source: Source = Source.RHINO) -> TierAssignment:
    """Return the tier assignment for an OCG layer name.

    `source` selects the pattern library:
      - `Source.RHINO` (default): preserves pre-Phase-E5 behavior 1:1.
      - `Source.AUTOCAD`: AIA NCS / ISO 13567-2 layer-name conventions.

    Match is case-insensitive. For AutoCAD/AIA NCS, the name is hyphen-padded
    so field tokens like `-WALL-` match field boundaries rather than
    accidental substrings.
    """
    if source == Source.AUTO:
        # Caller should have resolved `auto` to a concrete source. Fall back
        # to Rhino to preserve historical behavior; callers that care about
        # detection should call `detect_source` first.
        source = Source.RHINO

    rules = DISPATCH.get(source, RHINO_RULES)
    default = DEFAULTS.get(source, DEFAULT)

    upper = name.upper()
    # For AutoCAD/AIA NCS, hyphen-pad so field-anchored patterns (`-WALL-`)
    # only match field boundaries. Spaces are also legal terminators (e.g.
    # layer-list display names with trailing space).
    haystack = f"-{upper}-" if source == Source.AUTOCAD else upper

    for patterns, assignment in rules:
        if isinstance(patterns, str):
            if patterns in haystack:
                return assignment
        else:
            for p in patterns:
                if p in haystack:
                    return assignment
    return default


def as_jsx_function(function_name: str = "weightFor", source: Source = Source.RHINO) -> str:
    """Emit the classifier as ExtendScript-compatible JS for a single source.

    The single-source emitter keeps existing JSX consumers stable. Multi-source
    JSX dispatch is a Phase E5 v0.5+ stretch goal.
    """
    rules = DISPATCH.get(source, RHINO_RULES)
    default = DEFAULTS.get(source, DEFAULT)

    lines = [f"function {function_name}(name) {{", "    var n = String(name).toUpperCase();"]
    if source == Source.AUTOCAD:
        lines.append('    n = "-" + n + "-";')
    for patterns, assignment in rules:
        if isinstance(patterns, str):
            patterns = (patterns,)
        cond = " || ".join(f'n.indexOf("{p}") !== -1' for p in patterns)
        lines.append(f"    if ({cond}) return {assignment.weight_pt};")
    lines.append(f"    return {default.weight_pt};")
    lines.append("}")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Source detection
# --------------------------------------------------------------------------- #

# NCS-shape regex: `<one capital>-<four capitals>-` anchored at start.
_NCS_SHAPE_RE = re.compile(r"^[A-Z]-[A-Z]{2,4}(-|$| )")


# Producer/Creator substring -> (source, confidence). First match wins.
# Order is important: more specific tokens come first.
_PRODUCER_HEURISTICS: list[tuple[str, Source, float]] = [
    ("rhinoceros", Source.RHINO, 0.95),
    ("rhino", Source.RHINO, 0.95),
    ("mcneel", Source.RHINO, 0.95),
    ("make2d", Source.RHINO, 0.95),
    ("autocad", Source.AUTOCAD, 0.85),
    ("dwg to pdf", Source.AUTOCAD, 0.85),
    ("autodesk dwg", Source.AUTOCAD, 0.85),
    ("bricscad", Source.AUTOCAD, 0.85),
    ("draftsight", Source.AUTOCAD, 0.85),
    ("nanocad", Source.AUTOCAD, 0.85),
    # Adobe Illustrator is intentionally weak: it could be a re-export of
    # anything. Producer alone is ambiguous; layer-shape inference will
    # disambiguate downstream.
]


def detect_source(
    pdf_metadata: dict | None,
    layer_names: list[str] | None,
) -> tuple[Source, float]:
    """Return `(source, confidence)` best-guess for a PDF.

    Priority:
      1. PDF `/Producer` / `/Creator` substring match.
      2. Layer-name shape inference (`::`-joined → Rhino; `^[A-Z]-[A-Z]{4}-`
         → AutoCAD/AIA NCS).

    If neither yields a confident answer, returns `(Source.AUTO, 0.0)` so
    the caller can fall back to the color classifier.

    See docs/research/layer-name-patterns.md §2 for the full heuristic table.
    """
    pdf_metadata = pdf_metadata or {}
    layer_names = layer_names or []

    producer = str(pdf_metadata.get("/Producer") or pdf_metadata.get("producer") or "").lower()
    creator = str(pdf_metadata.get("/Creator") or pdf_metadata.get("creator") or "").lower()
    metadata_blob = f"{producer} {creator}"

    for needle, src, conf in _PRODUCER_HEURISTICS:
        if needle in metadata_blob:
            # Even when metadata says Rhino, re-saved-via-Illustrator files
            # might have lost their `::` layer hierarchy. We trust producer
            # at full confidence — caller can override with --source if wrong.
            return src, conf

    # Layer-name shape inference.
    n = len(layer_names)
    if n == 0:
        return Source.AUTO, 0.0

    rhino_hits = sum(1 for x in layer_names if "::" in x)
    if rhino_hits / n >= 0.5:
        return Source.RHINO, 0.90

    ncs_hits = sum(1 for x in layer_names if _NCS_SHAPE_RE.match(x.strip().upper()))
    if ncs_hits / n >= 0.3:
        return Source.AUTOCAD, 0.70

    return Source.AUTO, 0.0


def explain_source_match(name: str, source: Source) -> str:
    """One-line description of which source's pattern library handled `name`.

    Useful for the `explain-layer` CLI — tells the user which library the
    match came from so they can audit / override.
    """
    a = classify_layer(name, source=source)
    src_label = a.source.value if isinstance(a.source, Source) else str(a.source)
    return (
        f"{a.weight_pt} pt — {a.tier} ({a.why}) "
        f"[source={src_label}, confidence={a.confidence:.2f}]"
    )
