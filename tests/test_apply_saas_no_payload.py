"""Tests for the no-native-payload (PDF-only / converted .ai) error path.

A "converted" Illustrator export (PDF-only, or an .ai produced by a tool that
didn't embed Illustrator's native private payload) carries a
``/PieceInfo /Illustrator /Private`` dictionary that is missing ``/NumBlock``
(and the ``/AIPrivateData<i>`` streams). The headless apply-saas pipeline needs
that native payload, so it must fail with a clean, user-facing error instead of
a raw ``KeyError('/NumBlock')`` traceback.
"""

from __future__ import annotations

import click
import pikepdf
import pytest
from click.testing import CliRunner

from arch_line_weights.apply_saas import apply_to_file
from arch_line_weights.cli import cli
from arch_line_weights.poche_saas import apply_saas_with_poche, write_synthetic_test_ai


def _make_converted_ai(path: str) -> None:
    """Write a converted/PDF-only .ai lacking the Illustrator native payload.

    The page has a ``/PieceInfo /Illustrator /Private`` dict (so it superficially
    looks Illustrator-touched) but no ``/NumBlock`` and no ``/AIPrivateData``
    streams — exactly the shape apply-saas cannot consume.
    """
    pdf = pikepdf.new()
    pdf.add_blank_page(page_size=(200, 200))
    page = pdf.pages[0]

    priv = pikepdf.Dictionary()  # deliberately no /NumBlock, no AIPrivateData
    illu = pikepdf.Dictionary()
    illu["/Private"] = priv
    pi = pikepdf.Dictionary()
    pi["/Illustrator"] = illu
    page.obj["/PieceInfo"] = pi

    pdf.save(str(path))
    pdf.close()


def test_apply_saas_no_numblock_raises_clean_error(tmp_path):
    src = tmp_path / "converted.ai"
    dst = tmp_path / "out.ai"
    _make_converted_ai(str(src))

    with pytest.raises(
        ValueError, match=r"native private payload \(no /NumBlock and no /AIPrivateData streams\)"
    ):
        apply_to_file(str(src), str(dst), {})


def test_apply_saas_no_numblock_points_to_alternative(tmp_path):
    src = tmp_path / "converted.ai"
    dst = tmp_path / "out.ai"
    _make_converted_ai(str(src))

    with pytest.raises(ValueError) as excinfo:
        apply_to_file(str(src), str(dst), {})

    message = str(excinfo.value)
    assert "apply-jsx" in message
    assert "poche" in message


def test_apply_saas_cli_no_numblock_raises_click_exception(tmp_path):
    src = tmp_path / "converted.ai"
    dst = tmp_path / "out.ai"
    mapping = tmp_path / "mapping.json"
    _make_converted_ai(str(src))
    mapping.write_text("{}")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["apply-saas", str(src), "-o", str(dst), "--mapping", str(mapping)],
        standalone_mode=False,
    )

    assert isinstance(result.exception, click.ClickException)
    message = str(result.exception)
    assert (
        "This .ai has no Illustrator native private payload (no /NumBlock and no /AIPrivateData streams)."
        in message
    )
    assert "apply-saas needs a native Illustrator .ai." in message
    assert "arch-lw apply-jsx then arch-lw poche" in message
    assert "KeyError" not in message
    assert "Traceback" not in result.output

    displayed = runner.invoke(
        cli,
        ["apply-saas", str(src), "-o", str(dst), "--mapping", str(mapping)],
    )
    assert displayed.exit_code == 1
    assert (
        "Error: This .ai has no Illustrator native private payload (no /NumBlock and no /AIPrivateData streams)."
        in displayed.output
    )
    assert "arch-lw apply-jsx then arch-lw poche" in displayed.output
    assert "KeyError" not in displayed.output
    assert "Traceback" not in displayed.output


