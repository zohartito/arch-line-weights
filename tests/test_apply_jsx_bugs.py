"""Tests for the four apply-jsx UX bugs surfaced during Phase A1 (2026-05-01).

Closes:
  * Issue #8  — JSX heartbeat polling
  * Issue #10 — `[Converted]` doc-state detection
  * Issue #11 — configurable `--timeout` + ARCH_LW_JSX_TIMEOUT_MIN env var
  * Issue #13 — `--preset` flag + JSX template parameterisation

These tests exercise the pure-Python primitives only (no live Illustrator).
The heartbeat poller is verified by writing to a synthetic heartbeat file
the way the JSX would, and asserting the wrapper picks up the lines.
"""

from __future__ import annotations

import time

import pytest
from click.testing import CliRunner

from arch_line_weights.apply_jsx import (
    DEFAULT_TIMEOUT_MIN,
    HEARTBEAT_POLL_SEC,
    MAX_TIMEOUT_MIN,
    STALE_HEARTBEAT_SEC,
    TIMEOUT_ENV_VAR,
    _HeartbeatPoller,
    _is_converted_match,
    render_jsx,
    resolve_timeout_minutes,
)
from arch_line_weights.cli import cli
from arch_line_weights.layer_classify import (
    Source,
    as_jsx_function,
    tier_weights_for_preset,
)

# --------------------------------------------------------------------------- #
# Issue #8 — heartbeat polling
# --------------------------------------------------------------------------- #


def test_heartbeat_poller_picks_up_appended_lines(tmp_path):
    """Writes new lines to the heartbeat file and confirms the poller reads
    them in order, the way the JSX does in production."""
    hb = tmp_path / "hb.txt"
    hb.write_text("")  # JSX truncates on launch

    captured: list[str] = []
    poller = _HeartbeatPoller(
        str(hb),
        poll_interval=0.05,
        stale_threshold_sec=10,
        printer=lambda s: captured.append(s),
    )
    poller.start()

    try:
        # Mimic the JSX writing per-layer status lines.
        with open(hb, "a", encoding="utf-8") as f:
            f.write("starting\n")
            f.flush()
        time.sleep(0.2)

        with open(hb, "a", encoding="utf-8") as f:
            f.write("1/3: foo (10 paths)\n")
            f.write("2/3: bar (12 paths)\n")
            f.flush()
        time.sleep(0.2)

        with open(hb, "a", encoding="utf-8") as f:
            f.write("3/3: baz (8 paths)\n")
            f.write("DONE\n")
            f.flush()
        time.sleep(0.3)
    finally:
        poller.stop()
        poller.join(timeout=2)

    text = "\n".join(captured)
    assert "starting" in text
    assert "1/3: foo (10 paths)" in text
    assert "2/3: bar (12 paths)" in text
    assert "3/3: baz (8 paths)" in text
    assert poller.done is True
    assert poller.lines_seen >= 5


def test_heartbeat_poller_emits_stale_warning(tmp_path):
    """If no new bytes arrive within the stale threshold, the poller emits
    a single warning (and does NOT abort)."""
    hb = tmp_path / "hb.txt"
    hb.write_text("starting\n")

    captured: list[str] = []
    # Force a tiny stale threshold so the warning fires fast.
    poller = _HeartbeatPoller(
        str(hb),
        poll_interval=0.05,
        stale_threshold_sec=0.3,
        printer=lambda s: captured.append(s),
    )
    poller.start()

    try:
        # Wait long enough for the staleness check to trigger.
        time.sleep(0.7)
    finally:
        poller.stop()
        poller.join(timeout=2)

    warnings = [c for c in captured if "no JSX heartbeat" in c]
    assert len(warnings) >= 1, f"expected a stale-heartbeat warning, got {captured}"
    assert poller.stale_warning_emitted is True
    # Must NOT mark itself done — abort is the user's call.
    assert poller.done is False


def test_heartbeat_poll_constants_have_sane_defaults():
    assert HEARTBEAT_POLL_SEC == 2
    assert STALE_HEARTBEAT_SEC == 300


