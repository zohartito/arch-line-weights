"""Rhino 8 Python helper: Export Selected Make2D with a small manifest.

Usage:
  ! _-RunPythonScript "/path/to/export_selected_make2d_manifest.py"

The script exports the currently selected Make2D curves and records enough
local evidence for the next arch-lw steps without embedding private drawing
data in the repository:
  - export_path
  - selected_object_count
  - layer_counts
  - orthographic view state
  - next command hint: arch-lw layout-jsx
"""

# ruff: noqa: UP032 - Rhino's script runtime rejects f-strings.

import json
import os

import Rhino
import rhinoscriptsyntax as rs
import scriptcontext as sc

try:
    INTEGER_TYPES = (int, long)
except NameError:
    INTEGER_TYPES = (int,)

try:
    STRING_TYPES = (basestring,)
except NameError:
    STRING_TYPES = (str,)

DEFAULT_EXPORT_NAME = "01-rhino-make2d-export.ai"
DEFAULT_ARTBOARD = "24x36in"
DEFAULT_MARGIN = "0.5in"


def _selected_objects():
    return rs.SelectedObjects(include_lights=False, include_grips=False) or []


def _layer_counts(object_ids):
    counts = {}
    for object_id in object_ids:
        layer = str(rs.ObjectLayer(object_id) or "<unknown>")
        counts[layer] = int(counts.get(layer, 0)) + 1
    return dict(sorted(counts.items()))


def _active_view_info():
    view = sc.doc.Views.ActiveView
    viewport = view.ActiveViewport if view else None
    return {
        "name": view.ActiveViewport.Name if view else "",
        "orthographic": bool(viewport and viewport.IsParallelProjection),
    }


def _model_units():
    try:
        return str(sc.doc.ModelUnitSystem)
    except Exception:
        return "unknown"


def _default_export_folder():
    if sc.doc.Path:
        return os.path.dirname(sc.doc.Path)
    return os.path.expanduser("~")


def _choose_export_path():
    folder = _default_export_folder()
    raw = rs.SaveFileName(
        "Export Selected Make2D for arch-lw",
        "Illustrator (*.ai)|*.ai|PDF (*.pdf)|*.pdf||",
        folder,
        DEFAULT_EXPORT_NAME,
        "ai",
    )
    if not raw:
        return None
    return raw


def _replace_suffix(path, suffix):
    root, _ext = os.path.splitext(str(path))
    return root + suffix


def _manifest_path_for(export_path):
    return _replace_suffix(export_path, ".manifest.json")


def _command_quote(path):
    return '"{}"'.format(str(path).replace('"', '\\"'))


def _json_safe(value):
    if isinstance(value, dict):
        return dict((str(key), _json_safe(item)) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, INTEGER_TYPES):
        return int(value)
    if isinstance(value, float):
        return float(value)
    if isinstance(value, STRING_TYPES):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        pass
    return str(value)


def _export_selected(export_path):
    folder = os.path.dirname(os.path.abspath(str(export_path)))
    if folder and not os.path.exists(folder):
        os.makedirs(folder)
    command = "_-Export {} _Enter".format(_command_quote(export_path))
    return bool(rs.Command(command, echo=True))


def _write_manifest(
    manifest_path,
    export_path,
    selected,
    export_ok,
):
    view = _active_view_info()
    export_exists = os.path.exists(str(export_path))
    export_size = int(os.path.getsize(str(export_path))) if export_exists else 0
    export_command_ok = bool(export_ok)
    effective_export_ok = export_command_ok and export_exists and export_size > 0
    warnings = []
    if export_command_ok and not export_exists:
        warnings.append("export file was not written")
    elif export_command_ok and export_size <= 0:
        warnings.append("export file is empty")
    elif not export_command_ok:
        warnings.append("Rhino export command did not report success")
    if not view["orthographic"]:
        warnings.append("active view is not orthographic; model scale may not be preserved")

    manifest = {
        "schema_version": 1,
        "summary": {
            "status": "passed" if effective_export_ok else "failed",
            "next_action": (
                "Run arch-lw layout-jsx on export_path."
                if effective_export_ok
                else "Review Rhino export output, then rerun Export Selected."
            ),
        },
        "command": "Export Selected",
        "manifest_path": str(manifest_path),
        "export_path": str(export_path),
        "export_command_ok": export_command_ok,
        "export_exists": export_exists,
        "export_size_bytes": export_size,
        "export_ok": effective_export_ok,
        "selected_object_count": len(selected),
        "layer_counts": _layer_counts(selected),
        "units": _model_units(),
        "view": view,
        "warnings": warnings,
        "next_step": (
            "arch-lw layout-jsx {path} --artboard {artboard} --fit fit "
            "--margin {margin} --report-json {report}"
        ).format(
            path=_command_quote(export_path),
            artboard=DEFAULT_ARTBOARD,
            margin=DEFAULT_MARGIN,
            report=_command_quote(_replace_suffix(export_path, ".layout-report.json")),
        ),
    }
    safe_manifest = _json_safe(manifest)
    with open(str(manifest_path), "w") as stream:
        stream.write(json.dumps(safe_manifest, indent=2, sort_keys=True) + "\n")
    return safe_manifest


def main():
    selected = _selected_objects()
    if not selected:
        Rhino.RhinoApp.WriteLine("[arch-lw] No selected objects; select Make2D inputs first.")
        return

    export_path = _choose_export_path()
    if export_path is None:
        Rhino.RhinoApp.WriteLine("[arch-lw] Export canceled.")
        return

    manifest_path = _manifest_path_for(export_path)
    Rhino.RhinoApp.WriteLine("[arch-lw] exporting selected objects: {}".format(export_path))
    export_ok = _export_selected(export_path)
    manifest = _write_manifest(
        manifest_path,
        export_path,
        selected,
        export_ok,
    )
    Rhino.RhinoApp.WriteLine("[arch-lw] wrote manifest: {}".format(manifest_path))
    Rhino.RhinoApp.WriteLine("[arch-lw] next: {}".format(manifest["next_step"]))
    if not export_ok:
        Rhino.RhinoApp.WriteLine("[arch-lw] export command did not report success; review Rhino output.")


if __name__ == "__main__":
    main()
