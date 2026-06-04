"""Linetype assignment for layer names (spec doc 49 §1.2 + AIA status suffixes).

This module is the *pure linetype* half of the line-weight pipeline. It maps a
layer name onto a dashed/solid linetype and an AIA construction status
(new / demolish / existing), and emits the PostScript dash array that a content
stream needs (``[on off ...] phase d``). It does NOT decide line *weights* —
that lives in :mod:`arch_line_weights.presets` /
:mod:`arch_line_weights.line_weights`. The status modifier here only carries a
``weight_scale`` multiplier so the weight stage can dim screened linework;
this module never resolves a millimetre value itself.

Token vocabulary follows the AIA *CAD Layer Guidelines* (NCS) minor-group
field names (HIDD, CNTR, PHTM, SECT, ...) and is matched with the same
substring strategy as :mod:`arch_line_weights.layer_classify`, so the rules
can be lifted into ExtendScript. AutoCAD/AIA names are hyphen-padded so a token
like ``CL`` matches a field boundary rather than an accidental substring.

Schema convention follows the rest of the package (``@dataclass`` + ``enum``),
not Pydantic.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

from .layer_classify import Source


class LineType(Enum):
    """A drafting linetype. String values are the stable wire tokens."""

    CONTINUOUS = "continuous"
    DASHED = "dashed"
    DASH_DOT = "dash-dot"
    PHANTOM = "phantom"
    CUTTING_PLANE = "cutting-plane"
    BREAK = "break"
    PROPERTY = "property"
    DIMENSION = "dimension"
    NON_PLOTTING = "non-plotting"


class AIAStatus(Enum):
    """AIA construction-status suffix on a layer name.

    NEWW = new work, DEMO = to be demolished, EXST = existing to remain,
    NONE = no status field present.
    """

    NEWW = "neww"
    DEMO = "demo"
    EXST = "exst"
    NONE = "none"


@dataclass(frozen=True)
class LineTypeAssignment:
    """The linetype decision for one layer, alongside dash + screening hints.

    ``dash_pattern_pt`` is ``((on, off, ...), phase)`` in PostScript points, or
    ``None`` for a solid line. ``weight_scale`` is a multiplier the *weight*
    stage applies (1.0 = full, 0.5 = screened/half). ``why`` is a short human
    note describing the match.
    """

    linetype: LineType
    excluded: bool
    screened: bool
    weight_scale: float
    dash_pattern_pt: tuple[tuple[float, ...], float] | None
    why: str


# Dash geometry per linetype, in PostScript points: ((on, off, ...), phase).
# CONTINUOUS / DIMENSION / PROPERTY / CUTTING_PLANE / BREAK are treated as
# solid in v1 and are intentionally absent from this table.
DASH_PATTERNS_PT: dict[LineType, tuple[tuple[float, ...], float]] = {
    LineType.DASHED: ((3.0, 2.0), 0.0),
    LineType.DASH_DOT: ((4.0, 2.0, 1.0, 2.0), 0.0),
    LineType.PHANTOM: ((6.0, 2.0, 1.0, 2.0, 1.0, 2.0), 0.0),
}


# Uppercase AIA/NCS field tokens -> LineType. Insertion order is the match
# order (Python dicts preserve it); longer / more-specific tokens come first so
# they win before short ambiguous ones (e.g. CENT/CNTR before the bare CL).
LINETYPE_BY_TOKEN: dict[str, LineType] = {
    # Hidden / overhead / above (dashed)
    "HIDD": LineType.DASHED,
    "OVHD": LineType.DASHED,
    "ABOV": LineType.DASHED,
    "HID": LineType.DASHED,
    # Centerline / axis (dash-dot)
    "CNTR": LineType.DASH_DOT,
    "CENT": LineType.DASH_DOT,
    "CL": LineType.DASH_DOT,
    # Phantom (long-dash double-short-dash)
    "PHTM": LineType.PHANTOM,
    "PHAN": LineType.PHANTOM,
    # Section / cutting plane
    "SECT": LineType.CUTTING_PLANE,
    "CUTL": LineType.CUTTING_PLANE,
    # Break line
    "BRK": LineType.BREAK,
    # Property / projection line
    "PROP": LineType.PROPERTY,
    "PROJ": LineType.PROPERTY,
    # Dimensions / leaders / annotation / text (solid annotation linework)
    "DIMS": LineType.DIMENSION,
    "LEAD": LineType.DIMENSION,
    "ANNO": LineType.DIMENSION,
    "TEXT": LineType.DIMENSION,
    # Non-plotting (excluded from output)
    "NPLT": LineType.NON_PLOTTING,
}


# AIA status field tokens -> AIAStatus. Matched as hyphen/space-anchored fields.
_STATUS_BY_TOKEN: dict[str, AIAStatus] = {
    "NEWW": AIAStatus.NEWW,
    "DEMO": AIAStatus.DEMO,
    "EXST": AIAStatus.EXST,
}


def _haystack(name: str, source: Source) -> str:
    """Uppercase ``name`` and, for AutoCAD/AIA, hyphen-pad it to ``-NAME-``."""
    upper = name.upper()
    return f"-{upper}-" if source == Source.AUTOCAD else upper


def _token_in(token: str, haystack: str, source: Source) -> bool:
    """Match a token against the haystack.

    AutoCAD/AIA layer names are field-delimited, so the token must sit between
    field boundaries (``-CL-``) — this prevents false positives such as ``CL``
    inside ``CLNG`` or ``ANNO`` inside an unrelated name. Rhino names have no
    field grammar, so a plain substring is used (and is exercised by tests).
    """
    if source == Source.AUTOCAD:
        return f"-{token}-" in haystack
    return token in haystack


def linetype_for_layer(name: str, *, source: Source = Source.RHINO) -> LineTypeAssignment:
    """Resolve the (pure) linetype for a layer name.

    Uppercases the name (hyphen-padding AutoCAD/AIA names), then returns the
    first matching token in :data:`LINETYPE_BY_TOKEN`. With no match the default
    is :attr:`LineType.CONTINUOUS` (solid). Non-plotting (``-NPLT``) is checked
    FIRST so it wins over every other token (a non-plotting annotation or
    centerline is still excluded), setting ``excluded=True``.
    """
    haystack = _haystack(name, source)

    # Non-plotting must outrank every other linetype token.
    if _token_in("NPLT", haystack, source):
        return LineTypeAssignment(
            linetype=LineType.NON_PLOTTING,
            excluded=True,
            screened=False,
            weight_scale=1.0,
            dash_pattern_pt=None,
            why="token 'NPLT' -> non-plotting (excluded)",
        )

    for token, linetype in LINETYPE_BY_TOKEN.items():
        if linetype is LineType.NON_PLOTTING:
            continue  # handled by the pre-check above
        if _token_in(token, haystack, source):
            return LineTypeAssignment(
                linetype=linetype,
                excluded=False,
                screened=False,
                weight_scale=1.0,
                dash_pattern_pt=DASH_PATTERNS_PT.get(linetype),
                why=f"token {token!r} -> {linetype.value}",
            )

    return LineTypeAssignment(
        linetype=LineType.CONTINUOUS,
        excluded=False,
        screened=False,
        weight_scale=1.0,
        dash_pattern_pt=None,
        why="no linetype token matched -> continuous (solid)",
    )


def aia_status_from_name(name: str) -> AIAStatus:
    """Parse the AIA status field (``-NEWW`` / ``-DEMO`` / ``-EXST``).

    The status token is matched as a hyphen/space-anchored field so it is not
    confused with an arbitrary substring. Returns :attr:`AIAStatus.NONE` when
    no status field is present.
    """
    haystack = f"-{name.upper()}-".replace(" ", "-")
    for token, status in _STATUS_BY_TOKEN.items():
        if f"-{token}-" in haystack:
            return status
    return AIAStatus.NONE


def apply_status(base: LineTypeAssignment, status: AIAStatus) -> LineTypeAssignment:
    """Fold an :class:`AIAStatus` into a base linetype assignment.

    NEWW forces a full-weight solid line. DEMO / EXST force a screened dashed
    line at half weight. NONE returns ``base`` unchanged. An already-excluded
    (non-plotting) assignment is never resurrected by a status.
    """
    if status is AIAStatus.NONE or base.excluded:
        return base

    if status is AIAStatus.NEWW:
        return replace(
            base,
            linetype=LineType.CONTINUOUS,
            dash_pattern_pt=None,
            screened=False,
            weight_scale=1.0,
            why=f"{base.why}; status NEWW -> continuous, full weight",
        )

    # DEMO or EXST -> screened dashed at half weight.
    return replace(
        base,
        linetype=LineType.DASHED,
        dash_pattern_pt=DASH_PATTERNS_PT[LineType.DASHED],
        screened=True,
        weight_scale=0.5,
        why=f"{base.why}; status {status.name} -> dashed, screened, half weight",
    )


def dash_token(a: LineTypeAssignment) -> bytes | None:
    """Render a PostScript dash setter (``[on off ...] phase d``) for ``a``.

    Returns ``None`` when the assignment is excluded. A solid assignment
    (``dash_pattern_pt is None``) renders ``b"[] 0 d"``. Numbers use ``f"{n:g}"``
    so whole numbers carry no trailing ``.0``.
    """
    if a.excluded:
        return None

    if a.dash_pattern_pt is None:
        return b"[] 0 d"

    pattern, phase = a.dash_pattern_pt
    inside = " ".join(f"{n:g}" for n in pattern)
    return f"[{inside}] {phase:g} d".encode("ascii")


__all__ = [
    "DASH_PATTERNS_PT",
    "LINETYPE_BY_TOKEN",
    "AIAStatus",
    "LineType",
    "LineTypeAssignment",
    "aia_status_from_name",
    "apply_status",
    "dash_token",
    "linetype_for_layer",
]
