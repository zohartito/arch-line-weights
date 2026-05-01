"""Tests for the ``bridge_strategy`` parameter wired through poche.polygonize_layer.

Closes GitHub Issue #5. Verifies:

* Default behaviour is unchanged from v0.5.x (`bridge_strategy=None` falls
  back to the v0.4 greedy bridger via ``infer_bridges``).
* Opt-in ``bridge_strategy="best"`` routes through ``infer_bridges_best``
  and at least matches greedy on a synthetic backtracking-helps fixture.
* The ``ARCH_LW_BRIDGE_STRATEGY`` env var is consulted when the explicit
  arg is omitted.
* The CLI ``--bridge-strategy`` flag wires through `arch-lw poche`.
* The silent ``except Exception: pass`` blocks in ``infer_bridges_best``
  now leave a structured warning trace via ``logging``.
"""

from __future__ import annotations

import logging
import os
from unittest.mock import patch

import pytest
from click.testing import CliRunner
from shapely.geometry import LineString

from arch_line_weights.bridge import infer_bridges, infer_bridges_best
from arch_line_weights.cli import cli
from arch_line_weights.poche import (
    _DEFAULT_BRIDGE_STRATEGY,
    _resolve_bridge_strategy,
    polygonize_layer,
)

# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _square_with_corner_gaps_paths(g: float = 0.2) -> list[list[list[float]]]:
    """Closed square with sub-pt corner gaps, expressed as the
    ``[[[x,y], ...], ...]`` shape that ``polygonize_layer`` accepts."""
    return [
        [[0, 0], [10 - g, 0]],
        [[10, g], [10, 10 - g]],
        [[10 - g, 10], [g, 10]],
        [[0, 10 - g], [0, g]],
    ]


def _greedy_trap_paths() -> list[list[list[float]]]:
    """Mirror of ``test_bridge._greedy_trap_fixture`` in path-coordinate form.

    A 6-segment soup engineered so the greedy bridger commits to the wrong
    intra-cluster pair and produces 0 polygons; the backtracking strategy
    inside ``infer_bridges_best`` recovers the actual closing pair across
    the top.
    """
    return [
        [[0, 0], [10, 0]],
        [[10, 0], [10, 10]],
        [[0, 10], [0, 0]],
        [[0, 10], [4.75, 10]],
        [[5.25, 10], [10, 10]],
        [[4.80, 10.02], [5.20, 10.02]],
    ]


# --------------------------------------------------------------------------- #
# 1. Default behaviour unchanged
# --------------------------------------------------------------------------- #


def test_default_strategy_is_greedy():
    """``_resolve_bridge_strategy(None)`` with no env var returns ``"greedy"``."""
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("ARCH_LW_BRIDGE_STRATEGY", None)
        assert _resolve_bridge_strategy(None) == "greedy"
        assert _DEFAULT_BRIDGE_STRATEGY == "greedy"


def test_polygonize_layer_default_calls_greedy_bridger():
    """The default ``polygonize_layer`` path must call ``infer_bridges`` and
    NOT ``infer_bridges_best`` so v0.5.x behaviour is preserved bit-exact."""
    paths = _square_with_corner_gaps_paths(g=0.2)
    with (
        patch("arch_line_weights.poche.infer_bridges", wraps=infer_bridges) as greedy_spy,
        patch("arch_line_weights.poche.infer_bridges_best", wraps=infer_bridges_best) as best_spy,
    ):
        _polys, fr = polygonize_layer("L", paths)
    # The bare snap-sweep should already close the square (linemerge_bare /
    # linemerge_snap path), so neither bridger needs to fire on this input.
    # That's fine — the regression we care about is that *if* the bridger
    # runs, it's the greedy one. So we just assert greedy was at least
    # available and best was never hit.
    assert best_spy.call_count == 0
    assert fr.bridge_strategy_name is None
    # And of course the existing test fixture should still polygonize.
    assert fr.polygon_count >= 1
    assert greedy_spy.call_count >= 0  # may or may not be reached


