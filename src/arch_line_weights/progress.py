"""Per-stage and per-layer progress reporter for ``apply-saas`` (Issue #15).

The ``apply-saas`` and ``apply-saas --poche`` pipelines can take 15+ minutes
on large drawings while producing zero stdout. This module provides a tiny,
zero-dependency progress reporter that:

  * Writes per-stage start/done events to a tail-able file
    (default ``/tmp/arch_lw_saas_progress.txt``) — parallel to the
    ``apply_jsx`` heartbeat file (Issue #8) so external tools can poll.
  * Echoes the same events to stderr (with ANSI color when stderr is a TTY)
    so interactive CLI users see a live progress bar.
  * Tracks per-layer iteration through the polygonize loop (the slow stage).
  * Computes a rough 0-100% completion estimate using empirical stage
    weights so the user can see a percentage rather than guessing.

Stage weights (sum to 100), calibrated from ``docs/research/benchmarks.md``:

    read_payload      10%
    enumerate_layers   2%
    polygonize        60%   (scaled by completed_layers / total_layers)
    rewrite_payload    5%
    inject_poche       3%
    write_payload     20%

The reporter is a no-op when ``enabled=False`` — no file is opened, no bytes
written to stderr, no syscalls made beyond the cheap stage-name compare.

Output format (one event per line, tab-separated, parseable by future tools):

    ISO8601_TS \\t LEVEL \\t STAGE \\t SUB \\t PERCENT \\t META

Example:

    2026-05-05T14:31:02Z\\tSTART\\tread_payload\\t-\\t0\\tchunks=305
    2026-05-05T14:31:24Z\\tDONE\\tread_payload\\t-\\t10\\telapsed=22.1s decompressed=55_524_864
    2026-05-05T14:31:25Z\\tSTART\\tpolygonize\\tlayer=1/24\\t12\\tname=14_CU_CORR_PERF_SCREEN segments=87
    2026-05-05T14:31:38Z\\tDONE\\tpolygonize\\tlayer=1/24\\t14\\telapsed=12.4s polygons=51 strategy=linemerge_bare conf=1.00

The stderr mirror uses a friendlier human-readable rendering with color codes
(cyan = STAGE, green = DONE, yellow = percent).
"""

from __future__ import annotations

import contextlib
import os
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import IO

# --------------------------------------------------------------------------- #
# Defaults & constants
# --------------------------------------------------------------------------- #

DEFAULT_PROGRESS_FILE = "/tmp/arch_lw_saas_progress.txt"

# Stage percentage weights — calibrated from benchmarks. The polygonize stage
# scales by completed_layers / total_layers so the bar advances smoothly even
# on layers that take 100+ seconds (the historic stubborn-layer worst case).
STAGE_WEIGHTS: dict[str, int] = {
    "read_payload": 10,
    "enumerate_layers": 2,
    "polygonize": 60,
    "rewrite_payload": 5,
    "inject_poche_polygons": 3,
    "write_payload": 20,
}

# Cumulative percent at the *end* of each stage. Used to bracket the percent
# estimator: at the start of a stage we report the prior cumulative, at the
# end we report the new cumulative. polygonize is special: we interpolate
# inside the loop based on layer index.
_STAGE_ORDER = (
    "read_payload",
    "enumerate_layers",
    "polygonize",
    "rewrite_payload",
    "inject_poche_polygons",
    "write_payload",
)


def _cumulative_percent_at_end_of(stage: str) -> int:
    """Return the cumulative percent after ``stage`` finishes."""
    total = 0
    for s in _STAGE_ORDER:
        total += STAGE_WEIGHTS.get(s, 0)
        if s == stage:
            return total
    return 100


def _cumulative_percent_at_start_of(stage: str) -> int:
    """Return the cumulative percent just before ``stage`` starts."""
    total = 0
    for s in _STAGE_ORDER:
        if s == stage:
            return total
        total += STAGE_WEIGHTS.get(s, 0)
    return total


# --------------------------------------------------------------------------- #
# ANSI color helpers — no external `colorama` dependency
# --------------------------------------------------------------------------- #

_ANSI_RESET = "\033[0m"
_ANSI_CYAN = "\033[36m"
_ANSI_GREEN = "\033[32m"
_ANSI_YELLOW = "\033[33m"
_ANSI_DIM = "\033[2m"


def _supports_color(stream: IO[str] | None) -> bool:
    """Return True iff ``stream`` looks like a TTY that handles ANSI codes.

    Errs on the side of "off" — we'd rather lose color in a misdetected
    environment than corrupt logs in CI / piped runs.
    """
    if stream is None:
        return False
    if os.environ.get("NO_COLOR"):
        return False
    try:
        return bool(stream.isatty())
    except (AttributeError, ValueError, OSError):
        return False


