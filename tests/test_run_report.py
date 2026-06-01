from __future__ import annotations

import json

from click.testing import CliRunner
from shapely.geometry import Polygon

from arch_line_weights import cli as cli_mod
from arch_line_weights.cli import cli
from arch_line_weights.make2d_completion import CompletionCandidate
from arch_line_weights.poche import FillResult, PocheReport
from arch_line_weights.poche_saas import PocheSaasResult
from arch_line_weights.run_report import (
    build_apply_saas_report,
    build_layout_jsx_report,
    build_poche_geometry_report,
    build_poche_report,
)


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
    assert data["layers"][0]["review"]["needs_review"] is True
    assert data["layers"][0]["review"]["visual_acceptance_required"] is True
    assert (
        "inferred concrete/foundation fill requires W5/W7 visual acceptance"
        in data["layers"][0]["review"]["reasons"]
    )


def test_apply_saas_report_marks_structural_helper_evidence_from_poche_report():
    layer = "axon::Visible::ClippingPlaneIntersections::TEC_CONCRETE_BASE"
    data = _report(
        [FillResult(layer, "structural_open_loop", 0.88, 1, 8)],
        polygons={layer: [[[100, 0], [130, 0], [130, 160], [100, 160], [100, 0]]]},
        injected=1,
        helper_counts={layer: 2},
    )

    assert data["layers"][0]["evidence"]["used_structural_helpers"] is True
    assert data["layers"][0]["evidence"]["structural_helper_count"] == 2


def test_report_marks_alpha_shape_as_low_confidence_diagnostic_only():
    layer = "LayerA"
    data = _report([FillResult(layer, "alpha_shape", 0.55, 1, 3)])

    assert data["layers"][0]["status"] == "low_confidence"
    assert data["layers"][0]["action"] == "diagnostic_only"
    assert data["layers"][0]["review"]["needs_review"] is True
    assert data["summary"]["polygons_diagnostic_only"] == 1


def test_apply_saas_report_marks_partial_foundation_concrete_coverage_no_go():
    layer = "axon::Visible::ClippingPlaneIntersections::TEC_CONCRETE_BASE"
    data = _report([FillResult(layer, "auto_bridge", 0.69, 1, 18)])

    assert data["summary"]["no_go_limitations"] == 1
    assert data["limitations"][0]["code"] == "foundation_concrete_partial_coverage"
    assert data["limitations"][0]["status"] == "no_go"
    assert data["limitations"][0]["scope"] == "foundation_concrete"
    assert data["layers"][0]["review"]["needs_review"] is True


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

def test_apply_saas_report_schema_v2_includes_input_format_and_visual_artifacts():
    layer = "LayerA"
    data = build_apply_saas_report(
        input_path="in.ai",
        output_path="out.ai",
        source={"mode": "apply-saas"},
        poche_report=PocheReport(fills=[FillResult(layer, "linemerge_bare", 1.0, 1, 4)]),
        poche_result=PocheSaasResult(polygons_injected=1),
        input_format={"input_kind": "native_ai", "header_kind": "pdf"},
        visual_artifacts={"before": "before.png", "after": "after.png", "diff": "diff.png"},
        command="arch-lw apply-saas in.ai --poche --report report.json",
    )

    assert data["schema_version"] == 2
    assert data["source"]["input_format"]["input_kind"] == "native_ai"
    assert data["source"]["command"] == "arch-lw apply-saas in.ai --poche --report report.json"
    assert data["visual_artifacts"]["diff"] == "diff.png"


