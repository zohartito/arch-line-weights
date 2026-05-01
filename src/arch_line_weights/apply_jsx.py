"""Layer-preserving apply path: emit a JSX, hand it to Illustrator via osascript.

Trade-off vs the pikepdf path:
  - Slower (3-15 min for ~340K paths) but Illustrator stays the source of truth
  - PieceInfo and the entire layer/group structure are preserved
  - Works with any .ai file Illustrator can open, regardless of origin

Required: Adobe Illustrator 2024+ installed at the standard path on macOS.
The file MUST already be open in Illustrator (or this function will open it).

v0.5.2 / 2026-05-01 fixes the four UX bugs surfaced during the first
non-section drawing run (see docs/POSTMORTEM.md Attempt 9):

  Issue #8  — heartbeat-driven progress polling instead of silent runs.
              The JSX writes per-layer status to a heartbeat file, and the
              Python wrapper polls every 2 s, prints new lines, and warns
              if no update arrives for >5 min (likely Illustrator hang).
  Issue #10 — explicit `[Converted]` doc-state detection. When Illustrator
              has a non-AI source (PDF / older .ai) open as
              ``<name> [Converted]``, AppleScript ``open POSIX file``
              returns silently and the JSX can't find the target. We
              now query the active doc up front and either operate on
              the open doc directly or surface a clear error.
  Issue #11 — configurable timeout via ``--timeout MINUTES`` (default 30,
              max 240) and the ``ARCH_LW_JSX_TIMEOUT_MIN`` env var. The
              60-min hard-coded timeout was too short for 98 MB drawings
              and too long for small ones.
  Issue #13 — `--preset` flag wires the chosen preset family
              (section/plan/elevation/detail) into the embedded JSX
              classifier so the JSX path picks the right tier ladder
              for non-section drawings.
"""

from __future__ import annotations

import contextlib
import os
import re
import subprocess
import textwrap
import threading
import time
from pathlib import Path

from .layer_classify import as_jsx_function

ILLUSTRATOR_APP = "/Applications/Adobe Illustrator 2026/Adobe Illustrator.app"

# Default JSX timeout, in minutes. Empirically v0.5.1 used 60 min; the new
# default is shorter so small files don't waste a full hour on a hang. The
# CLI / env var lifts this for big drawings.
DEFAULT_TIMEOUT_MIN = 30
MAX_TIMEOUT_MIN = 240
TIMEOUT_ENV_VAR = "ARCH_LW_JSX_TIMEOUT_MIN"

# Heartbeat staleness threshold. If the JSX hasn't written a new heartbeat
# line in this many seconds, we surface a warning that Illustrator may be
# hung, but we DO NOT abort — the user decides. (Issue #8.)
STALE_HEARTBEAT_SEC = 300

# Heartbeat polling cadence. Cheap to increase if it ever feels noisy.
HEARTBEAT_POLL_SEC = 2


