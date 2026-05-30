"""Tests for the typed ISO 128 line-weight ladder.

Covers:
  * every ladder rung round-trips through `validate_weight`
  * off-ladder values raise ValueError
  * floats within ±0.005 mm of a rung snap to the nearest rung
  * floats outside the tolerance raise
  * string inputs (numeric + enum name) work
  * LineWeightAssignment coerces a raw float to the enum on construction
  * presets.py consumes the canonical ladder (wire-in check)
"""

from __future__ import annotations

from itertools import pairwise

import pytest

from arch_line_weights import presets
from arch_line_weights.line_weights import (
    ISO_LADDER_MM,
    ISO_LADDER_PT,
    MM_TO_PT,
    SNAP_TOL_MM,
    LineWeight,
    LineWeightAssignment,
    mm_to_pt,
    pt_to_mm,
    validate_weight,
)

# ------------------------------------------------------------------ ladder #


def test_iso_ladder_is_sqrt2_geometric_series():
    """ISO 128-20 specifies a √2 ratio between adjacent rungs."""
    for prev, nxt in pairwise(ISO_LADDER_MM):
        ratio = nxt / prev
        assert ratio == pytest.approx(2**0.5, rel=0.05), (
            f"{prev}→{nxt} ratio {ratio} not √2"
        )


def test_ladder_endpoints():
    """The first/last rungs match ISO 128-20 §4.2."""
    assert ISO_LADDER_MM[0] == 0.13
    assert ISO_LADDER_MM[-1] == 2.00


def test_pt_conversion_matches_postscript_constant():
    """1 mm × 2.835 = 2.835 pt; round to 3 dp matches `presets.mm`."""
    assert mm_to_pt(1.0) == round(MM_TO_PT, 3)
    assert pt_to_mm(MM_TO_PT) == pytest.approx(1.0, abs=1e-3)
    # The two pt ladders must agree (otherwise the wire-in is wrong)
    assert list(ISO_LADDER_PT) == [presets.mm(w) for w in ISO_LADDER_MM]


# ----------------------------------------------------------- validate_weight #


@pytest.mark.parametrize("rung", list(LineWeight))
def test_every_rung_validates_to_itself(rung: LineWeight):
    assert validate_weight(rung) is rung
    assert validate_weight(rung.value) is rung


@pytest.mark.parametrize("mm_value", list(ISO_LADDER_MM))
def test_ladder_floats_pass(mm_value: float):
    """The exact ladder values must validate without snapping."""
    out = validate_weight(mm_value)
    assert out.value == mm_value


@pytest.mark.parametrize(
    "off_ladder",
    [0.10, 0.20, 0.30, 0.40, 0.60, 0.80, 1.20, 1.60, 3.0],
)
def test_off_ladder_raises(off_ladder: float):
    with pytest.raises(ValueError, match="off the ISO 128 ladder"):
        validate_weight(off_ladder)


def test_within_tolerance_snaps_to_nearest_rung():
    """0.501 mm and 0.499 mm both snap to the 0.50 rung."""
    assert validate_weight(0.501) is LineWeight.W_0_50
    assert validate_weight(0.499) is LineWeight.W_0_50
    # Exact boundary case: ±SNAP_TOL_MM still snaps
    assert validate_weight(0.50 + SNAP_TOL_MM) is LineWeight.W_0_50
    assert validate_weight(0.50 - SNAP_TOL_MM) is LineWeight.W_0_50


def test_outside_tolerance_raises():
    """A value beyond the snap window must reject, not snap silently."""
    with pytest.raises(ValueError):
        validate_weight(0.50 + SNAP_TOL_MM * 2 + 1e-6)


def test_string_numeric_input_works():
    assert validate_weight("0.50") is LineWeight.W_0_50


def test_string_enum_name_input_works():
    assert validate_weight("W_0_50") is LineWeight.W_0_50


def test_unrelated_string_raises():
    with pytest.raises(ValueError):
        validate_weight("not a weight")


def test_wrong_type_raises():
    with pytest.raises(ValueError):
        validate_weight([0.5])  # type: ignore[arg-type]


# ------------------------------------------------------- LineWeightAssignment #


def test_assignment_accepts_enum():
    a = LineWeightAssignment(color="#1A1A1A", weight=LineWeight.W_0_70)
    assert a.weight is LineWeight.W_0_70
    assert a.color == "#1A1A1A"
    assert a.notes is None


def test_assignment_coerces_float():
    """Raw 0.50 mm on construction must be snapped to W_0_50."""
    a = LineWeightAssignment(color="cut", weight=0.50)  # type: ignore[arg-type]
    assert a.weight is LineWeight.W_0_50


def test_assignment_coerces_snapped_float():
    a = LineWeightAssignment(color="cut", weight=0.499)  # type: ignore[arg-type]
    assert a.weight is LineWeight.W_0_50


def test_assignment_rejects_off_ladder():
    with pytest.raises(ValueError):
        LineWeightAssignment(color="bad", weight=0.42)  # type: ignore[arg-type]


def test_assignment_carries_notes():
    a = LineWeightAssignment(
        color="section_cut", weight=LineWeight.W_0_70, notes="Ramsey/Sleeper §1.4"
    )
    assert a.notes == "Ramsey/Sleeper §1.4"


# ---------------------------------------------------- consumer wire-in check #


def test_presets_uses_canonical_ladder():
    """presets.py must source its ladder from line_weights, not its own list."""
    assert list(ISO_LADDER_MM) == presets._ISO_LADDER_MM
    assert list(ISO_LADDER_PT) == presets._ISO_LADDER_PT


def test_iso_print_tiers_use_ladder_weights():
    """Every main-hierarchy weight in *_ISO_PRINT presets must be on the ladder.

    'special' tiers (glazing, water, sky) are explicitly non-architectural and
    by convention not required to sit on the cut→texture ladder — `classify.py`
    already skips them. We mirror that exclusion here.
    """
    print_families = [
        presets.SECTION_ISO_PRINT,
        presets.PLAN_ISO_PRINT,
        presets.ELEVATION_ISO_PRINT,
        presets.DETAIL_ISO_PRINT,
    ]
    for family in print_families:
        for tier in family:
            if tier.name.startswith("special"):
                continue
            assert tier.weight_pt in ISO_LADDER_PT, (
                f"{tier.name}={tier.weight_pt} pt is off the ISO ladder "
                f"(allowed: {list(ISO_LADDER_PT)})"
            )


def test_select_preset_returns_ladder_aligned_tiers():
    """Scale-shifting must keep main-hierarchy tiers on the ladder."""
    tiers = presets.select_preset("section", "1/4", for_print=True)
    for tier in tiers:
        if tier.name.startswith("special"):
            continue
        assert tier.weight_pt in ISO_LADDER_PT
