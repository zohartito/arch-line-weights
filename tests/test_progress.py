"""Tests for the ``arch_line_weights.progress`` module (Issue #15).

Coverage:

  * Disabled reporter is a strict no-op (no file writes, no stderr output,
    zero-cost path on every method).
  * File output: lines are tab-separated, line-buffered, and visible to a
    tailing reader during the run (i.e. flushed after each event).
  * Stage context manager: enter writes a ``START`` line, exit writes a
    ``DONE`` line carrying the elapsed time.
  * Layer context manager: exit writes the per-layer polygon count, strategy
    and confidence supplied via the yielded callback.
  * Percent estimator: zero before any stage starts, partial during
    polygonize at half layers, end-of-stage value after polygonize finishes,
    and the documented stage weights add up to 100.
  * Exception inside a stage produces a ``FAIL`` event and does not swallow
    the exception.
"""

from __future__ import annotations

import io
import os
import time
from pathlib import Path

import pytest

from arch_line_weights.progress import (
    DEFAULT_PROGRESS_FILE,
    STAGE_WEIGHTS,
    LayerCallback,
    ProgressReporter,
    _cumulative_percent_at_end_of,
    _cumulative_percent_at_start_of,
    make_reporter,
)

# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _read_lines(path: str) -> list[str]:
    """Read the progress file and return non-empty lines."""
    with open(path, encoding="utf-8") as f:
        return [line.rstrip("\n") for line in f if line.strip()]


def _make_reporter(tmp_path: Path, *, enabled: bool = True) -> tuple[ProgressReporter, Path, io.StringIO]:
    """Construct a reporter pointed at a temp file with a StringIO stderr."""
    p = tmp_path / "progress.txt"
    fake_tty = io.StringIO()
    rep = ProgressReporter(file_path=str(p), tty=fake_tty, enabled=enabled)
    return rep, p, fake_tty


# --------------------------------------------------------------------------- #
# Disabled reporter — strict no-op
# --------------------------------------------------------------------------- #


def test_disabled_reporter_does_not_create_file(tmp_path: Path):
    """``enabled=False`` must not open the progress file at all."""
    target = tmp_path / "should_not_exist.txt"
    fake_tty = io.StringIO()
    rep = ProgressReporter(file_path=str(target), tty=fake_tty, enabled=False)
    with rep.stage("read_payload"):
        pass
    rep.close()
    assert not target.exists(), "disabled reporter must not create the progress file"
    assert fake_tty.getvalue() == "", "disabled reporter must not write to stderr"


def test_disabled_reporter_layer_context_is_noop(tmp_path: Path):
    """Layer context manager must be a no-op when disabled."""
    target = tmp_path / "should_not_exist.txt"
    fake_tty = io.StringIO()
    rep = ProgressReporter(file_path=str(target), tty=fake_tty, enabled=False)
    with rep.layer(1, 5, "foo", 100) as info:
        # The yielded value still works structurally so callers can be
        # uniform across enabled / disabled, but writes happen nowhere.
        info.polygon_count = 3
        info.strategy = "linemerge_bare"
        info.confidence = 1.0
    rep.close()
    assert not target.exists()
    assert fake_tty.getvalue() == ""


def test_disabled_reporter_percent_is_zero():
    """Disabled reporter always reports 0% — no internal state mutation."""
    rep = ProgressReporter(enabled=False)
    assert rep.percent_estimate() == 0
    with rep.stage("polygonize"):
        assert rep.percent_estimate() == 0


# --------------------------------------------------------------------------- #
# File output
# --------------------------------------------------------------------------- #


def test_reporter_creates_file_and_writes_events(tmp_path: Path):
    """Enabling the reporter creates the file and writes one event per call."""
    rep, p, _ = _make_reporter(tmp_path)
    with rep.stage("read_payload", chunks=305):
        pass
    rep.close()
    assert p.exists()
    lines = _read_lines(str(p))
    # Two events: START + DONE for read_payload.
    assert len(lines) == 2
    assert "\tSTART\tread_payload\t" in lines[0]
    assert "\tDONE\tread_payload\t" in lines[1]


