"""Durable JSON run reports for arch-lw apply/poche pipelines."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from itertools import pairwise
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
_FOUNDATION_CONCRETE_TOKENS = (
    "TEC_CONCRETE_BASE",
    "CONCRETE_BASE",
    "TEC_FOUNDATION",
    "FOUNDATION",
    "FOOTING",
)
_VISUAL_ACCEPTANCE_COMPONENTS = _FOUNDATION_CONCRETE_TOKENS


def _short_name(layer: str) -> str:
    return layer.rsplit("::", 1)[-1]


def _is_foundation_concrete_layer(layer: str) -> bool:
    component = _short_name(layer).upper()
    return any(token in component for token in _FOUNDATION_CONCRETE_TOKENS)


def _known_limitation_dict(item: Mapping[str, Any]) -> dict[str, Any]:
    evidence = {
        "kind": "visual_roi_black_ratio",
        "evidence_screenshot": item.get("evidence_screenshot"),
        "roi": item.get("roi"),
        "expected_min_black_ratio": item.get("expected_min_black_ratio"),
        "current_black_ratio_observed": item.get("current_black_ratio_observed"),
    }
    evidence = {key: value for key, value in evidence.items() if value is not None}
    limitation = {
        "id": str(item.get("id") or "known_visual_proof_miss"),
        "code": str(item.get("code") or "known_visual_proof_miss"),
        "status": str(item.get("status") or "no_go"),
        "scope": str(item.get("scope") or "foundation_concrete"),
        "reason": str(item.get("reason") or "Known visual proof limitation."),
        "next_action": str(
            item.get("next_action")
            or "Fix the known proof limitation and recapture proof before launch."
        ),
        "evidence": evidence,
    }
    if item.get("blocks_issue") is not None:
        limitation["blocks_issue"] = item["blocks_issue"]
    return limitation


def _known_limitations(items: list[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    return [_known_limitation_dict(item) for item in items or []]


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


def _requires_visual_acceptance(result: FillResult) -> bool:
    if result.strategy not in _INFERRED_STRATEGIES:
        return False
    upper = _short_name(result.layer).upper()
    return any(component in upper for component in _VISUAL_ACCEPTANCE_COMPONENTS)


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


def _foundation_concrete_limitation(
    layer: str,
    *,
    status: str,
    action: str,
    redact_layer_name: bool,
) -> dict[str, Any] | None:
    if not _is_foundation_concrete_layer(layer):
        return None
    if status in {"filled", "inferred"} and action == "injected":
        return None

    limitation: dict[str, Any] = {
        "id": "foundation_concrete_partial_coverage",
        "code": "foundation_concrete_partial_coverage",
        "status": "no_go",
        "scope": "foundation_concrete",
        "reason": "Foundation/concrete poché coverage is incomplete or diagnostic-only.",
        "next_action": "Review cut geometry, fix Make2D closure, and recapture proof before launch.",
        "evidence": {
            "kind": "poche_layer_status",
            "layer_status": status,
            "layer_action": action,
        },
    }
    if redact_layer_name:
        limitation["layer_id"] = _stable_layer_id(layer)
    else:
        limitation["layer"] = layer
        limitation["component_key"] = _short_name(layer).upper()
    return limitation


def _no_go_limitations(limitations: list[Mapping[str, Any]]) -> int:
    return sum(1 for limitation in limitations if limitation.get("status") == "no_go")


def build_apply_saas_report(
    *,
    input_path: str | Path,
    output_path: str | Path,
    source: Mapping[str, Any],
    poche_report: PocheReport | None,
    poche_result: PocheSaasResult | None,
    input_format: Mapping[str, Any] | None = None,
    command: str | None = None,
    visual_artifacts: Mapping[str, Any] | None = None,
    known_limitations: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a JSON-serializable report for one ``apply-saas`` run."""
    poche_report = poche_report or PocheReport()
    poche_result = poche_result or PocheSaasResult()
    structural_helper_counts = getattr(poche_report, "structural_helper_counts", {})

    candidates_by_layer: dict[str, list[object]] = {}
    for candidate in poche_report.completion_candidates:
        target = str(getattr(candidate, "target_layer", ""))
        candidates_by_layer.setdefault(target, []).append(candidate)

    missing_layers = set(poche_result.layers_missing)
    layers: list[dict[str, Any]] = []
    limitations: list[dict[str, Any]] = []
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
        structural_helper_count = int(structural_helper_counts.get(fill.layer, 0) or 0)
        review_reasons: list[str] = []
        if status in {"low_confidence", "failed", "missing_payload"}:
            review_reasons.append(status.replace("_", " "))
        if fill.strategy in _REVIEW_STRATEGIES:
            review_reasons.append(f"strategy {fill.strategy} is review-only")
        if 0 < fill.confidence < 0.85:
            review_reasons.append(f"confidence {fill.confidence:.2f} below 0.85")
        if _requires_visual_acceptance(fill):
            review_reasons.append(
                "inferred concrete/foundation fill requires W5/W7 visual acceptance"
            )
        if missing_payload:
            review_reasons.append("payload layer could not be located for injection")
        if any(_meaningful_rejection(candidate) for candidate in layer_candidates):
            review_reasons.append("one or more Make2D completion candidates were rejected")
        limitation = _foundation_concrete_limitation(
            fill.layer,
            status=status,
            action=action,
            redact_layer_name=False,
        )
        if limitation is not None:
            limitations.append(limitation)
            review_reasons.append("foundation/concrete coverage is launch-blocking")
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
                    "used_structural_helpers": bool(layer_candidates)
                    or bool(structural_helper_count),
                    "structural_helper_count": structural_helper_count,
                    "used_visible_completion": fill.strategy == "structural_visible_completion",
                },
                "review": {
                    "needs_review": bool(review_reasons),
                    "visual_acceptance_required": _requires_visual_acceptance(fill),
                    "reasons": sorted(set(review_reasons)),
                },
            }
        )

    limitations.extend(_known_limitations(known_limitations))
    summary = {
        "cut_layers_considered": len(poche_report.fills),
        "layers_filled": sum(1 for layer in layers if layer["status"] == "filled"),
        "layers_inferred": sum(1 for layer in layers if layer["status"] == "inferred"),
        "layers_skipped": sum(1 for layer in layers if layer["status"] == "skipped"),
        "layers_low_confidence": sum(1 for layer in layers if layer["status"] == "low_confidence"),
        "layers_failed": sum(1 for layer in layers if layer["status"] == "failed"),
        "layers_needs_review": sum(1 for layer in layers if layer["review"]["needs_review"]),
        "visual_acceptance_gated_layers": sum(
            1 for layer in layers if layer["review"]["visual_acceptance_required"]
        ),
        "polygons_filled": poche_result.polygons_injected,
        "polygons_diagnostic_only": diagnostic_polygons,
        "bytes_injected": poche_result.bytes_injected,
        "limitations_count": len(limitations),
        "no_go_limitations": _no_go_limitations(limitations),
    }

    source_payload: dict[str, Any] = {
        "input": str(input_path),
        "output": str(output_path),
        **dict(source),
    }
    if input_format is not None:
        source_payload["input_format"] = dict(input_format)
    if command is not None:
        source_payload["command"] = command

    report = {
        "schema_version": 2,
        "source": {
            **source_payload,
        },
        "summary": summary,
        "layers": layers,
        "completion_candidates": [
            _candidate_dict(candidate) for candidate in poche_report.completion_candidates
        ],
        "missing_payload_layers": poche_result.layers_missing,
        "limitations": limitations,
    }
    if visual_artifacts is not None:
        report["visual_artifacts"] = dict(visual_artifacts)
    return report


