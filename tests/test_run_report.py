from __future__ import annotations

from shapely.geometry import Polygon

from arch_line_weights.make2d_completion import CompletionCandidate
from arch_line_weights.poche import FillResult, PocheReport
from arch_line_weights.poche_saas import PocheSaasResult
from arch_line_weights.run_report import build_apply_saas_report, build_poche_report


def _report(
    fills: list[FillResult],
    *,
    polygons: dict[str, list[list[list[float]]]] | None = None,
    candidates: list[object] | None = None,
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


def test_poche_report_marks_needs_review_and_groups_layers():
    filled = "axon::Visible::ClippingPlaneIntersections::09_SHS_50x50x5_HORIZ"
    skipped = "axon::Visible::ClippingPlaneIntersections::23_WINDOW_FRAMES_REMAP"
    low_confidence = "axon::Visible::ClippingPlaneIntersections::TEC_CONCRETE_BASE"
    data = build_poche_report(
        input_path="section.ai",
        output_path="section-POCHE.ai",
        source={"style": "solid", "bridge_strategy": "best"},
        poche_report=PocheReport(
            fills=[
                FillResult(filled, "linemerge_bare", 1.0, 1, 22),
                FillResult(skipped, "skipped", 0.0, 0, 12),
                FillResult(low_confidence, "auto_bridge", 0.69, 1, 18),
            ],
            polygons={filled: [[[0, 0], [10, 0], [10, 10], [0, 10]]]},
        ),
    )

    assert data["source"]["input"] == "section.ai"
    assert data["source"]["output"] == "section-POCHE.ai"
    assert data["source"]["command"] == "poche"
    assert data["source"]["stage"] == "poche"
    assert data["summary"]["status"] == "needs_review"
    assert data["summary"]["why"]
    assert "Review low-confidence or skipped cut layers" in data["summary"]["next_action"]
    assert data["summary"]["layers_filled"] == 1
    assert data["summary"]["layers_skipped"] == 1
    assert data["summary"]["layers_low_confidence"] == 1
    assert data["summary"]["layers_failed"] == 0
    assert data["summary"]["polygons_total"] == 2
    assert data["summary"]["polygons_injected"] == 1
    assert data["layers_by_status"]["filled"] == [filled]
    assert data["layers_by_status"]["skipped"] == [skipped]
    assert data["layers_by_status"]["low_confidence"] == [low_confidence]
    assert data["layers"][0]["strategy"] == "linemerge_bare"
    assert data["layers"][0]["confidence"] == 1.0


def test_poche_report_marks_no_go_when_no_layers_are_injectable():
    failed = "axon::Visible::ClippingPlaneIntersections::TEC_FOUNDATION"
    data = build_poche_report(
        input_path="section.ai",
        output_path="section-POCHE.ai",
        source={"style": "solid"},
        poche_report=PocheReport(
            fills=[FillResult(failed, "failed", 0.0, 0, 9)],
            polygons={},
        ),
    )

    assert data["summary"]["status"] == "no_go"
    assert "No reliable poché polygons were produced" in data["summary"]["why"]
    assert "Generate/review cut geometry" in data["summary"]["next_action"]
    assert data["layers_by_status"]["failed"] == [failed]


def test_poche_report_marks_failed_when_command_error_is_supplied():
    data = build_poche_report(
        input_path="section.ai",
        output_path="section-POCHE.ai",
        source={"style": "solid"},
        poche_report=None,
        error="Illustrator did not write geometry JSON",
    )

    assert data["summary"]["status"] == "failed"
    assert data["summary"]["why"] == ["Illustrator did not write geometry JSON"]
    assert data["summary"]["next_action"] == "Fix the reported command failure, then rerun arch-lw poche."
