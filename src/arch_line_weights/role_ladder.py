"""Drawing-role ladder — spec doc 49 §1.1 (roles) and §1.4 (assignment).

This module bridges *semantic drawing roles* (what a line means: a section cut,
a spatial edge, a surface change, …) onto the **existing** preset tier
vocabulary defined in :mod:`arch_line_weights.presets`. It does NOT invent new
weights: every weight is resolved by calling
:func:`presets.select_preset` and reading :attr:`presets.Tier.weight_pt`, and
every millimetre value is snapped to an ISO 128 rung with
:func:`line_weights.validate_weight`.

§1.1 role ladder (heaviest → lightest):

    CUT_PROFILE   — the section plane slices through it (the heaviest line)
    SPATIAL_EDGE  — a profile that separates solid from void in space
    PLANAR_CORNER — a plane change / object corner inside a solid
    SURFACE       — a surface change, material indication
    LAYOUT        — texture, hatch, layout / reference linework (lightest)

§1.4 assignment procedure is encoded in :func:`assign_role`, in the exact
priority order the spec lists.

**Integrity rule (geometry-free half).** A *cut profile* line, and any line
flagged ``integrity_protected``, must never be matched or exceeded in weight by
a lighter-role line. This module enforces the half of that rule that needs no
geometry: depth modulation and emphasis never touch a protected assignment, and
:func:`enforce_integrity` flags any lighter-role assignment that lands at or
above the heaviest protected weight.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

from .line_weights import ISO_LADDER_MM, pt_to_mm, validate_weight
from .presets import Tier, select_preset

# Tiers that are NOT part of the heaviest→lightest structural ladder: glazing /
# water / sky etc. live off to the side and must never be a fallback or clamp
# target.
_SPECIAL_TIER = "special"


def _snap_mm(weight_pt: float) -> float:
    """Convert a pt weight to mm and snap onto the nearest ISO 128 rung.

    Print weights land exactly on a rung, so :func:`validate_weight` succeeds.
    Screen ladders intentionally carry sub-0.13 mm weights that are *off* the
    ISO ladder; for those :func:`validate_weight` raises, so we fall back to the
    nearest rung by absolute distance and never raise.
    """
    mm = pt_to_mm(weight_pt)
    try:
        return validate_weight(mm).mm
    except ValueError:
        return min(ISO_LADDER_MM, key=lambda rung: abs(rung - mm))


class Role(Enum):
    """The §1.1 semantic role ladder, heaviest role first."""

    CUT_PROFILE = "cut-profile"
    SPATIAL_EDGE = "spatial-edge"
    PLANAR_CORNER = "planar-corner"
    SURFACE = "surface"
    LAYOUT = "layout"


# Authoritative role -> existing-preset-tier-name map. Every tier name here is
# verified to exist in select_preset(...) output for at least one preset; where a
# preset lacks the named tier, weight_for_role() falls back to the nearest
# heavier non-special tier.
ROLE_TO_PRESET_TIER: dict[Role, dict[str, str]] = {
    # "usc" is a deprecated alias for "studio"; both keys map identically so
    # weight_for_role() resolves either to the same studio tier ladder.
    Role.CUT_PROFILE: {
        "section": "cut",
        "studio": "cut",
        "usc": "cut",
        "plan": "walls_cut",
        "detail": "cut_primary",
        "elevation": "silhouette",
    },
    Role.SPATIAL_EDGE: {
        "section": "profile",
        "studio": "profile",
        "usc": "profile",
        "plan": "casework",
        "detail": "cut_secondary",
        "elevation": "silhouette",
    },
    Role.PLANAR_CORNER: {
        "section": "edges",
        "studio": "edges",
        "usc": "edges",
        "plan": "furniture",
        "detail": "edges",
        "elevation": "openings",
    },
    Role.SURFACE: {
        "section": "material",
        "studio": "material",
        "usc": "material",
        "plan": "pattern",
        "detail": "material",
        "elevation": "material",
    },
    Role.LAYOUT: {
        "section": "texture",
        "studio": "texture",
        "usc": "texture",
        "plan": "texture",
        "detail": "texture",
        "elevation": "texture",
    },
}


@dataclass(frozen=True)
class RoleAssignment:
    """One resolved role: which preset tier it maps to and at what weight.

    ``weight_pt`` is the value read straight from the preset tier (PostScript
    points). ``weight_mm`` is that value snapped onto an ISO 128 rung.
    """

    role: Role
    weight_mm: float
    weight_pt: float
    preset_tier: str
    continuous: bool
    integrity_protected: bool
    dashed_demote: bool
    why: str


def _normalize_preset(preset: str) -> str:
    """Unknown preset -> ``"section"`` (the documented default)."""
    return preset if preset in ROLE_TO_PRESET_TIER[Role.CUT_PROFILE] else "section"


def _ladder(preset: str, scale: str, for_print: bool) -> list[Tier]:
    """Available non-special tiers, ordered heaviest -> lightest."""
    tiers = [t for t in select_preset(preset, scale, for_print) if t.name != _SPECIAL_TIER]
    return sorted(tiers, key=lambda t: t.weight_pt, reverse=True)


def _lightest_pt(ladder: list[Tier]) -> float:
    """Lightest non-special weight (the floor for clamping / receding)."""
    return ladder[-1].weight_pt


def _make_assignment(role: Role, tier: Tier, why: str) -> RoleAssignment:
    """Build a :class:`RoleAssignment` from a resolved tier, snapping the mm."""
    return RoleAssignment(
        role=role,
        weight_mm=_snap_mm(tier.weight_pt),
        weight_pt=tier.weight_pt,
        preset_tier=tier.name,
        continuous=role is Role.CUT_PROFILE,
        integrity_protected=role in (Role.CUT_PROFILE, Role.SPATIAL_EDGE),
        dashed_demote=False,
        why=why,
    )


def weight_for_role(
    role: Role,
    *,
    preset: str = "section",
    scale: str = "1/4",
    for_print: bool = False,
) -> RoleAssignment:
    """Resolve ``role`` to a concrete preset tier + weight.

    The tier name comes from :data:`ROLE_TO_PRESET_TIER` (unknown ``preset``
    falls back to ``"section"``). If that tier name is absent from the selected
    preset, we fall back to the nearest **heavier** existing non-``special``
    tier; if none is heavier, we take the heaviest available. ``weight_mm`` is
    the tier's pt weight converted to mm and snapped onto an ISO 128 rung.
    """
    preset = _normalize_preset(preset)
    ladder = _ladder(preset, scale, for_print)
    by_name = {t.name: t for t in ladder}

    tier_name = ROLE_TO_PRESET_TIER[role][preset]
    if tier_name in by_name:
        return _make_assignment(role, by_name[tier_name], f"role {role.value} -> tier {tier_name}")

    # Tier missing in this preset: take the canonical weight the same tier name
    # carries in the default section ladder as the target, then choose the
    # nearest heavier existing tier (ladder is heaviest -> lightest).
    reference = {t.name: t.weight_pt for t in _ladder("section", scale, for_print)}
    wanted_pt = reference.get(tier_name, ladder[0].weight_pt)

    heavier = [t for t in ladder if t.weight_pt >= wanted_pt]
    chosen = heavier[-1] if heavier else ladder[0]
    return _make_assignment(
        role,
        chosen,
        f"role {role.value} -> tier {tier_name} absent in {preset}; "
        f"fell back to nearest heavier tier {chosen.name}",
    )


def modulate_by_depth(
    role: Role,
    base: RoleAssignment,
    depth_rank: int,
    depth_total: int,
    preset: str,
    scale: str,
    for_print: bool,
) -> RoleAssignment:
    """Recede a role's weight with depth.

    **v1 limitation:** the depth signal is the *colour-bucket order only* — the
    rank a line's colour occupies among the buckets present. There is NO
    geometry (no camera distance, no z-depth, no occlusion). ``depth_rank=0`` is
    the nearest bucket and is returned unchanged; each further rank recedes the
    weight by at most one ISO step, never below the preset's lightest
    non-``special`` rung.

    An ``integrity_protected`` assignment (a cut profile / spatial edge) is
    never modulated — :func:`modulate_by_depth` returns ``base`` unchanged.
    """
    if base.integrity_protected or depth_rank <= 0:
        return base

    preset = _normalize_preset(preset)
    ladder = _ladder(preset, scale, for_print)  # heaviest -> lightest
    floor_pt = _lightest_pt(ladder)

    # Index of the base weight on the ascending ladder, then step *down*
    # (lighter) by depth_rank, clamped at the lightest non-special rung.
    ascending = list(reversed(ladder))
    start = min(range(len(ascending)), key=lambda i: abs(ascending[i].weight_pt - base.weight_pt))
    target_idx = max(0, start - depth_rank)
    receded = ascending[target_idx]
    if receded.weight_pt < floor_pt:
        receded = ascending[0]

    return replace(
        base,
        weight_pt=receded.weight_pt,
        weight_mm=_snap_mm(receded.weight_pt),
        preset_tier=receded.name,
        why=f"{base.why}; receded {depth_rank} bucket(s) by colour order to {receded.name}",
    )


def _bump_one_step_heavier(
    assignment: RoleAssignment,
    preset: str,
    scale: str,
    for_print: bool,
) -> RoleAssignment:
    """Bump one ISO step heavier on the preset ladder (clamped at heaviest)."""
    ladder = _ladder(preset, scale, for_print)  # heaviest -> lightest
    ascending = list(reversed(ladder))
    idx = min(range(len(ascending)), key=lambda i: abs(ascending[i].weight_pt - assignment.weight_pt))
    bumped = ascending[min(len(ascending) - 1, idx + 1)]
    if bumped.weight_pt == assignment.weight_pt:
        return assignment
    return replace(
        assignment,
        weight_pt=bumped.weight_pt,
        weight_mm=_snap_mm(bumped.weight_pt),
        preset_tier=bumped.name,
        why=f"{assignment.why}; emphasis bump to {bumped.name}",
    )


def _clamp_to_ladder(
    assignment: RoleAssignment,
    preset: str,
    scale: str,
    for_print: bool,
) -> RoleAssignment:
    """Clamp a weight to [lightest_non_special, heaviest] available rungs."""
    ladder = _ladder(preset, scale, for_print)  # heaviest -> lightest
    heaviest_pt = ladder[0].weight_pt
    lightest_pt = _lightest_pt(ladder)

    if lightest_pt <= assignment.weight_pt <= heaviest_pt:
        return assignment

    target = ladder[0] if assignment.weight_pt > heaviest_pt else ladder[-1]
    return replace(
        assignment,
        weight_pt=target.weight_pt,
        weight_mm=_snap_mm(target.weight_pt),
        preset_tier=target.name,
        why=f"{assignment.why}; clamped to {target.name}",
    )


def assign_role(
    *,
    is_cut: bool = False,
    separates_solid_void: bool = False,
    is_planar_corner: bool = False,
    is_surface_change: bool = False,
    depth_rank: int = 0,
    depth_total: int = 1,
    emphasis: bool = False,
    too_dark_for_surface: bool = False,
    preset: str = "section",
    scale: str = "1/4",
    for_print: bool = False,
) -> RoleAssignment:
    """Encode the §1.4 assignment procedure, in the spec's exact order.

    Order:
      1. ``is_cut`` -> CUT_PROFILE (continuous + integrity-protected).
      2. ``separates_solid_void`` -> SPATIAL_EDGE (heaviest available;
         integrity-protected).
      3. ``is_planar_corner`` -> PLANAR_CORNER.
      4. ``is_surface_change`` -> SURFACE; if ``too_dark_for_surface`` set
         ``dashed_demote=True`` but keep the SURFACE weight (the ladder is not
         broken — we demote *line style*, not weight).
      5. otherwise -> LAYOUT.
      6. modulate by depth for the chosen role.
      7. emphasis: on a tie, bump one ISO step heavier, never past an
         integrity-protected line.
      8. clamp to the preset's available rungs (never below the lightest
         non-``special`` rung).

    Steps 6–8 never alter an ``integrity_protected`` assignment's weight.
    """
    preset = _normalize_preset(preset)

    if is_cut:
        role = Role.CUT_PROFILE
    elif separates_solid_void:
        role = Role.SPATIAL_EDGE
    elif is_planar_corner:
        role = Role.PLANAR_CORNER
    elif is_surface_change:
        role = Role.SURFACE
    else:
        role = Role.LAYOUT

    assignment = weight_for_role(role, preset=preset, scale=scale, for_print=for_print)

    if role is Role.SURFACE and too_dark_for_surface:
        assignment = replace(
            assignment,
            dashed_demote=True,
            why=f"{assignment.why}; too dark -> dashed demote (style only, weight kept)",
        )

    # (6) depth modulation (no-op for integrity-protected roles).
    assignment = modulate_by_depth(role, assignment, depth_rank, depth_total, preset, scale, for_print)

    # (7) emphasis bump — never touch an integrity-protected weight.
    if emphasis and not assignment.integrity_protected:
        assignment = _bump_one_step_heavier(assignment, preset, scale, for_print)

    # (8) clamp — never touch an integrity-protected weight.
    if not assignment.integrity_protected:
        assignment = _clamp_to_ladder(assignment, preset, scale, for_print)

    return assignment


def enforce_integrity(assignments: list[RoleAssignment]) -> list[str]:
    """Geometry-free half of the integrity rule.

    Returns one warning string per non-``integrity_protected`` assignment whose
    ``weight_pt`` is greater than or equal to the heaviest
    ``integrity_protected`` assignment's ``weight_pt``. If there is no protected
    assignment, or nothing violates it, returns an empty list.
    """
    protected = [a for a in assignments if a.integrity_protected]
    if not protected:
        return []

    heaviest_protected_pt = max(a.weight_pt for a in protected)

    warnings: list[str] = []
    for assignment in assignments:
        if assignment.integrity_protected:
            continue
        if assignment.weight_pt >= heaviest_protected_pt:
            warnings.append(
                f"integrity violation: {assignment.role.value} "
                f"({assignment.preset_tier}, {assignment.weight_pt} pt) "
                f">= heaviest integrity-protected line ({heaviest_protected_pt} pt)"
            )
    return warnings


__all__ = [
    "ROLE_TO_PRESET_TIER",
    "Role",
    "RoleAssignment",
    "assign_role",
    "enforce_integrity",
    "modulate_by_depth",
    "weight_for_role",
]
