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


@pytest.mark.parametrize("transition", [b"0.5 G", b"0 0 0 1 K", b"/DeviceGray CS 0.5 SC", b"/Pattern CS /P1 SCN"])
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
