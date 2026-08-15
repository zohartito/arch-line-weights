"""Tonal recede — value demotion for beyond-cut geometry.

The weight pipeline makes un-cut geometry *thinner*; strong studio sections
also make it *lighter* (``docs/research/target-look-spec.md`` §1.3, §4.2 gap):

    "black = cut, grey = solid-but-uncut, hairline = organizing line,
     dashed = subordinate, tone = material"  — spec §1.3

    "Tonal recede for 'beyond' geometry. The best sections push un-cut
     structure to thin grey; the engine sets weights but does not auto-demote
     value/opacity of beyond-cut layers."  — spec §4.2

This module supplies that missing value ramp. It is **off by default** — the
apply paths only consult it when the caller opts in via ``--tonal-recede``.

Determinism boundary (AGENTS.md): the tone math lives entirely here, in code,
with no model in the loop; the same ``(rgb, weight)`` always yields the same
color.

Design — tone follows the weight ladder, not the layer name
-----------------------------------------------------------
A stroke's *role* is already encoded in the weight the pipeline assigns it: the
section cut is the heaviest line (spec §1.2 "cut > profile > texture"), and each
lighter tier is a step down the same role ladder. Keying the value ramp off the
resolved weight makes it work for **both** input classes with one rule:

  * color-coded drawings (``--auto`` / ``--mapping``) where the weight comes
    from the color bucket — e.g. the synthetic demo section, which has no OCG
    layers at all; and
  * layer-named Rhino exports (``--architectural``) where the weight comes from
    the layer role.

The cut keeps full value (never lightened); every step down the weight ladder
retains a documented fraction of its original darkness, scaling toward white.
"""

from __future__ import annotations

from collections.abc import Callable

# --------------------------------------------------------------------------- #
# The value ramp — every rung cites the corpus spec it serves.
# docs/research/target-look-spec.md §1.2 (the weight ramp) / §1.3 (the cut owns
# the darkest value).
# --------------------------------------------------------------------------- #

# Darkness-retention floor: a beyond stroke never lightens past this fraction of
# its original darkness, so hairlines stay legible and nothing recedes to pure
# white (spec §1.3 "hairline = organizing line" — the thinnest lines must still
# read). The lightest ramp rung (0.32) already sits above this; the floor is the
# hard guard that keeps future ramp edits honest.
TONE_FLOOR = 0.28

# (min_weight_pt inclusive, darkness_factor, tier_label). Descending by weight.
# The factors are the task's suggested anchors, chosen to land the demo section's
# five weight tiers (1.0 / 0.5 / 0.3 / 0.13 / 0.08 pt) on five distinct rungs and
# to match the §1.3 role ladder (cut → profile → edge → material → texture):
#
#   cut      1.00  the cut owns the darkest value; never demoted   (spec §1.3)
#   profile  0.72  solid-but-uncut primary structure → thin grey   (spec §1.3)
#   edges    0.55  beyond edges / secondary members / enclosure     (spec §1.2)
#   material 0.42  material indication / annotation / entourage     (spec §1.3)
#   texture  0.32  surface texture / hatch — the lightest linework  (spec §1.2)
#
# Thresholds sit *between* the section screen weights in ``architectural.py``
# (_SECTION_SCREEN_WEIGHTS) so each named tier lands on its own rung.
_TONE_LADDER: tuple[tuple[float, float, str], ...] = (
    (0.85, 1.00, "cut"),
    (0.45, 0.72, "profile"),
    (0.22, 0.55, "edges"),
    (0.10, 0.42, "material"),
    (0.00, 0.32, "texture"),
)

# Supported recede modes. "value" preserves hue (scales the source color toward
# white, so Fork-E system-color drawings keep their coding — spec §2); "grey"
# neutralizes to a grey of equal value first, for a monochrome tonal-cut sheet.
MODES = ("value", "grey")
DEFAULT_MODE = "value"


