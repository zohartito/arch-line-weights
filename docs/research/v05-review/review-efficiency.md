# v0.5 Efficiency Review — arch-line-weights

Reference drawing: 24 MB / 340K strokes / 62 layers / 21 cut layers / 55 MB decompressed AI24 payload.

---

## Top 3 efficiency issues by severity

### 1. SEVERITY: HIGH — `enumerate_layer_paths_from_payload` parses ALL 62 layers when only 21 are needed

**File:** `src/arch_line_weights/poche_saas.py`, lines ~338-411 + caller in `apply_saas_with_poche` line ~456-458.

The function accepts a `layer_filter: re.Pattern[bytes] | None` argument that can prune the output during the byte scan. But the caller does:

```python
cut_paths = enumerate_layer_paths_from_payload(payload)         # full payload, no filter
cut_paths = {k: v for k, v in cut_paths.items() if _is_cut_layer(k)}
```

This wastes work two ways: (a) the inner per-line tokenizer (`block.split(b"\r")`, then `line.split(b" ")` per line, then float parsing of `m`/`L`/`C` operators) runs for **every** layer including the ~41 non-cut layers — annotation, dimensions, hidden, curves, etc. On a 55 MB payload with 340 K strokes, the non-cut layers carry the bulk of the geometry. (b) The output dict accumulates per-layer path lists that are then thrown away.

Fix sketch: pass `layer_filter=re.compile(rb"ClippingPlaneIntersections")` and drop the post-filter. Saves on the order of 60-80% of the scan + parse cost on real Rhino exports. Hot path of every `apply-saas --poche` invocation.

### 2. SEVERITY: HIGH — Per-cut-layer polygonization is sequential when each layer is independent

**File:** `src/arch_line_weights/poche_saas.py`, `compute_polygons_for_layers` (lines ~262-300). Same shape in `poche.py` `polygonize_dump`.

The loop over `paths_by_layer.items()` calls `polygonize_layer` on each cut layer in series. `polygonize_layer` itself runs `TOLERANCE_SWEEP` (6 tolerances → 6 invocations of `_polys_at_tolerance` each calling `linemerge` + `polygonize`), and on layers that fail the sweep it falls through to `infer_bridges` (which the v0.5 wired-in `infer_bridges_best` makes 4× more expensive — see issue 3). Each layer's compute is **fully independent** (only `closing_lines` is shared, read-only after extraction).

For 21 cut layers on the reference drawing this is the dominant `apply-saas --poche` runtime. A `concurrent.futures.ProcessPoolExecutor` over the layers would give ~6-8x speedup on a typical M-series Mac (8 cores) since shapely C-extensions release the GIL but `infer_bridges_backtrack` is mostly Python — process-pool avoids the question.

### 3. SEVERITY: HIGH — `infer_bridges_best` runs all 4 strategies unconditionally; backtracking has unbounded `_polygon_count` cost per recursion node

**File:** `src/arch_line_weights/bridge.py`, `infer_bridges_best` (lines ~447-541) + `_backtrack_search` (lines ~316-386).

Two compounding problems:

**(a) Strategy selector fires all four strategies in series with no early exit.** It tries greedy, backtrack, DBSCAN, then DBSCAN+backtrack — even if greedy already returns `n_polys >= expected` with confidence 1.0. For layers where the bare snap-sweep fails but greedy succeeds (the v0.4 common case), this does 4× the work of v0.4. There's no `if results[0][0][0] >= expected: return` early-out.

**(b) `_backtrack_search` calls `_polygon_count(segments + bridges)` at every recursion node.** `_polygon_count` runs `linemerge(segments)` + `polygonize(...)` on the full segment list each time — both are O(n log n) over n segments. For a layer with 200 segments and depth 8, that's ~9 nodes deep × per-node O(n log n) shapely round-trips, all on freshly allocated Python lists (`segments + bridges` rebuilds every call).

See worst-case analysis below for the branching factor.

---

## Worst-case complexity analysis — new algorithms

### `_backtrack_search` (bridge.py)

