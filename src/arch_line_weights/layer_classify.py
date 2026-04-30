"""Semantic layer-name classifier for Rhino-style OCG layer naming.

Rhino's Make2D + ClippingPlane export creates an OCG hierarchy:
    <view>::Visible|Hidden::Curves|ClippingPlaneIntersections::<src_layer>

`ClippingPlaneIntersections::*` is **always** the cut tier regardless of
material — it's the cut profile produced by the section plane.

`Curves::*` is whatever's visible in elevation/projection — the weight is
chosen by parsing the trailing material code (TEC_TIMBER, CLT_, SHS_, CU_,
EPDM_, FLOOR_DATUMS, etc.).

This classifier uses substring matching, not regex, for ExtendScript portability:
the same logic can be lifted into a JSX file via `as_jsx()`.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TierAssignment:
    weight_pt: float
    tier: str
    why: str


# Order matters — first match wins (most specific patterns first).
RULES: list[tuple[str | tuple[str, ...], TierAssignment]] = [
    # 1. Cut — section plane intersection (heaviest, regardless of material)
    ("CLIPPINGPLANEINTERSECTIONS", TierAssignment(1.0, "cut", "section plane intersection")),

    # 2. Glazing — special, lighter than profile
    (("WINDOW_IGU_GLASS", "WINDOW_GLASS"), TierAssignment(0.25, "glazing", "transparent material")),

    # 3. Reference / datum lines
    (("FLOOR_DATUMS", "_DATUM", "_GRID", "_REF"), TierAssignment(0.13, "reference", "construction reference")),

    # 4. Structure primary — heavy load-bearing in elevation
    (
        ("TEC_TIMBER", "TEC_CLT_SLABS", "TEC_ROOF_CLT", "TEC_CONCRETE_BASE", "TEC_FOUNDATION",
         "_CLT_BACKUP_", "_CLT_THICK_", "_CLT_GAP_ROOF_"),
        TierAssignment(0.5, "structure_primary", "heavy structural assembly in elevation"),
    ),

    # 5. Stairs (excluding risers — finer)
    ("TEC_STAIR", TierAssignment(0.5, "structure_primary", "stair structure in elevation")),

    # 6. Window frames
    (("WINDOW_FRAME", "WINDOW_ALUM_FRAME"), TierAssignment(0.3, "frames", "window frame in elevation")),

    # 7. Stair risers (finer than primary structure)
    ("TEC_STAIR_RISERS", TierAssignment(0.3, "edges_secondary", "stair risers")),

    # 8. Steel framing — secondary structure (SHS, RHS, CHS, UC, UB)
    (("_SHS_", "_RHS_", "_CHS_", "_UC_", "_UB_", "_STL_"),
     TierAssignment(0.35, "structure_secondary", "secondary steel framing")),

    # 9. Connectors / brackets / cleats — finer
    (("TEC_STEEL_CONNECTOR", "L-BRACKET", "_SS_", "CLEAT_PLATE"),
     TierAssignment(0.25, "connectors", "steel connectors / brackets")),

    # 10. Cladding panels — material surface
    (("_CU_CORR_", "_CU_FLAT_", "_CU_PUNCH_", "CLADDING"),
     TierAssignment(0.18, "cladding", "cladding / surface panels")),

    # 11. Membranes / sealants — light material
    (("EPDM", "_MEM_", "_WP_", "MEMBRANE", "SEALANT"),
     TierAssignment(0.13, "material_minor", "membrane / sealant")),

    # 12. Insulation
    (("_INS_", "_MW_", "_RW_", "_XPS_", "_PIR_", "INSULATION"),
     TierAssignment(0.13, "insulation", "insulation hatch")),

    # 13. Annotation
    (("_DIM", "_TEXT", "_TAG", "ANNOTATION"),
     TierAssignment(0.13, "annotation", "dimension / annotation")),
]

DEFAULT = TierAssignment(0.25, "default", "no pattern match — assigned middle weight")


def classify_layer(name: str) -> TierAssignment:
    """Return the tier assignment for an OCG layer name (case-insensitive)."""
    upper = name.upper()
    for patterns, assignment in RULES:
        if isinstance(patterns, str):
            if patterns in upper:
                return assignment
        else:
            for p in patterns:
                if p in upper:
                    return assignment
    return DEFAULT


def as_jsx_function(function_name: str = "weightFor") -> str:
    """Emit the classifier as ExtendScript-compatible JS."""
    lines = [f"function {function_name}(name) {{",
             "    var n = String(name).toUpperCase();"]
    for patterns, assignment in RULES:
        if isinstance(patterns, str):
            patterns = (patterns,)
        cond = " || ".join(f'n.indexOf("{p}") !== -1' for p in patterns)
        lines.append(f"    if ({cond}) return {assignment.weight_pt};")
    lines.append(f"    return {DEFAULT.weight_pt};")
    lines.append("}")
    return "\n".join(lines)
