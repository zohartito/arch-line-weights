from __future__ import annotations

import json
from unittest.mock import patch

from click.testing import CliRunner

from arch_line_weights.bridge_rhino_ai import bridge_rhino_ai
from arch_line_weights.cli import cli
from arch_line_weights.poche import FillResult, PocheReport


def test_bridge_rhino_ai_dry_run_plans_layout_apply_and_poche_without_gui(tmp_path):
    src = tmp_path / "01-rhino-make2d-export.ai"
    src.write_text("%PDF-1.6\n")
    report_dir = tmp_path / "proof"

    with (
        patch("arch_line_weights.bridge_rhino_ai.layout_via_jsx") as layout,
        patch("arch_line_weights.bridge_rhino_ai.apply_via_jsx") as apply,
        patch("arch_line_weights.bridge_rhino_ai.apply_poche") as poche,
    ):
        layout.return_value = {
            "output": str(tmp_path / "02-layout.ai"),
            "report_json": str(report_dir / "layout-report.json"),
            "report": '{"summary":{"status":"dry_run"}}',
            "dry_run": True,
        }
        result = bridge_rhino_ai(
            str(src),
            artboard="30x42in",
            fit_mode="fit",
            margin="1in",
            preset="usc",
            source="rhino",
            for_print=True,
            run_apply_jsx=True,
            run_poche=True,
            report_dir=str(report_dir),
            dry_run=True,
        )

    layout.assert_called_once()
    apply.assert_not_called()
    poche.assert_not_called()
    assert result["summary"]["status"] == "dry_run"
    assert [stage["name"] for stage in result["stages"]] == ["layout", "apply-jsx", "poche"]
    assert result["stages"][0]["status"] == "dry_run"
    assert result["stages"][1]["status"] == "planned"
    assert result["stages"][2]["status"] == "planned"
    assert (report_dir / "bridge-report.json").exists()


def test_bridge_rhino_ai_runs_apply_then_poche_on_layout_output(tmp_path):
    src = tmp_path / "01-rhino-make2d-export.ai"
    src.write_text("%PDF-1.6\n")
    layout_output = tmp_path / "02-layout.ai"
    hierarchy_output = tmp_path / "02-layout HIERARCHY-jsx.ai"
    report_dir = tmp_path / "proof"
    layer = "axon::Visible::ClippingPlaneIntersections::TEC_FOUNDATION"

    with (
        patch("arch_line_weights.bridge_rhino_ai.layout_via_jsx") as layout,
        patch("arch_line_weights.bridge_rhino_ai.apply_via_jsx") as apply,
        patch("arch_line_weights.bridge_rhino_ai.apply_poche") as poche,
    ):
        layout.return_value = {
            "output": str(layout_output),
            "report_json": str(report_dir / "layout-report.json"),
            "report": '{"summary":{"status":"passed"}}',
            "dry_run": False,
        }
        apply.return_value = {
            "output": str(hierarchy_output),
            "report": "ok",
            "report_path": "/tmp/arch_lw_report.txt",
        }
        poche.return_value = PocheReport(
            fills=[FillResult(layer, "linemerge_bare", 1.0, 1, 4)],
            polygons={layer: [[[0, 0], [1, 0], [1, 1], [0, 1]]]},
        )
        result = bridge_rhino_ai(
            str(src),
            run_apply_jsx=True,
            run_poche=True,
            report_dir=str(report_dir),
            timeout_min=9,
            preset="usc",
            source="rhino",
            bridge_strategy="best",
        )

    _, layout_kwargs = layout.call_args
    assert layout_kwargs["report_json"] == str(report_dir / "layout-report.json")
    apply.assert_called_once()
    assert apply.call_args.args[0] == str(layout_output)
    assert apply.call_args.kwargs["timeout_min"] == 9
    poche.assert_called_once()
    assert poche.call_args.args[0] == str(hierarchy_output)
    assert poche.call_args.kwargs["geometry_report_path"] == str(report_dir / "geometry-report.json")
    assert result["summary"]["status"] == "passed"
    assert result["stages"][-1]["output"].endswith("POCHE.ai")
    assert json.loads((report_dir / "poche-report.json").read_text())["summary"]["status"] == "passed"


def test_bridge_rhino_ai_requires_apply_before_poche(tmp_path):
    src = tmp_path / "01-rhino-make2d-export.ai"
    src.write_text("%PDF-1.6\n")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "bridge-rhino-ai",
            "--input",
            str(src),
            "--poche",
            "--dry-run",
        ],
    )

    assert result.exit_code != 0
    assert "--poche requires --apply-jsx" in result.output


def test_cli_bridge_rhino_ai_threads_options_to_orchestrator(tmp_path):
    src = tmp_path / "01-rhino-make2d-export.ai"
    src.write_text("%PDF-1.6\n")
    report_dir = tmp_path / "proof"

    def fake_bridge(*args, **kwargs):
        return {
            "summary": {"status": "dry_run"},
            "stages": [{"name": "layout", "status": "dry_run"}],
            "report_json": str(report_dir / "bridge-report.json"),
        }

    runner = CliRunner()
    with patch("arch_line_weights.cli.bridge_rhino_ai", side_effect=fake_bridge) as bridge:
        result = runner.invoke(
            cli,
            [
                "bridge-rhino-ai",
                "--input",
                str(src),
                "--artboard",
                "24x36in",
                "--fit",
                "fit",
                "--margin",
                "0.5in",
                "--preset",
                "usc",
                "--source",
                "rhino",
                "--for-print",
                "--apply-jsx",
                "--report-dir",
                str(report_dir),
                "--dry-run",
            ],
        )

    assert result.exit_code == 0, result.output
    bridge.assert_called_once()
    assert bridge.call_args.args[0] == str(src)
    _, kwargs = bridge.call_args
    assert kwargs["artboard"] == "24x36in"
    assert kwargs["fit_mode"] == "fit"
    assert kwargs["margin"] == "0.5in"
    assert kwargs["preset"] == "usc"
    assert kwargs["source"] == "rhino"
    assert kwargs["for_print"] is True
    assert kwargs["run_apply_jsx"] is True
    assert kwargs["report_dir"] == str(report_dir)
    assert kwargs["dry_run"] is True
    assert "bridge: dry_run" in result.output
