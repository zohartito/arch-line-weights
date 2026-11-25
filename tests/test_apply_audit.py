"""Synthetic PDF regression cases for the public audit (no desktop apps)."""

import pikepdf
import pytest

from arch_line_weights.apply import apply_to_file


def write_pdf(path, content):
    with pikepdf.new() as pdf:
        page = pdf.add_blank_page(page_size=(200, 200))
        page.Contents = pdf.make_stream(content)
        pdf.save(path)


def widths(path):
    with pikepdf.open(path) as pdf:
        return [float(args[0]) for args, op in pikepdf.parse_content_stream(pdf.pages[0]) if str(op) == "w"]


@pytest.mark.parametrize(
    "transition", [b"0.5 G", b"0 0 0 1 K", b"/DeviceGray CS 0.5 SC", b"/Pattern CS /P1 SCN"]
)
def test_alw03_restores_rgb_and_resets_on_color_space_change(tmp_path, transition):
    src, dst = tmp_path / "state.pdf", tmp_path / "out.pdf"
    stroke = b"0 0 m 50 0 l S "
    write_pdf(src, b"1 0 0 RG q 0 0 1 RG " + stroke + b"Q " + stroke + transition + b" " + stroke)
    apply_to_file(str(src), str(dst), {(255, 0, 0): 2.0, (0, 0, 255): 0.2})
    assert widths(dst) == [0.2, 2.0, 0.25]


def test_alw03_device_rgb_sc_and_nested_state(tmp_path):
    src, dst = tmp_path / "state.pdf", tmp_path / "out.pdf"
    stroke = b"0 0 m 50 0 l S "
    write_pdf(src, b"/DeviceRGB CS 1 0 0 SC q 0 G q 0 0 1 RG " + stroke + b"Q " + stroke + b"Q " + stroke)
    apply_to_file(str(src), str(dst), {(255, 0, 0): 2.0, (0, 0, 255): 0.2})
    assert widths(dst) == [0.2, 0.25, 2.0]


def test_alw04_rejects_form_xobjects_without_touching_output(tmp_path):
    src, dst = tmp_path / "form.pdf", tmp_path / "out.pdf"
    with pikepdf.new() as pdf:
        page = pdf.add_blank_page(page_size=(200, 200))
        form = pdf.make_stream(b"1 0 0 RG 0 0 m 50 0 l S 0 0 1 RG 0 10 m 50 10 l S")
        form.Type = pikepdf.Name.XObject
        form.Subtype = pikepdf.Name.Form
        form.BBox = [0, 0, 200, 200]
        page.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(Fm0=form))
        page.Contents = pdf.make_stream(b"3 w /Fm0 Do")
        pdf.save(src)
    original = src.read_bytes()
    dst.write_bytes(b"previous output")
    with pytest.raises(ValueError, match="Form XObject"):
        apply_to_file(str(src), str(dst), {(255, 0, 0): 2.0})
    assert src.read_bytes() == original
    assert dst.read_bytes() == b"previous output"


@pytest.mark.parametrize("value", ["-2", "nan", "inf", "0", "101"])
@pytest.mark.parametrize("command", ["apply", "apply-saas"])
def test_alw15_rejects_invalid_default_width_before_writing(tmp_path, command, value):
    from click.testing import CliRunner
    from test_cleanup import _single_layer_payload, _write_native_ai

    from arch_line_weights.cli import cli

    src, dst, mapping = tmp_path / "source.ai", tmp_path / "out.ai", tmp_path / "map.json"
    _write_native_ai(src, _single_layer_payload())
    with pikepdf.open(src, allow_overwriting_input=True) as pdf:
        pdf.pages[0].Contents = pdf.make_stream(b"0 0 1 RG 0 0 m 50 0 l S")
        pdf.save(src)
    mapping.write_text('{"RGB(255,0,0)": 1}')
    result = CliRunner().invoke(
        cli, [command, str(src), "--mapping", str(mapping), "--default-width", value, "-o", str(dst)]
    )
    assert result.exit_code == 2
    assert "finite" in result.output
    assert not dst.exists()
