"""Phase E5 tests: per-source layer-name classifier + source detection.

Covers:
  - Rhino Make2D regression: existing layer names still classify identically.
  - AIA NCS / AutoCAD: ~25 NCS layer names hit the right tier.
  - Source detection: PDF metadata (Producer) + layer-name shape inference.
  - `--source autocad` override bypasses detection.
  - Mixed-source files (Rhino + AIA in the same population).
  - Failure mode: unknown layer falls back to default 0.25 pt.
"""

from __future__ import annotations

import pytest

from arch_line_weights.layer_classify import (
    AUTOCAD_DEFAULT,
    DEFAULT,
    Source,
    classify_layer,
    detect_source,
    explain_source_match,
)

# --------------------------------------------------------------------------- #
# Rhino regression — existing behavior must NOT change
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "layer,expected_weight,expected_tier",
    [
        ("axon::Visible::ClippingPlaneIntersections::TEC_TIMBER_BEAMS", 1.0, "cut"),
        ("axon::Visible::ClippingPlaneIntersections::TEC_FOUNDATION", 1.0, "cut"),
        ("axon::Visible::Curves::03c_WINDOW_IGU_GLASS", 0.25, "glazing"),
        ("axon::Visible::Curves::WINDOW_FRAME", 0.3, "frames"),
        ("axon::Visible::Curves::FLOOR_DATUMS", 0.13, "reference"),
        ("axon::Visible::Curves::TEC_TIMBER_COLUMNS", 0.5, "structure_primary"),
        ("axon::Visible::Curves::TEC_STAIR", 0.5, "structure_primary"),
        # NOTE: TEC_STAIR_RISERS matches the broader TEC_STAIR rule first
        # in the existing rule order (a quirk preserved as-is from pre-Phase-E5).
        ("axon::Visible::Curves::TEC_STAIR_RISERS", 0.5, "structure_primary"),
        ("axon::Visible::Curves::C03_CU_CORR_PANELS", 0.18, "cladding"),
        ("axon::Visible::Curves::WP_MEMBRANE_ROOF", 0.13, "material_minor"),
        ("axon::Visible::Curves::INSULATION_MW", 0.13, "insulation"),
        ("axon::Visible::Curves::DIM_TEXT", 0.13, "annotation"),
    ],
)
def test_rhino_regression(layer, expected_weight, expected_tier):
    """All previously-classified Rhino names still map to the same tier."""
    a = classify_layer(layer)  # default source = Rhino
    assert a.weight_pt == expected_weight
    assert a.tier == expected_tier


def test_rhino_unknown_falls_back_to_default():
    """Unknown Rhino-style layer name still hits the 0.25 default."""
    a = classify_layer("totally_unknown_layer_name")
    assert a.weight_pt == DEFAULT.weight_pt
    assert a.tier == "default"


def test_default_source_arg_is_rhino():
    """No `source=` arg ⇒ Rhino dispatch (back-compat)."""
    a = classify_layer("axon::Visible::ClippingPlaneIntersections::TEC_TIMBER")
    assert a.tier == "cut"