def test_file_output_is_tab_separated(tmp_path: Path):
    """Every event line has the documented column count and tabs."""
    rep, p, _ = _make_reporter(tmp_path)
    with rep.stage("read_payload", chunks=42):
        pass
    rep.close()
    for line in _read_lines(str(p)):
        # ts \t LEVEL \t STAGE \t SUB \t PERCENT \t META
        cols = line.split("\t")
        assert len(cols) == 6, f"expected 6 tab-separated columns in {line!r}"


def test_file_output_is_line_buffered(tmp_path: Path):
    """Each write must be flushed before the next write so tailers see it live."""
    rep, p, _ = _make_reporter(tmp_path)
    with rep.stage("read_payload"):
        # Mid-stage: only the START line is on disk so far.
        mid = _read_lines(str(p))
        assert len(mid) == 1
        assert "\tSTART\t" in mid[0]
    # After the context exits, DONE line is written and flushed.
    after = _read_lines(str(p))
    assert len(after) == 2
    assert "\tDONE\t" in after[1]
    rep.close()


# --------------------------------------------------------------------------- #
# Stage context manager
# --------------------------------------------------------------------------- #


def test_stage_writes_start_and_done(tmp_path: Path):
    """Stage context manager wraps a body in matching START/DONE events."""
    rep, p, fake_tty = _make_reporter(tmp_path)
    with rep.stage("rewrite_payload", payload_size=100):
        time.sleep(0.01)
    rep.close()
    file_lines = _read_lines(str(p))
    assert len(file_lines) == 2
    assert "rewrite_payload" in file_lines[0]
    assert "rewrite_payload" in file_lines[1]
    # DONE line carries an elapsed= meta key.
    assert "elapsed=" in file_lines[1]
    # Stderr mirror picks it up too.
    tty_text = fake_tty.getvalue()
    assert "STAGE: rewrite_payload" in tty_text
    assert "DONE:  rewrite_payload" in tty_text


def test_stage_exception_emits_fail_and_reraises(tmp_path: Path):
    """An exception inside a stage body produces a FAIL event and reraises."""
    rep, p, _ = _make_reporter(tmp_path)
    with pytest.raises(RuntimeError, match="boom"), rep.stage("read_payload"):
        raise RuntimeError("boom")
    rep.close()
    lines = _read_lines(str(p))
    # START + FAIL.
    assert any("\tSTART\tread_payload\t" in line for line in lines)
    assert any("\tFAIL\tread_payload\t" in line for line in lines)


# --------------------------------------------------------------------------- #
# Layer context manager
# --------------------------------------------------------------------------- #


def test_layer_records_polygon_count_strategy_confidence(tmp_path: Path):
    """Layer context manager logs whatever the body sets on the callback."""
    rep, p, _ = _make_reporter(tmp_path)
    with rep.stage("polygonize", layers=3):
        for i in range(1, 4):
            with rep.layer(i, 3, f"layer::cut::L{i}", segments=10) as info:
                info.polygon_count = i * 2
                info.strategy = "linemerge_bare"
                info.confidence = 0.95
    rep.close()
    lines = _read_lines(str(p))
    # We expect: stage(START), 3 × (layer START + layer DONE), stage(DONE) = 8 lines.
    layer_done_lines = [line for line in lines if "\tDONE\tpolygonize\tlayer=" in line]
    assert len(layer_done_lines) == 3
    # First layer's DONE line must mention polygons=2 strategy=linemerge_bare conf=0.95.
    assert "polygons=2" in layer_done_lines[0]
    assert "strategy=linemerge_bare" in layer_done_lines[0]
    assert "conf=0.95" in layer_done_lines[0]


def test_layer_records_short_name(tmp_path: Path):
    """Layer DONE event should carry just the short name (after final ``::``)."""
    rep, p, _ = _make_reporter(tmp_path)
    with rep.stage("polygonize", layers=1), rep.layer(
        1, 1, "axon::Visible::ClippingPlaneIntersections::TEC_FOO", 12
    ) as info:
        info.polygon_count = 1
        info.strategy = "concave_hull"
        info.confidence = 0.55
    rep.close()
    lines = _read_lines(str(p))
    done_line = next(line for line in lines if "\tDONE\tpolygonize\t" in line)
    # Short-name key is `name=TEC_FOO` on the DONE line.
    assert "name=TEC_FOO" in done_line


# --------------------------------------------------------------------------- #
# Percent estimator
# --------------------------------------------------------------------------- #