- `N` = `len(candidates)`, sorted by gap distance. From a layer with `k` segments, `_collect_endpoints` produces `2k` endpoints. `_candidate_pairs` runs an STRtree `dwithin(max_gap=50)` query per endpoint and dedups symmetric pairs. On a real cut layer where the corrugation pinches sit close, many endpoints fall inside `max_gap`, so `N` is roughly `O(k)` to `O(k²)` depending on density. The 50 candidate pairs / 200 endpoints quoted in the prompt is realistic.
- The recursion tree at depth `D = max_depth = 8` has branching factor up to `N` at each level (the `for k in range(start_idx, len(candidates))` loop).
- **Worst-case nodes visited: O(N choose D) ≈ N^D / D! when commits monotonically advance `start_idx`.** With `N=50, D=8`: `50^8 / 8! ≈ 10^9`. With `N=100`: `~10^12`.
- **Per node: `_polygon_count(segments + bridges)` is O(M log M)** where `M = len(segments) + len(bridges)`. For 200-segment layers: ~200 ops × O(log 200) ≈ ~1500 ops, all in shapely's C path but with Python overhead from list concatenation.
- Saving graces in the actual code: (a) `_bridge_for_pair` rejects most candidate pairs (direction-incompat, crossing, sub-`min_gap`), (b) `used_eps` shrinks the live set after each commit, (c) `crosses_chosen` rejects bridges that overlap a previously-committed bridge, (d) the early-exit on `n_polys >= expected` short-circuits the moment a viable closure is found.
- **Realistic case:** for the failures we care about (closing 2-4 corner gaps in a single layer), the algorithm hits `expected` fast and returns. Not catastrophic in practice.
- **Adversarial case:** a cut layer where no admissible bridge configuration ever reaches `expected` (all candidates get pruned by direction/crossing). The recursion has to **fully explore the tree to confirm "no solution"** before returning, then `infer_bridges_best` calls it AGAIN on the DBSCAN-collapsed segment set. This is the 30+ second per-layer pathological case.
- **Recommendation:** add a budget — e.g. cap nodes-visited at ~10⁵ and bail to "best-so-far". The current `max_depth=8` only bounds tree *depth*, not total nodes. Without a node budget the worst case is theoretically a few seconds per stubborn layer × 21 layers × no concurrency = potentially minutes of wall clock.

### `_dbscan` (bridge.py, lines ~491-336)

- `n` = number of endpoints in the layer, ≤ a few hundred per the comment.
- `neighbours(idx)` is O(n) using `np.sqrt((diff * diff).sum(axis=1))` — vectorized.
- The outer `for i in range(n)` plus the `seeds` BFS visits each point at most once (DBSCAN canonical bound). Each visit calls `neighbours` → O(n).
- **Worst case: O(n²)**, as the docstring acknowledges. For n=400 endpoints, that's 160K ops per layer per DBSCAN call. Vectorized, so wall-cost is sub-millisecond.
- `_adaptive_eps` builds an `n × n × 2` diff array — **O(n²) memory.** For n=1000 endpoints (large layer), that's 16 MB — fine. For n=10K (unlikely but possible if a layer has thousands of small dashes): 1.6 GB. There's no upper bound check. Practical risk is low; documenting the assumption ("≤ a few hundred per layer") is correct but a defensive `if n > 5000: return floor` would prevent a memory blow-up if someone hands the function a degenerate layer.

---

## Per-file findings

### `bridge.py`

- **`_polygon_count` rebuilds `segments + bridges` each recursion node** — a fresh list copy plus shapely-side reconstruction. Could be incrementalized (linemerge supports incremental insertion via `unary_union`) but the cleaner win is a node-budget guard.
- **`infer_bridges_best` calls `infer_bridges` (greedy) which itself calls `_candidate_pairs`**, then `infer_bridges_backtrack` calls `_candidate_pairs` AGAIN, then `collapse_endpoint_clusters` rebuilds endpoints + DBSCAN on them, then DBSCAN+backtrack runs `_candidate_pairs` again on the collapsed set. The endpoint collection (`_collect_endpoints`) and `_candidate_pairs` (with its STRtree build) is duplicated 3× per layer. Modest waste — for 200-endpoint layers, STRtree build is fast — but in a budget-conscious refactor these results could be threaded through.
- **`crosses_chosen` check inside the recursion is `O(B)`** where B = number of bridges already chosen. With `max_depth=8`, B≤8, fine.
- `_strategy_score` caps at `expected` which suppresses overshooting but means a strategy that produces 2× the expected polygon count is treated equal to one that hits expected — fine for the stated goal.

### `poche_saas.py`

- `enumerate_layer_paths_from_payload` filter not used (issue 1).
- `compute_polygons_for_layers` serial (issue 2).
- `find_layer_envelope` is called once per layer in `inject_poche_polygons`, after `enumerate_layer_paths_from_payload` already located every `(name) Ln` marker. **Duplicate scan** of the 55 MB payload — `enumerate_layer_paths_from_payload` could return offset metadata so `inject_poche_polygons` doesn't re-search. Modest savings (`payload.find` is C-optimized) but noticeable on a 55 MB payload.
- `inject_poche_polygons` does `out[:lb_offset] + fragment + out[lb_offset:]` per layer — **O(payload_size)** per insert. With 21 cut layers and a 55 MB payload: ~1.2 GB of intermediate bytes copied. The right-to-left ordering preserves correctness but the slicing pattern still copies. Should build via `bytearray` + iterating sorted offsets, splicing from rightmost first into a single growing `bytearray` (or accumulate `(start, end, fragment)` triples and emit one final `b"".join`). Real impact: tens of MB allocated transiently per `apply-saas --poche` call.
- The `apply_saas_with_poche` ordering (compute polygons → rewrite widths → inject polys) is correct — payload is decompressed exactly **once** per the prompt's "no double-decompression" requirement. Confirmed: `_read_payload` is called once.