# --------------------------------------------------------------------------- #
# AIA NCS / AutoCAD — new in Phase E5
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "layer,expected_weight,expected_tier",
    [
        # Cut tier — heavy section profiles
        ("A-WALL-FULL", 1.0, "cut"),
        ("A-WALL-FULL-N", 1.0, "cut"),
        ("A-WALL-CONC", 1.0, "cut"),
        ("A-FLOR-DECK", 1.0, "cut"),
        ("A-ROOF-OTLN", 1.0, "cut"),
        ("S-COLS", 1.0, "cut"),
        ("S-COLS-PIER", 1.0, "cut"),
        ("S-FNDN", 1.0, "cut"),
        # Structure primary
        ("S-BEAM", 0.5, "structure_primary"),
        ("S-BEAM-MAIN", 0.5, "structure_primary"),
        ("S-JOIS", 0.5, "structure_primary"),
        ("A-ROOF-STRC", 0.5, "structure_primary"),
        # Glazing
        ("A-GLAZ", 0.25, "glazing"),
        ("A-GLAZ-FULL", 0.25, "glazing"),
        ("A-GLAZ-SILL", 0.25, "glazing"),
        ("A-WALL-GLAZ", 0.25, "glazing"),
        # Frames — door/window jambs/heads
        ("A-WALL-JAMB", 0.3, "frames"),
        ("A-WALL-HEAD", 0.3, "frames"),
        ("A-DOOR-FRAM", 0.3, "frames"),
        ("A-WALL-SILL", 0.3, "frames"),
        # Edges secondary — door leaves, stairs, equipment, furniture
        ("A-DOOR", 0.3, "edges_secondary"),
        ("A-FLOR", 0.3, "edges_secondary"),
        ("A-FLOR-STRS", 0.3, "edges_secondary"),
        ("A-FLOR-OTLN", 0.3, "edges_secondary"),
        ("A-EQPM", 0.3, "edges_secondary"),
        ("A-FURN", 0.3, "edges_secondary"),
        # Cladding — surface pattern hatches
        ("A-WALL-PATT", 0.18, "cladding"),
        ("A-FLOR-PATT", 0.18, "cladding"),
        ("A-ROOF-PATT", 0.18, "cladding"),
        # Material minor — insulation, membrane
        ("A-WALL-INSL", 0.13, "material_minor"),
        ("A-ROOF-INSL", 0.13, "material_minor"),
        ("A-WALL-MEMB", 0.13, "material_minor"),
        # Reference — grid + datum
        ("S-GRID", 0.13, "reference"),
        ("A-GRID", 0.13, "reference"),
        ("A-ANNO-REFR", 0.13, "reference"),
        # Annotation — IDEN tags + dims + text + title block
        ("A-DOOR-IDEN", 0.13, "annotation"),
        ("A-ANNO-DIMS", 0.13, "annotation"),
        ("A-ANNO-TEXT", 0.13, "annotation"),
        ("A-ANNO-NOTE", 0.13, "annotation"),
        ("A-ANNO-TTLB", 0.13, "annotation"),
        ("A-ANNO-SYMB", 0.13, "annotation"),
    ],
)
def test_autocad_aia_ncs_classification(layer, expected_weight, expected_tier):
    """Encoded AIA NCS patterns map to correct tiers."""
    a = classify_layer(layer, source=Source.AUTOCAD)
    assert a.weight_pt == expected_weight, f"{layer}: got {a.weight_pt} ({a.tier})"
    assert a.tier == expected_tier
    assert a.source == Source.AUTOCAD


def test_autocad_unknown_layer_falls_back_to_default():
    """Names that don't match any encoded AIA pattern hit the AutoCAD default."""
    a = classify_layer("M-DUCT-MAIN", source=Source.AUTOCAD)
    assert a.weight_pt == AUTOCAD_DEFAULT.weight_pt
    assert a.tier == "default"
    assert a.confidence < 0.5


def test_autocad_case_insensitive():
    """Lowercase input still classifies — NCS allows mixed case in display."""
    a_upper = classify_layer("A-WALL-FULL", source=Source.AUTOCAD)
    a_lower = classify_layer("a-wall-full", source=Source.AUTOCAD)
    assert a_upper.tier == a_lower.tier == "cut"


def test_autocad_field_anchored_no_substring_false_positives():
    """Hyphen-anchored matching: `A-WALL-FULLY-CUSTOM` should NOT match `WALL-FULL`."""
    # We pad with hyphens — so `-WALL-FULL-` won't match `-WALL-FULLY-`.
    a = classify_layer("A-WALL-FULLY", source=Source.AUTOCAD)
    assert a.tier != "cut"  # the WALL-FULL pattern shouldn't bleed into FULLY


# --------------------------------------------------------------------------- #
# Annotation precedence — A-DOOR-IDEN must hit "annotation" not "edges_secondary"
# --------------------------------------------------------------------------- #