def test_poche_report_uses_same_changed_skipped_failed_shape():
    layer = "axon::Visible::ClippingPlaneIntersections::TEC_FOUNDATION"
    data = build_poche_report(
        input_path="hierarchy.ai",
        output_path="poche.ai",
        source={"mode": "poche", "style": "solid"},
        poche_report=PocheReport(
            fills=[
                FillResult(layer, "linemerge_bare", 1.0, 2, 8),
                FillResult("BadLayer", "failed", 0.0, 0, 3),
            ],
            polygons={layer: [[[0, 0], [10, 0], [10, 10], [0, 10]]]},
        ),
        input_format={"input_kind": "pdf_compatible_ai"},
        command="arch-lw poche hierarchy.ai --report report.json",
    )

    assert data["schema_version"] == 2
    assert data["source"]["mode"] == "poche"
    assert data["summary"]["layers_filled"] == 1
    assert data["summary"]["layers_failed"] == 1
    assert data["summary"]["polygons_filled"] == 1
    assert data["layers"][0]["status"] == "filled"
    assert data["layers"][0]["action"] == "injected"
    assert data["layers"][1]["status"] == "failed"


def test_poche_report_marks_inferred_foundation_concrete_as_needing_visual_acceptance():
    layer = "axon::Visible::ClippingPlaneIntersections::TEC_CONCRETE_BASE"
    data = build_poche_report(
        input_path="hierarchy.ai",
        output_path="poche.ai",
        source={"mode": "poche", "style": "solid"},
        poche_report=PocheReport(
            fills=[FillResult(layer, "structural_open_loop", 0.88, 1, 8)],
            polygons={layer: [[[0, 0], [10, 0], [10, 10], [0, 10]]]},
        ),
    )

    assert data["layers"][0]["status"] == "inferred"
    assert data["layers"][0]["review"]["needs_review"] is True
    assert data["layers"][0]["review"]["visual_acceptance_required"] is True
    assert (
        "inferred concrete/foundation fill requires W5/W7 visual acceptance"
        in data["layers"][0]["review"]["reasons"]
    )
    assert data["summary"]["status"] == "needs_review"
    assert data["summary"]["layers_needs_review"] == 1
    assert "1 poché layer(s) require review." in data["summary"]["why"]
    assert "Review gated poché layers" in data["summary"]["next_action"]


def test_poche_cli_writes_durable_report(monkeypatch, tmp_path):
    import pikepdf

    src = tmp_path / "hierarchy.ai"
    output = tmp_path / "out.ai"
    report_path = tmp_path / "report.json"
    pdf = pikepdf.new()
    pdf.add_blank_page(page_size=(100, 100))
    pdf.save(src)
    pdf.close()

    def fake_apply_poche(*_args, **_kwargs):
        return PocheReport(
            fills=[FillResult("LayerA", "linemerge_bare", 1.0, 1, 4)],
            polygons={"LayerA": [[[0, 0], [1, 0], [1, 1], [0, 1]]]},
        )

    monkeypatch.setattr(cli_mod, "apply_poche", fake_apply_poche)

    result = CliRunner().invoke(
        cli,
        ["poche", str(src), "-o", str(output), "--report", str(report_path)],
    )

    assert result.exit_code == 0, result.output
    data = json.loads(report_path.read_text())
    assert data["schema_version"] == 2
    assert data["source"]["mode"] == "poche"
    assert data["source"]["input_format"]["input_kind"] == "pdf_compatible_ai"
    assert data["summary"]["polygons_filled"] == 1


def test_report_keeps_non_foundation_inferred_fill_as_inferred_without_visual_gate():
    layer = "axon::Visible::ClippingPlaneIntersections::TEC_CLT_SLABS"
    data = _report(
        [FillResult(layer, "structural_open_loop", 0.88, 1, 12)],
        polygons={layer: [[[0, 0], [10, 0], [10, 10], [0, 10]]]},
        injected=1,
    )

    assert data["layers"][0]["status"] == "inferred"
    assert data["layers"][0]["review"]["needs_review"] is False
    assert data["layers"][0]["review"]["visual_acceptance_required"] is False