### `layer_classify.py`

- **`detect_source` is cheap** — it does a substring check over PDF Producer/Creator (one string match, ~1µs) and only falls through to layer-name shape inference if metadata is inconclusive. The shape inference iterates `layer_names` (≤ 62 entries) with `"::" in x` and an `_NCS_SHAPE_RE.match`. Both are O(n) with tiny constants. **Not a hot-path bottleneck; the prompt's worry about iterating all layer names is unfounded** — even if the regex were slow, 62 iterations is negligible vs. the 55 MB payload work.
- `classify_layer` per-call cost is unchanged from v0.4 for the Rhino path (same upper-case + substring loop). The new `haystack = f"-{upper}-"` allocation for AutoCAD is one extra string copy per layer — fine.

### `cli.py`

- `_resolve_source` runs `detect_source` once at startup. Passes `pdf_metadata + layer_names` from the existing `inspect_file(...)` report — no extra payload reads. **No regression.**
- The `--poche` flag opens `pikepdf.open(src)` once and uses the same handle for read/rewrite/inject/save — no double-open.

### `hatch.py`

- `poisson_disk` cap (`max_samples=50_000`) is enforced in two layers: (a) `min_dist` is enlarged before the algorithm runs if estimated count would exceed the cap, (b) the main `while` loop checks `len(samples) < max_samples`. Plus the `grid_w * grid_h > 5_000_000` guard. **Consistently enforced.**
- The 5 new recipes (`hatch_cmu`, `hatch_board_formed_concrete`, `hatch_standing_seam_copper`, `hatch_stucco`, `hatch_insulation_polyiso`) are each thin wrappers over existing primitives (`brick_pattern`, `parallel_hatch`, `stipple_dots`, `stipple_triangles`, `hatch_concrete`). The `MultiPolygon` recursion uses `functools.reduce(operator.iadd, ...)` consistent with prior recipes — no per-polygon allocation regressions.
- `LAYER_TO_MATERIAL` is now ~75 entries vs. ~25. The `material_for_layer` lookup is a linear substring scan (first match wins), so 3× more work per layer name. With 62 layers per drawing: ~75 × 62 ≈ 4650 substring `in` checks — sub-millisecond. **Not a real bottleneck.**

### `presets.py`

- `select_preset` is constant-time per call (one dict lookup + one list comprehension over ≤ 9 tiers). v0.5 just adds more families and a wider scale-shift table. **No hot-path impact.**

### `inspect.py`

- `_extract_pdf_metadata` and `_extract_layer_names` are called once per `inspect_file`. They use PyMuPDF API calls that are cheap relative to the existing page-walk. **No regression.**

---

## Issues NOT found (premature-optimization rejected)

- **DBSCAN memory blow-up:** docstring caveat is correct; under realistic endpoint counts (≤ a few hundred per layer), n²-memory is sub-MB. Not a real bottleneck.
- **`detect_source` iterating layer names:** prompt suspicion was wrong; it's O(62) with tiny constants and only fires once at CLI startup, not per drawing.
- **Hatch library expansion:** 5 new recipes do not inflate per-call cost; they're conditional (only fire when a layer matches a pattern). The expanded `LAYER_TO_MATERIAL` list adds 50 substring checks per `material_for_layer` — negligible.
- **Recurring no-op state updates in polling loops:** none found in the diff. v0.5 doesn't add any polling/state-store loops.
- **`PocheSaasResult` data structure:** small, bounded by layer count. Not a memory risk.

---

## TL;DR — Recommended fixes in priority order

1. **Pass `layer_filter` to `enumerate_layer_paths_from_payload`** — one-line change, eliminates parsing of ~40 non-cut layers per `apply-saas --poche` run.
2. **Parallelize `compute_polygons_for_layers`** with `ProcessPoolExecutor` over the 21 cut layers — easy 6-8× speedup on the polygonization step.
3. **Add a node-budget guard to `_backtrack_search`** (cap at e.g. 100K visited nodes, return best-so-far) — bounds adversarial worst case from "minutes" to "tens of ms".
4. **Add early-exit in `infer_bridges_best`** — if greedy already hits expected with confidence 1.0, skip the other 3 strategies. Cheap, removes 75% of redundant work on the common case.
5. **Batch `inject_poche_polygons` splices** via `b"".join` of a single sorted edit list rather than 21 sequential O(payload_size) slice-concats — saves ~1 GB transient allocation on the reference drawing.