def test_annotation_beats_edges_secondary():
    """Door tags (A-DOOR-IDEN) should match annotation, not the bare A-DOOR rule."""
    a = classify_layer("A-DOOR-IDEN", source=Source.AUTOCAD)
    assert a.tier == "annotation"


def test_annotation_beats_door_for_iden_patterns():
    """Window tags (A-GLAZ-IDEN) → annotation, beating glazing."""
    a = classify_layer("A-GLAZ-IDEN", source=Source.AUTOCAD)
    assert a.tier == "annotation"


# --------------------------------------------------------------------------- #
# Source detection
# --------------------------------------------------------------------------- #


def test_detect_source_from_rhino_producer():
    """Producer mentions Rhino → Source.RHINO at high confidence."""
    src, conf = detect_source({"/Producer": "Rhinoceros 8 SR15"}, [])
    assert src == Source.RHINO
    assert conf >= 0.9


def test_detect_source_from_autocad_producer():
    """Producer mentions AutoCAD → Source.AUTOCAD."""
    src, conf = detect_source({"/Producer": "AutoCAD 2025 (DWG to PDF)"}, [])
    assert src == Source.AUTOCAD
    assert conf >= 0.8


def test_detect_source_from_dwg_to_pdf_producer():
    """`DWG to PDF` driver substring → AutoCAD."""
    src, conf = detect_source({"/Producer": "Autodesk DWG to PDF v25"}, [])
    assert src == Source.AUTOCAD
    assert conf >= 0.8


def test_detect_source_from_bricscad_producer():
    """BricsCAD is an AutoCAD clone → AutoCAD pattern library."""
    src, _conf = detect_source({"/Producer": "BricsCAD V24"}, [])
    assert src == Source.AUTOCAD


def test_detect_source_lowercase_metadata_keys():
    """PyMuPDF gives lowercase 'producer'; detector handles both cases."""
    src, _ = detect_source({"producer": "rhino", "creator": "rhino"}, [])
    assert src == Source.RHINO


def test_detect_source_layer_shape_rhino():
    """Metadata silent + most layers contain `::` → Rhino."""
    layers = [
        "axon::Visible::Curves::TEC_TIMBER",
        "axon::Visible::Curves::WINDOW_FRAME",
        "axon::Visible::ClippingPlaneIntersections::TEC_FOUNDATION",
        "plan::Hidden::Curves::TEC_CLT_SLABS",
    ]
    src, conf = detect_source({}, layers)
    assert src == Source.RHINO
    assert conf >= 0.85


def test_detect_source_layer_shape_aia_ncs():
    """Metadata silent + most layers match `A-XXXX-` shape → AutoCAD."""
    layers = ["A-WALL-FULL", "A-DOOR", "A-GLAZ-SILL", "S-COLS", "A-ANNO-DIMS"]
    src, conf = detect_source({}, layers)
    assert src == Source.AUTOCAD
    assert conf >= 0.6


def test_detect_source_returns_auto_when_inconclusive():
    """No metadata + opaque layer names → AUTO sentinel + zero confidence."""
    src, conf = detect_source({}, ["Layer 1", "Layer 2", "My Drawing"])
    assert src == Source.AUTO
    assert conf == 0.0


def test_detect_source_empty_input():
    """Nothing at all → AUTO."""
    src, conf = detect_source(None, None)
    assert src == Source.AUTO
    assert conf == 0.0


def test_detect_source_metadata_wins_over_layer_shape():
    """Even when layer shape says NCS, an explicit Rhino producer wins."""
    src, _ = detect_source(
        {"/Producer": "Rhinoceros 8"},
        ["A-WALL-FULL", "A-DOOR"],
    )
    assert src == Source.RHINO


# --------------------------------------------------------------------------- #
# Source override — `--source autocad` bypasses detection
# --------------------------------------------------------------------------- #


def test_source_override_uses_autocad_rules():
    """When the caller forces autocad, classifier uses AIA NCS even on Rhino-style names."""
    # `axon::Visible::ClippingPlaneIntersections::TEC_TIMBER` would be cut(1.0)
    # in Rhino mode. In AutoCAD mode it has no field-anchored match → default.
    a = classify_layer(
        "axon::Visible::ClippingPlaneIntersections::TEC_TIMBER",
        source=Source.AUTOCAD,
    )
    assert a.source == Source.AUTOCAD
    assert a.tier == "default"  # no AIA pattern matched