# --------------------------------------------------------------------------- #
# Reporter
# --------------------------------------------------------------------------- #


def _now_iso() -> str:
    """Return the current UTC time in ISO 8601 (Z-suffixed, second precision)."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _format_meta(meta: dict[str, object]) -> str:
    """Render a kwargs dict as ``key=value key2=value2`` for the file event line.

    Values get ``str()`` applied directly; spaces inside values are preserved
    (so ``name=foo bar`` is allowed), but tabs get squashed since the file
    format is tab-separated. Keys may not contain whitespace or ``=``.
    """
    parts: list[str] = []
    for k, v in meta.items():
        if v is None:
            continue
        s = str(v).replace("\t", " ").replace("\n", " ")
        parts.append(f"{k}={s}")
    return " ".join(parts)


class ProgressReporter:
    """Emit per-stage / per-layer progress to a file and (optionally) stderr.

    Construct with ``enabled=False`` to make every method a fast no-op — no
    file is opened, no string formatting happens. This is the default code
    path for ``apply-saas`` runs when stderr is piped or the user passed
    ``--no-progress``.

    Thread-safety: the reporter is *not* thread-safe; the apply-saas pipeline
    is single-threaded so this is fine. If a future caller threads stages,
    wrap method calls in a lock.

    Args:
        file_path: Where to write the tab-separated event log. ``None``
            disables the file write (stderr mirror still active when
            ``tty`` is provided). Defaults to ``DEFAULT_PROGRESS_FILE``.
        tty: Stream for the human-readable mirror. Pass ``sys.stderr`` to
            light up the CLI mirror; pass ``None`` to suppress stderr output
            (e.g. when output is piped). When the stream is a TTY the mirror
            uses ANSI color codes; otherwise plain text.
        enabled: Master kill switch. When ``False`` the reporter is a no-op
            on every method.
        total_polygonize_layers: Optional total layer count for the
            polygonize stage. May also be set later via :meth:`set_total_layers`.
    """

    def __init__(
        self,
        file_path: str | None = DEFAULT_PROGRESS_FILE,
        tty: IO[str] | None = None,
        *,
        enabled: bool = True,
        total_polygonize_layers: int = 0,
    ) -> None:
        self.enabled = enabled
        self.file_path = file_path if enabled else None
        self.tty = tty if enabled else None
        self._color = _supports_color(self.tty) if enabled else False
        self._total_layers = total_polygonize_layers
        self._completed_layers = 0
        # _current_stage is the most-recent STARTED stage that has not yet
        # DONEd — used to bracket the percent estimator.
        self._current_stage: str | None = None
        self._stage_start: float = 0.0
        self._fh: IO[str] | None = None
        self._closed = False

        if self.enabled and self.file_path:
            try:
                # Truncate on open — each apply-saas run starts a fresh log
                # so external tailers see a clean stream.
                self._fh = open(self.file_path, "w", encoding="utf-8", buffering=1)  # noqa: SIM115
            except OSError:
                # Don't fail the apply-saas run if /tmp is unwritable; just
                # downgrade to stderr-only.
                self._fh = None
                self.file_path = None

    # ----------------------------------------------------------------- #
    # Lifecycle
    # ----------------------------------------------------------------- #

    def close(self) -> None:
        """Flush + close the underlying file. Idempotent."""
        if self._closed:
            return
        self._closed = True
        if self._fh is not None:
            with contextlib.suppress(OSError, ValueError):
                self._fh.flush()
                with contextlib.suppress(OSError, AttributeError, ValueError):
                    os.fsync(self._fh.fileno())
                self._fh.close()
            self._fh = None

    def __enter__(self) -> ProgressReporter:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        # Best-effort terminal banner if we crashed mid-stage.
        if self.enabled and exc is not None and self._current_stage is not None:
            self._emit("FAIL", self._current_stage, "-", self._percent_estimate(),
                       {"exc": type(exc).__name__})
        self.close()

    # ----------------------------------------------------------------- #
    # Public API
    # ----------------------------------------------------------------- #

    def set_total_layers(self, total: int) -> None:
        """Set the total polygonize-layer count for percent interpolation.

        Called by ``compute_polygons_for_layers`` once it knows how many cut
        layers will run through the polygonize loop.
        """
        if not self.enabled:
            return
        self._total_layers = max(0, int(total))

    def percent_estimate(self) -> int:
        """Return the current rough completion percent (0–100).

        Public alias for the internal helper so tests and external tools can
        sample the percent at any time without driving a stage event.
        """
        if not self.enabled:
            return 0
        return self._percent_estimate()

    @contextmanager
    def stage(self, name: str, **meta: object) -> Iterator[None]:
        """Context manager that brackets a top-level stage.

        On enter, writes a ``START`` event with the stage name + meta kwargs.
        On exit, writes a ``DONE`` event with elapsed time. If the body
        raises, writes a ``FAIL`` event and re-raises.

        Example::

            with reporter.stage("read_payload", chunks=n):
                payload = _read_payload(pdf)
        """
        if not self.enabled:
            yield
            return

        self._current_stage = name
        self._stage_start = time.monotonic()
        start_pct = _cumulative_percent_at_start_of(name)
        self._emit("START", name, "-", start_pct, meta)
        try:
            yield
        except Exception as e:
            elapsed = time.monotonic() - self._stage_start
            self._emit(
                "FAIL",
                name,
                "-",
                start_pct,
                {"elapsed": f"{elapsed:.2f}s", "exc": type(e).__name__},
            )
            self._current_stage = None
            raise
        else:
            elapsed = time.monotonic() - self._stage_start
            end_pct = _cumulative_percent_at_end_of(name)
            self._emit(
                "DONE",
                name,
                "-",
                end_pct,
                {"elapsed": f"{elapsed:.2f}s"},
            )
            self._current_stage = None

    @contextmanager
    def layer(
        self,
        idx: int,
        total: int,
        name: str,
        segments: int,
    ) -> Iterator[LayerCallback]:
        """Context manager wrapping one iteration of the polygonize loop.

        Yields a :class:`LayerCallback` the body can call to record polygon
        count, strategy and confidence before the context closes. If the
        body doesn't call it, we still emit a DONE line with no per-layer
        polygon stats.

        Args:
            idx: 1-based index of the current layer in the polygonize loop.
            total: total layer count (used for the percent estimator).
            name: the layer's full name (gets logged for diagnostics).
            segments: number of input segments for this layer (rough proxy
                for layer cost — useful for spotting outliers in logs).
        """
        if not self.enabled:
            yield LayerCallback(_noop=True)
            return

        # Update total in case caller didn't call set_total_layers up front.
        if total > self._total_layers:
            self._total_layers = total

        self._current_stage = "polygonize"
        layer_label = f"layer={idx}/{total}"
        start_pct = self._percent_estimate_during_polygonize(idx - 1, total)
        layer_start = time.monotonic()
        # Trim the layer name for stderr but preserve full name in file log.
        short_name = name.split("::")[-1] if "::" in name else name
        self._emit(
            "START",
            "polygonize",
            layer_label,
            start_pct,
            {"name": name, "short": short_name, "segments": segments},
        )

        cb = LayerCallback()
        try:
            yield cb
        except Exception as e:
            elapsed = time.monotonic() - layer_start
            self._emit(
                "FAIL",
                "polygonize",
                layer_label,
                start_pct,
                {"name": name, "elapsed": f"{elapsed:.2f}s", "exc": type(e).__name__},
            )
            raise
        else:
            self._completed_layers = idx  # 1-based, so idx == "this many done"
            elapsed = time.monotonic() - layer_start
            end_pct = self._percent_estimate_during_polygonize(idx, total)
            done_meta: dict[str, object] = {
                "name": short_name,
                "elapsed": f"{elapsed:.2f}s",
            }
            if cb.polygon_count is not None:
                done_meta["polygons"] = cb.polygon_count
            if cb.strategy is not None:
                done_meta["strategy"] = cb.strategy
            if cb.confidence is not None:
                done_meta["conf"] = f"{cb.confidence:.2f}"
            self._emit("DONE", "polygonize", layer_label, end_pct, done_meta)
            # current_stage stays "polygonize" until the outer
            # `stage("polygonize")` context exits.

    # ----------------------------------------------------------------- #
    # Internals
    # ----------------------------------------------------------------- #

    def _percent_estimate(self) -> int:
        """Compute the current cumulative completion percent.

        Conservative: returns the start of the current stage when it's still
        running, plus interpolation inside the polygonize stage.
        """
        if self._current_stage is None:
            # No stage active — either we haven't started or we just
            # finished one. Best effort: report cumulative-after-last-stage.
            # We can't tell which stage just finished so we default to 0
            # before the first stage and to 100 if the caller has closed us.
            if self._closed:
                return 100
            return 0
        if self._current_stage == "polygonize":
            return self._percent_estimate_during_polygonize(
                self._completed_layers, self._total_layers
            )
        # Outside polygonize, return the start-of-current-stage percent.
        return _cumulative_percent_at_start_of(self._current_stage)

    def _percent_estimate_during_polygonize(self, done: int, total: int) -> int:
        """Interpolate inside the polygonize stage by completed-layer count."""
        base = _cumulative_percent_at_start_of("polygonize")
        if total <= 0:
            return base
        weight = STAGE_WEIGHTS.get("polygonize", 60)
        ratio = max(0.0, min(1.0, done / total))
        return int(base + ratio * weight)

    def _emit(
        self,
        level: str,
        stage: str,
        sub: str,
        percent: int,
        meta: dict[str, object],
    ) -> None:
        """Write one event to the file + stderr mirror."""
        ts = _now_iso()
        meta_str = _format_meta(meta)
        # File line: tab-separated, one event per line.
        if self._fh is not None:
            line = f"{ts}\t{level}\t{stage}\t{sub}\t{percent}\t{meta_str}\n"
            try:
                self._fh.write(line)
                self._fh.flush()
            except (OSError, ValueError):
                # Something is wrong with the file — degrade to stderr-only.
                self._fh = None

        # Stderr mirror: human-readable, optionally colorized.
        if self.tty is not None:
            self._write_tty(ts, level, stage, sub, percent, meta_str)

    def _write_tty(
        self,
        ts: str,
        level: str,
        stage: str,
        sub: str,
        percent: int,
        meta_str: str,
    ) -> None:
        """Render a single event to the stderr mirror with optional color."""
        if self._color:
            ts_str = f"{_ANSI_DIM}[{ts}]{_ANSI_RESET}"
            pct_str = f"{_ANSI_YELLOW}[{percent:>3}%]{_ANSI_RESET}"
            if level == "START":
                stage_str = f"{_ANSI_CYAN}STAGE: {stage}{_ANSI_RESET}"
            elif level == "DONE":
                stage_str = f"{_ANSI_GREEN}DONE:  {stage}{_ANSI_RESET}"
            else:
                stage_str = f"{level}: {stage}"
        else:
            ts_str = f"[{ts}]"
            pct_str = f"[{percent:>3}%]"
            if level == "START":
                stage_str = f"STAGE: {stage}"
            elif level == "DONE":
                stage_str = f"DONE:  {stage}"
            else:
                stage_str = f"{level}: {stage}"

        sub_str = f"  {sub}" if sub != "-" else ""
        meta_part = f"  {meta_str}" if meta_str else ""
        try:
            self.tty.write(f"{ts_str} {pct_str} {stage_str}{sub_str}{meta_part}\n")
            self.tty.flush()
        except (OSError, ValueError):
            self.tty = None  # silence further attempts on a broken pipe


class LayerCallback:
    """Mutable struct the polygonize-loop body fills to record per-layer stats.

    Used by :meth:`ProgressReporter.layer` so the body can do::

        with reporter.layer(i, n, name, segments) as info:
            polys, fr = polygonize_layer(...)
            info.polygon_count = len(polys)
            info.strategy = fr.strategy
            info.confidence = fr.confidence
    """

    __slots__ = ("_noop", "confidence", "polygon_count", "strategy")

    def __init__(self, *, _noop: bool = False) -> None:
        self.polygon_count: int | None = None
        self.strategy: str | None = None
        self.confidence: float | None = None
        self._noop = _noop


# --------------------------------------------------------------------------- #
# Module-level helpers
# --------------------------------------------------------------------------- #


def make_reporter(
    *,
    enabled: bool,
    file_path: str | None = DEFAULT_PROGRESS_FILE,
    stderr: IO[str] | None = None,
) -> ProgressReporter:
    """Construct a :class:`ProgressReporter` with sensible defaults.

    Convenience wrapper used by the CLI wiring so ``apply_to_file`` and
    ``apply_saas_with_poche`` don't need to know about ``sys.stderr``.

    When ``enabled=False``, returns a no-op reporter regardless of the other
    arguments — equivalent to passing ``ProgressReporter(enabled=False)``.
    """
    if not enabled:
        return ProgressReporter(file_path=None, tty=None, enabled=False)
    return ProgressReporter(
        file_path=file_path,
        tty=stderr if stderr is not None else sys.stderr,
        enabled=True,
    )


__all__ = [
    "DEFAULT_PROGRESS_FILE",
    "STAGE_WEIGHTS",
    "LayerCallback",
    "ProgressReporter",
    "make_reporter",
]
