"""Tests for the pure linetype assignment module (spec doc 49 §1.2)."""

from __future__ import annotations

import pytest

from arch_line_weights.layer_classify import Source
from arch_line_weights.linetypes import (
    DASH_PATTERNS_PT,
    LINETYPE_BY_TOKEN,
    AIAStatus,
    LineType,
    aia_status_from_name,
    apply_status,
    dash_token,
    linetype_for_layer,
)

# --------------------------------------------------------------------------- #
# linetype_for_layer — token -> LineType
# --------------------------------------------------------------------------- #


def test_hidd_autocad_is_dashed():
    a = linetype_for_layer("A-WALL-HIDD", source=Source.AUTOCAD)
    assert a.linetype is LineType.DASHED
    assert a.excluded is False
    assert a.dash_pattern_pt == DASH_PATTERNS_PT[LineType.DASHED]


@pytest.mark.parametrize(
    "name",
    ["A-WALL-CNTR", "A-GRID-CENT", "A-COLS-CL"],
)
def test_center_axis_tokens_are_dash_dot(name):
    a = linetype_for_layer(name, source=Source.AUTOCAD)
    assert a.linetype is LineType.DASH_DOT
    assert a.dash_pattern_pt == DASH_PATTERNS_PT[LineType.DASH_DOT]


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("A-DETL-PHTM", LineType.PHANTOM),
        ("A-SECT-CUTL", LineType.CUTTING_PLANE),
        ("A-DETL-BRK", LineType.BREAK),
        ("A-PROP-LINE", LineType.PROPERTY),
        ("S-COLS-OVHD", LineType.DASHED),
    ],
)
def test_assorted_tokens(name, expected):
    assert linetype_for_layer(name, source=Source.AUTOCAD).linetype is expected


def test_no_token_defaults_to_continuous_solid():
    a = linetype_for_layer("A-WALL-FULL", source=Source.AUTOCAD)
    assert a.linetype is LineType.CONTINUOUS
    assert a.dash_pattern_pt is None
    assert a.excluded is False
    assert a.screened is False
    assert a.weight_scale == 1.0


def test_dimension_leader_token_is_solid_dimension():
    a = linetype_for_layer("A-ANNO-DIMS", source=Source.AUTOCAD)
    assert a.linetype is LineType.DIMENSION
    assert a.dash_pattern_pt is None  # DIMENSION is solid in v1


@pytest.mark.parametrize("token", ["LEAD", "ANNO", "TEXT", "DIMS"])
def test_all_dimension_tokens_solid(token):
    a = linetype_for_layer(f"A-{token}-NOTE", source=Source.AUTOCAD)
    assert a.linetype is LineType.DIMENSION
    assert a.dash_pattern_pt is None


def test_rhino_source_no_hyphen_padding_still_matches():
    # Rhino names aren't hyphen-padded; a bare substring still hits.
    a = linetype_for_layer("WALL_HIDD_ABOVE", source=Source.RHINO)
    assert a.linetype is LineType.DASHED


# --------------------------------------------------------------------------- #
# Non-plotting -> excluded
# --------------------------------------------------------------------------- #


def test_nplt_layer_is_excluded_and_has_no_dash_token():
    a = linetype_for_layer("A-WALL-NPLT", source=Source.AUTOCAD)
    assert a.excluded is True
    assert a.linetype is LineType.NON_PLOTTING
    assert a.dash_pattern_pt is None
    assert dash_token(a) is None


# --------------------------------------------------------------------------- #
# AIA status parsing + application
# --------------------------------------------------------------------------- #


def test_demo_status_parse_and_apply():
    status = aia_status_from_name("A-WALL-FULL-DEMO")
    assert status is AIAStatus.DEMO

    base = linetype_for_layer("A-WALL-FULL", source=Source.AUTOCAD)
    out = apply_status(base, status)
    assert out.linetype is LineType.DASHED
    assert out.screened is True
    assert out.weight_scale == 0.5
    assert out.dash_pattern_pt == DASH_PATTERNS_PT[LineType.DASHED]


def test_exst_status_is_screened_dashed():
    status = aia_status_from_name("A-WALL-FULL-EXST")
    assert status is AIAStatus.EXST
    out = apply_status(linetype_for_layer("A-WALL-FULL", source=Source.AUTOCAD), status)
    assert out.linetype is LineType.DASHED
    assert out.screened is True
    assert out.weight_scale == 0.5


def test_neww_status_parse_and_apply_stays_continuous():
    status = aia_status_from_name("A-WALL-FULL-NEWW")
    assert status is AIAStatus.NEWW

    continuous_base = linetype_for_layer("A-WALL-FULL", source=Source.AUTOCAD)
    assert continuous_base.linetype is LineType.CONTINUOUS

    out = apply_status(continuous_base, status)
    assert out.linetype is LineType.CONTINUOUS
    assert out.dash_pattern_pt is None
    assert out.screened is False
    assert out.weight_scale == 1.0