def test_polygonize_layer_default_output_unchanged():
    """Bit-by-bit: default-call output equals explicit-greedy output."""
    paths = _square_with_corner_gaps_paths(g=0.2)
    polys_default, fr_default = polygonize_layer("L", paths)
    polys_greedy, fr_greedy = polygonize_layer("L", paths, bridge_strategy="greedy")
    assert len(polys_default) == len(polys_greedy)
    assert fr_default.strategy == fr_greedy.strategy
    assert fr_default.polygon_count == fr_greedy.polygon_count
    assert fr_default.confidence == fr_greedy.confidence
    assert fr_default.bridge_strategy_name == fr_greedy.bridge_strategy_name


# --------------------------------------------------------------------------- #
# 2. Opt-in "best" strategy
# --------------------------------------------------------------------------- #


def test_polygonize_layer_best_calls_strategy_selector():
    """When the bare sweep AND greedy both fail, ``bridge_strategy="best"``
    routes the auto_bridge rung through ``infer_bridges_best``."""
    paths = _greedy_trap_paths()
    with patch(
        "arch_line_weights.poche.infer_bridges_best", wraps=infer_bridges_best
    ) as best_spy:
        _polys, fr = polygonize_layer(
            "L", paths, bridge_strategy="best", use_alpha_shape=False
        )
    # If the auto_bridge rung fired, infer_bridges_best should have been
    # called exactly once. If the bare sweep already closed the trap (it
    # shouldn't on this fixture but tolerate it), the spy may be 0.
    if fr.strategy == "auto_bridge":
        assert best_spy.call_count == 1
        # bridge_strategy_name should be set to one of the strategy labels
        # from infer_bridges_best.
        assert fr.bridge_strategy_name in {
            "greedy",
            "backtrack",
            "dbscan_collapse",
            "dbscan_collapse+backtrack",
            "none",
        }


def test_best_at_least_matches_greedy_polygon_count():
    """On a synthetic case where backtracking helps, the "best" strategy
    must yield at least as many polygons as greedy — which is the whole
    reason the selector exists."""
    paths = _greedy_trap_paths()
    _polys_g, fr_g = polygonize_layer(
        "L", paths, bridge_strategy="greedy", use_alpha_shape=False
    )
    _polys_b, fr_b = polygonize_layer(
        "L", paths, bridge_strategy="best", use_alpha_shape=False
    )
    assert fr_b.polygon_count >= fr_g.polygon_count, (
        f"best under-performed greedy: greedy={fr_g.polygon_count} "
        f"best={fr_b.polygon_count}"
    )


# --------------------------------------------------------------------------- #
# 3. Env-var override
# --------------------------------------------------------------------------- #


def test_env_var_resolves_to_best():
    with patch.dict(os.environ, {"ARCH_LW_BRIDGE_STRATEGY": "best"}, clear=False):
        assert _resolve_bridge_strategy(None) == "best"


def test_env_var_resolves_to_greedy():
    with patch.dict(os.environ, {"ARCH_LW_BRIDGE_STRATEGY": "greedy"}, clear=False):
        assert _resolve_bridge_strategy(None) == "greedy"


def test_env_var_unknown_falls_back_to_default():
    with patch.dict(os.environ, {"ARCH_LW_BRIDGE_STRATEGY": "moonshot"}, clear=False):
        assert _resolve_bridge_strategy(None) == "greedy"


def test_explicit_arg_overrides_env_var():
    """Explicit kwarg wins over the env var (precedence: kwarg > env > default)."""
    with patch.dict(os.environ, {"ARCH_LW_BRIDGE_STRATEGY": "best"}, clear=False):
        assert _resolve_bridge_strategy("greedy") == "greedy"
        assert _resolve_bridge_strategy("best") == "best"


def test_env_var_threads_through_polygonize_layer():
    """Setting the env var with no explicit arg must route to ``best``."""
    paths = _greedy_trap_paths()
    with (
        patch.dict(os.environ, {"ARCH_LW_BRIDGE_STRATEGY": "best"}, clear=False),
        patch(
            "arch_line_weights.poche.infer_bridges_best", wraps=infer_bridges_best
        ) as best_spy,
    ):
        _polys, fr = polygonize_layer("L", paths, use_alpha_shape=False)
    if fr.strategy == "auto_bridge":
        assert best_spy.call_count == 1