def build_layout_jsx_report(
    *,
    input_path: str | Path,
    output_path: str | Path,
    source: Mapping[str, Any],
    status: str,
    artboard_width_pt: float,
    artboard_height_pt: float,
    margin_pt: float,
    selected_items: int | None = None,
    scale: float | None = None,
    translation: Mapping[str, float] | None = None,
    original_visible_bounds: list[float] | None = None,
    final_visible_bounds: list[float] | None = None,
    why: list[str] | None = None,
) -> dict[str, Any]:
    """Build a JSON-serializable report for one ``layout-jsx`` run."""
    reasons = why or []
    if status == "passed":
        next_action = "Continue to hierarchy, poché, or proof recapture."
    elif status == "dry_run":
        next_action = "Inspect the generated JSX/report contract, then rerun without --dry-run."
    elif status == "needs_review":
        next_action = "Review the converted-document match and output before proof recapture."
    elif status == "no_go":
        next_action = "Fix the layout input/artwork problem before proof recapture."
    else:
        next_action = "Fix the reported layout-jsx failure, then rerun."

    return {
        "schema_version": 1,
        "source": {
            "input": str(input_path),
            "output": str(output_path),
            "command": "layout-jsx",
            "stage": "layout",
            **dict(source),
        },
        "summary": {
            "status": status,
            "why": reasons,
            "next_action": next_action,
        },
        "layout": {
            "artboard": {
                "width_pt": round(float(artboard_width_pt), 4),
                "height_pt": round(float(artboard_height_pt), 4),
            },
            "margin_pt": round(float(margin_pt), 4),
            "selected_items": selected_items,
            "scale": None if scale is None else round(float(scale), 6),
            "translation": dict(translation or {}),
            "original_visible_bounds": original_visible_bounds,
            "final_visible_bounds": final_visible_bounds,
        },
    }