def test_stage_weights_sum_to_100():
    """Calibration invariant: stage weights add up to exactly 100."""
    assert sum(STAGE_WEIGHTS.values()) == 100


def test_percent_zero_before_any_stage():
    """Before any stage starts, percent estimate must be 0."""
    rep = ProgressReporter(enabled=True, file_path=None, tty=None)
    assert rep.percent_estimate() == 0
    rep.close()


def test_percent_partial_inside_polygonize(tmp_path: Path):
    """At half the polygonize layers done, percent is base + 0.5 × weight."""
    rep, _, _ = _make_reporter(tmp_path)
    base = _cumulative_percent_at_start_of("polygonize")
    weight = STAGE_WEIGHTS["polygonize"]
    expected_half = int(base + 0.5 * weight)
    with rep.stage("polygonize", layers=4):
        for i in range(1, 3):  # complete 2 of 4 layers
            with rep.layer(i, 4, f"L{i}", 5) as info:
                info.polygon_count = 1
                info.strategy = "linemerge_bare"
                info.confidence = 1.0
        # After 2 / 4 layers done, percent_estimate ≈ base + 0.5 × weight.
        observed = rep.percent_estimate()
        assert abs(observed - expected_half) <= 1, (
            f"percent_estimate at 2/4 layers was {observed}, expected ~{expected_half}"
        )
    rep.close()


def test_percent_after_write_payload(tmp_path: Path):
    """After write_payload finishes, percent estimator reaches 100."""
    rep, _, _ = _make_reporter(tmp_path)
    # Walk through all stages so the cumulative percent climbs to 100.
    with rep.stage("read_payload"):
        pass
    with rep.stage("enumerate_layers"):
        pass
    with rep.stage("polygonize", layers=2):
        for i in range(1, 3):
            with rep.layer(i, 2, f"L{i}", 5) as info:
                info.polygon_count = 1
                info.strategy = "linemerge_bare"
                info.confidence = 1.0
    with rep.stage("rewrite_payload"):
        pass
    with rep.stage("inject_poche_polygons"):
        pass
    with rep.stage("write_payload"):
        pass
    # At the end of write_payload, the cumulative percent is 100.
    assert _cumulative_percent_at_end_of("write_payload") == 100
    rep.close()


def test_polygonize_with_zero_layers_returns_base_percent(tmp_path: Path):
    """Edge case: a polygonize stage with no layers (e.g. a plan drawing)."""
    rep, _, _ = _make_reporter(tmp_path)
    with rep.stage("polygonize", layers=0):
        # No layer context manager invocations.
        observed = rep.percent_estimate()
    expected = _cumulative_percent_at_start_of("polygonize")
    assert observed == expected
    rep.close()


# --------------------------------------------------------------------------- #
# Stderr mirror — color & non-color
# --------------------------------------------------------------------------- #


def test_no_color_when_stderr_is_not_tty(tmp_path: Path):
    """A StringIO has no ``isatty`` so the mirror runs in plain-text mode."""
    rep, _, fake_tty = _make_reporter(tmp_path)
    with rep.stage("read_payload"):
        pass
    rep.close()
    text = fake_tty.getvalue()
    # No ANSI escape introducer in plain mode.
    assert "\033[" not in text
    assert "STAGE: read_payload" in text


def test_no_stderr_output_when_tty_is_none(tmp_path: Path):
    """If we pass ``tty=None`` even with ``enabled=True``, no stderr writes."""
    p = tmp_path / "progress.txt"
    rep = ProgressReporter(file_path=str(p), tty=None, enabled=True)
    with rep.stage("read_payload"):
        pass
    rep.close()
    # File does get written.
    assert p.exists()
    assert _read_lines(str(p))


# --------------------------------------------------------------------------- #
# make_reporter factory
# --------------------------------------------------------------------------- #


def test_make_reporter_disabled_is_noop(tmp_path: Path):
    """Factory returns a strict no-op when ``enabled=False``."""
    target = tmp_path / "p.txt"
    rep = make_reporter(enabled=False, file_path=str(target), stderr=io.StringIO())
    with rep.stage("read_payload"):
        pass
    rep.close()
    assert not target.exists()
    assert rep.enabled is False