def test_neww_overrides_a_dashed_base_to_continuous():
    base = linetype_for_layer("A-WALL-HIDD", source=Source.AUTOCAD)
    assert base.linetype is LineType.DASHED
    out = apply_status(base, AIAStatus.NEWW)
    assert out.linetype is LineType.CONTINUOUS
    assert out.dash_pattern_pt is None


def test_no_status_returns_base_unchanged():
    base = linetype_for_layer("A-WALL-HIDD", source=Source.AUTOCAD)
    assert aia_status_from_name("A-WALL-HIDD") is AIAStatus.NONE
    assert apply_status(base, AIAStatus.NONE) is base


def test_status_does_not_resurrect_excluded():
    base = linetype_for_layer("A-WALL-NPLT", source=Source.AUTOCAD)
    out = apply_status(base, AIAStatus.DEMO)
    assert out.excluded is True
    assert out is base


# --------------------------------------------------------------------------- #
# dash_token rendering
# --------------------------------------------------------------------------- #


def test_dash_token_dashed():
    a = linetype_for_layer("A-WALL-HIDD", source=Source.AUTOCAD)
    assert dash_token(a) == b"[3 2] 0 d"


def test_dash_token_continuous():
    a = linetype_for_layer("A-WALL-FULL", source=Source.AUTOCAD)
    assert a.linetype is LineType.CONTINUOUS
    assert dash_token(a) == b"[] 0 d"


def test_dash_token_dash_dot_uses_g_format():
    a = linetype_for_layer("A-COLS-CL", source=Source.AUTOCAD)
    # ((4.0, 2.0, 1.0, 2.0), 0.0) -> whole numbers, no trailing .0
    assert dash_token(a) == b"[4 2 1 2] 0 d"


def test_dash_token_phantom():
    a = linetype_for_layer("A-DETL-PHTM", source=Source.AUTOCAD)
    assert dash_token(a) == b"[6 2 1 2 1 2] 0 d"


def test_dash_token_renders_phase_and_fractions():
    # Sanity-check %g formatting on a synthetic fractional pattern.
    from arch_line_weights.linetypes import LineTypeAssignment

    a = LineTypeAssignment(
        linetype=LineType.DASHED,
        excluded=False,
        screened=False,
        weight_scale=1.0,
        dash_pattern_pt=((2.5, 1.0), 0.5),
        why="synthetic",
    )
    assert dash_token(a) == b"[2.5 1] 0.5 d"


# --------------------------------------------------------------------------- #
# Table sanity
# --------------------------------------------------------------------------- #


def test_required_tokens_present():
    required = {
        "HIDD": LineType.DASHED,
        "OVHD": LineType.DASHED,
        "ABOV": LineType.DASHED,
        "HID": LineType.DASHED,
        "CNTR": LineType.DASH_DOT,
        "CL": LineType.DASH_DOT,
        "CENT": LineType.DASH_DOT,
        "PHTM": LineType.PHANTOM,
        "PHAN": LineType.PHANTOM,
        "SECT": LineType.CUTTING_PLANE,
        "CUTL": LineType.CUTTING_PLANE,
        "BRK": LineType.BREAK,
        "PROP": LineType.PROPERTY,
        "PROJ": LineType.PROPERTY,
        "DIMS": LineType.DIMENSION,
        "LEAD": LineType.DIMENSION,
        "ANNO": LineType.DIMENSION,
        "TEXT": LineType.DIMENSION,
        "NPLT": LineType.NON_PLOTTING,
    }
    for token, expected in required.items():
        assert LINETYPE_BY_TOKEN[token] is expected


def test_solid_linetypes_absent_from_dash_table():
    for solid in (
        LineType.CONTINUOUS,
        LineType.DIMENSION,
        LineType.PROPERTY,
        LineType.CUTTING_PLANE,
        LineType.BREAK,
    ):
        assert solid not in DASH_PATTERNS_PT


# --------------------------------------------------------------------------- #
# Token precedence + field-bounded matching (regression guards)
# --------------------------------------------------------------------------- #


def test_nplt_outranks_an_earlier_matching_token():
    # `A-ANNO-NPLT` also contains the ANNO (dimension) token; NPLT must win.
    a = linetype_for_layer("A-ANNO-NPLT", source=Source.AUTOCAD)
    assert a.linetype is LineType.NON_PLOTTING
    assert a.excluded is True


def test_autocad_token_is_field_bounded():
    # `CL` (centerline) must NOT match inside `CLNG` (ceiling).
    a = linetype_for_layer("A-CLNG-STRC", source=Source.AUTOCAD)
    assert a.linetype is LineType.CONTINUOUS