def _poche_summary_status(summary: Mapping[str, Any], error: str | None) -> tuple[str, list[str], str]:
    if error:
        return "failed", [error], "Fix the reported command failure, then rerun arch-lw poche."

    why: list[str] = []
    if summary.get("no_go_limitations", 0):
        why.append(
            f"{summary['no_go_limitations']} launch-blocking poché coverage limitation(s) recorded"
        )
    if summary["cut_layers_considered"] == 0:
        why.append("No cut layers were considered")
    if summary["polygons_injected"] == 0:
        why.append("No reliable poché polygons were produced")
    if summary["layers_failed"]:
        why.append(f"{summary['layers_failed']} cut layer(s) failed to polygonize")

    if why:
        if summary.get("no_go_limitations", 0):
            return (
                "no_go",
                why,
                "Resolve no-go poché coverage limitations and recapture proof before launch.",
            )
        return (
            "no_go",
            why,
            "Generate/review cut geometry, fix Make2D layer closure, then rerun arch-lw poche.",
        )

    if summary["layers_low_confidence"] or summary["layers_skipped"]:
        if summary["layers_low_confidence"]:
            why.append(
                f"{summary['layers_low_confidence']} low-confidence layer(s) were diagnostic-only."
            )
        if summary["layers_skipped"]:
            why.append(f"{summary['layers_skipped']} layer(s) were skipped.")
        return "needs_review", why, "Review low-confidence or skipped cut layers before using the output."

    if summary.get("layers_needs_review", 0):
        why.append(f"{summary['layers_needs_review']} poché layer(s) require review.")
        return (
            "needs_review",
            why,
            "Review gated poché layers before using the output as proof.",
        )

    return "passed", [], "No action needed."