def test_apply_saas_poche_no_numblock_raises_clean_error(tmp_path):
    src = tmp_path / "converted.ai"
    dst = tmp_path / "out.ai"
    _make_converted_ai(str(src))

    with pytest.raises(
        ValueError, match=r"native private payload \(no /NumBlock and no /AIPrivateData streams\)"
    ):
        apply_saas_with_poche(str(src), str(dst), {})


def test_apply_saas_no_numblock_error_explains_cause_and_fix(tmp_path):
    """The error must now say what /NumBlock is, why it's missing, and how to fix it.

    Pins the expanded, actionable diagnostic so the previous terse message
    (which named /NumBlock but explained neither cause nor remediation) cannot
    silently return.
    """
    src = tmp_path / "converted.ai"
    dst = tmp_path / "out.ai"
    mapping = tmp_path / "mapping.json"
    _make_converted_ai(str(src))
    mapping.write_text("{}")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["apply-saas", str(src), "-o", str(dst), "--mapping", str(mapping)],
        standalone_mode=False,
    )
    message = str(result.exception)

    # What /NumBlock is (Illustrator-native block layout).
    assert "native private data" in message
    assert "how many blocks" in message
    # Why it's missing (not saved by Illustrator; Rhino/PDF export).
    assert "not saved by Illustrator" in message
    assert "Rhino/Make2D" in message
    # Concrete remediation: Save As .ai, or the PDF-stream apply path.
    assert "Save As Adobe Illustrator (.ai)" in message
    assert "arch-lw apply" in message


def test_apply_saas_aiprivate_without_numblock_runs(tmp_path):
    """Real converted Make2D Save As: zstd /AIPrivateData1 exists, /NumBlock does not."""
    src = tmp_path / "saved-as-converted.ai"
    dst = tmp_path / "out.ai"
    write_synthetic_test_ai(str(src))
    with pikepdf.open(src, allow_overwriting_input=True) as pdf:
        priv = pdf.pages[0].obj["/PieceInfo"]["/Illustrator"]["/Private"]
        del priv["/NumBlock"]
        pdf.save(str(src))

    result = apply_to_file(str(src), str(dst), {(0, 0, 0): 0.5})
    assert dst.is_file()
    assert result.widths_rewritten >= 1
    with pikepdf.open(dst) as pdf:
        priv = pdf.pages[0].obj["/PieceInfo"]["/Illustrator"]["/Private"]
        assert "/AIPrivateData1" in priv


def test_apply_saas_poche_aiprivate_without_numblock_runs(tmp_path):
    """The poché writer takes the same inferred block count as apply-saas."""
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent))
    from doctor_fixtures import SQUARE, write_ai

    src = write_ai(
        tmp_path / "saved-as-converted.ai", [("S::Visible::ClippingPlaneIntersections::SLAB", SQUARE)]
    )
    dst = tmp_path / "out.ai"
    with pikepdf.open(src, allow_overwriting_input=True) as pdf:
        del pdf.pages[0].obj["/PieceInfo"]["/Illustrator"]["/Private"]["/NumBlock"]
        pdf.save(str(src))

    apply_result, poche_result, _report = apply_saas_with_poche(str(src), str(dst), {(0, 0, 0): 0.5})
    assert apply_result.chunks_in >= 1
    assert poche_result.polygons_injected == 1
    with pikepdf.open(dst) as pdf:
        assert int(pdf.pages[0].obj["/PieceInfo"]["/Illustrator"]["/Private"]["/NumBlock"]) >= 1


def test_inferred_block_count_still_respects_stream_limit(tmp_path, monkeypatch):
    """Counting /AIPrivateData streams must not bypass the hardened stream cap."""
    from arch_line_weights import apply_saas

    monkeypatch.setattr(apply_saas, "MAX_NATIVE_STREAMS", 2)
    pdf = pikepdf.new()
    pdf.add_blank_page(page_size=(72, 72))
    priv = pikepdf.Dictionary()
    for index in range(1, 6):
        priv[f"/AIPrivateData{index}"] = pdf.make_stream(b"%AI24_ZStandard_Data")
    pdf.pages[0].obj["/PieceInfo"] = pikepdf.Dictionary(
        {"/Illustrator": pikepdf.Dictionary({"/Private": priv})}
    )

    assert apply_saas._native_block_count(priv) == 3  # stops one past the cap
    with pytest.raises(ValueError, match="safe limit"):
        apply_saas._read_payload(pdf)


