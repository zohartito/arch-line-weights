# `bridge_strategy` wire-notes — closing GitHub Issue #5

Status: shipped, 2026-04-30. Wires the v0.5 `infer_bridges_best` strategy
selector into the `polygonize_layer` rescue ladder behind an opt-in flag,
and replaces the silent `except Exception: pass` blocks in
`infer_bridges_best` with structured warning logs.

## Why this change

The v0.5 work landed three additional bridging strategies in
`src/arch_line_weights/bridge.py`:

* `infer_bridges_backtrack` — depth-bounded backtracking that recovers from
  the `11_CU_CORR_SOLID_OPAQUE` failure mode where greedy commits to an
  intra-cluster endpoint pair instead of the across-the-gap one.
* `collapse_endpoint_clusters` — DBSCAN with adaptive ε that pinches near-
  coincident endpoints into a shared point so `linemerge` chains them
  without bridging.
* `infer_bridges_best` — strategy selector that runs all four (greedy,
  backtrack, DBSCAN collapse, DBSCAN+backtrack) and picks the highest-yield
  with the highest confidence.

Until now, `poche.polygonize_layer`'s auto-bridge rung still called the v0.4
greedy bridger directly. The new strategies were unreachable from the
production pipeline — issue #5.

## What's wired

### `polygonize_layer(..., bridge_strategy=None)`

`src/arch_line_weights/poche.py` gains a `bridge_strategy` keyword:

* `"greedy"` (default) — calls `bridge.infer_bridges`. Preserves v0.5.1
  behaviour bit-exact: tests verify `polygonize_layer(paths)` and
  `polygonize_layer(paths, bridge_strategy="greedy")` produce identical
  `FillResult` rows on every existing fixture.
* `"best"` — calls `bridge.infer_bridges_best`. The selector runs all four
  strategies and returns whichever produced the most polygons (capped at
  the expected count) with the highest confidence. The chosen inner
  strategy name (`"greedy"`, `"backtrack"`, `"dbscan_collapse"`,
  `"dbscan_collapse+backtrack"`, or `"none"`) is recorded on the
  `FillResult.bridge_strategy_name` field for per-layer logging.

Resolution order:

1. Explicit kwarg.
2. `ARCH_LW_BRIDGE_STRATEGY` environment variable.
3. Default (`"greedy"`).

Unknown values silently fall back to `"greedy"` — this is a tuning knob
and a typo shouldn't break the pipeline.

The wiring threads through `polygonize_dump`, `apply_poche`,
`compute_polygons_for_layers`, and `apply_saas_with_poche`, so both the
JSX and native-payload paths honour the flag.

### CLI: `--bridge-strategy {greedy,best}`

Added to three commands with identical vocabulary:

* `arch-lw poche --bridge-strategy=best` — primary use case; threads
  straight through to `apply_poche`.
* `arch-lw apply-saas --bridge-strategy=best` — only effective when
  combined with `--poche`. The CLI emits a warning if `--bridge-strategy`
  is set without `--poche` (matches the existing `--no-alpha-shape`
  warning behaviour).
* `arch-lw apply-jsx --bridge-strategy=best` — surfaced for symmetry. The
  JSX path doesn't currently call the polygonize ladder directly, but the
  selection is exported via `ARCH_LW_BRIDGE_STRATEGY` so any future
  poché-via-JSX step inherits it.

Default in all cases is `"greedy"` so cold runs stay v0.5.1-equivalent.

## Logging the strategy selector's silent failures

Quality review #3 flagged the four `except Exception: pass` blocks in
`infer_bridges_best`: a real bug in any sub-strategy would silently
disappear behind "no result". Each block now reads:

```
except Exception as e:
    _log.warning(
        "infer_bridges_best: strategy=<name> raised %s: %s; "
        "falling back to next strategy",
        type(e).__name__,
        e,
    )
```

The selector still continues to the next strategy (per task constraint —
"don't remove silent fallback behavior, just add logging"), but every
swallowed exception now leaves a structured trace at WARNING level.
Tests cover both the happy path (no warnings) and the per-strategy fault
path (one warning, selector still returns a usable result).

## Expected impact on the 3 stubborn cut layers

The v0.5 stubborn-layers research file
(`docs/research/stubborn-layers-deep-dive.md`) identified three layers
that fail the bare snap-sweep and that greedy alone can't recover:

1. `11_CU_CORR_SOLID_OPAQUE` — greedy commits to the intra-cluster pinch;
   backtracking recovers across-the-gap.
2. `26_CLT_GAP_ROOF_CAP` — multi-component topology; alpha-shape (already
   shipped) is the better fit, but DBSCAN+backtrack also helps.
3. `TEC_FOUNDATION_LIP` — corrugation peaks near the foundation lip;
   DBSCAN collapse pinches them cleanly.

Running `arch-lw poche ... --bridge-strategy=best` is expected to lift
each from `confidence < 0.5` to ≥ 0.75 by routing through the strategy
that matches the failure mode. The full reference-drawing benchmark is
not re-run here — the smoke test is just to confirm the flag wires
through end-to-end.

## What this does NOT change

* `bridge.infer_bridges` (greedy) is untouched — still the default and
  still the path the existing 202+ tests exercise.
* The silent fallback behaviour of `infer_bridges_best` is preserved.
  Per-strategy exceptions are logged but not raised; the selector still
  picks the best surviving result.
* CLI defaults are still `greedy` so existing scripts that call
  `arch-lw poche` produce byte-identical output.

## Test count

`tests/test_bridge_strategy.py` adds 23 new tests grouped:

1. Default behaviour unchanged (3 tests)
2. Opt-in `"best"` strategy (2 tests)
3. Env-var override + precedence (5 tests)
4. CLI flag wiring across the 3 commands (6 tests)
5. Logging in `infer_bridges_best` (5 tests, including parametrised)
6. `FillResult.bridge_strategy_name` field (2 tests)

Total project test count: 202 → 253 (the +28 between is pre-existing
alpha-shape tests already on disk before this task).
