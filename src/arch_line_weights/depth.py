"""Depth-evidence parsing and line-weight grading helpers."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field

_Z_RE = re.compile(r"\b(?:z|depth)\s*[=:_-]\s*(-?\d+(?:\.\d+)?)\b", re.IGNORECASE)
_MIN_CONFIDENCE = 0.65


@dataclass(frozen=True)
class DepthSummary:
    source: str
    confidence: float
    explanation: str
    signals: dict[str, int | float | str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "confidence": round(float(self.confidence), 3),
            "explanation": self.explanation,
            "signals": dict(self.signals),
        }


@dataclass(frozen=True)
class DepthRank:
    source: str
    rank: int
    total: int
    confidence: float
    explanation: str


def _color_key(rgb: tuple[int, int, int]) -> str:
    return f"RGB({rgb[0]},{rgb[1]},{rgb[2]})"


def _normalized_layers(layer_names: Iterable[str] | None) -> list[str]:
    return [str(name) for name in (layer_names or []) if str(name).strip()]


def _z_values_from_layers(layer_names: Iterable[str] | None) -> list[float]:
    values: list[float] = []
    for layer in _normalized_layers(layer_names):
        for match in _Z_RE.finditer(layer):
            values.append(float(match.group(1)))
    return values


def _foreground_background_count(layer_names: Iterable[str] | None) -> int:
    count = 0
    for layer in _normalized_layers(layer_names):
        low = layer.lower()
        if any(token in low for token in ("foreground", "background", "occlusion", "overlap")):
            count += 1
    return count


def _entries(depth_by_color: dict | None) -> list[tuple[str, dict]]:
    if not depth_by_color:
        return []
    return [(str(key), value) for key, value in depth_by_color.items() if isinstance(value, dict)]


def _confident(entries: list[tuple[str, dict]], key: str) -> list[tuple[str, float, float]]:
    out: list[tuple[str, float, float]] = []
    for color, data in entries:
        if key not in data:
            continue
        try:
            value = float(data[key])
            confidence = float(data.get("confidence", 1.0))
        except (TypeError, ValueError):
            continue
        if confidence >= _MIN_CONFIDENCE:
            out.append((color, value, confidence))
    return out


def summarize_depth_evidence(
    *,
    pdf_metadata: dict | None = None,
    layer_names: Iterable[str] | None = None,
    depth_by_color: dict | None = None,
) -> DepthSummary:
    """Summarize whether depth grading has trustworthy Z or overlap evidence."""

    entries = _entries(depth_by_color)
    z_entries = _confident(entries, "z")
    if len(z_entries) >= 2:
        conf = min(conf for _color, _z, conf in z_entries)
        return DepthSummary(
            source="z",
            confidence=conf,
            explanation="using source Z/depth metadata from color-bound evidence",
            signals={"color_count": len(z_entries)},
        )

    overlap_entries = _confident(entries, "overlap_index")
    if len(overlap_entries) >= 2:
        conf = min(conf for _color, _overlap, conf in overlap_entries)
        return DepthSummary(
            source="overlap",
            confidence=conf,
            explanation="using confident overlap/occlusion ordering",
            signals={"color_count": len(overlap_entries)},
        )

    if entries:
        return DepthSummary(
            source="fallback",
            confidence=0.0,
            explanation="low-confidence depth evidence; using v1 role ladder",
            signals={"color_count": len(entries)},
        )

    z_values = _z_values_from_layers(layer_names)
    if len(z_values) >= 2 and max(z_values) != min(z_values):
        return DepthSummary(
            source="z",
            confidence=0.8,
            explanation="layer metadata includes multiple Z/depth values",
            signals={"layer_z_count": len(z_values), "z_min": min(z_values), "z_max": max(z_values)},
        )

    overlap_count = _foreground_background_count(layer_names)
    if overlap_count >= 2:
        return DepthSummary(
            source="overlap",
            confidence=0.66,
            explanation="layer names contain foreground/background overlap cues",
            signals={"layer_overlap_count": overlap_count},
        )

    metadata_text = " ".join(str(v) for v in (pdf_metadata or {}).values()).lower()
    if "foreground" in metadata_text and "background" in metadata_text:
        return DepthSummary(
            source="overlap",
            confidence=0.66,
            explanation="metadata contains foreground/background depth cues",
            signals={"metadata_overlap": 1},
        )

    return DepthSummary(
        source="fallback",
        confidence=0.0,
        explanation="no Z or confident overlap evidence; using v1 role ladder",
        signals={},
    )


def depth_ranks_for_colors(
    color_order: Iterable[tuple[int, int, int]],
    depth_by_color: dict | None,
) -> dict[tuple[int, int, int], DepthRank]:
    """Rank colors by trustworthy depth evidence.

    Lower Z is treated as nearer. Higher ``overlap_index`` is treated as nearer
    because it represents stronger foreground/occlusion evidence. When evidence
    is missing or low confidence, return an empty mapping so callers preserve
    the v1 role ladder exactly.
    """

    colors = list(color_order)
    entries = _entries(depth_by_color)
    by_key = {_color_key(rgb): rgb for rgb in colors}

    z_entries = [
        (by_key[color], value, conf) for color, value, conf in _confident(entries, "z") if color in by_key
    ]
    if len(z_entries) >= 2:
        ordered = sorted(z_entries, key=lambda item: (item[1], _color_key(item[0])))
        total = len(ordered)
        conf = min(item[2] for item in ordered)
        return {
            rgb: DepthRank(
                source="z",
                rank=rank,
                total=total,
                confidence=conf,
                explanation=f"z={z:g}; lower Z is nearer",
            )
            for rank, (rgb, z, _conf) in enumerate(ordered)
        }

    overlap_entries = [
        (by_key[color], value, conf)
        for color, value, conf in _confident(entries, "overlap_index")
        if color in by_key
    ]
    if len(overlap_entries) >= 2:
        ordered = sorted(overlap_entries, key=lambda item: (-item[1], _color_key(item[0])))
        total = len(ordered)
        conf = min(item[2] for item in ordered)
        return {
            rgb: DepthRank(
                source="overlap",
                rank=rank,
                total=total,
                confidence=conf,
                explanation=f"overlap_index={overlap:g}; higher overlap is nearer",
            )
            for rank, (rgb, overlap, _conf) in enumerate(ordered)
        }

    return {}


__all__ = ["DepthRank", "DepthSummary", "depth_ranks_for_colors", "summarize_depth_evidence"]