def _private_dict_pdf(stream_indices, numblock=None):
    pdf = pikepdf.new()
    pdf.add_blank_page(page_size=(72, 72))
    priv = pikepdf.Dictionary()
    if numblock is not None:
        priv["/NumBlock"] = numblock
    for index in stream_indices:
        priv[f"/AIPrivateData{index}"] = pdf.make_stream(b"%AI24_ZStandard_Data")
    pdf.pages[0].obj["/PieceInfo"] = pikepdf.Dictionary(
        {"/Illustrator": pikepdf.Dictionary({"/Private": priv})}
    )
    return pdf, priv


@pytest.mark.parametrize("numblock", [0, -1, pikepdf.String("two")])
def test_unusable_numblock_falls_back_to_counting_streams(numblock):
    from arch_line_weights.apply_saas import _native_block_count

    _pdf, priv = _private_dict_pdf([1, 2], numblock=numblock)
    assert _native_block_count(priv) == 2


def test_gap_in_stream_numbering_is_refused_not_truncated():
    """/AIPrivateData1 and 3 without 2: reading only block 1 would drop the rest."""
    from arch_line_weights.apply_saas import _native_block_count, _read_payload

    pdf, priv = _private_dict_pdf([1, 3])
    with pytest.raises(ValueError, match="without gaps"):
        _native_block_count(priv)
    with pytest.raises(ValueError, match="without gaps"):
        _read_payload(pdf)


@pytest.mark.parametrize(
    "first_size,second_size",
    [(200_000, 10), (10, 200_000)],
    ids=["shrink", "grow"],
)
def test_write_payload_round_trips_after_inferring_the_count(first_size, second_size):
    """Rewriting a payload whose count was inferred replaces every old block."""
    import os

    from arch_line_weights.apply_saas import CHUNK, _read_payload, _write_payload

    pdf, priv = _private_dict_pdf([])
    _write_payload(pdf, b"%!PS" + os.urandom(first_size))
    del priv["/NumBlock"]  # the converted Save As shape
    old_blocks = sum(1 for key in priv if str(key).startswith("/AIPrivateData"))

    second = b"%!PS" + os.urandom(second_size)
    old_n, new_n = _write_payload(pdf, second)

    assert old_n == old_blocks
    assert int(priv["/NumBlock"]) == new_n
    blocks = sorted(
        int(str(key).removeprefix("/AIPrivateData")) for key in priv if "AIPrivateData" in str(key)
    )
    assert blocks == list(range(1, new_n + 1))
    assert (new_n > 1) == (second_size > CHUNK)
    assert _read_payload(pdf) == second


def test_require_native_private_message_is_expanded(tmp_path):
    """The defensive apply-saas payload guard carries the same expanded message."""
    from arch_line_weights.apply_saas import _NO_NATIVE_PAYLOAD_MSG

    # Still names the block-count marker for grep/back-compat...
    assert (
        "This .ai has no Illustrator native private payload (no /NumBlock and no /AIPrivateData streams)."
        in _NO_NATIVE_PAYLOAD_MSG
    )
    assert "apply-saas needs a native Illustrator .ai." in _NO_NATIVE_PAYLOAD_MSG
    # ...but now also explains cause and remediation.
    assert "not saved by Illustrator" in _NO_NATIVE_PAYLOAD_MSG
    assert "Save As Adobe Illustrator (.ai)" in _NO_NATIVE_PAYLOAD_MSG
    assert "rewrite the PDF stream directly with arch-lw apply" in _NO_NATIVE_PAYLOAD_MSG
    assert "arch-lw apply-jsx then arch-lw poche" in _NO_NATIVE_PAYLOAD_MSG