# --------------------------------------------------------------------------- #
# Issue #10 — [Converted] state detection
# --------------------------------------------------------------------------- #


def test_is_converted_match_basic_ai_suffix():
    """`macro.ai` opened as `macro [Converted].ai` matches."""
    assert _is_converted_match("macro [Converted].ai", None, "/path/to/macro.ai") is True


def test_is_converted_match_basic_no_extension():
    """Some Illustrator versions display `[Converted]` without the .ai suffix."""
    assert _is_converted_match("macro [Converted]", None, "/path/to/macro.ai") is True


def test_is_converted_match_does_not_match_unrelated_doc():
    """A `[Converted]` doc with a different basename must NOT match."""
    assert (
        _is_converted_match("other_drawing [Converted].ai", None, "/path/to/macro.ai")
        is False
    )


def test_is_converted_match_does_not_match_non_converted_doc():
    """A regular saved doc (no `[Converted]`) must NOT match — the wrapper
    falls through to the normal `open POSIX file` path."""
    assert _is_converted_match("macro.ai", "/path/to/macro.ai", "/path/to/macro.ai") is False


def test_is_converted_match_returns_false_when_no_active_doc():
    assert _is_converted_match(None, None, "/path/to/macro.ai") is False


def test_is_converted_match_with_saved_path_to_same_file(tmp_path):
    """If AppleScript reports a saved path AND it points at the source,
    accept the [Converted] state as a match."""
    src = tmp_path / "macro.ai"
    src.write_text("dummy")
    assert (
        _is_converted_match("macro [Converted].ai", str(src), str(src)) is True
    )


def test_is_converted_match_with_saved_path_to_different_file(tmp_path):
    """If the active doc has a saved path to a *different* file, reject."""
    other = tmp_path / "other.ai"
    other.write_text("dummy")
    src = tmp_path / "macro.ai"
    src.write_text("dummy")
    assert (
        _is_converted_match("macro [Converted].ai", str(other), str(src)) is False
    )


# --------------------------------------------------------------------------- #
# Issue #11 — configurable timeout
# --------------------------------------------------------------------------- #


def test_resolve_timeout_uses_default_when_unset(monkeypatch):
    monkeypatch.delenv(TIMEOUT_ENV_VAR, raising=False)
    assert resolve_timeout_minutes(None) == DEFAULT_TIMEOUT_MIN


def test_resolve_timeout_explicit_arg_wins_over_env(monkeypatch):
    monkeypatch.setenv(TIMEOUT_ENV_VAR, "120")
    assert resolve_timeout_minutes(45) == 45


def test_resolve_timeout_reads_env_var(monkeypatch):
    monkeypatch.setenv(TIMEOUT_ENV_VAR, "90")
    assert resolve_timeout_minutes(None) == 90


def test_resolve_timeout_falls_back_when_env_is_garbage(monkeypatch):
    monkeypatch.setenv(TIMEOUT_ENV_VAR, "not-a-number")
    assert resolve_timeout_minutes(None) == DEFAULT_TIMEOUT_MIN


def test_resolve_timeout_clamps_at_max(monkeypatch):
    monkeypatch.delenv(TIMEOUT_ENV_VAR, raising=False)
    assert resolve_timeout_minutes(9999) == MAX_TIMEOUT_MIN


def test_resolve_timeout_clamps_at_min(monkeypatch):
    monkeypatch.delenv(TIMEOUT_ENV_VAR, raising=False)
    assert resolve_timeout_minutes(0) == 1
    assert resolve_timeout_minutes(-50) == 1


def test_cli_apply_jsx_help_shows_timeout_flag():
    runner = CliRunner()
    result = runner.invoke(cli, ["apply-jsx", "--help"])
    assert result.exit_code == 0
    assert "--timeout" in result.output


def test_cli_apply_jsx_rejects_timeout_above_max():
    runner = CliRunner()
    result = runner.invoke(cli, ["apply-jsx", "--timeout=999", "/nope.ai"])
    # IntRange will reject 999 before we even hit the path resolver.
    assert result.exit_code != 0
    assert "999" in result.output or "Invalid" in result.output


