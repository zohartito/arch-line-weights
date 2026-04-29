"""Decide which color belongs to which tier.

Phase 1 supports two strategies:
  * `from_user_mapping` — user provides {color_key: weight_pt}
  * `auto_by_luminance` — bucket colors into N tiers by relative luminance,
    most-frequent-and-lightest → texture, darkest → cut

Phase 3 will add smarter classification (saturation, hue family, frequency).
"""
from __future__ import annotations

from typing import Iterable

from .inspect import InspectionReport, color_to_rgb255
from .presets import Tier


def from_user_mapping(mapping_rgb_to_weight: dict[tuple[int, int, int], float]) -> dict[tuple[int, int, int], float]:
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
