"""Detect 'no role signal' input (spec doc 49 Part 2, item 5).

arch-lw assigns weights from a *role signal*: distinct stroke colors (a color
per role) or named layers (Rhino ``::``-layers, or AIA NCS ``A-WALL-FULL`` /
``-MCUT`` / ``-OTLN`` / ``-PATT`` / ``-NPLT``). A file with none of that —
0 strokes, a single stroke color, or no usable layers — has nothing to build a
hierarchy from. v1 must say so loudly (and exit non-zero) instead of silently
passing the drawing through at the lightest weight (the "stairs were a silent
no-op" bug).

Pure functions only, so the CLI stays a thin caller and the predicate is unit
testable without invoking Click.
"""

from __future__ import annotations

from .inspect import InspectionReport
from .layer_classify import Source


def no_role_signal(report: InspectionReport, source_conf: float) -> bool:
    """True when ``report`` carries no usable role signal.

    Fires when there are zero stroked paths, or when there is at most one
    distinct stroke color AND no confident layer signal (``source_conf > 0`` with
    at least one layer name). A single stroke color that coexists with confident
    named layers is NOT flagged — the layers carry the hierarchy.
    """
    if report.total_stroked == 0:
        return True
    has_layer_signal = source_conf > 0.0 and len(report.layer_names) > 0
    return len(report.stroke_colors) <= 1 and not has_layer_signal


def no_role_signal_message(
    report: InspectionReport,
    resolved_source: Source,
    source_conf: float,
    *,
    name: str,
) -> str:
    """Actionable, multi-line explanation of the missing role signal."""
    n_colors = len(report.stroke_colors)
    n_layers = len(report.layer_names)
    src = resolved_source.value if isinstance(resolved_source, Source) else str(resolved_source)
    return (
        f"no strokes / no role signal found in {name!r}.\n"
        "arch-lw assigns weights from a role signal: either color-coded strokes "
        "(a distinct stroke color per role) or named layers (Rhino ::-layers, or "
        "AIA NCS A-WALL-FULL / A-*-MCUT / -OTLN / -PATT / -NPLT).\n"
        f"This file has {n_colors} stroke color(s) and {n_layers} layer(s); "
        f"detected source={src} (confidence={source_conf:.2f}).\n"
        "How to fix:\n"
        "  • In Illustrator: give each hierarchy level a distinct stroke color, then re-export.\n"
        "  • Or export with named layers (Rhino Make2D + ClippingPlane, or AutoCAD AIA layers).\n"
        "  • Then re-run, optionally with --source rhino|autocad to force the convention."
    )


__all__ = ["no_role_signal", "no_role_signal_message"]
