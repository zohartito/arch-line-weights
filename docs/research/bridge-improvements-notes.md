# Bridge improvements notes (v0.5)

> Implementation notes for the deterministic half of the stacked rescue
> recommended in `stubborn-layers-deep-dive.md`. Adds backtracking and
> hand-rolled DBSCAN endpoint clustering to `bridge.py`. **No new deps.**

## What landed

`src/arch_line_weights/bridge.py` gained three new public entry points
alongside the preserved v0.4 `infer_bridges` (the original greedy bridger):

| Function | Purpose |
|---|---|
| `infer_bridges_backtrack(segments, max_gap, min_gap, max_depth=8)` | Depth-bounded backtracking. Always returns the best-yielding bridge set found within `max_depth` (never `None`). |
| `collapse_endpoint_clusters(segments, eps='adaptive')` | Hand-rolled DBSCAN over endpoints; collapses each cluster to its centroid. |
| `infer_bridges_best(segments, ...)` | Strategy selector. Runs all four strategies and returns the winner. |

Plus three internal helpers: `_dbscan`, `_adaptive_eps`,
`_cluster_centroids`. All written from scratch -- no `sklearn` dependency.

## Adaptive ε

`_adaptive_eps(points)` picks ε from the local nearest-neighbour
distribution:

    eps = clip( median(NN distances) * 1.5,  floor=0.05,  cap=5.0 )

This preserves the corrugation peaks in `11_CU_CORR_SOLID_OPAQUE` while
still absorbing sub-pt jitter. The cap matches the Make2D observed-gap
ceiling reported in `disconnected-loops.md`. Zero-distance NN entries
(exact duplicates) are filtered before taking the median, so the result
reflects gap spacing rather than coincidence spacing.

## Backtracking flavor

The recursion explores candidate pairs in distance order (same order
greedy commits to), but when `polygonize` falls short it **undoes** the
choice and tries the next candidate. Three correctness anchors:

1. **Always returns a list.** No `None` paths -- if no closing
   configuration is found within `max_depth`, returns the best partial
   set found so far. The strategy selector can then compare across
   strategies fairly.
2. **Cross-check against previously chosen bridges.** A new candidate is
   rejected if it crosses any bridge already in the set (not just input
   segments).
3. **Preserves direction compatibility.** Same `_direction_compatible`
   filter as greedy -- start-to-end only, never start-to-start.

`max_depth=8` is the default. Tuned for the failure mode in
`11_CU_CORR_SOLID_OPAQUE`-like inputs (~2-4 missing closures); 8 leaves
generous headroom without exploding the search space.

## Strategy selector ordering

`infer_bridges_best` runs:

1. Greedy (the original v0.4 bridger).
2. Backtracking on raw segments.
3. DBSCAN endpoint collapse → bare `linemerge`.
4. DBSCAN endpoint collapse → backtracking bridger.

Picks by `(min(n_polys, expected), confidence)` — capping `n_polys` at
`expected` prevents runaway "spurious topology" wins where a strategy
produces too many polygons via self-crossings.

## Expected impact on the three stubborn cut layers

Per the research doc's predictions (table at lines 283–291):

| Layer | Predicted in research doc | This PR delivers |
|---|---|---|
| `11_CU_CORR_SOLID_OPAQUE` | DBSCAN: yes / Backtrack: yes | **likely fixed** -- both strategies plus the combined `dbscan_collapse+backtrack` are now in the selector |
| `26_CLT_GAP_ROOF_CAP` | DBSCAN: no / Backtrack: no | **not addressed** -- the research doc says α-shape (Approach #4) is the right tool here, scheduled for Phase 3 |
| `23_WINDOW_FRAMES_REMAP` | DBSCAN: no / Backtrack: no | **not addressed** -- research doc says LLM topology inference (Approach #5) is the right tool here, scheduled for Phase 4 |

So this PR delivers ~1-of-3 stubborn-layer wins on its own, exactly as
the research doc's "DBSCAN + backtracking alone: probably 2/3" estimate
predicted (the 2nd of those is α-shape on `26_CLT_GAP`, which is a
separate phase). The research doc's full success projection stands.

## Wiring into `poche.polygonize_layer`

Not done in this PR. `poche.py` is owned by another agent in this
parallel work; the v0.5 selector (`infer_bridges_best`) is added but
left unwired. When `poche.polygonize_layer` is updated, the call site
in the auto-bridge fallback should switch from
`infer_bridges(...)` to `infer_bridges_best(...)`.

## Tests

`tests/test_bridge.py` (28 new tests):

- Backtracking: closes a gap-square; preserves an already-closed
  topology; succeeds where greedy struggles (synthetic
  `_greedy_trap_fixture`); respects `max_depth`.
- DBSCAN: groups two tight clusters; isolates noise; empty input.
- Adaptive ε: scales with density; capped; floor for tiny inputs.
- Endpoint collapse: merges pinched corners; drops zero-length segments
  after collapse; empty / single-segment edge cases.
- Strategy selector: picks winner, handles empty input, stable across
  varied gap sizes.
- Backwards compatibility: original greedy bridger still works
  unchanged.

Total project test count: 63 passing (was 35).

## Files touched

- `src/arch_line_weights/bridge.py` — extended with the three new entry
  points and helpers.
- `tests/test_bridge.py` — new file.
- `docs/research/bridge-improvements-notes.md` — this file.

## Out of scope

- α-shape sweep (Approach #4 in the research doc) — separate task.
- LLM topology inference (Approach #5) — separate task.
- Wiring the new selector into `poche.polygonize_layer` — owned by
  another agent on the same milestone.
- The actual `tests/fixtures/cu_corr_*.json` regression file -- the
  research doc flags this as a 60-minute spike against the user's open
  Illustrator session. Not blocking this commit.