def test_source_override_to_rhino_keeps_legacy_behavior():
    """Forcing rhino on an AIA name should not match AIA tier."""
    a = classify_layer("A-WALL-FULL", source=Source.RHINO)
    # Won't match any Rhino pattern → falls to Rhino DEFAULT
    assert a.tier == "default"


def test_auto_source_falls_back_to_rhino():
    """`Source.AUTO` passed directly to classify_layer behaves like Rhino."""
    a = classify_layer(
        "axon::Visible::ClippingPlaneIntersections::TEC_TIMBER",
        source=Source.AUTO,
    )
    assert a.tier == "cut"  # Rhino dispatch


# --------------------------------------------------------------------------- #
# Mixed-source files — both Rhino and AIA layers in same population
# --------------------------------------------------------------------------- #


def test_mixed_source_rhino_majority_picks_rhino():
    """7 Rhino + 3 AIA layers → detection picks Rhino (50% threshold met)."""
    layers = [
        "axon::Visible::Curves::TEC_TIMBER",
        "axon::Visible::Curves::WINDOW_FRAME",
        "axon::Visible::Curves::FLOOR_DATUMS",
        "axon::Visible::Curves::TEC_CONCRETE_BASE",
        "axon::Visible::ClippingPlaneIntersections::TEC_FOUNDATION",
        "axon::Hidden::Curves::TEC_TIMBER_BEAMS",
        "axon::Hidden::Curves::TEC_STAIR",
        "A-WALL-FULL",
        "A-DOOR",
        "A-GLAZ",
    ]
    src, _ = detect_source({}, layers)
    assert src == Source.RHINO


def test_mixed_source_aia_majority_picks_autocad():
    """6 AIA + 2 unknown → detection picks AutoCAD."""
    layers = [
        "A-WALL-FULL",
        "A-DOOR",
        "A-GLAZ-SILL",
        "S-COLS",
        "A-ANNO-DIMS",
        "A-FLOR",
        "Random Layer",
        "Notes",
    ]
    src, _ = detect_source({}, layers)
    assert src == Source.AUTOCAD


def test_mixed_classification_each_source_handles_own_layers():
    """Once a source is chosen, each source classifier handles its own layers correctly."""
    # If AutoCAD is detected, AIA layers classify properly...
    aia_a = classify_layer("A-WALL-FULL", source=Source.AUTOCAD)
    assert aia_a.tier == "cut"
    # ...and Rhino layers fall to default (no `::` semantics in AIA library).
    rhino_a = classify_layer(
        "axon::Visible::Curves::TEC_TIMBER", source=Source.AUTOCAD
    )
    assert rhino_a.tier == "default"


# --------------------------------------------------------------------------- #
# Confidence + explain helper
# --------------------------------------------------------------------------- #


def test_autocad_match_carries_baseline_confidence():
    """A successful AIA match carries the per-source baseline confidence (0.85)."""
    a = classify_layer("A-WALL-FULL", source=Source.AUTOCAD)
    assert a.confidence >= 0.8


def test_autocad_default_has_low_confidence():
    """A miss in AIA should have low confidence so callers can choose to fall back."""
    a = classify_layer("UnknownFoo", source=Source.AUTOCAD)
    assert a.confidence < 0.5


def test_explain_source_match_includes_source_label():
    """`explain_source_match` returns a string mentioning the source."""
    msg = explain_source_match("A-WALL-FULL", Source.AUTOCAD)
    assert "autocad" in msg
    assert "cut" in msg
    assert "1.0 pt" in msg


def test_explain_source_match_for_rhino():
    msg = explain_source_match(
        "axon::Visible::ClippingPlaneIntersections::TEC_TIMBER",
        Source.RHINO,
    )
    assert "rhino" in msg
    assert "cut" in msg
