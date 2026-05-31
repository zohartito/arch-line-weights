from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from arch_line_weights.cli import cli
from arch_line_weights.layout_jsx import (
    default_output_path,
    layout_via_jsx,
    parse_artboard_size,
    parse_length,
    render_layout_jsx,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("24x36in", (1728.0, 2592.0)),
        ("24 x 36", (1728.0, 2592.0)),
        ("612x792pt", (612.0, 792.0)),
        ("11in x 17in", (792.0, 1224.0)),
    ],
)
def test_parse_artboard_size_accepts_inches_and_points(raw, expected):
    assert parse_artboard_size(raw) == expected


def test_parse_length_rejects_unknown_units():
    with pytest.raises(ValueError, match="unsupported length"):
        parse_length("42cm")


def test_default_output_path_uses_layout_jsx_suffix():
    assert default_output_path("/tmp/wall.ai") == "/tmp/wall LAYOUT-jsx.ai"


def test_render_layout_jsx_sets_artboard_selects_all_centers_and_saves():
    jsx = render_layout_jsx(
        target="/tmp/source.ai",
        output="/tmp/out.ai",
        report_json="/tmp/report.json",
        artboard_width_pt=1728.0,
        artboard_height_pt=2592.0,
        margin_pt=36.0,
        fit_mode="fit",
        allow_enlarge=False,
    )

    assert "__TARGET__" not in jsx
    assert "var SHEET_W = 1728;" in jsx
    assert "var SHEET_H = 2592;" in jsx
    assert "doc.artboards[0].artboardRect = [0, SHEET_H, SHEET_W, 0];" in jsx
    assert 'app.executeMenuCommand("selectall");' in jsx
    assert "resize(scalePct, scalePct" in jsx
    assert "item.translate(dx, dy);" in jsx
    assert "saveOpts.pdfCompatible = true;" in jsx


def test_cli_layout_jsx_threads_options_to_runner(tmp_path):
    src = tmp_path / "rhino-export.ai"
    src.write_text("%PDF-1.6\n")
    output = tmp_path / "centered.ai"
    report = tmp_path / "layout-report.json"

    def fake_layout_via_jsx(*args, **kwargs):
        return {
            "output": str(output),
            "report_json": str(report),
            "report": '{"status":"passed"}',
        }

    runner = CliRunner()
    with patch("arch_line_weights.cli.layout_via_jsx", side_effect=fake_layout_via_jsx) as layout:
        result = runner.invoke(
            cli,
            [
                "layout-jsx",
                str(src),
                "--output",
                str(output),
                "--artboard",
                "24x36in",
                "--fit",
                "fit",
                "--margin",
                "0.5in",
                "--report-json",
                str(report),
                "--timeout",
                "7",
            ],
        )

    assert result.exit_code == 0, result.output
    layout.assert_called_once()
    _, kwargs = layout.call_args
    assert kwargs["dst"] == str(output)
    assert kwargs["artboard"] == "24x36in"
    assert kwargs["fit_mode"] == "fit"
    assert kwargs["margin"] == "0.5in"
    assert kwargs["report_json"] == str(report)
    assert kwargs["timeout_min"] == 7
    assert "layout: wrote" in result.output


def test_cli_layout_jsx_rejects_bad_artboard(tmp_path):
    src = tmp_path / "rhino-export.ai"
    src.write_text("%PDF-1.6\n")

    runner = CliRunner()
    result = runner.invoke(cli, ["layout-jsx", str(src), "--artboard", "banana"])

    assert result.exit_code != 0
    assert "artboard" in result.output.lower()


def test_layout_dry_run_does_not_probe_illustrator(tmp_path):
    src = tmp_path / "rhino-export.ai"
    src.write_text("%PDF-1.6\n")
    output = tmp_path / "layout.ai"
    report = tmp_path / "layout-report.json"
    jsx = tmp_path / "layout.jsx"

    with patch("arch_line_weights.layout_jsx.query_active_doc") as query_active_doc:
        result = layout_via_jsx(
            str(src),
            dst=str(output),
            report_json=str(report),
            jsx_path=str(jsx),
            dry_run=True,
        )

    query_active_doc.assert_not_called()
    assert result["dry_run"] is True
    assert report.exists()
    assert jsx.exists()
    assert not output.exists()