def build_poche_report(
    *,
    input_path: str | Path,
    output_path: str | Path,
    source: Mapping[str, Any],
    poche_report: PocheReport | None,
    input_format: Mapping[str, Any] | None = None,
    command: str | None = None,
    visual_artifacts: Mapping[str, Any] | None = None,
    error: str | None = None,
    known_limitations: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a stable JSON report for the standalone ``arch-lw poche`` command."""
    poche_report = poche_report or PocheReport()
    structural_helper_counts = getattr(poche_report, "structural_helper_counts", {})
    layers: list[dict[str, Any]] = []
    layers_by_status = _empty_layers_by_status()
    limitations: list[dict[str, Any]] = []
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

        structural_helper_count = int(structural_helper_counts.get(fill.layer, 0) or 0)
        review_reasons: list[str] = []
        if status == "skipped":
            review_reasons.append("skipped by override")
        if status in {"low_confidence", "failed"}:
            review_reasons.append(status.replace("_", " "))
        if fill.strategy in _REVIEW_STRATEGIES:
            review_reasons.append(f"strategy {fill.strategy} is review-only")
        if 0 < fill.confidence < 0.85:
            review_reasons.append(f"confidence {fill.confidence:.2f} below 0.85")
        if _requires_visual_acceptance(fill):
            review_reasons.append(
                "inferred concrete/foundation fill requires W5/W7 visual acceptance"
            )
        limitation = _foundation_concrete_limitation(
            fill.layer,
            status=status,
            action=action,
            redact_layer_name=False,
        )
        if limitation is not None:
            limitations.append(limitation)
            review_reasons.append("foundation/concrete coverage is launch-blocking")

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
                    "used_structural_helpers": bool(structural_helper_count),
                    "structural_helper_count": structural_helper_count,
                    "used_visible_completion": False,
                },
                "review": {
                    "needs_review": bool(review_reasons),
                    "visual_acceptance_required": _requires_visual_acceptance(fill),
                    "reasons": sorted(set(review_reasons)),
                },
            }
        )

    limitations.extend(_known_limitations(known_limitations))
    summary: dict[str, Any] = {
        "cut_layers_considered": len(poche_report.fills),
        "layers_filled": sum(1 for layer in layers if layer["status"] == "filled"),
        "layers_inferred": sum(1 for layer in layers if layer["status"] == "inferred"),
        "layers_skipped": sum(1 for layer in layers if layer["status"] == "skipped"),
        "layers_low_confidence": sum(1 for layer in layers if layer["status"] == "low_confidence"),
        "layers_failed": sum(1 for layer in layers if layer["status"] == "failed"),
        "layers_needs_review": sum(1 for layer in layers if layer["review"]["needs_review"]),
        "visual_acceptance_gated_layers": sum(
            1 for layer in layers if layer["review"]["visual_acceptance_required"]
        ),
        "polygons_filled": sum(len(polys) for polys in poche_report.polygons.values()),
        "polygons_total": poche_report.total_polygons,
        "polygons_injected": poche_report.injected_polygons,
        "polygons_diagnostic_only": diagnostic_polygons,
        "limitations_count": len(limitations),
        "no_go_limitations": _no_go_limitations(limitations),
    }
    status, why, next_action = _poche_summary_status(summary, error)
    summary.update({"status": status, "why": why, "next_action": next_action})

    source_payload: dict[str, Any] = {
        "input": str(input_path),
        "output": str(output_path),
        "command": command or "poche",
        "stage": "poche",
        **dict(source),
    }
    if input_format is not None:
        source_payload["input_format"] = dict(input_format)

    report: dict[str, Any] = {
        "schema_version": 2,
        "source": source_payload,
        "summary": summary,
        "layers": layers,
        "layers_by_status": layers_by_status,
        "completion_candidates": [
            _candidate_dict(candidate) for candidate in poche_report.completion_candidates
        ],
        "limitations": limitations,
    }
    if visual_artifacts is not None:
        report["visual_artifacts"] = dict(visual_artifacts)
    return report


def _stable_layer_id(layer: str) -> str:
    return f"layer_{hashlib.sha256(layer.encode('utf-8')).hexdigest()[:12]}"


def _points(paths: list[list[list[float]]]):
    for path in paths:
        for point in path:
            if len(point) >= 2:
                yield float(point[0]), float(point[1])


def _bbox(paths: list[list[list[float]]]) -> list[float] | None:
    pts = list(_points(paths))
    if not pts:
        return None
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return [round(min(xs), 4), round(min(ys), 4), round(max(xs), 4), round(max(ys), 4)]


def _bbox_area(bounds: list[float] | None) -> float:
    if bounds is None:
        return 0.0
    return round(max(0.0, bounds[2] - bounds[0]) * max(0.0, bounds[3] - bounds[1]), 4)


def _path_segment_count(paths: list[list[list[float]]]) -> int:
    return sum(max(0, len(path) - 1) for path in paths)


def _polygon_area(coords: list[list[float]]) -> float:
    if len(coords) < 3:
        return 0.0
    area = 0.0
    closed = coords if coords[0] == coords[-1] else [*coords, coords[0]]
    for a, b in pairwise(closed):
        area += float(a[0]) * float(b[1]) - float(b[0]) * float(a[1])
    return round(abs(area) / 2.0, 4)


def _geometry_next_action(status: str, ambiguous_regions: list[dict[str, Any]]) -> str:
    if status in {"filled", "inferred"} and not ambiguous_regions:
        return "No action needed."
    if status == "skipped":
        return "Review the skip override before relying on this layer."
    if status == "failed":
        return "Review Make2D source curves and close or simplify this cut layer."
    return "Review Make2D source curves for low-confidence or ambiguous cut regions."


def _poche_geometry_summary_status(summary: Mapping[str, Any]) -> tuple[str, list[str], str]:
    why: list[str] = []
    if summary.get("no_go_limitations", 0):
        why.append(
            f"{summary['no_go_limitations']} launch-blocking poché coverage limitation(s) recorded"
        )
        return (
            "no_go",
            why,
            "Resolve no-go poché coverage limitations and recapture proof before launch.",
        )
    if summary.get("ambiguous_regions_total", 0):
        why.append(f"{summary['ambiguous_regions_total']} ambiguous cut geometry region(s) recorded")
        return (
            "needs_review",
            why,
            "Review ambiguous cut geometry before relying on the poché output.",
        )
    return "passed", [], "No action needed."


def build_poche_geometry_report(
    *,
    source: Mapping[str, Any],
    paths_by_layer: Mapping[str, list[list[list[float]]]],
    poche_report: PocheReport | None,
    known_limitations: list[Mapping[str, Any]] | None = None,
    redact_layer_names: bool = True,
) -> dict[str, Any]:
    """Build a redacted, stable summary of cut geometry used by ``arch-lw poche``."""
    poche_report = poche_report or PocheReport()
    fills_by_layer = {fill.layer: fill for fill in poche_report.fills}
    candidates_by_layer: dict[str, list[object]] = {}
    for candidate in poche_report.completion_candidates:
        target = str(getattr(candidate, "target_layer", ""))
        candidates_by_layer.setdefault(target, []).append(candidate)

    layers: list[dict[str, Any]] = []
    limitations: list[dict[str, Any]] = []
    for layer, paths in paths_by_layer.items():
        if layer == "__POCHE_CLOSE__":
            continue
        fill = fills_by_layer.get(layer)
        injected_polygons = poche_report.polygons.get(layer, [])
        if fill is None:
            status = "failed"
            action = "missing_polygonize_result"
            strategy = "failed"
            confidence = 0.0
            polygon_count = 0
            tolerance = None
            bridge_strategy_name = None
        else:
            status, action = _layer_status(
                fill,
                injected_count=len(injected_polygons),
                missing_payload=False,
            )
            strategy = fill.strategy
            confidence = round(float(fill.confidence), 4)
            polygon_count = fill.polygon_count
            tolerance = fill.tolerance
            bridge_strategy_name = fill.bridge_strategy_name

        ambiguous_regions: list[dict[str, Any]] = []
        if status == "low_confidence":
            ambiguous_regions.append({"reason": "low confidence", "confidence": confidence})
        elif status == "skipped":
            ambiguous_regions.append({"reason": "skipped"})
        elif status == "failed":
            ambiguous_regions.append({"reason": "failed"})
        for candidate in candidates_by_layer.get(layer, []):
            if not bool(getattr(candidate, "accepted", False)):
                ambiguous_regions.append(
                    {
                        "reason": str(getattr(candidate, "reason", "rejected completion candidate")),
                        "confidence": round(float(getattr(candidate, "confidence", 0.0)), 4),
                    }
                )
        limitation = _foundation_concrete_limitation(
            layer,
            status=status,
            action=action,
            redact_layer_name=redact_layer_names,
        )
        if limitation is not None:
            limitations.append(limitation)

        bounds = _bbox(paths)
        generated_polygon_areas = [_polygon_area(poly) for poly in injected_polygons]
        layer_data: dict[str, Any] = {
            "layer_id": _stable_layer_id(layer) if redact_layer_names else layer,
            "source_cut_contours_count": len(paths),
            "source_segment_count": _path_segment_count(paths),
            "generated_poche_polygons_count": polygon_count,
            "injected_polygon_count": len(injected_polygons),
            "strategy": strategy,
            "confidence": confidence,
            "status": status,
            "action": action,
            "tolerance": tolerance,
            "bridge_strategy_name": bridge_strategy_name,
            "source_bbox": bounds,
            "source_bbox_area": _bbox_area(bounds),
            "generated_polygon_areas": generated_polygon_areas,
            "voids": {"available": False, "count": 0},
            "ambiguous_regions": ambiguous_regions,
            "limitations": [limitation] if limitation is not None else [],
            "next_action": _geometry_next_action(status, ambiguous_regions),
        }
        if not redact_layer_names:
            layer_data["layer_name"] = layer
        layers.append(layer_data)

    limitations.extend(_known_limitations(known_limitations))
    summary = {
        "layers_considered": len(layers),
        "source_cut_contours_total": sum(layer["source_cut_contours_count"] for layer in layers),
        "source_segments_total": sum(layer["source_segment_count"] for layer in layers),
        "generated_poche_polygons_total": sum(
            layer["generated_poche_polygons_count"] for layer in layers
        ),
        "injected_polygons_total": sum(layer["injected_polygon_count"] for layer in layers),
        "ambiguous_regions_total": sum(len(layer["ambiguous_regions"]) for layer in layers),
        "limitations_count": len(limitations),
        "no_go_limitations": _no_go_limitations(limitations),
    }
    status, why, next_action = _poche_geometry_summary_status(summary)
    summary.update({"status": status, "why": why, "next_action": next_action})

    return {
        "schema_version": 1,
        "source": {
            "command": "poche",
            "stage": "cut_geometry",
            "layer_names_redacted": redact_layer_names,
            **dict(source),
        },
        "summary": summary,
        "layers": layers,
        "limitations": limitations,
    }