JSX_TEMPLATE = r"""#target illustrator

(function () {
    var TARGET   = "__TARGET__";
    var OUTPUT   = "__OUTPUT__";
    var PROGRESS = "__PROGRESS__";
    var REPORT   = "__REPORT__";
    var HEART    = "__HEARTBEAT__";
    var USE_OPEN_DOC = __USE_OPEN_DOC__;

    try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch (e) {}

__CLASSIFIER__

    function writeFile(p, s) { var f = new File(p); f.encoding = "UTF-8"; f.open("w"); f.write(s); f.close(); }
    function appendFile(p, s) { var f = new File(p); f.encoding = "UTF-8"; f.open("a"); f.write(s); f.close(); }
    function progress(s) { writeFile(PROGRESS, new Date().toString() + "\n" + s); }
    function heartbeat(s) { appendFile(HEART, s + "\n"); }

    var savedUndo = null;
    var undoKeys = ["maximumUndoDepth", "Undo/UndoCount", "Undo/MaximumUndoCount"];

    try {
        // Reset heartbeat file on every run so the wrapper can poll cleanly.
        writeFile(HEART, "");
        heartbeat("starting");
        progress("starting");

        var doc = null;
        if (USE_OPEN_DOC) {
            // Issue #10: skip the open POSIX file step and operate on the
            // currently active document directly. The wrapper has already
            // confirmed it's the right file (just in [Converted] state).
            try { doc = app.activeDocument; } catch (e) {}
            if (!doc) {
                writeFile(REPORT, "ERROR: USE_OPEN_DOC mode but no active doc");
                heartbeat("DONE");
                return;
            }
            heartbeat("using already-open doc: " + doc.name);
        } else {
            for (var di = 0; di < app.documents.length; di++) {
                try { if (app.documents[di].fullName.fsName === TARGET) { doc = app.documents[di]; break; } } catch (e) {}
            }
            if (!doc) { writeFile(REPORT, "ERROR: target doc not open: " + TARGET); heartbeat("DONE"); return; }
            if (app.activeDocument !== doc) app.activeDocument = doc;
        }

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
        heartbeat("found " + leaves.length + " leaf layers");

        var counts = {}, byTier = {}, modified = 0, unstroked = 0, errors = 0;
        var t0 = (new Date()).getTime();

        for (var i = 0; i < leaves.length; i++) {
            var meta = leaves[i];
            var w = weightFor(meta.fullName);
            if (!byTier[w]) byTier[w] = [];
            byTier[w].push(meta.fullName);
            var paths = meta.layer.pathItems;
            var n = paths.length;
            // Issue #8: per-layer heartbeat — wrapper polls this.
            heartbeat((i + 1) + "/" + leaves.length + ": " + meta.fullName + " (" + n + " paths)");
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
        heartbeat("saving as " + OUTPUT);
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
        heartbeat("DONE");
    } catch (e) {
        try { app.executeMenuCommand("preview"); } catch (e2) {}
        writeFile(REPORT, "EXCEPTION: " + e.toString() + (e.line ? " line " + e.line : ""));
        progress("exception: " + e.toString());
        heartbeat("DONE");
    }
})();
"""


def render_jsx(
    target: str,
    output: str,
    progress_path: str,
    report_path: str,
    heartbeat_path: str,
    *,
    use_open_doc: bool = False,
    preset: str | None = None,
    scale: str = "1/4",
    for_print: bool = False,
) -> str:
    """Render the JSX template with all paths injected.

    `use_open_doc=True` (Issue #10) tells the JSX to operate on the active
    document instead of attempting to find it by `fullName`. Used when the
    wrapper detected a `[Converted]` state where the doc IS the right file.

    `preset` (Issue #13): when set to "section" / "plan" / "elevation" /
    "detail", embeds preset-aware tier weights into the JSX classifier so
    non-section drawings pick up the right ladder. `None` preserves the
    pre-fix v0.5.1 weights (which match the section preset).
    """
    classifier = as_jsx_function(preset=preset, scale=scale, for_print=for_print)
    return (
        JSX_TEMPLATE.replace("__TARGET__", target)
        .replace("__OUTPUT__", output)
        .replace("__PROGRESS__", progress_path)
        .replace("__REPORT__", report_path)
        .replace("__HEARTBEAT__", heartbeat_path)
        .replace("__USE_OPEN_DOC__", "true" if use_open_doc else "false")
        .replace("__CLASSIFIER__", textwrap.indent(classifier, "    "))
    )


def open_in_illustrator(path: str, *, timeout_sec: int = 1800) -> None:
    """Ask Illustrator to open `path` (uses AppleScript native `open` command)."""
    script = f'''with timeout of {timeout_sec} seconds
        tell application "Adobe Illustrator"
            activate
            open POSIX file "{path}"
        end tell
    end timeout'''
    subprocess.run(["osascript", "-e", script], check=True, timeout=timeout_sec)


def run_jsx_in_illustrator(jsx_path: str, timeout: int = 3600) -> None:
    """Hand a JSX file to Illustrator via osascript do javascript."""
    applescript = f'''with timeout of {timeout} seconds
        tell application "Adobe Illustrator"
            do javascript (read POSIX file "{jsx_path}" as «class utf8»)
        end tell
    end timeout'''
    subprocess.run(["osascript", "-e", applescript], check=True, timeout=timeout + 60)