def test_layout_real_run_normalizes_illustrator_report_to_stable_schema(tmp_path):
    src = tmp_path / "rhino-export.ai"
    src.write_text("%PDF-1.6\n")
    output = tmp_path / "layout.ai"
    report = tmp_path / "layout-report.json"
    jsx = tmp_path / "layout.jsx"

    def fake_run_jsx(_jsx_path, *, timeout):
        output.write_text("%AI\n")
        report.write_text(
            json.dumps(
                {
                    "status": "passed",
                    "selected_items": 922,
                    "scale": 1,
                    "translation": {"dx": 12.5, "dy": -4.0},
                    "original_visible_bounds": [1, 2, 3, 4],
                    "final_visible_bounds": [36, 1200, 1692, 36],
                }
            )
        )

    with (
        patch("arch_line_weights.layout_jsx.query_active_doc", return_value=(None, None)),
        patch("arch_line_weights.layout_jsx.open_in_illustrator"),
        patch("arch_line_weights.layout_jsx.run_jsx_in_illustrator", side_effect=fake_run_jsx),
    ):
        result = layout_via_jsx(
            str(src),
            dst=str(output),
            artboard="24x36in",
            fit_mode="fit",
            margin="0.5in",
            report_json=str(report),
            jsx_path=str(jsx),
        )

    data = json.loads(result["report"])
    assert data["schema_version"] == 1
    assert data["source"]["command"] == "layout-jsx"
    assert data["summary"]["status"] == "passed"
    assert data["layout"]["artboard"] == {"width_pt": 1728.0, "height_pt": 2592.0}
    assert data["layout"]["selected_items"] == 922
    assert data["layout"]["translation"] == {"dx": 12.5, "dy": -4.0}
    assert json.loads(report.read_text()) == data


def test_layout_real_run_failed_report_raises_and_normalizes(tmp_path):
    src = tmp_path / "rhino-export.ai"
    src.write_text("%PDF-1.6\n")
    output = tmp_path / "layout.ai"
    report = tmp_path / "layout-report.json"
    jsx = tmp_path / "layout.jsx"

    def fake_run_jsx(_jsx_path, *, timeout):
        report.write_text(json.dumps({"status": "failed", "why": ["target document not open"]}))

    with (
        patch("arch_line_weights.layout_jsx.query_active_doc", return_value=(None, None)),
        patch("arch_line_weights.layout_jsx.open_in_illustrator"),
        patch("arch_line_weights.layout_jsx.run_jsx_in_illustrator", side_effect=fake_run_jsx),
        pytest.raises(RuntimeError, match="target document not open"),
    ):
        layout_via_jsx(
            str(src),
            dst=str(output),
            report_json=str(report),
            jsx_path=str(jsx),
        )

    data = json.loads(report.read_text())
    assert data["schema_version"] == 1
    assert data["summary"]["status"] == "failed"
    assert data["summary"]["why"] == ["target document not open"]
    assert not output.exists()


def test_layout_real_run_passed_report_without_output_raises(tmp_path):
    src = tmp_path / "rhino-export.ai"
    src.write_text("%PDF-1.6\n")
    output = tmp_path / "layout.ai"
    report = tmp_path / "layout-report.json"
    jsx = tmp_path / "layout.jsx"

    def fake_run_jsx(_jsx_path, *, timeout):
        report.write_text(json.dumps({"status": "passed", "selected_items": 1}))

    with (
        patch("arch_line_weights.layout_jsx.query_active_doc", return_value=(None, None)),
        patch("arch_line_weights.layout_jsx.open_in_illustrator"),
        patch("arch_line_weights.layout_jsx.run_jsx_in_illustrator", side_effect=fake_run_jsx),
        pytest.raises(RuntimeError, match="output file was not written"),
    ):
        layout_via_jsx(
            str(src),
            dst=str(output),
            report_json=str(report),
            jsx_path=str(jsx),
        )

    data = json.loads(report.read_text())
    assert data["summary"]["status"] == "failed"
    assert data["summary"]["why"] == ["output file was not written"]


def test_layout_real_run_missing_report_raises(tmp_path):
    src = tmp_path / "rhino-export.ai"
    src.write_text("%PDF-1.6\n")
    output = tmp_path / "layout.ai"
    jsx = tmp_path / "layout.jsx"
    report = tmp_path / "missing-layout-report.json"

    with (
        patch("arch_line_weights.layout_jsx.query_active_doc", return_value=(None, None)),
        patch("arch_line_weights.layout_jsx.open_in_illustrator"),
        patch("arch_line_weights.layout_jsx.run_jsx_in_illustrator"),
        pytest.raises(RuntimeError, match="did not write a report"),
    ):
        layout_via_jsx(
            str(src),
            dst=str(output),
            report_json=str(report),
            jsx_path=str(jsx),
        )

    assert not output.exists()


def test_cli_layout_jsx_failure_is_nonzero_without_wrote_claim(tmp_path):
    src = tmp_path / "rhino-export.ai"
    src.write_text("%PDF-1.6\n")

    runner = CliRunner()
    with patch(
        "arch_line_weights.cli.layout_via_jsx",
        side_effect=RuntimeError("layout-jsx failed: target document not open"),
    ):
        result = runner.invoke(cli, ["layout-jsx", str(src)])

    assert result.exit_code != 0
    assert "target document not open" in result.output
    assert "layout: wrote" not in result.output
