"""Exercise spike reporting with in-memory pixels, without PDF rendering."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

SPEC = importlib.util.spec_from_file_location(
    "spike_pdfium_preview", Path(__file__).resolve().parents[1] / "scripts" / "spike_pdfium_preview.py"
)
spike = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(spike)


@pytest.mark.parametrize("pdfium_size", [(3, 5), (4, 4)])
def test_main_writes_results_with_or_without_size_mismatch(tmp_path, monkeypatch, capsys, pdfium_size):
    monkeypatch.setitem(sys.modules, "pypdfium2", SimpleNamespace())
    monkeypatch.setattr(spike, "version", lambda name: "test")
    monkeypatch.setattr(spike, "write_control", lambda path: None)
    monkeypatch.setattr(
        spike,
        "PyMuPDFRenderer",
        lambda: SimpleNamespace(render_page=lambda *args: Image.new("RGB", (4, 4), "black")),
    )
    monkeypatch.setattr(spike, "pdfium_render", lambda *args: Image.new("RGB", pdfium_size, "black"))
    monkeypatch.setattr(sys, "argv", ["spike_pdfium_preview.py", "--runs", "1", "--out-dir", str(tmp_path)])
    if pdfium_size != (4, 4):

        def unexpected_diff(*args):
            pytest.fail("Pixel diff must be skipped when dimensions differ")

        monkeypatch.setattr(spike.ImageChops, "difference", unexpected_diff)
        for label in ("fixture", "control"):
            (tmp_path / label).mkdir()
            (tmp_path / label / "difference.png").write_bytes(b"stale")

    assert spike.main() == 0
    reports = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))
    assert reports == json.loads(capsys.readouterr().out)
    assert len(reports) == 2
    for label, report in zip(("fixture", "control"), reports, strict=True):
        assert report["renderer_sizes_px"] == {"pymupdf": [4, 4], "pypdfium2": list(pdfium_size)}
        if pdfium_size != (4, 4):
            assert "dimensions differ" in report["pixel_diff_skipped"]
            assert report["size_px"] is None
            assert report["mean_absolute_channel_difference"] is None
            assert report["pixels_differing_over_12_percent"] is None
            assert not (tmp_path / label / "difference.png").exists()
        else:
            assert report["pixel_diff_skipped"] is None
            assert report["size_px"] == [4, 4]
            assert report["mean_absolute_channel_difference"] == 0
            assert report["pixels_differing_over_12_percent"] == 0
            assert (tmp_path / label / "difference.png").is_file()
        for name, size in report["renderer_sizes_px"].items():
            with Image.open(tmp_path / label / f"{name}.png") as image:
                assert list(image.size) == size
        with Image.open(tmp_path / label / "comparison.png") as image:
            assert image.size == (4 + pdfium_size[0], max(4, pdfium_size[1]) + 28)
