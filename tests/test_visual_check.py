from __future__ import annotations

import json
from unittest.mock import patch

from click.testing import CliRunner

from arch_line_weights.cli import cli
from arch_line_weights.visual_check import build_visual_check_summary, format_visual_check_markdown


def test_visual_check_summary_redacts_local_paths_and_keeps_review_gate() -> None:
    summary = build_visual_check_summary(
        "/Users/zohartito/Desktop/private/USC section.ai",
        before="/private/tmp/proof/before.png",
        after="/private/tmp/proof/after.png",
        diff="/var/folders/xx/proof/diff.png",
        report="/Users/zohartito/Desktop/proof/report.json",
        status="needs_review",
        reviewer="Zohar",
        issues=("#7", "30"),
        notes=("Opened /Users/zohartito/Desktop/private/USC section.ai in Illustrator.",),
    )
    serialized = json.dumps(summary)

    assert "/Users/" not in serialized
    assert "/private/" not in serialized
    assert "/var/folders/" not in serialized
    assert summary["artifacts"]["subject"] == "USC section.ai"
    assert summary["artifacts"]["before"] == "before.png"
    assert summary["issues"] == ["#7", "#30"]
    assert summary["review"]["accepted"] is False
    assert "NO-GO" in summary["posting_clearance"]


def test_visual_check_markdown_is_human_readable_and_public_safe() -> None:
    summary = build_visual_check_summary(
        "/Users/zohartito/Desktop/private/USC section.ai",
        status="accepted",
        reviewer="W5",
        issues=("#7", "#19"),
        notes=("Illustrator visual comparison passed at print scale.",),
        opened_in_illustrator=True,
    )

    text = format_visual_check_markdown(summary)

    assert "Status: accepted" in text
    assert "Subject: USC section.ai" in text
    assert "Issues: #7, #19" in text
    assert "Illustrator visual comparison passed" in text
    assert "/Users/" not in text
    assert "Private drawings/screenshots/raw reports stay out of git." in text


def test_visual_check_cli_writes_json_and_markdown_without_private_paths(tmp_path) -> None:
    subject = tmp_path / "private source.ai"
    subject.write_bytes(b"%!PS-Adobe-3.0")
    report = tmp_path / "run-report.json"
    report.write_text("{}", encoding="utf-8")
    json_output = tmp_path / "visual-check.json"
    markdown_output = tmp_path / "visual-check.md"

    result = CliRunner().invoke(
        cli,
        [
            "visual-check",
            str(subject),
            "--report",
            str(report),
            "--issue",
            "30",
            "--note",
            f"Local report lives at {report}",
            "--json-output",
            str(json_output),
            "--markdown-output",
            str(markdown_output),
        ],
    )

    assert result.exit_code == 0, result.output
    data = json.loads(json_output.read_text(encoding="utf-8"))
    markdown = markdown_output.read_text(encoding="utf-8")
    assert data["artifacts"]["subject"] == "private source.ai"
    assert data["artifacts"]["report"] == "run-report.json"
    assert data["issues"] == ["#30"]
    assert str(tmp_path) not in json_output.read_text(encoding="utf-8")
    assert str(tmp_path) not in markdown
    assert "Status: needs_review" in result.output


def test_visual_check_cli_can_open_illustrator_without_leaking_paths(tmp_path) -> None:
    subject = tmp_path / "section.ai"
    subject.write_bytes(b"%!PS-Adobe-3.0")

    with patch("arch_line_weights.cli.open_in_illustrator") as opened:
        result = CliRunner().invoke(cli, ["visual-check", str(subject), "--open-illustrator"])

    assert result.exit_code == 0, result.output
    opened.assert_called_once_with(subject, app_name="Adobe Illustrator")
    assert str(tmp_path) not in result.output
    assert "Opened In Illustrator: yes" in result.output
