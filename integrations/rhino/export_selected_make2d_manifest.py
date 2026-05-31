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

from __future__ import annotations

import json
from pathlib import Path

import Rhino
import rhinoscriptsyntax as rs
import scriptcontext as sc

DEFAULT_EXPORT_NAME = "01-rhino-make2d-export.ai"
DEFAULT_ARTBOARD = "24x36in"
DEFAULT_MARGIN = "0.5in"


def _selected_objects():
    return rs.SelectedObjects(include_lights=False, include_grips=False) or []


def _layer_counts(object_ids):
    counts = {}
    for object_id in object_ids:
        layer = rs.ObjectLayer(object_id) or "<unknown>"
        counts[layer] = counts.get(layer, 0) + 1
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


def _default_export_folder() -> Path:
    if sc.doc.Path:
        return Path(sc.doc.Path).parent
    return Path.home()


def _choose_export_path() -> Path | None:
    folder = str(_default_export_folder())
    raw = rs.SaveFileName(
        "Export Selected Make2D for arch-lw",
        "Illustrator (*.ai)|*.ai|PDF (*.pdf)|*.pdf||",
        folder,
        DEFAULT_EXPORT_NAME,
        "ai",
    )
    if not raw:
        return None
    return Path(raw)


def _manifest_path_for(export_path: Path) -> Path:
    return export_path.with_suffix(".manifest.json")


def _command_quote(path: Path) -> str:
    return '"{}"'.format(str(path).replace('"', '\\"'))


def _export_selected(export_path: Path) -> bool:
    export_path.parent.mkdir(parents=True, exist_ok=True)
    command = f"_-Export {_command_quote(export_path)} _Enter"
    return bool(rs.Command(command, echo=True))


def _write_manifest(
    *,
    manifest_path: Path,
    export_path: Path,
    selected,
    export_ok: bool,
) -> dict:
    view = _active_view_info()
    export_exists = export_path.exists()
    export_size = export_path.stat().st_size if export_exists else 0
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
            report=_command_quote(export_path.with_suffix(".layout-report.json")),
        ),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


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
    Rhino.RhinoApp.WriteLine(f"[arch-lw] exporting selected objects: {export_path}")
    export_ok = _export_selected(export_path)
    manifest = _write_manifest(
        manifest_path=manifest_path,
        export_path=export_path,
        selected=selected,
        export_ok=export_ok,
    )
    Rhino.RhinoApp.WriteLine(f"[arch-lw] wrote manifest: {manifest_path}")
    Rhino.RhinoApp.WriteLine(f"[arch-lw] next: {manifest['next_step']}")
    if not export_ok:
        Rhino.RhinoApp.WriteLine("[arch-lw] export command did not report success; review Rhino output.")


if __name__ == "__main__":
    main()
