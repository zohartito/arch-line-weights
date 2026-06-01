from __future__ import annotations

from shapely.geometry import Polygon

from arch_line_weights.make2d_completion import CompletionCandidate
from arch_line_weights.poche import FillResult, PocheReport
from arch_line_weights.poche_saas import PocheSaasResult
from arch_line_weights.run_report import build_apply_saas_report


def _report(
    fills: list[FillResult],
    *,
    polygons: dict[str, list[list[list[float]]]] | None = None,
    candidates: list[object] | None = None,
    helper_counts: dict[str, int] | None = None,
    missing: list[str] | None = None,
    injected: int = 0,
):
    return build_apply_saas_report(
        input_path="in.ai",
        output_path="out.ai",
        source={"mode": "apply-saas", "architectural": True},
        poche_report=PocheReport(
            fills=fills,
            polygons=polygons or {},
            completion_candidates=candidates or [],
            structural_helper_counts=helper_counts or {},
        ),
        poche_result=PocheSaasResult(
            polygons_injected=injected,
            layers_missing=missing or [],
        ),
    )


def test_report_marks_injected_structural_open_loop_as_inferred():
    layer = "axon::Visible::ClippingPlaneIntersections::TEC_CONCRETE_BASE"
    data = _report(
        [FillResult(layer, "structural_open_loop", 0.88, 2, 12)],
        polygons={layer: [[[0, 0], [10, 0], [10, 10], [0, 10]]]},
        injected=2,
    )

    assert data["summary"]["layers_inferred"] == 1
    assert data["summary"]["polygons_filled"] == 2
    assert data["layers"][0]["status"] == "inferred"
    assert data["layers"][0]["action"] == "injected"
    assert data["layers"][0]["review"]["needs_review"] is False


def test_apply_saas_report_marks_structural_helper_evidence_from_poche_report():
    layer = "axon::Visible::ClippingPlaneIntersections::TEC_CONCRETE_BASE"
    data = _report(
        [FillResult(layer, "structural_open_loop", 0.88, 1, 8)],
        polygons={layer: [[[100, 0], [130, 0], [130, 160], [100, 160], [100, 0]]]},
        injected=1,
        helper_counts={layer: 2},
    )

    assert data["layers"][0]["evidence"]["used_structural_helpers"] is True


def test_report_marks_alpha_shape_as_low_confidence_diagnostic_only():
    layer = "LayerA"
    data = _report([FillResult(layer, "alpha_shape", 0.55, 1, 3)])

    assert data["layers"][0]["status"] == "low_confidence"
    assert data["layers"][0]["action"] == "diagnostic_only"
    assert data["layers"][0]["review"]["needs_review"] is True
    assert data["summary"]["polygons_diagnostic_only"] == 1


def test_report_marks_bbox_as_review_only():
    layer = "LayerA"
    data = _report([FillResult(layer, "bbox", 0.3, 1, 3)])

    assert data["layers"][0]["status"] == "low_confidence"
    assert "strategy bbox is review-only" in data["layers"][0]["review"]["reasons"]


def test_report_preserves_user_skip():
    layer = "LayerA"
    data = _report([FillResult(layer, "skipped", 0.0, 0, 3)])

    assert data["layers"][0]["status"] == "skipped"
    assert data["layers"][0]["action"] == "skipped_by_override"


def test_report_marks_missing_payload_layer():
    layer = "LayerA"
    data = _report(
        [FillResult(layer, "structural_open_loop", 0.9, 1, 3)],
        polygons={layer: [[[0, 0], [10, 0], [10, 10], [0, 10]]]},
        missing=[layer],
    )

    assert data["layers"][0]["status"] == "missing_payload"
    assert data["layers"][0]["action"] == "missing_payload"
    assert any("payload" in reason for reason in data["layers"][0]["review"]["reasons"])


def test_report_includes_completion_candidate_rejections():
    layer = "axon::Visible::ClippingPlaneIntersections::TEC_ROOF_CLT"
    poly = Polygon([(0, 0), (100, 0), (100, 80), (0, 80)])
    candidate = CompletionCandidate(
        component_key="TEC_ROOF_CLT",
        target_layer=layer,
        source_role="visible_curve",
        polygon=poly,
        confidence=0.0,
        provenance="cut+same-component-visible/tangent",
        accepted=False,
        reason="rejected: area 8000.0 exceeds layer limit 3500.0",
        cut_shared_length=42.5,
    )

    data = _report(
        [FillResult(layer, "structural_open_loop", 0.9, 1, 4)],
        polygons={layer: [[[0, 0], [10, 0], [10, 10], [0, 10]]]},
        candidates=[candidate],
        injected=1,
    )

    assert data["completion_candidates"][0]["reason"] == candidate.reason
    assert data["completion_candidates"][0]["area"] == 8000.0
    assert data["completion_candidates"][0]["cut_shared_length"] == 42.5
    assert data["completion_candidates"][0]["bounds"] == [0.0, 0.0, 100.0, 80.0]
    assert data["layers"][0]["review"]["needs_review"] is True
