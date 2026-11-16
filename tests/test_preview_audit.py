"""Offline preview command and renderer-discovery regressions."""

import pytest
from click.testing import CliRunner
from PIL import Image

from arch_line_weights.cli import cli
from arch_line_weights.preview import GhostscriptRenderer


@pytest.mark.parametrize("mode", ["side-by-side", "diff", "tier-overlay"])
def test_alw05_preview_modes_write_png(tmp_path, mode):
    dst = tmp_path / "preview.png"
    result = CliRunner().invoke(cli, ["preview", "examples/demo-section.pdf",
        "examples/demo-section HIERARCHY.pdf", "--mode", mode, "--dpi", "72", "-o", str(dst)])
    assert result.exit_code == 0, repr(result.exception)
    with Image.open(dst) as image:
        assert image.format == "PNG"
        assert image.width > 0 and image.height > 0


def test_alw06_discovers_windows_ghostscript(monkeypatch):
    monkeypatch.setattr("arch_line_weights.preview.shutil.which",
                        lambda name: "C:/GS/gswin64c.exe" if name == "gswin64c" else None)
    assert GhostscriptRenderer().binary == "C:/GS/gswin64c.exe"