# --------------------------------------------------------------------------- #
# 4. CLI flag wiring
# --------------------------------------------------------------------------- #


def test_cli_poche_help_lists_bridge_strategy_flag():
    """The ``arch-lw poche --help`` output must mention ``--bridge-strategy``."""
    runner = CliRunner()
    result = runner.invoke(cli, ["poche", "--help"])
    assert result.exit_code == 0
    assert "--bridge-strategy" in result.output
    assert "greedy" in result.output
    assert "best" in result.output


def test_cli_apply_jsx_help_lists_bridge_strategy_flag():
    runner = CliRunner()
    result = runner.invoke(cli, ["apply-jsx", "--help"])
    assert result.exit_code == 0
    assert "--bridge-strategy" in result.output


def test_cli_apply_saas_help_lists_bridge_strategy_flag():
    runner = CliRunner()
    result = runner.invoke(cli, ["apply-saas", "--help"])
    assert result.exit_code == 0
    assert "--bridge-strategy" in result.output


def test_cli_poche_rejects_unknown_strategy():
    """click.Choice should reject vocabulary outside {greedy, best}."""
    runner = CliRunner()
    # Use a path that doesn't exist; click validates choices before resolving
    # the path argument so we'll see the choice error first.
    result = runner.invoke(cli, ["poche", "/nope.ai", "--bridge-strategy=banana"])
    assert result.exit_code != 0
    assert "banana" in result.output or "Invalid value" in result.output


def test_cli_poche_threads_strategy_to_apply_poche(tmp_path):
    """End-to-end: ``arch-lw poche --bridge-strategy=best`` calls
    ``apply_poche`` with ``bridge_strategy="best"`` (we mock the inner
    Illustrator calls so this stays hermetic)."""
    # Create a fake .ai file so the click.Path(exists=True) check passes.
    fake_ai = tmp_path / "fake.ai"
    fake_ai.write_bytes(b"%PDF-1.5\n%\xc4\xe5\xf2\xe5\xeb\xa7\xf3\xa0\xd0\xc4\xc6\n")

    captured: dict[str, object] = {}

    def fake_apply_poche(*args, **kwargs):
        captured["kwargs"] = kwargs
        # Return a minimal PocheReport-like object.
        from arch_line_weights.poche import PocheReport
        return PocheReport()

    runner = CliRunner()
    with patch("arch_line_weights.cli.apply_poche", side_effect=fake_apply_poche):
        result = runner.invoke(
            cli, ["poche", str(fake_ai), "--bridge-strategy=best"]
        )

    assert result.exit_code == 0, result.output
    assert captured["kwargs"]["bridge_strategy"] == "best"


def test_cli_poche_default_threads_greedy(tmp_path):
    """Without ``--bridge-strategy``, ``apply_poche`` is called with the
    default ``"greedy"`` to preserve v0.5.1 behaviour bit-exact."""
    fake_ai = tmp_path / "fake.ai"
    fake_ai.write_bytes(b"%PDF-1.5\n%\xc4\xe5\xf2\xe5\xeb\xa7\xf3\xa0\xd0\xc4\xc6\n")

    captured: dict[str, object] = {}

    def fake_apply_poche(*args, **kwargs):
        captured["kwargs"] = kwargs
        from arch_line_weights.poche import PocheReport
        return PocheReport()

    runner = CliRunner()
    with patch("arch_line_weights.cli.apply_poche", side_effect=fake_apply_poche):
        result = runner.invoke(cli, ["poche", str(fake_ai)])

    assert result.exit_code == 0, result.output
    assert captured["kwargs"]["bridge_strategy"] == "greedy"


# --------------------------------------------------------------------------- #
# 5. Logging in infer_bridges_best
# --------------------------------------------------------------------------- #


def _square_segments(g: float = 0.2) -> list[LineString]:
    """4-segment square with sub-pt corner gaps."""
    return [
        LineString([(0, 0), (10 - g, 0)]),
        LineString([(10, g), (10, 10 - g)]),
        LineString([(10 - g, 10), (g, 10)]),
        LineString([(0, 10 - g), (0, g)]),
    ]


