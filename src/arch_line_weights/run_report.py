"""Durable JSON run reports for arch-lw apply/poche pipelines."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from shapely.geometry import Polygon

from .poche import FillResult, PocheReport, should_inject_fill
from .poche_saas import PocheSaasResult

_INFERRED_STRATEGIES = {
    "auto_bridge",
    "structural_open_loop",
    "structural_parallel_edges",
    "structural_visible_completion",
    "llm_topology",
}
_REVIEW_STRATEGIES = {"alpha_shape", "concave_hull", "bbox", "llm_topology"}


def _short_name(layer: str) -> str:
    return layer.rsplit("::", 1)[-1]


def _empty_layers_by_status() -> dict[str, list[str]]:
    return {
        "filled": [],
        "inferred": [],
        "skipped": [],
        "low_confidence": [],
        "failed": [],
    }


def _candidate_dict(candidate: object) -> dict[str, Any]:
    polygon = getattr(candidate, "polygon", None)
    bounds: list[float] = []
    area = 0.0
    if isinstance(polygon, Polygon):
        bounds = [round(float(v), 4) for v in polygon.bounds]
        area = round(float(polygon.area), 4)
    return {
        "target_layer": getattr(candidate, "target_layer", ""),
        "component_key": getattr(candidate, "component_key", ""),
        "source_role": getattr(candidate, "source_role", ""),
        "provenance": getattr(candidate, "provenance", ""),
        "accepted": bool(getattr(candidate, "accepted", False)),
        "confidence": round(float(getattr(candidate, "confidence", 0.0)), 4),
        "reason": getattr(candidate, "reason", ""),
        "area": area,
        "cut_shared_length": round(float(getattr(candidate, "cut_shared_length", 0.0)), 4),
        "bounds": bounds,
    }


def _meaningful_rejection(candidate: object) -> bool:
    if bool(getattr(candidate, "accepted", False)):
        return False
    reason = str(getattr(candidate, "reason", "")).lower()
    return "duplicates existing" not in reason


def _layer_status(
    result: FillResult,
    *,
    injected_count: int,
    missing_payload: bool,
) -> tuple[str, str]:
    if missing_payload:
        return "missing_payload", "missing_payload"
    if result.strategy == "skipped":
        return "skipped", "skipped_by_override"
    if result.strategy == "failed" or result.polygon_count <= 0:
        return "failed", "failed"
    if injected_count <= 0 or not should_inject_fill(result):
        return "low_confidence", "diagnostic_only"
    if result.strategy in _INFERRED_STRATEGIES:
        return "inferred", "injected"
    return "filled", "injected"


def build_apply_saas_report(
    *,
    input_path: str | Path,
    output_path: str | Path,
    source: Mapping[str, Any],
    poche_report: PocheReport | None,
    poche_result: PocheSaasResult | None,
) -> dict[str, Any]:
    """Build a JSON-serializable report for one ``apply-saas`` run."""
    poche_report = poche_report or PocheReport()
    poche_result = poche_result or PocheSaasResult()

    candidates_by_layer: dict[str, list[object]] = {}
    for candidate in poche_report.completion_candidates:
        target = str(getattr(candidate, "target_layer", ""))
        candidates_by_layer.setdefault(target, []).append(candidate)

    missing_layers = set(poche_result.layers_missing)
    layers: list[dict[str, Any]] = []
    diagnostic_polygons = 0
    for fill in poche_report.fills:
        injected_count = len(poche_report.polygons.get(fill.layer, []))
        missing_payload = fill.layer in missing_layers
        status, action = _layer_status(
            fill,
            injected_count=injected_count,
            missing_payload=missing_payload,
        )
        if action == "diagnostic_only":
            diagnostic_polygons += fill.polygon_count

        layer_candidates = candidates_by_layer.get(fill.layer, [])
        review_reasons: list[str] = []
        if status in {"low_confidence", "failed", "missing_payload"}:
            review_reasons.append(status.replace("_", " "))
        if fill.strategy in _REVIEW_STRATEGIES:
            review_reasons.append(f"strategy {fill.strategy} is review-only")
        if 0 < fill.confidence < 0.85:
            review_reasons.append(f"confidence {fill.confidence:.2f} below 0.85")
        if missing_payload:
            review_reasons.append("payload layer could not be located for injection")
        if any(_meaningful_rejection(candidate) for candidate in layer_candidates):
            review_reasons.append("one or more Make2D completion candidates were rejected")

        layers.append(
            {
                "layer": fill.layer,
                "short_name": _short_name(fill.layer),
                "component_key": _short_name(fill.layer).upper(),
                "status": status,
                "action": action,
                "strategy": fill.strategy,
                "confidence": round(float(fill.confidence), 4),
                "polygon_count": fill.polygon_count,
                "injected_polygon_count": injected_count,
                "segment_count": fill.segment_count,
                "tolerance": fill.tolerance,
                "bridge_strategy_name": fill.bridge_strategy_name,
                "evidence": {
                    "used_cut_layer": True,
                    "used_poche_close_layer": False,
                    "used_structural_helpers": bool(layer_candidates),
                    "used_visible_completion": fill.strategy == "structural_visible_completion",
                },
                "review": {
                    "needs_review": bool(review_reasons),
                    "reasons": sorted(set(review_reasons)),
                },
            }
        )

    summary = {
        "cut_layers_considered": len(poche_report.fills),
        "layers_filled": sum(1 for layer in layers if layer["status"] == "filled"),
        "layers_inferred": sum(1 for layer in layers if layer["status"] == "inferred"),
        "layers_skipped": sum(1 for layer in layers if layer["status"] == "skipped"),
        "layers_low_confidence": sum(1 for layer in layers if layer["status"] == "low_confidence"),
        "layers_failed": sum(1 for layer in layers if layer["status"] == "failed"),
        "layers_needs_review": sum(1 for layer in layers if layer["review"]["needs_review"]),
        "polygons_filled": poche_result.polygons_injected,
        "polygons_diagnostic_only": diagnostic_polygons,
        "bytes_injected": poche_result.bytes_injected,
    }

    return {
        "schema_version": 1,
        "source": {
            "input": str(input_path),
            "output": str(output_path),
            **dict(source),
        },
        "summary": summary,
        "layers": layers,
        "completion_candidates": [
            _candidate_dict(candidate) for candidate in poche_report.completion_candidates
        ],
        "missing_payload_layers": poche_result.layers_missing,
    }


def _poche_summary_status(summary: Mapping[str, Any], error: str | None) -> tuple[str, list[str], str]:
    if error:
        return "failed", [error], "Fix the reported command failure, then rerun arch-lw poche."

    why: list[str] = []
    if summary["cut_layers_considered"] == 0:
        why.append("No cut layers were considered")
    if summary["polygons_injected"] == 0:
        why.append("No reliable poché polygons were produced")
    if summary["layers_failed"]:
        why.append(f"{summary['layers_failed']} cut layer(s) failed to polygonize")

    if why:
        return "no_go", why, "Generate/review cut geometry, fix Make2D layer closure, then rerun arch-lw poche."

    if summary["layers_low_confidence"] or summary["layers_skipped"]:
        if summary["layers_low_confidence"]:
            why.append(
                f"{summary['layers_low_confidence']} low-confidence layer(s) were diagnostic-only."
            )
        if summary["layers_skipped"]:
            why.append(f"{summary['layers_skipped']} layer(s) were skipped.")
        return "needs_review", why, "Review low-confidence or skipped cut layers before using the output."

    return "passed", [], "No action needed."


def build_poche_report(
    *,
    input_path: str | Path,
    output_path: str | Path,
    source: Mapping[str, Any],
    poche_report: PocheReport | None,
    error: str | None = None,
) -> dict[str, Any]:
    """Build a stable JSON report for the standalone ``arch-lw poche`` command."""
    poche_report = poche_report or PocheReport()
    layers: list[dict[str, Any]] = []
    layers_by_status = _empty_layers_by_status()
    diagnostic_polygons = 0

    for fill in poche_report.fills:
        injected_count = len(poche_report.polygons.get(fill.layer, []))
        status, action = _layer_status(
            fill,
            injected_count=injected_count,
            missing_payload=False,
        )
        if action == "diagnostic_only":
            diagnostic_polygons += fill.polygon_count
        layers_by_status.setdefault(status, []).append(fill.layer)

        review_reasons: list[str] = []
        if status == "skipped":
            review_reasons.append("skipped by override")
        if status in {"low_confidence", "failed"}:
            review_reasons.append(status.replace("_", " "))
        if fill.strategy in _REVIEW_STRATEGIES:
            review_reasons.append(f"strategy {fill.strategy} is review-only")
        if 0 < fill.confidence < 0.85:
            review_reasons.append(f"confidence {fill.confidence:.2f} below 0.85")

        layers.append(
            {
                "layer": fill.layer,
                "short_name": _short_name(fill.layer),
                "component_key": _short_name(fill.layer).upper(),
                "status": status,
                "action": action,
                "strategy": fill.strategy,
                "confidence": round(float(fill.confidence), 4),
                "polygon_count": fill.polygon_count,
                "injected_polygon_count": injected_count,
                "segment_count": fill.segment_count,
                "tolerance": fill.tolerance,
                "bridge_strategy_name": fill.bridge_strategy_name,
                "review": {
                    "needs_review": bool(review_reasons),
                    "reasons": sorted(set(review_reasons)),
                },
            }
        )

    summary: dict[str, Any] = {
        "cut_layers_considered": len(poche_report.fills),
        "layers_filled": sum(1 for layer in layers if layer["status"] == "filled"),
        "layers_inferred": sum(1 for layer in layers if layer["status"] == "inferred"),
        "layers_skipped": sum(1 for layer in layers if layer["status"] == "skipped"),
        "layers_low_confidence": sum(1 for layer in layers if layer["status"] == "low_confidence"),
        "layers_failed": sum(1 for layer in layers if layer["status"] == "failed"),
        "layers_needs_review": sum(1 for layer in layers if layer["review"]["needs_review"]),
        "polygons_total": poche_report.total_polygons,
        "polygons_injected": poche_report.injected_polygons,
        "polygons_diagnostic_only": diagnostic_polygons,
    }
    status, why, next_action = _poche_summary_status(summary, error)
    summary.update({"status": status, "why": why, "next_action": next_action})

    return {
        "schema_version": 1,
        "source": {
            "input": str(input_path),
            "output": str(output_path),
            "command": "poche",
            "stage": "poche",
            **dict(source),
        },
        "summary": summary,
        "layers": layers,
        "layers_by_status": layers_by_status,
        "completion_candidates": [
            _candidate_dict(candidate) for candidate in poche_report.completion_candidates
        ],
    }
