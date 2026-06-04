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
from arch_line_weights.poche_saas import apply_saas_with_poche


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

    with pytest.raises(ValueError, match=r"native private payload \(/NumBlock\)"):
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
    assert "This .ai has no Illustrator native private payload (/NumBlock)." in message
    assert "apply-saas needs a native Illustrator .ai." in message
    assert "arch-lw apply-jsx then arch-lw poche" in message
    assert "KeyError" not in message
    assert "Traceback" not in result.output

    displayed = runner.invoke(
        cli,
        ["apply-saas", str(src), "-o", str(dst), "--mapping", str(mapping)],
    )
    assert displayed.exit_code == 1
    assert "Error: This .ai has no Illustrator native private payload (/NumBlock)." in displayed.output
    assert "arch-lw apply-jsx then arch-lw poche" in displayed.output
    assert "KeyError" not in displayed.output
    assert "Traceback" not in displayed.output


def test_apply_saas_poche_no_numblock_raises_clean_error(tmp_path):
    src = tmp_path / "converted.ai"
    dst = tmp_path / "out.ai"
    _make_converted_ai(str(src))

    with pytest.raises(ValueError, match=r"native private payload \(/NumBlock\)"):
        apply_saas_with_poche(str(src), str(dst), {})