def test_poche_report_marks_structural_helper_evidence_from_poche_report():
    layer = "axon::Visible::ClippingPlaneIntersections::TEC_CONCRETE_BASE"
    data = build_poche_report(
        input_path="hierarchy.ai",
        output_path="poche.ai",
        source={"mode": "poche", "style": "solid"},
        poche_report=PocheReport(
            fills=[FillResult(layer, "structural_open_loop", 0.88, 1, 8)],
            polygons={layer: [[[100, 0], [130, 0], [130, 160], [100, 160], [100, 0]]]},
            structural_helper_counts={layer: 2},
        ),
    )

    assert data["layers"][0]["evidence"]["used_structural_helpers"] is True
    assert data["layers"][0]["evidence"]["structural_helper_count"] == 2


def test_poche_report_marks_needs_review_and_groups_layers():
    filled = "axon::Visible::ClippingPlaneIntersections::09_SHS_50x50x5_HORIZ"
    skipped = "axon::Visible::ClippingPlaneIntersections::23_WINDOW_FRAMES_REMAP"
    low_confidence = "axon::Visible::ClippingPlaneIntersections::TEC_TIMBER_BEAMS"
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


def test_poche_report_marks_partial_foundation_concrete_coverage_no_go():
    layer = "axon::Visible::ClippingPlaneIntersections::TEC_CONCRETE_BASE"
    data = build_poche_report(
        input_path="section.ai",
        output_path="section-POCHE.ai",
        source={"style": "solid", "bridge_strategy": "best"},
        poche_report=PocheReport(
            fills=[FillResult(layer, "auto_bridge", 0.69, 1, 18)],
            polygons={},
        ),
    )

    assert data["summary"]["status"] == "no_go"
    assert data["summary"]["no_go_limitations"] == 1
    assert data["limitations"] == [
        {
            "id": "foundation_concrete_partial_coverage",
            "code": "foundation_concrete_partial_coverage",
            "status": "no_go",
            "scope": "foundation_concrete",
            "layer": layer,
            "component_key": "TEC_CONCRETE_BASE",
            "reason": "Foundation/concrete poché coverage is incomplete or diagnostic-only.",
            "next_action": "Review cut geometry, fix Make2D closure, and recapture proof before launch.",
            "evidence": {
                "kind": "poche_layer_status",
                "layer_status": "low_confidence",
                "layer_action": "diagnostic_only",
            },
        }
    ]
    assert data["layers"][0]["review"]["needs_review"] is True
    assert "foundation/concrete coverage is launch-blocking" in data["layers"][0]["review"]["reasons"]


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
    assert "Resolve no-go poché coverage limitations" in data["summary"]["next_action"]
    assert data["summary"]["no_go_limitations"] == 1
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


def test_poche_report_includes_known_visual_no_go_limitation():
    layer = "axon::Visible::ClippingPlaneIntersections::TEC_TIMBER_BEAMS"
    data = build_poche_report(
        input_path="section.ai",
        output_path="section-POCHE.ai",
        source={"style": "solid"},
        poche_report=PocheReport(
            fills=[FillResult(layer, "linemerge_bare", 1.0, 1, 4)],
            polygons={layer: [[[0, 0], [10, 0], [10, 10], [0, 10]]]},
        ),
        known_limitations=[
            {
                "id": "foundation_concrete_under_wood_column_left_footing",
                "scope": "foundation_concrete",
                "status": "no_go",
                "evidence_screenshot": "known_miss_closeup",
                "roi": [300, 6200, 1600, 6760],
                "expected_min_black_ratio": 0.15,
                "current_black_ratio_observed": 0.0,
                "reason": "The left foundation/concrete mass below the wood column is outline-only.",
            }
        ],
    )

    assert data["summary"]["status"] == "no_go"
    assert data["summary"]["no_go_limitations"] == 1
    assert data["limitations"][0]["id"] == "foundation_concrete_under_wood_column_left_footing"
    assert data["limitations"][0]["code"] == "known_visual_proof_miss"
    assert data["limitations"][0]["scope"] == "foundation_concrete"
    assert data["limitations"][0]["evidence"] == {
        "kind": "visual_roi_black_ratio",
        "evidence_screenshot": "known_miss_closeup",
        "roi": [300, 6200, 1600, 6760],
        "expected_min_black_ratio": 0.15,
        "current_black_ratio_observed": 0.0,
    }


