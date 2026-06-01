"""Tests for shared input-format sniffing diagnostics."""

import pytest

from arch_line_weights.input_format import (
    UnsupportedInputError,
    diagnostic_for_command,
    raise_if_unsupported,
    sniff_input,
)


def _write(path, data: bytes):
    path.write_bytes(data)
    return path


def _plain_pdf(path):
    import pikepdf

    pdf = pikepdf.new()
    pdf.add_blank_page(page_size=(72, 72))
    pdf.save(path)
    return path


def _illustrator_pdf(path, *, numblock: int | None):
    import pikepdf

    pdf = pikepdf.new()
    page = pdf.add_blank_page(page_size=(72, 72))
    priv = pikepdf.Dictionary()
    if numblock is not None:
        priv["/NumBlock"] = numblock
    page.obj["/PieceInfo"] = pikepdf.Dictionary({"/Illustrator": pikepdf.Dictionary({"/Private": priv})})
    pdf.save(path)
    return path


@pytest.mark.parametrize(
    ("filename", "data", "header_kind", "input_kind", "container_kind"),
    [
        ("header.pdf", b"%PDF-1.7\n", "pdf", "pdf", "pdf"),
        ("header.ai", b"%!PS-Adobe-3.0\n", "postscript", "postscript_ai", "postscript"),
        ("archive.pdf", b"PK\x03\x04hello", "zip", "zip", "zip"),
        ("empty.ai", b"", "empty", "empty", "empty"),
        ("unknown.ai", b"\x00\x01not-a-known-format", "unknown", "unknown", "unknown"),
    ],
)
def test_sniff_header_only_cases(tmp_path, filename, data, header_kind, input_kind, container_kind):
    diag = sniff_input(_write(tmp_path / filename, data))

    assert diag.header_kind == header_kind
    assert diag.input_kind == input_kind
    assert diag.container_kind == container_kind


def test_sniff_valid_sample_pdf_is_plain_pdf(tmp_path):
    diag = sniff_input(_plain_pdf(tmp_path / "sample.pdf"))

    assert diag.header_kind == "pdf"
    assert diag.input_kind == "plain_pdf"
    assert diag.container_kind == "pdf"
    assert diag.has_illustrator_pieceinfo is False
    assert diag.has_native_numblock is False
    assert diag.command_support["inspect"] is True
    assert diag.command_support["apply"] is True
    assert diag.command_support["apply-saas"] is False
    assert diag.is_no_op is None
    assert diag.has_drawings is None


def test_sniff_pdf_compatible_ai_with_pieceinfo_but_no_numblock(tmp_path):
    diag = sniff_input(_illustrator_pdf(tmp_path / "converted.ai", numblock=None))

    assert diag.header_kind == "pdf"
    assert diag.input_kind == "pdf_compatible_ai_without_native_payload"
    assert diag.container_kind == "pdf"
    assert diag.has_illustrator_pieceinfo is True
    assert diag.has_native_numblock is False
    assert diag.command_support["inspect"] is True
    assert diag.command_support["apply"] is True
    assert diag.command_support["apply-saas"] is False
    assert "no Illustrator native private payload" in diag.command_support_reasons["apply-saas"]


def test_sniff_native_ai_numblock_payload(tmp_path):
    diag = sniff_input(_illustrator_pdf(tmp_path / "native.ai", numblock=1))

    assert diag.header_kind == "pdf"
    assert diag.input_kind == "native_ai"
    assert diag.container_kind == "pdf"
    assert diag.has_illustrator_pieceinfo is True
    assert diag.has_native_numblock is True
    assert diag.command_support["inspect"] is True
    assert diag.command_support["apply"] is True
    assert diag.command_support["apply-saas"] is True
    assert diag.command_support["poche"] is True


def test_sniff_pdf_compatible_ai_without_pieceinfo(tmp_path):
    diag = sniff_input(_plain_pdf(tmp_path / "saved_as_ai.ai"))

    assert diag.header_kind == "pdf"
    assert diag.input_kind == "pdf_compatible_ai"
    assert diag.container_kind == "pdf"
    assert diag.has_illustrator_pieceinfo is False
    assert diag.has_native_numblock is False


def test_diagnostic_for_command_marks_postscript_ai_unsupported(tmp_path):
    diag = diagnostic_for_command(_write(tmp_path / "legacy.ai", b"%!PS-Adobe-3.0\n"), "inspect")

    assert diag.input_kind == "postscript_ai"
    assert diag.command_support["inspect"] is False
    assert diag.unsupported_reason == "Legacy PostScript .ai files are not supported."
    assert "Open in Illustrator and Save As a PDF-compatible .ai or .pdf" in diag.suggested_next_step


def test_zip_suffix_mismatch_is_detected_and_explained(tmp_path):
    diag = diagnostic_for_command(_write(tmp_path / "maybe.pdf", b"PK\x03\x04zip"), "inspect")

    assert diag.header_kind == "zip"
    assert diag.suffix == ".pdf"
    assert diag.suffix_mismatch is True
    assert diag.unsupported_reason == "File header is ZIP but suffix is .pdf."
    assert "Check that the selected file is a PDF-compatible .ai or .pdf" in diag.suggested_next_step


def test_empty_and_unknown_files_are_unsupported(tmp_path):
    empty = diagnostic_for_command(_write(tmp_path / "empty.pdf", b""), "apply")
    unknown = diagnostic_for_command(_write(tmp_path / "unknown.pdf", b"???"), "apply")

    assert empty.input_kind == "empty"
    assert empty.is_no_op is True
    assert empty.has_drawings is False
    assert empty.unsupported_reason == "File is empty."
    assert unknown.input_kind == "unknown"
    assert unknown.unsupported_reason == "File header is not recognized."


def test_raise_if_unsupported_carries_diagnostic(tmp_path):
    path = _write(tmp_path / "legacy.ai", b"%!PS-Adobe-3.0\n")

    with pytest.raises(UnsupportedInputError) as excinfo:
        raise_if_unsupported(path, "apply-saas")

    assert excinfo.value.diagnostic.path == str(path)
    assert "Legacy PostScript .ai files are not supported" in str(excinfo.value)