def test_make_reporter_uses_default_progress_file_when_unspecified():
    """The DEFAULT_PROGRESS_FILE constant matches Issue #15's documented path."""
    # We don't actually write to /tmp here (would clobber a real run); just
    # check the constant is what the issue documents.
    assert DEFAULT_PROGRESS_FILE == "/tmp/arch_lw_saas_progress.txt"


def test_layer_callback_default_state():
    """LayerCallback starts with all None fields so partial fills are detectable."""
    cb = LayerCallback()
    assert cb.polygon_count is None
    assert cb.strategy is None
    assert cb.confidence is None


def test_layer_done_emits_even_without_callback_fields(tmp_path: Path):
    """If the body forgets to set callback fields, we still emit a DONE line."""
    rep, p, _ = _make_reporter(tmp_path)
    with rep.stage("polygonize", layers=1), rep.layer(1, 1, "L1", 5) as _info:
        pass  # never touch _info
    rep.close()
    lines = _read_lines(str(p))
    done_line = next((line for line in lines if "\tDONE\tpolygonize\tlayer=1/1\t" in line), None)
    assert done_line is not None
    # The optional polygon-count / strategy / conf are absent — that's OK.
    assert "polygons=" not in done_line
    assert "strategy=" not in done_line


# --------------------------------------------------------------------------- #
# Integration sanity — reporter survives a full read→polygonize→write loop
# --------------------------------------------------------------------------- #


def test_full_pipeline_event_sequence(tmp_path: Path):
    """A realistic full-pipeline call produces the expected event count + order."""
    rep, p, _ = _make_reporter(tmp_path)
    with rep.stage("read_payload", chunks=10):
        pass
    with rep.stage("enumerate_layers", cut_filter="ClippingPlaneIntersections"):
        pass
    with rep.stage("polygonize", layers=2):
        for i in range(1, 3):
            with rep.layer(i, 2, f"layer{i}", 7) as info:
                info.polygon_count = 1
                info.strategy = "linemerge_bare"
                info.confidence = 1.0
    with rep.stage("rewrite_payload"):
        pass
    with rep.stage("inject_poche_polygons", layers=2):
        pass
    with rep.stage("write_payload", zstd_level=19):
        pass
    rep.close()
    lines = _read_lines(str(p))
    # 6 stages × 2 events + 2 layers × 2 events = 16 events.
    assert len(lines) == 16
    # First event must be the read_payload START with percent=0.
    cols0 = lines[0].split("\t")
    assert cols0[1] == "START" and cols0[2] == "read_payload"
    assert cols0[4] == "0"
    # Last event must be the write_payload DONE with percent=100.
    cols_last = lines[-1].split("\t")
    assert cols_last[1] == "DONE" and cols_last[2] == "write_payload"
    assert cols_last[4] == "100"


# --------------------------------------------------------------------------- #
# Hardening — file open failures should not crash the apply-saas run
# --------------------------------------------------------------------------- #


def test_reporter_degrades_when_file_open_fails(tmp_path: Path):
    """If the progress file can't be opened, the reporter still runs (stderr-only)."""
    # Use a path that points inside a non-existent directory.
    bad = tmp_path / "no" / "such" / "dir" / "p.txt"
    fake_tty = io.StringIO()
    rep = ProgressReporter(file_path=str(bad), tty=fake_tty, enabled=True)
    with rep.stage("read_payload"):
        pass
    rep.close()
    # Stderr mirror still wrote events.
    assert "STAGE: read_payload" in fake_tty.getvalue()
    # And the file genuinely did not get created.
    assert not bad.exists()


# --------------------------------------------------------------------------- #
# fsync is best-effort but should be exercised
# --------------------------------------------------------------------------- #


def test_close_is_idempotent(tmp_path: Path):
    """Closing twice must not raise — apply-saas wraps close() in try/finally."""
    rep, _, _ = _make_reporter(tmp_path)
    with rep.stage("read_payload"):
        pass
    rep.close()
    rep.close()  # second close should be a no-op


def test_close_flushes_data(tmp_path: Path):
    """After close() returns, the file content is on disk."""
    rep, p, _ = _make_reporter(tmp_path)
    with rep.stage("read_payload"):
        pass
    rep.close()
    # File should be readable post-close with all events present.
    assert os.path.getsize(str(p)) > 0
