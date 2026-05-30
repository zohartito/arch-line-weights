"""ISO 128 line-weight ladder, encoded as a strict type.

The ISO 128-20 √2 geometric series for architectural drawings:

    0.13, 0.18, 0.25, 0.35, 0.50, 0.70, 1.00, 1.40, 2.00 mm

This module replaces free-text line-weight conventions with a single canonical
source of truth — an enum + validator that any consumer can rely on. Off-ladder
millimetre values raise `ValueError`; floats within ±0.005 mm of a rung snap
to the nearest rung.

The project tracks line weights internally in PostScript **points** (pt) for
historical reasons (pikepdf content streams write `<w> w` in points). Use
`mm_to_pt` and `pt_to_mm` to round-trip between the typed mm ladder and the
pt values stored on :class:`presets.Tier`.

Schema convention follows the rest of the package (`@dataclass`), not Pydantic.
arch-line-weights does not depend on Pydantic and does not need to.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

# PostScript point per millimetre. The same constant lives in `presets.MM_TO_PT`
# and is re-exposed there for backward compatibility.
MM_TO_PT: float = 2.835

# Snap tolerance: a float within ±SNAP_TOL_MM of a ladder rung is treated as
# that rung. 0.005 mm = half a thousandth of a millimetre — tighter than any
# CAD/drafting workflow can meaningfully distinguish.
SNAP_TOL_MM: float = 0.005


class LineWeight(Enum):
    """The ISO 128-20 √2 line-weight ladder, in millimetres.

    Enum values are floats so a `LineWeight` member can be used directly in
    arithmetic (e.g. `LineWeight.W_0_70.value * MM_TO_PT`).
    """

    W_0_13 = 0.13
    W_0_18 = 0.18
    W_0_25 = 0.25
    W_0_35 = 0.35
    W_0_50 = 0.50
    W_0_70 = 0.70
    W_1_00 = 1.00
    W_1_40 = 1.40
    W_2_00 = 2.00

    @property
    def mm(self) -> float:
        """Weight in millimetres."""
        return float(self.value)

    @property
    def pt(self) -> float:
        """Weight in PostScript points (rounded to 3 dp, matching `presets.mm`)."""
        return round(self.value * MM_TO_PT, 3)


# Canonical ordered ladder (ascending). Other modules may import this instead
# of hard-coding `[0.13, 0.18, ...]`.
ISO_LADDER_MM: tuple[float, ...] = tuple(w.value for w in LineWeight)
ISO_LADDER_PT: tuple[float, ...] = tuple(w.pt for w in LineWeight)


def mm_to_pt(mm: float) -> float:
    """Millimetres → PostScript points, rounded to 3 dp."""
    return round(mm * MM_TO_PT, 3)


def pt_to_mm(pt: float) -> float:
    """PostScript points → millimetres, rounded to 3 dp."""
    return round(pt / MM_TO_PT, 3)


def validate_weight(value: float | str | LineWeight) -> LineWeight:
    """Coerce `value` to a :class:`LineWeight`, snapping within ±0.005 mm.

    Accepted inputs:
      * a :class:`LineWeight` member — returned as-is
      * a float in millimetres (e.g. ``0.50``) — must be within
        ±:data:`SNAP_TOL_MM` of a ladder rung
      * a string — either the numeric mm value (``"0.50"``) or the enum
        member name (``"W_0_50"``)

    Anything off-ladder raises :class:`ValueError`.
    """
    if isinstance(value, LineWeight):
        return value

    if isinstance(value, str):
        # Try enum-name first ("W_0_50"), then numeric ("0.50").
        try:
            return LineWeight[value]
        except KeyError:
            try:
                value = float(value)
            except ValueError as exc:
                raise ValueError(
                    f"{value!r} is not a valid LineWeight name or numeric mm value"
                ) from exc

    if not isinstance(value, (int, float)):
        raise ValueError(
            f"validate_weight expects float | str | LineWeight, got {type(value).__name__}"
        )

    nearest = min(LineWeight, key=lambda w: abs(w.value - float(value)))
    # `> SNAP_TOL_MM + 1e-9` allows the exact boundary (±0.005 mm) through.
    # Using strict `>` alone makes 0.505 fail because float subtraction yields
    # 0.005000…001 rather than exactly 0.005.
    if abs(nearest.value - float(value)) > SNAP_TOL_MM + 1e-9:
        raise ValueError(
            f"{value} mm is off the ISO 128 ladder "
            f"({list(ISO_LADDER_MM)}); nearest rung is {nearest.value} mm "
            f"(Δ={abs(nearest.value - float(value)):.4f} mm > tol {SNAP_TOL_MM})"
        )
    return nearest


@dataclass(frozen=True)
class LineWeightAssignment:
    """Bind one colour to one ladder rung, with an optional human note.

    `color` is intentionally typed as ``str`` so callers can use either a
    hex string (``"#1A1A1A"``) or a named colour (``"section_cut"``);
    arch-line-weights' RGB lookup happens elsewhere (see
    :mod:`arch_line_weights.classify`).

    `weight` is always a :class:`LineWeight` after construction — the
    `__post_init__` runs the same snap/validate logic as
    :func:`validate_weight`.
    """

    color: str
    weight: LineWeight
    notes: str | None = None

    def __post_init__(self) -> None:
        # Allow callers to pass a raw float / str; coerce on the way in.
        if not isinstance(self.weight, LineWeight):
            object.__setattr__(self, "weight", validate_weight(self.weight))  # type: ignore[arg-type]


__all__ = [
    "ISO_LADDER_MM",
    "ISO_LADDER_PT",
    "MM_TO_PT",
    "SNAP_TOL_MM",
    "LineWeight",
    "LineWeightAssignment",
    "mm_to_pt",
    "pt_to_mm",
    "validate_weight",
]
