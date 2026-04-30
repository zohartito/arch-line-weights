"""Layer-preserving apply path: emit a JSX, hand it to Illustrator via osascript.

Trade-off vs the pikepdf path:
  - Slower (3-15 min for ~340K paths) but Illustrator stays the source of truth
  - PieceInfo and the entire layer/group structure are preserved
  - Works with any .ai file Illustrator can open, regardless of origin

Required: Adobe Illustrator 2024+ installed at the standard path on macOS.
The file MUST already be open in Illustrator (or this function will open it).
"""

from __future__ import annotations

import contextlib
import os
import subprocess
import textwrap
import time
from pathlib import Path

from .layer_classify import as_jsx_function

ILLUSTRATOR_APP = "/Applications/Adobe Illustrator 2026/Adobe Illustrator.app"


JSX_TEMPLATE = r"""#target illustrator

(function () {
    var TARGET   = "__TARGET__";
    var OUTPUT   = "__OUTPUT__";
    var PROGRESS = "__PROGRESS__";
    var REPORT   = "__REPORT__";

    try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch (e) {}

__CLASSIFIER__

    function writeFile(p, s) { var f = new File(p); f.encoding = "UTF-8"; f.open("w"); f.write(s); f.close(); }
    function progress(s) { writeFile(PROGRESS, new Date().toString() + "\n" + s); }

    var savedUndo = null;
    var undoKeys = ["maximumUndoDepth", "Undo/UndoCount", "Undo/MaximumUndoCount"];

    try {
        progress("starting");

        var doc = null;
        for (var di = 0; di < app.documents.length; di++) {
            try { if (app.documents[di].fullName.fsName === TARGET) { doc = app.documents[di]; break; } } catch (e) {}
        }
        if (!doc) { writeFile(REPORT, "ERROR: target doc not open: " + TARGET); return; }
        if (app.activeDocument !== doc) app.activeDocument = doc;

        for (var uk = 0; uk < undoKeys.length; uk++) {
            try {
                savedUndo = app.preferences.getIntegerPreference(undoKeys[uk]);
                app.preferences.setIntegerPreference(undoKeys[uk], 1);
                progress("undo cap: " + undoKeys[uk] + " was " + savedUndo);
                break;
            } catch (e) {}
        }

        try { app.executeMenuCommand("showartwork"); } catch (e) {}

        var leaves = [];
        function visit(layer, prefix) {
            var fullName = prefix ? (prefix + "::" + layer.name) : layer.name;
            if (layer.layers.length > 0) {
                for (var s = 0; s < layer.layers.length; s++) visit(layer.layers[s], fullName);
            } else {
                leaves.push({layer: layer, fullName: fullName});
            }
        }
        for (var L = 0; L < doc.layers.length; L++) visit(doc.layers[L], "");
        progress("found " + leaves.length + " leaf layers");

        var counts = {}, byTier = {}, modified = 0, unstroked = 0, errors = 0;
        var t0 = (new Date()).getTime();

        for (var i = 0; i < leaves.length; i++) {
            var meta = leaves[i];
            var w = weightFor(meta.fullName);
            if (!byTier[w]) byTier[w] = [];
            byTier[w].push(meta.fullName);
            var paths = meta.layer.pathItems;
            var n = paths.length;
            for (var p = 0; p < n; p++) {
                try {
                    var pi = paths[p];
                    if (!pi.stroked) { unstroked++; continue; }
                    pi.strokeWidth = w;
                    counts[w] = (counts[w] || 0) + 1;
                    modified++;
                } catch (e) { errors++; }
            }
            var elapsed = ((new Date()).getTime() - t0) / 1000;
            progress("layer " + (i+1) + "/" + leaves.length
                + "  w=" + w + "pt  paths=" + n
                + "  total=" + modified + "  elapsed=" + elapsed.toFixed(1) + "s");
        }

        var totalElapsed = ((new Date()).getTime() - t0) / 1000;
        progress("loop done in " + totalElapsed.toFixed(1) + "s");

        try { app.executeMenuCommand("preview"); } catch (e) {}
        if (savedUndo !== null) {
            for (var uk2 = 0; uk2 < undoKeys.length; uk2++) {
                try { app.preferences.setIntegerPreference(undoKeys[uk2], savedUndo); break; } catch (e) {}
            }
        }

        var saveFile = new File(OUTPUT);
        var saveOpts = new IllustratorSaveOptions();
        saveOpts.pdfCompatible = true;
        progress("saveAs " + OUTPUT);
        doc.saveAs(saveFile, saveOpts);

        var rep = "DONE\nelapsed: " + totalElapsed.toFixed(1) + "s\nleaf layers: " + leaves.length
                + "\nmodified: " + modified + "\nunstroked: " + unstroked + "\nerrors: " + errors + "\n";
        rep += "weight distribution:\n";
        for (var k in counts) rep += "  " + k + " pt: " + counts[k] + "\n";
        rep += "tier->layers:\n";
        for (var w2 in byTier) {
            rep += "  --- " + w2 + " pt ---\n";
            for (var kk = 0; kk < byTier[w2].length; kk++) rep += "    " + byTier[w2][kk] + "\n";
        }
        rep += "saved as: " + OUTPUT + "\n";
        writeFile(REPORT, rep);
        progress("complete");
    } catch (e) {
        try { app.executeMenuCommand("preview"); } catch (e2) {}
        writeFile(REPORT, "EXCEPTION: " + e.toString() + (e.line ? " line " + e.line : ""));
        progress("exception: " + e.toString());
    }
})();
"""