def test_layout_jsx_report_records_sheet_and_dry_run_gate():
    data = build_layout_jsx_report(
        input_path="rhino-export.ai",
        output_path="rhino-export LAYOUT-jsx.ai",
        source={"fit_mode": "fit", "allow_enlarge": False},
        status="dry_run",
        artboard_width_pt=1728.0,
        artboard_height_pt=2592.0,
        margin_pt=36.0,
    )

    assert data["source"]["command"] == "layout-jsx"
    assert data["source"]["stage"] == "layout"
    assert data["source"]["fit_mode"] == "fit"
    assert data["summary"]["status"] == "dry_run"
    assert "rerun without --dry-run" in data["summary"]["next_action"]
    assert data["layout"]["artboard"] == {"width_pt": 1728.0, "height_pt": 2592.0}
    assert data["layout"]["margin_pt"] == 36.0


def test_poche_geometry_report_summarizes_and_redacts_private_layer_geometry():
    private_foundation = "private_project::Visible::ClippingPlaneIntersections::FOUNDATION_WALL"
    private_ambiguous = "private_project::Visible::ClippingPlaneIntersections::CONCRETE_BASE"
    paths_by_layer = {
        private_foundation: [
            [[0, 0], [10, 0], [10, 3], [0, 3], [0, 0]],
            [[20, 0], [25, 0]],
        ],
        private_ambiguous: [
            [[0, 10], [10, 10], [10, 12]],
        ],
    }
    data = build_poche_geometry_report(
        source={"fixture": "synthetic_private"},
        paths_by_layer=paths_by_layer,
        poche_report=PocheReport(
            fills=[
                FillResult(private_foundation, "linemerge_bare", 1.0, 1, 5),
                FillResult(private_ambiguous, "alpha_shape", 0.55, 1, 2),
            ],
            polygons={private_foundation: [[[0, 0], [10, 0], [10, 3], [0, 3], [0, 0]]]},
        ),
        redact_layer_names=True,
    )

    dumped = str(data)
    assert "private_project" not in dumped
    assert "FOUNDATION_WALL" not in dumped
    assert "CONCRETE_BASE" not in dumped
    assert data["source"]["command"] == "poche"
    assert data["source"]["stage"] == "cut_geometry"
    assert data["summary"]["status"] == "no_go"
    assert data["summary"]["no_go_limitations"] == 1
    assert data["summary"]["layers_considered"] == 2
    assert data["summary"]["source_cut_contours_total"] == 3
    assert data["summary"]["generated_poche_polygons_total"] == 2
    assert data["summary"]["ambiguous_regions_total"] == 1
    assert data["limitations"][0]["code"] == "foundation_concrete_partial_coverage"
    assert data["limitations"][0]["layer_id"].startswith("layer_")
    assert "layer" not in data["limitations"][0]
    assert "component_key" not in data["limitations"][0]

    filled = data["layers"][0]
    assert filled["layer_id"].startswith("layer_")
    assert "layer_name" not in filled
    assert filled["source_cut_contours_count"] == 2
    assert filled["source_segment_count"] == 5
    assert filled["generated_poche_polygons_count"] == 1
    assert filled["injected_polygon_count"] == 1
    assert filled["source_bbox"] == [0.0, 0.0, 25.0, 3.0]
    assert filled["source_bbox_area"] == 75.0
    assert filled["generated_polygon_areas"] == [30.0]
    assert filled["voids"]["available"] is False
    assert filled["voids"]["count"] == 0

    ambiguous = data["layers"][1]
    assert ambiguous["ambiguous_regions"][0]["reason"] == "low confidence"
    assert "Review Make2D source curves" in ambiguous["next_action"]
