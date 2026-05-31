from __future__ import annotations

from pathlib import Path


def test_export_selected_make2d_manifest_script_has_manifest_contract():
    script = Path("integrations/rhino/export_selected_make2d_manifest.py")
    text = script.read_text()

    compile(text, str(script), "exec")
    assert "Export Selected" in text
    assert "manifest_path" in text
    assert "selected_object_count" in text
    assert "layer_counts" in text
    assert "orthographic" in text
    assert "arch-lw layout-jsx" in text
