from __future__ import annotations

import json
from unittest.mock import patch

from click.testing import CliRunner

from arch_line_weights.cli import cli
from arch_line_weights.poche import FillResult, PocheReport


def test_cli_poche_writes_structured_report_json(tmp_path):
    src = tmp_path / "section.ai"
    src.write_bytes(b"%PDF-1.6\n")
    output = tmp_path / "section POCHE.ai"
    report_json = tmp_path / "reports" / "arch_lw_poche_report.json"
    layer = "axon::Visible::ClippingPlaneIntersections::09_SHS_50x50x5_HORIZ"

    def fake_apply_poche(*args, **kwargs):
        return PocheReport(
            fills=[FillResult(layer, "linemerge_bare", 1.0, 1, 22)],
            polygons={layer: [[[0, 0], [10, 0], [10, 10], [0, 10]]]},
        )

    runner = CliRunner()
    with patch("arch_line_weights.cli.apply_poche", side_effect=fake_apply_poche) as apply:
        result = runner.invoke(
            cli,
            [
                "poche",
                str(src),
                "-o",
                str(output),
                "--report-json",
                str(report_json),
            ],
        )

    assert result.exit_code == 0, result.output
    apply.assert_called_once()
    data = json.loads(report_json.read_text())
    assert data["source"]["input"] == str(src)
    assert data["source"]["output"] == str(output)
    assert data["source"]["command"] == "poche"
    assert data["source"]["stage"] == "poche"
    assert data["summary"]["status"] == "passed"
    assert data["summary"]["layers_filled"] == 1
    assert data["summary"]["polygons_injected"] == 1
    assert data["layers_by_status"]["filled"] == [layer]
    assert "report: wrote" in result.output


def test_cli_poche_threads_geometry_json_path(tmp_path):
    src = tmp_path / "section.ai"
    src.write_bytes(b"%PDF-1.6\n")
    geometry_json = tmp_path / "reports" / "geometry.json"
    captured = {}

    def fake_apply_poche(*args, **kwargs):
        captured["kwargs"] = kwargs
        return PocheReport()

    runner = CliRunner()
    with patch("arch_line_weights.cli.apply_poche", side_effect=fake_apply_poche):
        result = runner.invoke(
            cli,
            [
                "poche",
                str(src),
                "--geometry-json",
                str(geometry_json),
            ],
        )

    assert result.exit_code == 0, result.output
    assert captured["kwargs"]["geometry_report_path"] == str(geometry_json)