# --------------------------------------------------------------------------- #
# Issue #10 — `[Converted]` doc-state detection
# --------------------------------------------------------------------------- #


def query_active_doc() -> tuple[str | None, str | None]:
    """Return `(active_doc_name, active_doc_path)` from Illustrator.

    `active_doc_path` is the `POSIX path of` the doc's `file path` if the
    doc has been saved, else `None` (a `[Converted]` virtual doc has no
    saved path until the user does Save As).

    Returns `(None, None)` when there's no active doc or AppleScript fails.

    Issue #14: the doc name may contain internal trailing whitespace
    (e.g. ``"wall section iso cut  [Converted].ai"`` for a disk file
    named ``"wall section iso cut .ai"``). We only strip the single
    trailing newline that ``osascript`` appends, NOT all surrounding
    whitespace, so the matcher downstream sees the exact name shape
    Illustrator reported.
    """
    script = (
        'tell application "Adobe Illustrator"\n'
        '  if (count of documents) is 0 then\n'
        '    return ""\n'
        '  end if\n'
        '  set docName to name of active document\n'
        '  try\n'
        '    set docPath to POSIX path of (file path of active document)\n'
        '  on error\n'
        '    set docPath to ""\n'
        '  end try\n'
        '  return docName & "|" & docPath\n'
        'end tell'
    )
    try:
        raw = subprocess.run(
            ["osascript", "-e", script],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
    except (subprocess.SubprocessError, OSError):
        return None, None
    # Trim ONLY the trailing newline(s) osascript appends; preserve any
    # whitespace inside the name field (Issue #14).
    out = raw.rstrip("\r\n")
    if not out:
        return None, None
    name, _, path = out.partition("|")
    return (name or None), (path or None)


# Matches a Unicode whitespace run immediately preceding the `[Converted]`
# token, plus any whitespace + optional extension trailing it. Used to peel
# the [Converted] decoration off an Illustrator doc name to recover the
# normalized stem.
_CONVERTED_DECOR_RE = re.compile(r"\s*\[Converted\]\s*(?:\.[A-Za-z0-9]+)?\s*$")


def _normalize_stem(s: str) -> str:
    """Return `s` with any trailing whitespace stripped.

    Whitespace here is the full Unicode notion (``str.rstrip()`` default):
    ASCII space, tab, NBSP, etc. Used by `_is_converted_match` to make the
    comparison robust to disk filenames that end in whitespace before the
    extension (Issue #14).
    """
    return s.rstrip()


def _strip_converted_decoration(name: str) -> str:
    """Return the active-doc name with the trailing ``[Converted]`` decoration
    removed, including any whitespace immediately before/after it and the
    optional file extension that Illustrator may re-append.

    Examples (Issue #14):

        "macro [Converted].ai"            -> "macro"
        "macro [Converted]"               -> "macro"
        "wall section iso cut  [Converted].ai"
                                          -> "wall section iso cut"
        "wall\\t[Converted]"              -> "wall"

    If the input has no ``[Converted]`` token, returns the file's stem
    (extension stripped) so the caller can compare against a disk stem.
    """
    if "[Converted]" in name:
        stripped = _CONVERTED_DECOR_RE.sub("", name)
        return _normalize_stem(stripped)
    # No [Converted] decoration — fall back to plain stem.
    return _normalize_stem(Path(name).stem)


def _is_converted_match(active_name: str | None, active_path: str | None, src: str) -> bool:
    """Return True iff the active doc is the same file as `src`, just in
    `[Converted]` state.

    Illustrator opens non-AI sources (PDF, older .ai) as
    ``<basename> [Converted]`` virtual docs. The active doc has the
    `[Converted]` suffix in its name and either an empty file-path or a
    file-path pointing at the original `src`.

    Normalization rules (Issue #14):

      * Both stems are compared after :func:`str.rstrip` strips ALL trailing
        whitespace (ASCII space, tab, NBSP, other Unicode whitespace).
      * The ``[Converted]`` token, the whitespace surrounding it, and any
        Illustrator-appended extension are peeled from the active doc name
        before stem comparison.
      * Comparison is case-sensitive on the stem itself but case-insensitive
        when falling back to a basename-substring check (legacy looser path).

    These normalizations let a disk file like
    ``/path/wall section iso cut .ai`` (trailing space before ``.ai``)
    correctly match Illustrator's
    ``"wall section iso cut  [Converted].ai"`` (two spaces before
    ``[Converted]`` because the trailing space is preserved between the
    stem and Illustrator's own leading space).
    """
    if not active_name:
        return False
    # NOTE: do NOT use `str.strip()` here — it would discard internal
    # trailing whitespace that lives between the disk-name stem and the
    # Illustrator-added " [Converted]" suffix. Only strip the kind of
    # leading/trailing space that osascript could realistically introduce
    # — but `query_active_doc()` already does that conservatively.
    name = active_name
    src_path = Path(src)
    src_basename = src_path.name
    src_stem = src_path.stem
    src_stem_norm = _normalize_stem(src_stem)
    src_basename_norm = _normalize_stem(src_basename)

    # Primary path: peel the [Converted] decoration and compare normalized
    # stems for equality. We require the [Converted] token to be present,
    # otherwise a regular saved doc whose path matches `src` would falsely
    # match here (the wrapper relies on this False return to fall through
    # to the standard `open POSIX file` path).
    if "[Converted]" in name:
        active_stem_norm = _strip_converted_decoration(name)
        if active_stem_norm and active_stem_norm == src_stem_norm:
            # Stems match after whitespace normalization; fall through to
            # the path-consistency check below.
            pass
        else:
            # Fall through to legacy candidate-suffix sweep.
            active_stem_norm = None
    else:
        active_stem_norm = None
    if active_stem_norm is None:
        # Legacy candidate-suffix sweep — kept so any pre-existing exact
        # name shape we already supported still matches. Compare against
        # both the raw and the normalized basename / stem.
        converted_suffixes = (
            f"{src_basename} [Converted]",
            f"{src_basename} [Converted].ai",
            f"{src_stem} [Converted]",
            f"{src_stem} [Converted].ai",
            f"{src_basename_norm} [Converted]",
            f"{src_basename_norm} [Converted].ai",
            f"{src_stem_norm} [Converted]",
            f"{src_stem_norm} [Converted].ai",
        )
        if not any(name == s or name.endswith(s) for s in converted_suffixes):
            # Looser fallback: name must contain "[Converted]" AND share a
            # basename substring with the source.
            if "[Converted]" not in name:
                return False
            if (
                src_stem.lower() not in name.lower()
                and src_basename.lower() not in name.lower()
                and src_stem_norm.lower() not in name.lower()
                and src_basename_norm.lower() not in name.lower()
            ):
                return False

    # Path check: a [Converted] virtual doc usually has no saved path. If
    # AppleScript returned a path, accept it only if it actually points at
    # the source file (covers the case where the user saved-as later).
    if active_path:
        try:
            return os.path.realpath(active_path) == os.path.realpath(src)
        except OSError:
            return False
    return True


# --------------------------------------------------------------------------- #
# Issue #8 — heartbeat polling
# --------------------------------------------------------------------------- #


class _HeartbeatPoller(threading.Thread):
    """Background thread that polls a heartbeat file and prints new lines.

    Detects two completion signals:
      * the literal line `"DONE"` (JSX wrote it explicitly), or
      * file mtime stale for >`stale_threshold_sec` (probable hang;
        we surface a warning but don't kill anything).
    """

    def __init__(
        self,
        heartbeat_path: str,
        *,
        poll_interval: float = HEARTBEAT_POLL_SEC,
        stale_threshold_sec: float = STALE_HEARTBEAT_SEC,
        printer=print,
    ):
        super().__init__(daemon=True)
        self.heartbeat_path = heartbeat_path
        self.poll_interval = poll_interval
        self.stale_threshold_sec = stale_threshold_sec
        self._printer = printer
        # Don't name this `_stop` — `threading.Thread` internals look up
        # `self._stop()` as a callable (private cleanup hook). Using a
        # different attribute name avoids stomping on it.
        self._stop_event = threading.Event()
        self.last_line: str | None = None
        self.lines_seen = 0
        self.done = False
        self.stale_warning_emitted = False

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        last_size = 0
        last_mtime = time.time()
        while not self._stop_event.is_set():
            try:
                stat = os.stat(self.heartbeat_path)
                size = stat.st_size
                mtime = stat.st_mtime
                if size > last_size:
                    with open(self.heartbeat_path, encoding="utf-8") as f:
                        f.seek(last_size)
                        new = f.read()
                    last_size = size
                    last_mtime = mtime
                    self.stale_warning_emitted = False
                    for raw in new.splitlines():
                        line = raw.strip()
                        if not line:
                            continue
                        self.last_line = line
                        self.lines_seen += 1
                        self._printer(f"  jsx: {line}")
                        if line == "DONE":
                            self.done = True
                            return
                else:
                    # No new bytes — check staleness.
                    elapsed = time.time() - last_mtime
                    if (
                        not self.stale_warning_emitted
                        and elapsed > self.stale_threshold_sec
                    ):
                        self._printer(
                            f"  warning: no JSX heartbeat for {int(elapsed)} s — Illustrator may be hung "
                            "(NOT aborting; cancel with Ctrl-C if needed)"
                        )
                        self.stale_warning_emitted = True
            except FileNotFoundError:
                # The wrapper recreates this file before launching JSX; if
                # we got here before the JSX wrote its first line it's just
                # a race — wait and retry.
                pass
            self._stop_event.wait(self.poll_interval)


# --------------------------------------------------------------------------- #
# Issue #12 — distinct default output path per apply path
# --------------------------------------------------------------------------- #

# Suffix appended to the source stem when the user does not pass `-o`. Kept
# distinct from `apply-saas` so concurrent runs of both pipelines on the
# same source don't race on the same output filename. The legacy `apply`
# command (pikepdf, layer-flattening) keeps the bare " HIERARCHY" suffix
# for back-compat with users who already script around it.
DEFAULT_OUTPUT_SUFFIX = " HIERARCHY-jsx"


def default_output_path(src: str | os.PathLike[str]) -> str:
    """Return the default output path for `apply-jsx` given the source.

    Issue #12: the `apply-jsx` and `apply-saas` defaults must differ so the
    two pipelines don't overwrite each other when both run on the same
    source. We add a `-jsx` suffix here; `apply_saas.default_output_path`
    uses `-saas`. Users override with `-o` / `--output`.

    Examples:

        ``/x/macro.ai`` -> ``/x/macro HIERARCHY-jsx.ai``
        ``/x/macro.pdf`` -> ``/x/macro HIERARCHY-jsx.pdf``
    """
    p = Path(src)
    return str(p.with_name(f"{p.stem}{DEFAULT_OUTPUT_SUFFIX}{p.suffix}"))


# --------------------------------------------------------------------------- #
# Issue #11 — configurable timeout
# --------------------------------------------------------------------------- #


def resolve_timeout_minutes(timeout_min: int | None = None) -> int:
    """Resolve the JSX timeout in minutes.

    Priority:
      1. Explicit `timeout_min` argument.
      2. `ARCH_LW_JSX_TIMEOUT_MIN` env var.
      3. `DEFAULT_TIMEOUT_MIN`.

    Clamped to `[1, MAX_TIMEOUT_MIN]`.
    """
    if timeout_min is None:
        env = os.environ.get(TIMEOUT_ENV_VAR)
        if env:
            try:
                timeout_min = int(env)
            except ValueError:
                timeout_min = DEFAULT_TIMEOUT_MIN
        else:
            timeout_min = DEFAULT_TIMEOUT_MIN
    if timeout_min < 1:
        timeout_min = 1
    if timeout_min > MAX_TIMEOUT_MIN:
        timeout_min = MAX_TIMEOUT_MIN
    return timeout_min


# --------------------------------------------------------------------------- #
# Public entry point
# --------------------------------------------------------------------------- #


def apply_via_jsx(
    src: str,
    dst: str | None = None,
    *,
    jsx_path: str | None = None,
    timeout_min: int | None = None,
    preset: str | None = None,
    scale: str = "1/4",
    for_print: bool = False,
    printer=print,
) -> dict:
    """Open `src` in Illustrator and apply layer-aware hierarchy. Save to `dst`.

    Args:
        src: Path to the source `.ai` file. Must exist.
        dst: Optional output path. Defaults to `<src> HIERARCHY-jsx.<ext>`
            (Issue #12: distinct from ``apply-saas`` so the two pipelines
            don't overwrite each other when both run on the same source).
        jsx_path: Optional override for where the rendered JSX is written.
        timeout_min: JSX timeout in minutes. Defaults to
            ``ARCH_LW_JSX_TIMEOUT_MIN`` env var, then ``DEFAULT_TIMEOUT_MIN``
            (30). Clamped to [1, ``MAX_TIMEOUT_MIN``=240].
        preset: Optional preset family name. When set to one of
            "section" / "plan" / "elevation" / "detail", the embedded JSX
            classifier is parameterised on that preset's tier weights.
            ``None`` (default) preserves v0.5.1 hardcoded weights.
        scale: Plot scale used by the preset family for ISO 128 weight
            shifting (only matters when ``for_print=True``).
        for_print: If True, use the preset family's print ladder instead of
            the screen ladder.
        printer: Callable used for progress lines (default: ``print``).
            Tests inject a list-appending stub.

    Returns a dict with the parsed report.
    """
    src = os.path.abspath(src)
    if dst is None:
        dst = default_output_path(src)
    dst = os.path.abspath(dst)
    if dst == src:
        raise ValueError("dst must differ from src")

    timeout_min = resolve_timeout_minutes(timeout_min)
    timeout_sec = timeout_min * 60

    progress_path = "/tmp/arch_lw_progress.txt"
    report_path = "/tmp/arch_lw_report.txt"
    heartbeat_path = "/tmp/arch_lw_jsx_progress.txt"
    for f in (progress_path, report_path, heartbeat_path):
        with contextlib.suppress(FileNotFoundError):
            os.unlink(f)
    # Prime the heartbeat file so the poller can attach immediately even
    # before the JSX writes its first line.
    Path(heartbeat_path).write_text("")

    # Issue #10: pre-flight active-doc query. If the user has the source
    # already open as a `[Converted]` virtual doc, skip the brittle
    # `open POSIX file` step and operate on the open doc directly.
    use_open_doc = False
    active_name, active_path = query_active_doc()
    if active_name and "[Converted]" in active_name:
        if _is_converted_match(active_name, active_path, src):
            printer(
                f"# detected [Converted] doc '{active_name}' for source — "
                "operating on the open document directly (Issue #10)"
            )
            use_open_doc = True
        else:
            raise RuntimeError(
                f"Illustrator has '{active_name}' open. Save it (Cmd+S) and "
                "close the original to allow apply-jsx to open the disk file "
                "fresh, or close the [Converted] doc entirely."
            )

    if jsx_path is None:
        jsx_path = "/tmp/arch_lw_apply.jsx"
    Path(jsx_path).write_text(
        render_jsx(
            src,
            dst,
            progress_path,
            report_path,
            heartbeat_path,
            use_open_doc=use_open_doc,
            preset=preset,
            scale=scale,
            for_print=for_print,
        )
    )

    if not use_open_doc:
        open_in_illustrator(src, timeout_sec=min(timeout_sec, 1800))
        time.sleep(2)

    # Spin up the heartbeat poller before launching JSX.
    poller = _HeartbeatPoller(heartbeat_path, printer=printer)
    poller.start()
    try:
        run_jsx_in_illustrator(jsx_path, timeout=timeout_sec)
    finally:
        poller.stop()
        poller.join(timeout=5)

    if not os.path.exists(report_path):
        raise RuntimeError(f"JSX did not produce a report at {report_path}")
    return {
        "report_path": report_path,
        "output": dst,
        "report": Path(report_path).read_text(),
        "heartbeat_lines": poller.lines_seen,
        "use_open_doc": use_open_doc,
    }