def tone_factor_for_weight(weight_pt: float) -> float:
    """Return the darkness-retention factor for a stroke of ``weight_pt``.

    1.0 means "keep full value" (the cut tier); lighter tiers return a smaller
    fraction. The returned factor is never below :data:`TONE_FLOOR`.
    """
    for threshold, factor, _label in _TONE_LADDER:
        if weight_pt >= threshold:
            return max(factor, TONE_FLOOR)
    return max(_TONE_LADDER[-1][1], TONE_FLOOR)


def tone_tier_for_weight(weight_pt: float) -> str:
    """Return the tier label (``"cut"`` … ``"texture"``) for ``weight_pt``."""
    for threshold, _factor, label in _TONE_LADDER:
        if weight_pt >= threshold:
            return label
    return _TONE_LADDER[-1][2]


def _rec709_luminance(rgb: tuple[int, int, int]) -> float:
    """Rec. 709 relative luminance in 0..255 space."""
    r, g, b = rgb
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _lighten_channel(channel: float, factor: float) -> int:
    """Scale one channel toward white, retaining ``factor`` of its darkness."""
    value = 255.0 - factor * (255.0 - channel)
    return round(max(0.0, min(255.0, value)))


def recede_rgb(
    rgb: tuple[int, int, int],
    weight_pt: float,
    *,
    mode: str = DEFAULT_MODE,
) -> tuple[int, int, int] | None:
    """Lighten a beyond-cut stroke color by its weight tier.

    Returns the demoted RGB, or ``None`` when the stroke must be left untouched:
    the cut tier (factor ``1.0``) is integrity-protected and never lightened
    (spec §1.3), and a no-op result (already at the target value) also returns
    ``None`` so callers can skip emitting a redundant color op.

    ``mode``:
      * ``"value"`` — scale the source color toward white, preserving hue so a
        color-coded (Fork-E) drawing keeps its system coding (spec §2).
      * ``"grey"`` — neutralize to a grey of the source's luminance first, then
        apply the same value scaling: a monochrome tonal-cut sheet (Fork B).
    """
    factor = tone_factor_for_weight(weight_pt)
    if factor >= 1.0:
        return None  # cut tier — never demote its value

    if mode == "grey":
        lum = _rec709_luminance(rgb)
        toned_value = _lighten_channel(lum, factor)
        toned = (toned_value, toned_value, toned_value)
    else:  # "value" (hue-preserving) — the default
        toned = (
            _lighten_channel(rgb[0], factor),
            _lighten_channel(rgb[1], factor),
            _lighten_channel(rgb[2], factor),
        )

    if toned == rgb:
        return None
    return toned


def tonal_recede_resolver(
    mode: str = DEFAULT_MODE,
) -> Callable[[tuple[int, int, int], float], tuple[int, int, int] | None]:
    """Return a ``(rgb, weight_pt) -> rgb | None`` callback for the apply paths.

    The callback lightens beyond-cut strokes per :func:`recede_rgb`. The apply
    modules resolve each stroke's weight (from the layer role or color bucket)
    and hand it here alongside the current stroke color.
    """
    if mode not in MODES:
        raise ValueError(f"unknown tonal-recede mode {mode!r}; expected one of {MODES}")

    def _resolve(rgb: tuple[int, int, int], weight_pt: float) -> tuple[int, int, int] | None:
        return recede_rgb(rgb, weight_pt, mode=mode)

    return _resolve


def describe_ramp(mode: str = DEFAULT_MODE) -> list[str]:
    """Human-readable ramp description for CLI echo (heaviest → lightest)."""
    lines = [f"# tonal-recede: {mode}-mode ramp for beyond-cut geometry (spec §1.3/§4.2)"]
    for _threshold, factor, label in _TONE_LADDER:
        if factor >= 1.0:
            lines.append(f"#   {label:<9} keep full value (cut owns the darkest value)")
        else:
            lines.append(f"#   {label:<9} retain {factor:.0%} of original darkness")
    return lines


__all__ = [
    "DEFAULT_MODE",
    "MODES",
    "TONE_FLOOR",
    "describe_ramp",
    "recede_rgb",
    "tonal_recede_resolver",
    "tone_factor_for_weight",
    "tone_tier_for_weight",
]
