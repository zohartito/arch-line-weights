"""Per-preset drawing rules — spec doc 49 §1.3.

Each built-in preset carries a small bundle of *rules* describing how its
weight ladder behaves: whether it is **cut-driven** (a section plane slices
through the heaviest line, integrity enforced), which :class:`Role` is the
heaviest line, how depth grading recedes weight, and whether it owns a
groundline.

This module is metadata + thin resolvers only. It invents no weights: every
concrete weight is resolved through
:func:`arch_line_weights.role_ladder.weight_for_role`, which itself reads the
existing preset tiers via :func:`presets.select_preset`. The role vocabulary
(:class:`Role`) and the role→tier map (``ROLE_TO_PRESET_TIER``) are imported
from :mod:`arch_line_weights.role_ladder`; they are never redefined here.

§1.3 distinctions encoded here:

* ``plan`` / ``section`` / ``usc`` / ``detail`` are **cut-driven** — heaviest
  role is :attr:`Role.CUT_PROFILE` and the integrity rule is enforced.
* ``elevation`` is a **no-cut** figure-ground drawing — heaviest role is
  :attr:`Role.SPATIAL_EDGE` (the silhouette). It owns one true cut, the
  *groundline* through soil, so ``has_groundline`` is ``True``.
* ``axon`` is also no-cut figure-ground, but a floating axonometric has **no**
  groundline. The generic :func:`figure_ground_rule` is therefore a pure
  3-tier order (``SPATIAL_EDGE`` > ``PLANAR_CORNER`` > ``SURFACE``) with no
  groundline, so a future dedicated axon preset can adopt it verbatim.

Depth-grading direction differs per drawing type, captured by
:class:`DepthModel`:

* plan -> :attr:`DepthModel.DROP_BELOW_CUT` (farther below the cut plane is
  lighter);
* section / usc / detail -> :attr:`DepthModel.BEHIND_CUT` (farther behind the
  cut is lighter);
* elevation / axon -> :attr:`DepthModel.FIGURE_GROUND` (recede with distance).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

from .role_ladder import ROLE_TO_PRESET_TIER, Role, weight_for_role

# Default preset, mirroring select_preset() / role_ladder fallback behaviour.
_DEFAULT_PRESET = "section"

# The no-cut figure-ground order, heaviest -> lightest. Pure 3-tier, no
# groundline — reusable verbatim by elevation and a future axon preset.
_FIGURE_GROUND_ORDER: tuple[Role, ...] = (
    Role.SPATIAL_EDGE,
    Role.PLANAR_CORNER,
    Role.SURFACE,
)


class DepthModel(Enum):
    """How a preset grades weight with depth (§1.3)."""

    DROP_BELOW_CUT = "drop-below-cut"
    BEHIND_CUT = "behind-cut"
    FIGURE_GROUND = "figure-ground"


@dataclass(frozen=True)
class PresetRule:
    """The §1.3 rule bundle for one preset.

    Attributes:
        preset: The preset label this rule describes.
        cut_driven: ``True`` when a section plane drives the heaviest line.
        heaviest_role: The :class:`Role` that owns the heaviest weight.
        depth_model: How depth grading recedes weight (:class:`DepthModel`).
        integrity_enforced: ``True`` when the integrity rule applies (no
            lighter-role line may match/exceed the heaviest protected weight).
        range_widen_steps: Recorded metadata — extra ISO steps the native
            ladder already spans (detail = 1). Not an aggressive shift.
        has_groundline: ``True`` when the preset owns a groundline (the one
            true cut through soil). Elevation = ``True``; a floating axon =
            ``False``.
    """

    preset: str
    cut_driven: bool
    heaviest_role: Role
    depth_model: DepthModel
    integrity_enforced: bool
    range_widen_steps: int
    has_groundline: bool


PRESET_RULES: dict[str, PresetRule] = {
    "section": PresetRule(
        preset="section",
        cut_driven=True,
        heaviest_role=Role.CUT_PROFILE,
        depth_model=DepthModel.BEHIND_CUT,
        integrity_enforced=True,
        range_widen_steps=0,
        has_groundline=False,
    ),
    "usc": PresetRule(
        preset="usc",
        cut_driven=True,
        heaviest_role=Role.CUT_PROFILE,
        depth_model=DepthModel.BEHIND_CUT,
        integrity_enforced=True,
        range_widen_steps=0,
        has_groundline=False,
    ),
    "plan": PresetRule(
        preset="plan",
        cut_driven=True,
        heaviest_role=Role.CUT_PROFILE,
        depth_model=DepthModel.DROP_BELOW_CUT,
        integrity_enforced=True,
        range_widen_steps=0,
        has_groundline=False,
    ),
    "elevation": PresetRule(
        preset="elevation",
        cut_driven=False,
        heaviest_role=Role.SPATIAL_EDGE,
        depth_model=DepthModel.FIGURE_GROUND,
        integrity_enforced=False,
        range_widen_steps=0,
        has_groundline=True,
    ),
    "detail": PresetRule(
        preset="detail",
        cut_driven=True,
        heaviest_role=Role.CUT_PROFILE,
        depth_model=DepthModel.BEHIND_CUT,
        integrity_enforced=True,
        range_widen_steps=1,
        has_groundline=False,
    ),
}


def figure_ground_rule() -> tuple[Role, ...]:
    """Generic no-cut figure-ground order, heaviest -> lightest.

    ``(SPATIAL_EDGE, PLANAR_CORNER, SURFACE)`` — pure 3-tier, no groundline.
    Reusable verbatim by elevation and a future dedicated axon preset.
    """
    return _FIGURE_GROUND_ORDER


def rule_for_preset(preset: str) -> PresetRule:
    """Return the :class:`PresetRule` for ``preset``.

    ``"axon"`` is not a registered preset but resolves to the dedicated no-cut
    figure-ground rule (:func:`rule_for_axon`). Any other unknown preset falls
    back to the ``"section"`` rule, mirroring :func:`presets.select_preset`.
    """
    if preset == "axon":
        return rule_for_axon()
    return PRESET_RULES.get(preset, PRESET_RULES[_DEFAULT_PRESET])


def rule_for_axon() -> PresetRule:
    """No-cut figure-ground rule for a floating axonometric.

    Reuses elevation's figure-ground weights (the ``"elevation"`` preset
    mapping) but with **no groundline** — a floating axon owns no cut through
    soil. The returned rule is labelled ``"axon"``.
    """
    return replace(
        PRESET_RULES["elevation"],
        preset="axon",
        has_groundline=False,
    )


def ladder_for_preset(
    preset: str,
    scale: str = "1/4",
    for_print: bool = False,
) -> dict[Role, float]:
    """Map every :class:`Role` to its ``weight_pt`` for ``preset``.

    Weights are resolved through
    :func:`arch_line_weights.role_ladder.weight_for_role`, so they come
    straight from the existing preset tiers. ``"axon"`` reuses elevation's
    figure-ground weights (it has no native tier ladder of its own). Any other
    unknown ``preset`` falls back to section inside that call. Detail's wider
    range comes from its native tier weights; ``range_widen_steps`` is recorded
    metadata only and is not applied as an aggressive shift here.
    """
    resolved = "elevation" if preset == "axon" else preset
    return {
        role: weight_for_role(role, preset=resolved, scale=scale, for_print=for_print).weight_pt
        for role in ROLE_TO_PRESET_TIER
    }


__all__ = [
    "PRESET_RULES",
    "DepthModel",
    "PresetRule",
    "figure_ground_rule",
    "ladder_for_preset",
    "rule_for_axon",
    "rule_for_preset",
]
