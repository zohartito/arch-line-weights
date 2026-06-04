"""Decide which color belongs to which tier.

Phase 1 supports two strategies:
  * `from_user_mapping` — user provides {color_key: weight_pt}
  * `auto_by_luminance` — bucket colors into N tiers by relative luminance,
    most-frequent-and-lightest → texture, darkest → cut

Phase 3 will add smarter classification (saturation, hue family, frequency).
"""

from __future__ import annotations

from .inspect import InspectionReport, color_to_rgb255
from .linetypes import LineType
from .preset_rules import rule_for_preset
from .presets import Tier
from .role_ladder import Role, weight_for_role


def from_user_mapping(
    mapping_rgb_to_weight: dict[tuple[int, int, int], float],
) -> dict[tuple[int, int, int], float]:
    """Pass-through; just here for API symmetry."""
    return dict(mapping_rgb_to_weight)


def _luminance(rgb: tuple[int, int, int]) -> float:
    """Relative luminance per Rec. 709 (0=black, 1=white)."""
    r, g, b = (c / 255.0 for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def auto_by_luminance(
    report: InspectionReport,
    tiers: list[Tier],
) -> dict[tuple[int, int, int], float]:
    """Bucket every RGB stroke color in the report into one of `tiers`.

    Strategy: sort distinct colors darkest → lightest by Rec. 709 luminance,
    skip any tier named "special" (reserved for explicit mapping), and split
    colors into N buckets by *color index* so the darkest colors land in the
    heaviest tier and the lightest colors land in the lightest tier.

    Frequency is a tie-breaker only (more-common color of the same luminance
    leans lighter), not a primary signal — otherwise dominant texture colors
    would steal middle tiers.
    """
    main_tiers = [t for t in tiers if not t.name.startswith("special")]
    if not main_tiers:
        main_tiers = list(tiers)
    tiers_heavy_to_light = sorted(main_tiers, key=lambda t: -t.weight_pt)
    n_tiers = len(tiers_heavy_to_light)

    rgb_counts: list[tuple[tuple[int, int, int], int]] = []
    for ckey, count in report.stroke_colors.items():
        rgb = color_to_rgb255(ckey)
        if rgb is None:
            continue
        rgb_counts.append((rgb, count))
    if not rgb_counts:
        return {}

    # Darkest first; among same luminance, more frequent leans toward light.
    rgb_counts.sort(key=lambda rc: (_luminance(rc[0]), -rc[1]))
    n_colors = len(rgb_counts)

    mapping: dict[tuple[int, int, int], float] = {}
    if n_colors == 1:
        mapping[rgb_counts[0][0]] = tiers_heavy_to_light[-1].weight_pt
        return mapping
    for idx, (rgb, _count) in enumerate(rgb_counts):
        # Linear interpolation across tier indices, last color → last tier.
        bucket = round((idx / (n_colors - 1)) * (n_tiers - 1))
        mapping[rgb] = tiers_heavy_to_light[bucket].weight_pt
    return mapping


# Role order per drawing type. Cut-driven presets start at the section cut; no-cut
# presets (elevation/axon) start at the spatial edge — the silhouette is the
# heaviest line because there is no cut (spec doc 49 §1.3/§1.4).
_CUT_DRIVEN_ROLE_ORDER = [
    Role.CUT_PROFILE,
    Role.SPATIAL_EDGE,
    Role.PLANAR_CORNER,
    Role.SURFACE,
    Role.LAYOUT,
]
_NO_CUT_ROLE_ORDER = [
    Role.SPATIAL_EDGE,
    Role.PLANAR_CORNER,
    Role.SURFACE,
    Role.LAYOUT,
]


def auto_by_role(
    report: InspectionReport,
    preset: str = "section",
    scale: str = "1/4",
    for_print: bool = False,
) -> tuple[dict[tuple[int, int, int], float], dict[tuple[int, int, int], LineType]]:
    """Role-based color→weight mapping (spec doc 49 §1.4) — the default `--auto`.

    Replaces the coarse luminance tiers. Distinct stroke colors are sorted
    darkest → lightest and bucketed across the preset's ROLE ladder: a cut-driven
    preset starts at CUT_PROFILE (the section cut is the heaviest line); a no-cut
    preset (elevation) starts at SPATIAL_EDGE (the silhouette is heaviest — there
    is no cut). The darkest color gets the heaviest role; that ordering *is* the
    §1.4 depth grading (nearer/darker = heavier).

    Each weight is resolved through :func:`role_ladder.weight_for_role`, so it
    comes straight from the existing preset tiers (no hard-coded weights). The
    returned linetype is CONTINUOUS for every color: a stroke's *color* cannot
    reveal its linetype (hidden/center/etc.) — that signal lives in layer names
    (§1.2/§1.6) and is surfaced separately. The dash machinery in
    :mod:`arch_line_weights.apply` is exercised by the layer / explicit paths.
    """
    # "axon" has no native tier ladder — reuse elevation's no-cut figure-ground
    # weights (mirrors preset_rules.ladder_for_preset).
    weight_preset = "elevation" if preset == "axon" else preset
    role_order = _CUT_DRIVEN_ROLE_ORDER if rule_for_preset(weight_preset).cut_driven else _NO_CUT_ROLE_ORDER

    rgb_counts: list[tuple[tuple[int, int, int], int]] = []
    for ckey, count in report.stroke_colors.items():
        rgb = color_to_rgb255(ckey)
        if rgb is None:
            continue
        rgb_counts.append((rgb, count))

    weights: dict[tuple[int, int, int], float] = {}
    linetypes: dict[tuple[int, int, int], LineType] = {}
    if not rgb_counts:
        return weights, linetypes

    # Darkest first; among same luminance, more frequent leans toward light.
    rgb_counts.sort(key=lambda rc: (_luminance(rc[0]), -rc[1]))
    n_colors = len(rgb_counts)
    n_roles = len(role_order)

    role_weight = {
        role: weight_for_role(role, preset=weight_preset, scale=scale, for_print=for_print).weight_pt
        for role in role_order
    }

    for idx, (rgb, _count) in enumerate(rgb_counts):
        if n_colors == 1:
            role = role_order[0]  # single color → heaviest structural role
        else:
            bucket = round((idx / (n_colors - 1)) * (n_roles - 1))
            role = role_order[bucket]
        weights[rgb] = role_weight[role]
        linetypes[rgb] = LineType.CONTINUOUS
    return weights, linetypes


def explain_mapping(
    mapping: dict[tuple[int, int, int], float],
    report: InspectionReport,
) -> list[str]:
    """Pretty-print the mapping, sorted by tier then by stroke count."""
    rows: list[tuple[float, int, tuple[int, int, int]]] = []
    for rgb, w in mapping.items():
        ckey = f"RGB({rgb[0]},{rgb[1]},{rgb[2]})"
        count = report.stroke_colors.get(ckey, 0)
        rows.append((w, count, rgb))
    rows.sort(key=lambda r: (-r[0], -r[1]))
    out = []
    last_w = None
    for w, count, rgb in rows:
        if w != last_w:
            out.append(f"--- {w} pt ---")
            last_w = w
        out.append(f"  RGB({rgb[0]:>3},{rgb[1]:>3},{rgb[2]:>3})  {count:>7,} strokes")
    return out
