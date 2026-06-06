"""Regression: legacy PostScript ``.ai`` files must produce an actionable,
format-correct error instead of the old generic "damaged file / save a smaller
copy" hint.

This is the #1 failure class in the realness pass: 12 of 21 real Rhino/USC
drawings are legacy-PostScript ``.ai`` exports (see
strategy-lab/VALIDATION_MATRIX.md). pikepdf and PyMuPDF are both PDF-only, so
the real fix is to re-save the file PDF-compatible — which is exactly what the
working ``[Converted].ai`` versions are.
"""

import pytest

from arch_line_weights.inspect import _is_legacy_postscript, inspect_file


def test_detects_legacy_postscript_header(tmp_path):
    ps = tmp_path / "legacy.ai"
    ps.write_bytes(b"%!PS-Adobe-3.0\n% legacy illustrator export\n")
    assert _is_legacy_postscript(str(ps)) is True


def test_pdf_header_is_not_legacy_postscript(tmp_path):
    pdf = tmp_path / "modern.ai"
    pdf.write_bytes(b"%PDF-1.5\n% pdf-compatible illustrator export\n")
    assert _is_legacy_postscript(str(pdf)) is False


def test_inspect_legacy_postscript_raises_actionable_error(tmp_path):
    ps = tmp_path / "WALL SECTION.ai"
    # Minimal legacy PostScript header: enough that both PDF readers fail and
    # the format sniffer fires.
    ps.write_bytes(b"%!PS-Adobe-3.0 EPSF-3.0\n%%BoundingBox: 0 0 100 100\n")
    with pytest.raises(RuntimeError) as exc:
        inspect_file(str(ps))
    msg = str(exc.value)
    assert "legacy PostScript" in msg  # names the real cause
    assert "PDF Compatible" in msg  # points at the actual fix
    assert "smaller copy" not in msg  # not the misleading old hint