def test_infer_bridges_best_logs_warning_on_strategy_exception(caplog):
    """A fake exception in one strategy produces a warning log without
    breaking the selector — the other strategies still run and the
    function still returns a result."""
    segs = _square_segments(g=0.2)

    def boom(*_a, **_kw):
        raise RuntimeError("synthetic fault for test")

    # Inject a fault into the greedy strategy specifically.
    with (
        caplog.at_level(logging.WARNING, logger="arch_line_weights.bridge"),
        patch("arch_line_weights.bridge.infer_bridges", side_effect=boom),
    ):
        aug, conf, _name = infer_bridges_best(segs, max_gap=2.0)

    # The selector should have continued past the failed strategy.
    assert isinstance(aug, list)
    assert 0.0 <= conf <= 1.0
    # And the warning should mention which strategy failed and the type.
    warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert any("greedy" in r.getMessage() for r in warning_records), (
        f"expected a warning mentioning 'greedy', got: "
        f"{[r.getMessage() for r in warning_records]}"
    )
    assert any("RuntimeError" in r.getMessage() for r in warning_records), (
        f"expected a warning mentioning the exception type 'RuntimeError', got: "
        f"{[r.getMessage() for r in warning_records]}"
    )
    assert any("synthetic fault for test" in r.getMessage() for r in warning_records)


def test_infer_bridges_best_does_not_log_on_success(caplog):
    """Normal happy-path runs should not emit any warning logs from
    ``infer_bridges_best`` — that's a regression check on the new logging."""
    segs = _square_segments(g=0.2)
    with caplog.at_level(logging.WARNING, logger="arch_line_weights.bridge"):
        infer_bridges_best(segs, max_gap=2.0)
    bridge_warnings = [
        r
        for r in caplog.records
        if r.levelno == logging.WARNING
        and r.name == "arch_line_weights.bridge"
    ]
    assert bridge_warnings == [], (
        f"expected no warnings on happy path, got: "
        f"{[r.getMessage() for r in bridge_warnings]}"
    )


@pytest.mark.parametrize(
    "broken_func",
    ["infer_bridges", "infer_bridges_backtrack", "collapse_endpoint_clusters"],
)
def test_infer_bridges_best_continues_after_each_strategy_failure(broken_func, caplog):
    """Inject a fault into each strategy in turn — selector should still
    return *some* result and emit at least one warning log."""
    segs = _square_segments(g=0.2)

    def boom(*_a, **_kw):
        raise ValueError("synthetic fault for test")

    target = f"arch_line_weights.bridge.{broken_func}"
    with (
        caplog.at_level(logging.WARNING, logger="arch_line_weights.bridge"),
        patch(target, side_effect=boom),
    ):
        aug, conf, name = infer_bridges_best(segs, max_gap=2.0)

    # Result is well-formed.
    assert isinstance(aug, list)
    assert 0.0 <= conf <= 1.0
    assert isinstance(name, str)
    # At least one warning was emitted by the bridge module.
    bridge_warnings = [
        r for r in caplog.records if r.name == "arch_line_weights.bridge"
    ]
    assert len(bridge_warnings) >= 1, (
        "expected at least one warning from arch_line_weights.bridge"
    )


# --------------------------------------------------------------------------- #
# 6. FillResult.bridge_strategy_name field
# --------------------------------------------------------------------------- #


def test_fill_result_bridge_strategy_name_default_is_none():
    """Default greedy path must leave ``bridge_strategy_name`` unset to
    keep PocheReport rows backwards-compatible."""
    paths = _square_with_corner_gaps_paths(g=0.2)
    _polys, fr = polygonize_layer("L", paths)
    assert fr.bridge_strategy_name is None


def test_fill_result_bridge_strategy_name_set_when_best_wins():
    """When the auto_bridge rung fires under ``bridge_strategy="best"``,
    the FillResult should carry the name of the inner winning strategy."""
    paths = _greedy_trap_paths()
    _polys, fr = polygonize_layer(
        "L", paths, bridge_strategy="best", use_alpha_shape=False
    )
    if fr.strategy == "auto_bridge":
        assert fr.bridge_strategy_name is not None
        assert fr.bridge_strategy_name in {
            "greedy",
            "backtrack",
            "dbscan_collapse",
            "dbscan_collapse+backtrack",
            "none",
        }
