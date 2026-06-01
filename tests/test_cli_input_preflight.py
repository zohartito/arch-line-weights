from __future__ import annotations

import json

from click.testing import CliRunner

from arch_line_weights.cli import cli


def _blank_pdf(path) -> None:
    import pikepdf

    pdf = pikepdf.new()
    pdf.add_blank_page(page_size=(72, 72))
    pdf.save(path)
    pdf.close()


def _empty_native_ai(path) -> None:
    import pikepdf

    pdf = pikepdf.new()
    pdf.add_blank_page(page_size=(72, 72))
    page = pdf.pages[0]
    page.obj["/PieceInfo"] = pikepdf.Dictionary(
        {"/Illustrator": pikepdf.Dictionary({"/Private": pikepdf.Dictionary({"/NumBlock": 0})})}
    )
    pdf.save(path)
    pdf.close()


def test_inspect_postscript_ai_returns_machine_readable_diagnostic(tmp_path):
    src = tmp_path / "legacy.ai"
    src.write_bytes(b"%!PS-Adobe-3.0\n%%Title: Rhino legacy AI\n")

    result = CliRunner().invoke(cli, ["inspect", str(src), "--no-pretty"])

    assert result.exit_code == 1
    data = json.loads(result.stdout)
    assert data["input_format"]["header_kind"] == "postscript"
    assert data["input_format"]["input_kind"] == "postscript_ai"
    assert data["input_format"]["supported_commands"]["inspect"] is False
    assert "Illustrator" in data["input_format"]["suggested_next_step"]
    assert "Traceback" not in result.output


def test_apply_postscript_ai_fails_before_parser_traceback(tmp_path):
    src = tmp_path / "legacy.ai"
    dst = tmp_path / "out.ai"
    src.write_bytes(b"%!PS-Adobe-3.0\n%%Title: Rhino legacy AI\n")

    result = CliRunner().invoke(
        cli,
        ["apply", str(src), "--auto", "-o", str(dst)],
    )

    assert result.exit_code == 1
    assert not dst.exists()
    assert "legacy postscript .ai" in result.output.lower()
    assert "Illustrator" in result.output
    assert "Traceback" not in result.output


def test_inspect_zip_header_mismatch_reports_unsupported_input(tmp_path):
    src = tmp_path / "mislabeled.pdf"
    src.write_bytes(b"PK\x03\x04fake zip payload")

    result = CliRunner().invoke(cli, ["inspect", str(src), "--no-pretty"])

    assert result.exit_code == 1
    data = json.loads(result.stdout)
    assert data["input_format"]["header_kind"] == "zip"
    assert data["input_format"]["input_kind"] == "zip"
    assert data["input_format"]["suffix_mismatch"] is True
    assert data["input_format"]["supported_commands"]["inspect"] is False
    assert "zip" in data["input_format"]["unsupported_reason"].lower()


def test_inspect_blank_plain_pdf_reports_non_drawing_diagnostic(tmp_path):
    src = tmp_path / "reference.pdf"
    _blank_pdf(src)

    result = CliRunner().invoke(cli, ["inspect", str(src), "--no-pretty"])

    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert data["total_drawings"] == 0
    assert data["input_format"]["input_kind"] == "plain_pdf"
    assert data["input_format"]["has_drawings"] is False
    assert data["input_format"]["is_no_op"] is True
    assert "non-drawing" in data["input_format"]["no_drawing_reason"]


def test_inspect_empty_layer_aware_ai_has_different_empty_export_message(tmp_path):
    src = tmp_path / "empty_export.ai"
    _empty_native_ai(src)

    result = CliRunner().invoke(cli, ["inspect", str(src), "--no-pretty"])

    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert data["input_format"]["input_kind"] == "native_ai"
    assert data["input_format"]["has_drawings"] is False
    assert "empty drawing export" in data["input_format"]["no_drawing_reason"]
    assert "non-drawing" not in data["input_format"]["no_drawing_reason"]


def test_apply_blank_pdf_with_mapping_fails_before_noop_output(tmp_path):
    src = tmp_path / "reference.pdf"
    dst = tmp_path / "out.pdf"
    mapping = tmp_path / "mapping.json"
    _blank_pdf(src)
    mapping.write_text('{"RGB(0,0,0)": 1.0}')

    result = CliRunner().invoke(
        cli,
        ["apply", str(src), "--mapping", str(mapping), "-o", str(dst)],
    )

    assert result.exit_code != 0
    assert not dst.exists()
    assert "no rewriteable stroke geometry" in result.output
    assert "Nothing was written" in result.output