def render_jsx(target: str, output: str, progress_path: str, report_path: str) -> str:
    """Render the JSX template with all paths injected."""
    classifier = as_jsx_function()
    return (
        JSX_TEMPLATE.replace("__TARGET__", target)
        .replace("__OUTPUT__", output)
        .replace("__PROGRESS__", progress_path)
        .replace("__REPORT__", report_path)
        .replace("__CLASSIFIER__", textwrap.indent(classifier, "    "))
    )


def open_in_illustrator(path: str) -> None:
    """Ask Illustrator to open `path` (uses AppleScript native `open` command)."""
    script = f'''with timeout of 1800 seconds
        tell application "Adobe Illustrator"
            activate
            open POSIX file "{path}"
        end tell
    end timeout'''
    subprocess.run(["osascript", "-e", script], check=True, timeout=1800)


def run_jsx_in_illustrator(jsx_path: str, timeout: int = 3600) -> None:
    """Hand a JSX file to Illustrator via osascript do javascript."""
    applescript = f'''with timeout of {timeout} seconds
        tell application "Adobe Illustrator"
            do javascript (read POSIX file "{jsx_path}" as «class utf8»)
        end tell
    end timeout'''
    subprocess.run(["osascript", "-e", applescript], check=True, timeout=timeout + 60)


def apply_via_jsx(src: str, dst: str | None = None, *, jsx_path: str | None = None) -> dict:
    """Open `src` in Illustrator and apply layer-aware hierarchy. Save to `dst`.

    Returns a dict with the parsed report.
    """
    src = os.path.abspath(src)
    if dst is None:
        p = Path(src)
        dst = str(p.with_name(f"{p.stem} HIERARCHY{p.suffix}"))
    dst = os.path.abspath(dst)
    if dst == src:
        raise ValueError("dst must differ from src")

    progress_path = "/tmp/arch_lw_progress.txt"
    report_path = "/tmp/arch_lw_report.txt"
    for f in (progress_path, report_path):
        with contextlib.suppress(FileNotFoundError):
            os.unlink(f)

    if jsx_path is None:
        jsx_path = "/tmp/arch_lw_apply.jsx"
    Path(jsx_path).write_text(render_jsx(src, dst, progress_path, report_path))

    open_in_illustrator(src)
    time.sleep(2)
    run_jsx_in_illustrator(jsx_path)

    if not os.path.exists(report_path):
        raise RuntimeError(f"JSX did not produce a report at {report_path}")
    return {"report_path": report_path, "output": dst, "report": Path(report_path).read_text()}
