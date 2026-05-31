from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest


def test_export_selected_make2d_manifest_script_has_manifest_contract():
    script = Path("integrations/rhino/export_selected_make2d_manifest.py")
    text = script.read_text()

    compile(text, str(script), "exec")
    assert "from __future__ import annotations" not in text
    assert "from pathlib import Path" not in text
    assert " -> " not in text
    assert " | None" not in text
    assert 'f"' not in text
    assert "f'" not in text
    assert "Export Selected" in text
    assert "manifest_path" in text
    assert "selected_object_count" in text
    assert "layer_counts" in text
    assert "orthographic" in text
    assert "export_path" in text
    assert "_-Export" in text
    assert "rs.Command" in text
    assert "arch-lw layout-jsx" in text


@pytest.fixture
def rhino_export_script(monkeypatch):
    viewport = types.SimpleNamespace(Name="Top", IsParallelProjection=True)
    view = types.SimpleNamespace(ActiveViewport=viewport)
    views = types.SimpleNamespace(ActiveView=view)
    doc = types.SimpleNamespace(
        Path="",
        Views=views,
        ModelUnitSystem="Inches",
    )
    rs = types.SimpleNamespace(ObjectLayer=lambda object_id: f"Layer {object_id}")
    monkeypatch.setitem(sys.modules, "Rhino", types.SimpleNamespace())
    monkeypatch.setitem(sys.modules, "rhinoscriptsyntax", rs)
    monkeypatch.setitem(sys.modules, "scriptcontext", types.SimpleNamespace(doc=doc))

    path = Path("integrations/rhino/export_selected_make2d_manifest.py")
    spec = importlib.util.spec_from_file_location("rhino_export_selected_make2d_manifest_test", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_export_manifest_marks_missing_export_as_failed(tmp_path, rhino_export_script):
    export_path = tmp_path / "missing.ai"
    manifest_path = tmp_path / "missing.manifest.json"

    manifest = rhino_export_script._write_manifest(
        manifest_path=manifest_path,
        export_path=export_path,
        selected=[1, 2],
        export_ok=True,
    )

    assert manifest["summary"]["status"] == "failed"
    assert manifest["export_command_ok"] is True
    assert manifest["export_ok"] is False
    assert manifest["export_exists"] is False
    assert manifest["export_size_bytes"] == 0
    assert manifest["manifest_path"] == str(manifest_path)
    assert "export file was not written" in manifest["warnings"]


def test_export_manifest_records_written_export_size(tmp_path, rhino_export_script):
    export_path = tmp_path / "written.ai"
    export_path.write_bytes(b"%PDF-1.6\n")
    manifest_path = tmp_path / "written.manifest.json"

    manifest = rhino_export_script._write_manifest(
        manifest_path=manifest_path,
        export_path=export_path,
        selected=[1],
        export_ok=True,
    )

    assert manifest["summary"]["status"] == "passed"
    assert manifest["export_command_ok"] is True
    assert manifest["export_ok"] is True
    assert manifest["export_exists"] is True
    assert manifest["export_size_bytes"] == len(b"%PDF-1.6\n")
    assert manifest["manifest_path"] == str(manifest_path)


def test_json_safe_normalizes_non_standard_values(rhino_export_script):
    class OddValue:
        def __str__(self):
            return "odd"

    data = rhino_export_script._json_safe(
        {
            123: OddValue(),
            "nested": [OddValue(), {"x": 2}],
        }
    )

    assert data == {
        "123": "odd",
        "nested": ["odd", {"x": 2}],
    }


def test_json_safe_coerces_rhino_long_like_values_to_int(rhino_export_script):
    class RhinoLongLike:
        def __int__(self):
            return 78819

        def __str__(self):
            return "78819L"

    data = rhino_export_script._json_safe(
        {
            "selected_object_count": RhinoLongLike(),
            "nested": {"layer_count": RhinoLongLike()},
        }
    )

    assert data == {
        "selected_object_count": 78819,
        "nested": {"layer_count": 78819},
    }