# --------------------------------------------------------------------------- #
# Issue #13 — --preset flag + JSX template parameterisation
# --------------------------------------------------------------------------- #


def test_tier_weights_for_section_preset_matches_classifier():
    """Section preset (default) should produce weights that match the
    classifier's stock values for the cut tier."""
    weights = tier_weights_for_preset("section")
    # cut→cut at 1.0pt is the section ladder's heaviest tier
    assert weights["cut"] == pytest.approx(1.0)
    # structure_primary → profile (0.5pt)
    assert weights["structure_primary"] == pytest.approx(0.5)


def test_tier_weights_for_plan_preset_uses_walls_cut():
    """Plan preset re-maps `cut` to `walls_cut` — 1 ISO step lighter (0.71pt screen)."""
    weights = tier_weights_for_preset("plan")
    assert weights["cut"] == pytest.approx(0.71, abs=0.01)
    # casework is the analog of structure_primary in plan
    assert weights["structure_primary"] == pytest.approx(0.5, abs=0.01)


def test_tier_weights_for_elevation_preset_uses_silhouette():
    """Elevation has no cut tier; the heaviest line is the silhouette."""
    weights = tier_weights_for_preset("elevation")
    assert weights["cut"] == pytest.approx(1.0, abs=0.01)  # silhouette = 1.0pt screen


def test_tier_weights_for_detail_preset_is_heavier():
    """Detail preset shifts everything 1 ISO step up; cut_primary at 1.5pt screen."""
    weights = tier_weights_for_preset("detail")
    assert weights["cut"] == pytest.approx(1.5, abs=0.01)
    # detail's analog of structure_primary is cut_secondary (1.0 pt screen)
    assert weights["structure_primary"] == pytest.approx(1.0, abs=0.01)


def test_as_jsx_function_with_no_preset_preserves_v051_behaviour():
    """Passing preset=None must keep the v0.5.1 hardcoded weights."""
    jsx = as_jsx_function(preset=None)
    # The cut tier (heaviest) should still emit 1.0
    assert "return 1.0;" in jsx
    # structure_primary tier
    assert "return 0.5;" in jsx


def test_as_jsx_function_with_plan_preset_emits_plan_weights():
    """Plan preset's cut→walls_cut(0.71) should appear in the emitted JS."""
    jsx = as_jsx_function(preset="plan")
    # The CLIPPINGPLANEINTERSECTIONS rule must now emit 0.71 (plan walls_cut)
    assert "CLIPPINGPLANEINTERSECTIONS" in jsx
    assert "return 0.71" in jsx
    # And no longer emit the section default of 1.0 for cut
    # (other rules might still emit 1.0; we only check that 0.71 is present)


def test_as_jsx_function_with_detail_preset_emits_detail_weights():
    """Detail preset cut_primary at 1.5pt screen must appear."""
    jsx = as_jsx_function(preset="detail")
    assert "return 1.5" in jsx


def test_render_jsx_embeds_preset_weights():
    """End-to-end: render_jsx() with preset='plan' must produce a JSX
    string containing the plan-preset weights."""
    out = render_jsx(
        "/tmp/src.ai",
        "/tmp/dst.ai",
        "/tmp/p.txt",
        "/tmp/r.txt",
        "/tmp/h.txt",
        preset="plan",
    )
    assert "/tmp/src.ai" in out
    assert "/tmp/h.txt" in out
    assert "return 0.71" in out


def test_render_jsx_default_no_preset_matches_v051():
    """Without preset, the rendered JSX must contain the v0.5.1 weights."""
    out = render_jsx(
        "/tmp/src.ai",
        "/tmp/dst.ai",
        "/tmp/p.txt",
        "/tmp/r.txt",
        "/tmp/h.txt",
    )
    assert "return 1.0;" in out  # cut tier
    assert "return 0.5;" in out  # structure_primary tier


