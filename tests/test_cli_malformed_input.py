from __future__ import annotations

import click
from click.testing import CliRunner

from arch_line_weights.cli import cli


def test_apply_auto_malformed_input_reports_clean_error(tmp_path):
    src = tmp_path / "malformed.ai"
    dst = tmp_path / "out.ai"
    src.write_bytes(b"this is not a PDF or Illustrator file\n")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["apply", str(src), "--auto", "-o", str(dst)],
        standalone_mode=False,
    )

    assert isinstance(result.exception, click.ClickException)
    message = str(result.exception)
    assert "Failed to inspect" in message
    assert "Save As" in message or "save as" in message.lower()
    assert "Traceback" not in result.output
    assert not dst.exists()

    displayed = runner.invoke(cli, ["apply", str(src), "--auto", "-o", str(dst)])
    assert displayed.exit_code == 1
    assert "Error: Failed to inspect" in displayed.output
    assert "Save As" in displayed.output or "save as" in displayed.output.lower()
    assert "Traceback" not in displayed.output
    assert not dst.exists()
