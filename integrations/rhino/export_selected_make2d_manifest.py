"""Rhino 8 Python helper: Export Selected Make2D with a small manifest.

Usage:
  ! _-RunPythonScript "/path/to/export_selected_make2d_manifest.py"

The script records enough local evidence for the next arch-lw steps without
embedding private drawing data in the repository:
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


def _default_manifest_path() -> Path:
    doc_path = Path(sc.doc.Path) if sc.doc.Path else Path.home() / "rhino-make2d"
    stem = doc_path.stem if doc_path.suffix else doc_path.name
    return doc_path.with_name(f"{stem}-make2d-manifest.json")


def main():
    selected = _selected_objects()
    if not selected:
        Rhino.RhinoApp.WriteLine("[arch-lw] No selected objects; select Make2D inputs first.")
        return

    manifest_path = _default_manifest_path()
    manifest = {
        "schema_version": 1,
        "command": "Export Selected",
        "selected_object_count": len(selected),
        "layer_counts": _layer_counts(selected),
        "view": _active_view_info(),
        "next_step": "arch-lw layout-jsx <exported.ai> --artboard 24x36in --fit fit",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    Rhino.RhinoApp.WriteLine("[arch-lw] wrote manifest: {}".format(manifest_path))


if __name__ == "__main__":
    main()
