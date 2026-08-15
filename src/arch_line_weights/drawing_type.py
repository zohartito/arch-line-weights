"""Infer the architectural drawing type from metadata and layer names."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

_PRESET_KIND = {
    "section": "section",
    "studio": "section",
    "usc": "section",  # Deprecated alias for "studio".
    "plan": "plan",
    "elevation": "elevation",
    "axon": "axon",
    "paraline": "axon",
    "detail": "detail",
}

_KEYWORDS: dict[str, tuple[str, ...]] = {
    "section": (
        "section",
        "cut section",
        "building section",
        "clippingplane",
        "clipping plane",
        "mcut",
        "cutline",
        "cut line",
    ),
    "plan": (
        "floor plan",
        "roof plan",
        "site plan",
        "plan",
        "room",
        "door",
        "furniture",
        "a-wall",
        "wall-full",
        "level ",
    ),
    "elevation": (
        "elevation",
        "facade",
        "facade",
        "front view",
        "side view",
        "north elev",
        "south elev",
        "east elev",
        "west elev",
    ),
    "axon": (
        "axon",
        "axonometric",
        "isometric",
        "isometry",
        "paraline",
        "oblique",
        "three-dimensional",
    ),
}


@dataclass(frozen=True)
class DrawingTypeGuess:
    kind: str
    confidence: float
    explanation: str
    signals: dict[str, int | float | str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "confidence": round(float(self.confidence), 3),
            "explanation": self.explanation,
            "signals": dict(self.signals),
        }


def _metadata_text(pdf_metadata: dict | None) -> str:
    if not pdf_metadata:
        return ""
    parts: list[str] = []
    for key in ("/Title", "title", "/Subject", "subject", "/Creator", "creator", "/Producer", "producer"):
        val = pdf_metadata.get(key)
        if val:
            parts.append(str(val))
    return " ".join(parts).lower()


def _normalized_lines(items: Iterable[str] | None) -> list[str]:
    return [str(item).lower() for item in (items or []) if str(item).strip()]


def _score_text(text: str, layer_text: str) -> dict[str, float]:
    scores = {kind: 0.0 for kind in _KEYWORDS}
    haystacks = ((text, 1.6), (layer_text, 1.0))
    for kind, keywords in _KEYWORDS.items():
        for haystack, weight in haystacks:
            if not haystack:
                continue
            for keyword in keywords:
                if keyword in haystack:
                    scores[kind] += weight
    return scores


def _clamp_conf(score: float, runner_up: float) -> float:
    if score <= 0:
        return 0.2
    # Confidence rises with both absolute evidence and distance from the next
    # best explanation. It is intentionally capped below explicit overrides.
    margin = max(score - runner_up, 0.0)
    conf = 0.45 + min(score * 0.11, 0.35) + min(margin * 0.08, 0.15)
    return round(min(conf, 0.95), 3)


def classify_drawing_type(
    *,
    pdf_metadata: dict | None = None,
    layer_names: Iterable[str] | None = None,
    width_pt: float | None = None,
    height_pt: float | None = None,
    explicit_preset: str | None = None,
) -> DrawingTypeGuess:
    """Return a drawing-type guess with confidence and a short reason.

    The classifier is deliberately conservative: obvious metadata/layer terms
    win, page orientation only nudges ambiguous cases, and an explicit preset
    always wins so users can override the guess at the CLI.
    """

    if explicit_preset:
        preset = explicit_preset.strip().lower()
        kind = _PRESET_KIND.get(preset, preset)
        return DrawingTypeGuess(
            kind=kind,
            confidence=1.0,
            explanation=f"explicit --preset {preset} override selected {kind}",
            signals={"explicit_preset": preset},
        )

    metadata = _metadata_text(pdf_metadata)
    layers = _normalized_lines(layer_names)
    layer_text = " ".join(layers)
    scores = _score_text(metadata, layer_text)

    clipping_layers = sum(1 for layer in layers if "clippingplane" in layer or "clipping plane" in layer)
    if clipping_layers:
        scores["section"] += 4.0 + clipping_layers

    axon_layers = sum(1 for layer in layers if "axon" in layer or "paraline" in layer or "isometric" in layer)
    if axon_layers and not clipping_layers:
        scores["axon"] += 2.0 + axon_layers

    if width_pt and height_pt:
        aspect = width_pt / height_pt if height_pt else 1.0
        if aspect > 1.25:
            scores["plan"] += 0.35
        elif aspect < 0.8:
            scores["section"] += 0.2

    ordered = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    kind, score = ordered[0]
    runner_up = ordered[1][1] if len(ordered) > 1 else 0.0

    if score <= 0:
        return DrawingTypeGuess(
            kind="section",
            confidence=0.2,
            explanation="no drawing-type metadata or layer-name signal; defaulting to section",
            signals={"score": 0.0, "runner_up": 0.0},
        )

    confidence = _clamp_conf(score, runner_up)
    signal_bits = []
    if clipping_layers:
        signal_bits.append(f"{clipping_layers} clipping plane layer(s)")
    if metadata and any(keyword in metadata for keyword in _KEYWORDS[kind]):
        signal_bits.append("metadata keyword")
    layer_hits = [keyword for keyword in _KEYWORDS[kind] if keyword in layer_text]
    if layer_hits:
        signal_bits.append(f"layer keyword: {layer_hits[0]}")
    if not signal_bits:
        signal_bits.append("weak page/layer context")
    explanation = f"{kind} inferred from " + ", ".join(signal_bits)

    return DrawingTypeGuess(
        kind=kind,
        confidence=confidence,
        explanation=explanation,
        signals={
            "score": round(score, 3),
            "runner_up": round(runner_up, 3),
            "layer_count": len(layers),
            "clipping_layer_count": clipping_layers,
        },
    )


__all__ = ["DrawingTypeGuess", "classify_drawing_type"]
