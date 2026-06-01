"""Human-readable diagnostics for arch-lw JSON run reports."""

from __future__ import annotations

from typing import Any

PREVIEW_WARNING = (
    "PDF preview is not authoritative for AI-native PieceInfo outputs; "
    "review the Illustrator document or exported Illustrator smoke-check image."
)


def _short_name(layer: str) -> str:
    return layer.rsplit("::", 1)[-1]


def _reason_list(layer: dict[str, Any]) -> list[str]:
    review = layer.get("review") or {}
    reasons = review.get("reasons") or []
    return [str(reason) for reason in reasons]


def _layer_summary(layer: dict[str, Any]) -> dict[str, Any]:
    name = str(layer.get("layer", ""))
    return {
        "layer": name,
        "short_name": str(layer.get("short_name") or _short_name(name)),
        "status": str(layer.get("status", "unknown")),
        "action": str(layer.get("action", "unknown")),
        "strategy": str(layer.get("strategy", "unknown")),
        "confidence": float(layer.get("confidence", 0.0) or 0.0),
        "polygon_count": int(layer.get("polygon_count", 0) or 0),
        "reasons": _reason_list(layer),
    }


def summarize_report(report: dict[str, Any]) -> dict[str, Any]:
    """Summarize a durable run report into a designer-readable diagnosis."""
    layers = [_layer_summary(layer) for layer in report.get("layers", [])]
    inferred = [layer for layer in layers if layer["status"] == "inferred"]
    filled = [layer for layer in layers if layer["status"] == "filled"]
    low_confidence = [layer for layer in layers if layer["status"] == "low_confidence"]
    skipped = [layer for layer in layers if layer["status"] == "skipped"]
    failed = [layer for layer in layers if layer["status"] in {"failed", "missing_payload", "no-go", "no_go"}]
    review_layers = [
        layer
        for layer in layers
        if layer["status"] in {"low_confidence", "failed", "missing_payload", "no-go", "no_go"}
        or bool(layer["reasons"])
    ]

    if failed or low_confidence or review_layers:
        status = "needs_review"
        next_step = (
            "Open the Illustrator output and inspect the listed review layers before "
            "approving proof output; repair or re-run failed and low-confidence layers."
        )
    else:
        status = "clean"
        next_step = (
            "No review-only or failed layers were reported; still perform an Illustrator "
            "visual smoke check before external proof claims."
        )

    return {
        "status": status,
        "counts": {
            "filled": len(filled),
            "inferred": len(inferred),
            "low_confidence": len(low_confidence),
            "skipped": len(skipped),
            "failed": len(failed),
            "needs_review": len(review_layers),
        },
        "filled_layers": filled,
        "inferred_layers": inferred,
        "review_layers": review_layers,
        "failed_layers": failed,
        "skipped_layers": skipped,
        "next_step": next_step,
        "preview_warning": PREVIEW_WARNING,
    }


def format_diagnosis(summary: dict[str, Any]) -> str:
    """Format :func:`summarize_report` for terminal use."""
    counts = summary["counts"]
    lines = [
        f"Status: {summary['status']}",
        f"Filled layers: {counts['filled']}",
        f"Inferred closures: {counts['inferred']}",
        f"Low-confidence/review layers: {counts['needs_review']}",
        f"Failed/missing layers: {counts['failed']}",
        "",
        "Review Layers:",
    ]

    review_layers = summary.get("review_layers") or []
    if review_layers:
        for layer in review_layers:
            reasons = "; ".join(layer["reasons"]) if layer["reasons"] else layer["status"]
            lines.append(
                f"- {layer['short_name']}: {layer['status']} via {layer['strategy']} "
                f"(confidence {layer['confidence']:.2f}) - {reasons}"
            )
    else:
        lines.append("- none")

    failed_layers = summary.get("failed_layers") or []
    if failed_layers:
        lines.extend(["", "Failed/Missing Layers:"])
        for layer in failed_layers:
            reasons = "; ".join(layer["reasons"]) if layer["reasons"] else layer["status"]
            lines.append(f"- {layer['short_name']}: {reasons}")

    lines.extend(
        [
            "",
            f"Next step: {summary['next_step']}",
            f"Preview warning: {summary['preview_warning']}",
        ]
    )
    return "\n".join(lines)


__all__ = [
    "PREVIEW_WARNING",
    "format_diagnosis",
    "summarize_report",
]