def test_render_jsx_use_open_doc_flag_is_propagated():
    """When `use_open_doc=True`, the JSX template's USE_OPEN_DOC literal must be `true`."""
    out_true = render_jsx(
        "/tmp/src.ai",
        "/tmp/dst.ai",
        "/tmp/p.txt",
        "/tmp/r.txt",
        "/tmp/h.txt",
        use_open_doc=True,
    )
    assert "var USE_OPEN_DOC = true;" in out_true

    out_false = render_jsx(
        "/tmp/src.ai",
        "/tmp/dst.ai",
        "/tmp/p.txt",
        "/tmp/r.txt",
        "/tmp/h.txt",
        use_open_doc=False,
    )
    assert "var USE_OPEN_DOC = false;" in out_false


def test_cli_apply_jsx_help_shows_preset_flag():
    runner = CliRunner()
    result = runner.invoke(cli, ["apply-jsx", "--help"])
    assert result.exit_code == 0
    assert "--preset" in result.output
    # All four preset family names must appear in the help output.
    for name in ("section", "plan", "elevation", "detail"):
        assert name in result.output


def test_cli_apply_jsx_help_shows_for_print_flag():
    runner = CliRunner()
    result = runner.invoke(cli, ["apply-jsx", "--help"])
    assert result.exit_code == 0
    assert "--for-print" in result.output


def test_section_preset_default_preserves_v051_weights():
    """`--preset section` (the new default) must produce JSX weights
    byte-identical to the v0.5.1 hardcoded weights, so existing users see
    zero behaviour change. The CLI achieves this by mapping the default
    `--preset section` to `preset=None` internally.

    Verified by checking that `as_jsx_function(preset=None)` and the
    section preset both emit 1.0pt for the cut tier and 0.5pt for
    structure_primary — the two heaviest classifier tiers."""
    jsx_none = as_jsx_function(preset=None)
    weights_section = tier_weights_for_preset("section")
    # Section cross-walk must reproduce the v0.5.1 cut + structure_primary weights.
    assert weights_section["cut"] == pytest.approx(1.0)
    assert weights_section["structure_primary"] == pytest.approx(0.5)
    # And the no-preset emitter must still contain those.
    assert "return 1.0;" in jsx_none
    assert "return 0.5;" in jsx_none


def test_cli_apply_jsx_rejects_unknown_preset():
    runner = CliRunner()
    result = runner.invoke(cli, ["apply-jsx", "--preset=unknown", "/nope.ai"])
    assert result.exit_code != 0
    # click.Choice will reject before resolving the path
    assert "unknown" in result.output or "Invalid" in result.output


# --------------------------------------------------------------------------- #
# JSX template invariants — make sure the heartbeat hook is still wired
# --------------------------------------------------------------------------- #


def test_jsx_template_has_heartbeat_hook():
    """Sanity: the rendered JSX must contain the per-layer heartbeat call so
    the wrapper poller has lines to consume."""
    out = render_jsx(
        "/tmp/src.ai",
        "/tmp/dst.ai",
        "/tmp/p.txt",
        "/tmp/r.txt",
        "/tmp/h.txt",
    )
    assert "heartbeat(" in out
    # Final DONE line is what the poller watches for.
    assert 'heartbeat("DONE")' in out


def test_jsx_template_substitutes_all_placeholders():
    """No `__FOO__` placeholders may survive into the rendered JSX."""
    out = render_jsx(
        "/tmp/src.ai",
        "/tmp/dst.ai",
        "/tmp/p.txt",
        "/tmp/r.txt",
        "/tmp/h.txt",
    )
    for tag in (
        "__TARGET__",
        "__OUTPUT__",
        "__PROGRESS__",
        "__REPORT__",
        "__HEARTBEAT__",
        "__USE_OPEN_DOC__",
        "__CLASSIFIER__",
    ):
        assert tag not in out, f"unsubstituted placeholder: {tag}"


# --------------------------------------------------------------------------- #
# AutoCAD source still works through the new emitter
# --------------------------------------------------------------------------- #


def test_as_jsx_function_autocad_source_with_no_preset():
    """The new preset arg must not break the AutoCAD pattern library path."""
    jsx = as_jsx_function(source=Source.AUTOCAD, preset=None)
    assert "function weightFor" in jsx
    assert 'n = "-" + n + "-";' in jsx
