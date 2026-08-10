"""`arch-lw inspect` must surface whether Illustrator's native /NumBlock payload
is present, so users know before running whether the headless ``apply-saas``
path is available for a given file.

The signal already exists in the JSON as ``input_format.has_native_numblock``;
these tests pin both that field and the new human-readable ``# numblock:`` line
printed to stderr.
"""

from __future__ import annotations

import json

import pikepdf
from click.testing import CliRunner

from arch_line_weights.cli import cli


def _make_converted_ai(path: str) -> None:
    """A converted/PDF-only .ai: has /PieceInfo but no /NumBlock."""
    pdf = pikepdf.new()
    pdf.add_blank_page(page_size=(200, 200))
    page = pdf.pages[0]
    priv = pikepdf.Dictionary()  # no /NumBlock
    illu = pikepdf.Dictionary({"/Private": priv})
    page.obj["/PieceInfo"] = pikepdf.Dictionary({"/Illustrator": illu})
    pdf.save(str(path))
    pdf.close()


def _make_native_ai(path: str) -> None:
    """A native-looking .ai: /PieceInfo /Illustrator /Private with /NumBlock."""
    pdf = pikepdf.new()
    pdf.add_blank_page(page_size=(200, 200))
    page = pdf.pages[0]
    priv = pikepdf.Dictionary({"/NumBlock": 1})
    illu = pikepdf.Dictionary({"/Private": priv})
    page.obj["/PieceInfo"] = pikepdf.Dictionary({"/Illustrator": illu})
    pdf.save(str(path))
    pdf.close()


def test_inspect_reports_numblock_absent(tmp_path):
    src = tmp_path / "converted.ai"
    _make_converted_ai(str(src))

    result = CliRunner().invoke(cli, ["inspect", str(src)])
    assert result.exit_code == 0, result.output

    report = json.loads(result.stdout)
    assert report["input_format"]["has_native_numblock"] is False

    assert "# numblock: absent" in result.stderr
    assert "apply-saas unavailable" in result.stderr


def test_inspect_reports_numblock_present(tmp_path):
    src = tmp_path / "native.ai"
    _make_native_ai(str(src))

    result = CliRunner().invoke(cli, ["inspect", str(src)])
    assert result.exit_code == 0, result.output

    report = json.loads(result.stdout)
    assert report["input_format"]["has_native_numblock"] is True

    assert "# numblock: present" in result.stderr
    assert "apply-saas supported" in result.stderr
