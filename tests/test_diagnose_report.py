from __future__ import annotations

import json

from click.testing import CliRunner

from arch_line_weights.cli import cli
from arch_line_weights.diagnose_report import format_diagnosis, summarize_report


def _sample_report() -> dict:
    return {
        "schema_version": 1,
        "summary": {
            "layers_filled": 1,
            "layers_inferred": 1,
            "layers_low_confidence": 1,
            "layers_failed": 1,
            "layers_needs_review": 2,
            "polygons_filled": 4,
            "polygons_diagnostic_only": 1,
        },
        "layers": [
            {
                "layer": "axon::Visible::ClippingPlaneIntersections::TEC_CLT_SLABS",
                "status": "inferred",
                "action": "injected",
                "strategy": "structural_open_loop",
                "confidence": 0.88,
                "polygon_count": 2,
                "review": {"needs_review": False, "reasons": []},
            },
            {
                "layer": "axon::Visible::ClippingPlaneIntersections::26_CLT_GAP_ROOF_CAP",
                "status": "low_confidence",
                "action": "diagnostic_only",
                "strategy": "bbox",
                "confidence": 0.3,
                "polygon_count": 1,
                "review": {
                    "needs_review": True,
                    "reasons": ["strategy bbox is review-only", "confidence 0.30 below 0.85"],
                },
            },
            {
                "layer": "axon::Visible::ClippingPlaneIntersections::TEC_CONCRETE_BASE",
                "status": "failed",
                "action": "failed",
                "strategy": "failed",
                "confidence": 0.0,
                "polygon_count": 0,
                "review": {"needs_review": True, "reasons": ["failed"]},
            },
        ],
    }


def test_summarize_report_groups_review_layers_and_next_step():
    summary = summarize_report(_sample_report())

    assert summary["status"] == "needs_review"
    assert summary["counts"]["inferred"] == 1
    assert summary["counts"]["low_confidence"] == 1
    assert summary["counts"]["failed"] == 1
    assert summary["review_layers"][0]["short_name"] == "26_CLT_GAP_ROOF_CAP"
    assert summary["failed_layers"][0]["short_name"] == "TEC_CONCRETE_BASE"
    assert "Illustrator" in summary["next_step"]
    assert "PDF preview is not authoritative" in summary["preview_warning"]


def test_format_diagnosis_is_human_readable_and_reasoned():
    text = format_diagnosis(summarize_report(_sample_report()))

    assert "Status: needs_review" in text
    assert "Inferred closures: 1" in text
    assert "26_CLT_GAP_ROOF_CAP" in text
    assert "strategy bbox is review-only" in text
    assert "TEC_CONCRETE_BASE" in text
    assert "PDF preview is not authoritative" in text


def test_diagnose_cli_reads_report_and_can_emit_json(tmp_path):
    report_path = tmp_path / "run-report.json"
    report_path.write_text(json.dumps(_sample_report()))
    runner = CliRunner()

    text_result = runner.invoke(cli, ["diagnose", str(report_path)])
    assert text_result.exit_code == 0, text_result.output
    assert "Status: needs_review" in text_result.output
    assert "26_CLT_GAP_ROOF_CAP" in text_result.output

    json_result = runner.invoke(cli, ["diagnose", str(report_path), "--json"])
    assert json_result.exit_code == 0, json_result.output
    data = json.loads(json_result.output)
    assert data["status"] == "needs_review"
    assert data["review_layers"][0]["short_name"] == "26_CLT_GAP_ROOF_CAP"
