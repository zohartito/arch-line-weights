# Stubborn cut layers — deep dive

> Sub-agent research, 2026-04-30. Three layers in the USC ARCH 202B reference
> drawing resist the v0.4 rescue ladder (`linemerge → snap-sweep → auto-bridge
> → concave_hull → bbox`). Each requires a user-side `__POCHE_CLOSE__`
> workaround today. This doc evaluates eight algorithmic approaches, makes a
> recommendation, and sketches the implementation.

## The three problem layers

Reconstructed from `docs/POSTMORTEM.md`, `docs/research/disconnected-loops.md`,
and the v0.4 rescue ladder in `src/arch_line_weights/poche.py` /
`src/arch_line_weights/bridge.py`.

| Layer | Why bare `linemerge` fails | Why `snap`-sweep fails | Why `auto_bridge` fails | Why `concave_hull` fails |
|---|---|---|---|---|
| `23_WINDOW_FRAMES_REMAP` | Too few anchor points (frames are short stubs, ~2-vertex polylines, scattered) | Endpoints are far apart — snap at 5 pt over-merges adjacent frame stubs | < 3 distinct endpoints inside any `max_gap=50pt` neighborhood per stub; bridge inference yields nothing | `concave_hull(MultiPoint, ratio=0.3)` over sparse stubs returns a degenerate hull or a single huge blob spanning all windows |
| `26_CLT_GAP_ROOF_CAP` | 2+ disconnected sub-shapes (cap is genuinely two roof slabs with a gap in between) | Same — snapping doesn't help when the gap is intentional | Greedy nearest-neighbor in `bridge._candidate_pairs` finds no pair under `max_gap` because the two clumps are far apart and intra-clump endpoints already share | Hull merges the two roof caps into one blob that covers the gap |
| `11_CU_CORR_SOLID_OPAQUE` | Endpoint clusters: many short corrugation segments share endpoints in tight pinches; `linemerge` chains the wrong pair | Snap collapses corrugation peaks → linemerge produces self-intersecting blob (Attempt 3-style failure) | Greedy bridger picks shortest neighbor regardless of context — picks an endpoint inside a cluster instead of across the actual gap | Hull treats every corrugation valley as a concavity; produces a sawtooth that doesn't match the cut |

The shared diagnosis: **three different topology pathologies, one rescue
ladder.** Per-pathology rescue is what's missing.

---

## Approach analysis

For each: algorithm sketch, implementation effort, expected success on the
three layers, and pros/cons. "Effort" is a solo-engineer estimate that
includes tests but not productionization (logging, overrides, JSON schema).

### 1. DBSCAN with adaptive ε on endpoint clusters

**Algorithm.** Collect every endpoint of every input segment. Run DBSCAN
(`sklearn.cluster.DBSCAN`) with `eps = adaptive` (e.g. median nearest-neighbor
distance × 1.5, capped at 5pt) and `min_samples=2`. Each resulting cluster is
a "join point" — collapse all endpoints in one cluster to their centroid (or
to the most-central existing endpoint). Then run `linemerge + polygonize`.

The adaptive ε matters. Static thresholds collapse corrugation peaks
(`11_CU_CORR_SOLID_OPAQUE` failure mode); ε derived from the local
nearest-neighbor distribution scales with the layer's intrinsic spacing. See
[scikit-learn DBSCAN docs](https://scikit-learn.org/stable/modules/generated/sklearn.cluster.DBSCAN.html).

**Effort.** ~4-6 hours. ~80 lines (k-d tree of endpoints, DBSCAN call,
collapse step, re-merge). Adds `scikit-learn` as a dependency (or a hand-rolled
DBSCAN, ~40 lines).

**Expected success on the three:**
- `11_CU_CORR_SOLID_OPAQUE`: **likely fixes** — adaptive ε will pick a value
  smaller than the corrugation peak spacing, so peaks survive while
  cluster-pinches collapse.
- `26_CLT_GAP_ROOF_CAP`: **does not fix** — the two roof caps are *separately*
  nearly-closed; DBSCAN won't bridge across the intentional gap. (This is
  actually correct behavior — the gap should produce two polygons, not one,
  if `polygonize` succeeds.)
- `23_WINDOW_FRAMES_REMAP`: **does not fix** — too few endpoints per cluster;
  DBSCAN labels them all as noise.

**Pros.** Robust to varying point density; widely-implemented; explainable.
**Cons.** Requires picking ε; doesn't do bridging, only snapping.

### 2. Spectral clustering on the polyline graph

**Algorithm.** Build a graph: each segment is a node, edges connect segments
whose endpoints fall within a tolerance. Run spectral clustering
(`sklearn.cluster.SpectralClustering`) on the graph Laplacian, using the
eigengap heuristic to pick `k`. Each cluster = one connected component =
polygonize separately.

**Effort.** ~6-8 hours. Graph construction is fiddly; eigengap selection on
small graphs is unstable.

**Expected success on the three:**
- `26_CLT_GAP_ROOF_CAP`: **likely fixes** — the two roof caps are exactly
  what spectral clustering is designed to separate. After splitting,
  `linemerge + polygonize` runs on each cluster independently.
- `11_CU_CORR_SOLID_OPAQUE`: **partial** — corrugations form one large
  connected component already, so clustering wouldn't split anything.
- `23_WINDOW_FRAMES_REMAP`: **does not fix** — each window frame is its own
  tiny cluster, but clusters of 2-3 segments still polygonize to nothing.

**Pros.** Handles "intentionally disconnected" cases (gaps that the user
*wants* to keep open). **Cons.** Heavy dependency, eigengap unstable on small
graphs, doesn't help the actual closing problem.

### 3. Voronoi-based gap detection

**Algorithm.** Compute a Voronoi diagram of the endpoint set. Edges of the
Voronoi diagram correspond to "channels" between endpoint clusters. Long
Voronoi edges = wide gaps (likely intentional); short edges = narrow gaps
(likely accidental disconnections). Bridge across short Voronoi edges only.

**Effort.** ~8-10 hours. `scipy.spatial.Voronoi` gives the diagram; the
threshold tuning and the "bridge across an edge" geometry is non-trivial.

**Expected success on the three:**
- All three: **uncertain.** Theoretically elegant, practically brittle. The
  Voronoi diagram of corrugation endpoints is dense and noisy; the diagram of
  WINDOW_FRAMES is degenerate (collinear points → unbounded cells).

**Pros.** Principled "intentional vs. accidental gap" distinction.
**Cons.** Voronoi is fragile under near-collinear inputs; doesn't compose
well with the existing strategy ladder.

### 4. Alpha-shape / α-complex (instead of `concave_hull`)

**Algorithm.** Replace shapely's `concave_hull` (which is a heuristic
ratio-based concave envelope) with a true α-complex from
[`alphashape`](https://pypi.org/project/alphashape/). Sweep `α ∈ [0.01, 0.5]`
and pick the value whose resulting shape's vertex count best matches the
input vertex count.

**Effort.** ~3-4 hours. Drop-in replacement plus an α-sweep.

**Expected success on the three:**
- `23_WINDOW_FRAMES_REMAP`: **partial** — α-shape on a too-sparse point
  cloud is still degenerate. Better than `concave_hull` but only marginally.
- `26_CLT_GAP_ROOF_CAP`: **likely fixes** — for the right α, an α-shape can
  preserve the gap as a hole or as two separate components. Better than the
  current "lumpy single polygon" fallback.
- `11_CU_CORR_SOLID_OPAQUE`: **does not fix** — α-shape on corrugation
  endpoints inherits the same sawtooth problem. (Densifying first helps but
  doesn't solve.)

**Pros.** Mathematically principled; preserves holes; cheap dependency.
**Cons.** α tuning is per-layer; doesn't address bridging.

### 5. Small-LLM topology inference

**Algorithm.** When all geometric methods fail, package the layer name + the
N polyline endpoints as a JSON prompt to a small LLM (Claude Haiku 3.5 or
GPT-4o-mini), and ask it to return a list of `(segment_a_endpoint,
segment_b_endpoint)` bridges that close the topology. The LLM uses two
priors:

1. **Architectural domain knowledge.** A layer named `WINDOW_FRAMES_REMAP`
   is small repeating frames — the LLM should output 4-bridge "close each
   stub into a small rectangle" hints. A layer named `CLT_GAP_ROOF_CAP`
   suggests two separate caps with a gap. A layer named
   `CU_CORR_SOLID_OPAQUE` (copper corrugated solid opaque) is one large
   undulating profile.
2. **Spatial reasoning over endpoints.** Given a list of `(seg_idx, end_idx,
   x, y)` tuples, the LLM can spot symmetric pairs, nearest neighbors,
   visually-implied closure even without running geometric algorithms.

**Prompt template** (Haiku):

```
You are an architectural-drawing topology expert. A vector cut-layer has
disconnected polyline segments that should form one or more closed
polygons. The layer is named {layer_name}. Architectural context:
{layer_classify_hint}.

Endpoints (each line: segment_index end_index x y):
{endpoints_listing}

Polylines (each: segment_index : (x1,y1) (x2,y2) ...):
{polylines_listing}

Return a JSON object:
{
  "topology": "one_polygon" | "multiple_polygons" | "open_chain",
  "expected_polygon_count": <int>,
  "bridges": [
    [seg_a_idx, end_a_idx, seg_b_idx, end_b_idx],  // closes a-end to b-start
    ...
  ],
  "reasoning": "<one-sentence>"
}

Constraints: each bridge connects an endpoint of one segment to an endpoint
of a different segment; never start-to-start (that would invert winding);
the resulting graph should produce {expected_polygon_count} closed loops.
```

**Cost estimate.** Haiku 3.5: $0.80 / 1M input tokens, $4.00 / 1M output.

A typical call: ~2,000 input tokens (layer name + 30 endpoints + prompt
boilerplate) + ~300 output tokens. Per-call cost ≈ `2000 × 0.8e-6 + 300 ×
4e-6` = `0.0016 + 0.0012` ≈ **$0.003 per stubborn layer**. With 3 stubborn
layers per drawing → **~$0.01 per drawing** of LLM cost. (Well under
the user's mental price ceiling.)

**Effort.** ~6-10 hours. Anthropic SDK call, prompt-template assembly,
JSON-schema validation of the response, integration as a fallback after
auto-bridge fails. Plus prompt caching (the prompt boilerplate is identical
across calls — see `claude-api` skill for ergonomic caching).

**Expected success on the three:**
- `23_WINDOW_FRAMES_REMAP`: **likely fixes** — the LLM sees "WINDOW_FRAMES"
  and a list of stub endpoints, infers each stub should close into a small
  frame rectangle. A small-LLM strength.
- `26_CLT_GAP_ROOF_CAP`: **likely fixes** — "GAP_ROOF_CAP" plus two
  spatially-clustered endpoint groups → infers two-polygon topology.
- `11_CU_CORR_SOLID_OPAQUE`: **likely fixes** — "CORR" (corrugated) plus a
  long zigzag of endpoints → infers single-polygon topology with bridges
  along the bottom edge connecting alternating corrugation troughs.

**Pros.** Generalizes to layers we haven't seen; uses information our
geometric methods don't have access to (the layer *name*); cheap.
**Cons.** Adds an external API dependency (offline mode regresses); LLM
hallucinations possible; failure modes are non-deterministic.

### 6. Rhino source `.3dm` query

**Algorithm.** If the user uploads the source `.3dm` alongside the `.ai`,
query the underlying NURBS curves directly via `rhino3dm` and trace the
intended cut polylines without going through Make2D's lossy projection.

**Effort.** ~16-24 hours. Adds a whole new file-format input path, plus
ClippingPlaneIntersection emulation in Python (Rhino does this with C++; the
Python rhino3dm bindings only read geometry, they don't run section ops).

**Expected success on the three:** **almost certainly all 3** — but only when
the user uploads `.3dm`. Doesn't help the .ai-only case (which is the v0.4
ICP for paying customers per `docs/research/saas-architecture.md`).

**Pros.** Highest fidelity. **Cons.** Massive scope creep; rhino3dm can't run
ClippingPlane operations server-side. Park as a future feature.

### 7. Iterative bridging with backtracking

**Algorithm.** The current bridger (`bridge.py:_pair_endpoints`) is
greedy: it sorts candidate pairs by distance and commits to the shortest
non-crossing one. Replace with a backtracking search: pick a candidate
bridge, recursively try to close the topology, and if `polygonize` yields
fewer polygons than expected, undo the bridge and try the next candidate.

```
def bridge_with_backtrack(segments, max_depth=8):
    candidates = sorted_candidate_pairs(segments)
    def search(used, bridges, depth):
        if depth > max_depth: return None
        polys = polygonize(linemerge(segments + bridges))
        if matches_expected(polys, segments): return bridges
        for cand in candidates:
            if cand.endpoints_in(used): continue
            new_used = used | cand.endpoints
            result = search(new_used, bridges + [cand.bridge], depth+1)
            if result: return result
        return None
    return search(set(), [], 0)
```

**Effort.** ~6-8 hours. The recursion is straightforward; the pruning
heuristics (so we don't explore exponentially) are the work.

**Expected success on the three:**
- `11_CU_CORR_SOLID_OPAQUE`: **likely fixes** — the failure mode is "greedy
  picked the wrong pair"; backtracking finds the right pair.
- `26_CLT_GAP_ROOF_CAP`: **does not fix** — the issue isn't bridge-pair
  selection; it's that the two clusters are too far apart for any
  `max_gap` setting.
- `23_WINDOW_FRAMES_REMAP`: **does not fix** — too few candidates, even
  exhaustive search produces nothing.

**Pros.** Pure improvement to existing module; no new deps. **Cons.** Helps
one of three layers; recursion depth is a fudge factor; can be slow on
dense inputs.

### 8. Endpoint snapping to a coarse grid

**Algorithm.** Before `linemerge`, round every endpoint to the nearest 0.1pt
(or layer-adaptive grid), then call `linemerge`. Removes sub-pixel float
errors.

**Effort.** ~1 hour. ~10 lines.

**Expected success on the three:**
- All three: **does not fix.** The pathology in all three is *real* gaps
  (≥ 1pt for `26_CLT_GAP_ROOF_CAP`, semantic ambiguity for the other two),
  not float-precision noise. The existing tolerance sweep already snaps at
  0.1, 0.5, 1.0, 2.0, 5.0pt — adding a grid round on top is redundant.

**Pros.** Cheap. **Cons.** Doesn't help our actual problem cases; risks
introducing new bugs (rounding into a self-intersection).

---

## Summary table

| # | Approach | Effort | `23_WINDOW_FRAMES` | `26_CLT_GAP` | `11_CU_CORR` | New deps |
|---|---|---|---|---|---|---|
| 1 | DBSCAN + adaptive ε | 4-6h | no | no | yes | sklearn (or hand-rolled) |
| 2 | Spectral clustering | 6-8h | no | yes | partial | sklearn |
| 3 | Voronoi gap detection | 8-10h | uncertain | uncertain | uncertain | scipy (already a transitive dep) |
| 4 | α-shape sweep | 3-4h | partial | yes | no | `alphashape` |
| 5 | LLM topology inference | 6-10h | yes | yes | yes | `anthropic` SDK |
| 6 | Rhino .3dm query | 16-24h | yes | yes | yes | `rhino3dm` (heavy) |
| 7 | Backtracking bridger | 6-8h | no | no | yes | none |
| 8 | Coarse grid snap | 1h | no | no | no | none |

---

## Recommendation: stacked approach (1 + 7 + 5)

No single approach handles all three pathologies. Three pathologies want
three responses, layered on the existing rescue ladder:

```
strategy_ladder_v05 = [
    "linemerge_bare",                      # current
    "linemerge_snap_sweep",                # current
    "auto_bridge_greedy",                  # current
    "auto_bridge_backtrack",               # NEW (#7) — fixes 11_CU_CORR
    "dbscan_collapse_then_remerge",        # NEW (#1) — fixes some 11_CU_CORR
    "alpha_shape_sweep",                   # NEW (#4) — improves fallback fidelity for 26_CLT_GAP
    "llm_topology_inference",              # NEW (#5) — fixes 23_WINDOW_FRAMES + last-resort
    "concave_hull_0.3",                    # current (downgraded fallback)
    "bbox",                                # current (last resort)
]
```

**Why stacked.** Cheap geometric methods first (no API calls, deterministic);
LLM only fires on the ~3-out-of-21 layers that exhaust the ladder.

### Estimated success rate on the three layers

- DBSCAN + backtracking alone: probably **2/3** (`11_CU_CORR` fixed,
  `26_CLT_GAP` fixed by α-shape, `23_WINDOW_FRAMES` still requires
  `__POCHE_CLOSE__`).
- Adding LLM topology inference: probably **3/3**, with ~$0.01 per drawing in
  inference cost.
- Confidence: medium. The "LLM fixes WINDOW_FRAMES" claim is plausible from
  Haiku's known strengths on small structured-reasoning tasks but not yet
  empirically tested. Worth a 60-minute spike.

---

## Working pseudo-code for the stacked rescue

```python
# src/arch_line_weights/poche.py — extended polygonize_layer

def polygonize_layer_v05(layer_name, paths, closing_lines, override):
    lines = _lines_from_anchors(paths) + (closing_lines or [])
    if not lines:
        return [], FillResult(layer_name, "failed", 0.0, 0, 0)

    # Existing: linemerge sweep + auto_bridge greedy (unchanged)
    polys, conf, strat, tol = _sweep_existing(lines)
    if polys:
        return polys, FillResult(layer_name, strat, conf, len(polys), ...)

    # NEW: backtracking bridger
    aug, bconf = infer_bridges_backtrack(lines, max_gap=50.0, max_depth=8)
    polys = _polys_at_tolerance(aug, 0.0)
    if polys:
        return polys, FillResult(layer_name, "auto_bridge_backtrack",
                                 0.7 * bconf + 0.2, len(polys), ...)

    # NEW: DBSCAN endpoint collapse
    collapsed = collapse_endpoint_clusters(lines, eps="adaptive")
    polys = _polys_at_tolerance(collapsed, 0.0)
    if polys:
        return polys, FillResult(layer_name, "dbscan_collapse",
                                 0.65, len(polys), ...)

    # NEW: alpha-shape sweep
    poly = alpha_shape_best_alpha(lines, alpha_grid=[0.01, 0.05, 0.1, 0.3])
    if poly is not None:
        return [poly], FillResult(layer_name, "alpha_shape",
                                  0.55, 1, ...)

    # NEW: LLM topology inference (last resort before lossy fallbacks)
    if os.getenv("ARCH_LW_LLM_FALLBACK", "0") == "1":
        bridges = llm_infer_topology(layer_name, lines)
        if bridges:
            polys = _polys_at_tolerance(lines + bridges, 0.0)
            if polys:
                return polys, FillResult(layer_name, "llm_topology",
                                         0.7, len(polys), ...)

    # Existing: concave_hull, bbox (unchanged)
    return _existing_lossy_fallbacks(lines, layer_name)


def collapse_endpoint_clusters(lines, eps="adaptive"):
    """DBSCAN-collapse endpoints with adaptive eps."""
    eps_v = _adaptive_eps(lines) if eps == "adaptive" else float(eps)
    pts = _all_endpoints(lines)
    db = DBSCAN(eps=eps_v, min_samples=2).fit(pts)
    centroids = _cluster_centroids(pts, db.labels_)
    return _rewrite_lines_with_collapsed_endpoints(lines, db.labels_, centroids)


def llm_infer_topology(layer_name, lines):
    """Ask Claude Haiku for closing bridges. Returns list[LineString]."""
    import anthropic
    client = anthropic.Anthropic()
    endpoints, polylines_json = _serialize_for_llm(lines)

    msg = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=400,
        system=[{
            "type": "text",
            "text": LLM_SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},  # boilerplate is identical
        }],
        messages=[{"role": "user", "content": _format_user_msg(
            layer_name, endpoints, polylines_json
        )}],
    )
    plan = json.loads(msg.content[0].text)
    return _bridges_from_plan(plan, lines)
```

The full prompt template, JSON schema, and response validator live alongside
the implementation in `bridge_llm.py` (a new module).

---

## Implementation plan for E1 (next milestone)

| Phase | Task | Days |
|---|---|---|
| 1 | Land Approach #7 (backtracking bridger). Pure geometry, no new deps, unblocks `11_CU_CORR`. Includes test fixture in `tests/fixtures/cu_corr_*.json`. | 1.0 |
| 2 | Land Approach #1 (DBSCAN endpoint collapse). Add `scikit-learn` as opt dep (`pip install arch-line-weights[ml]`). Hand-rolled DBSCAN if dep is unwelcome. | 1.0 |
| 3 | Land Approach #4 (α-shape sweep). Replaces `concave_hull` fallback with a graded α-shape selection. Improves fidelity for `26_CLT_GAP`. | 0.5 |
| 4 | Land Approach #5 (LLM topology inference) behind feature flag `ARCH_LW_LLM_FALLBACK=1`. Requires `anthropic` opt dep + prompt caching per `claude-api` skill. Ship a 30-prompt regression suite (real layer dumps, golden polygon counts). | 1.5 |
| 5 | Add per-layer JSON override schema for "force strategy X" so users can pin the choice when the cascade picks wrong. | 0.5 |
| 6 | Update `disconnected-loops.md` to v0.5; backfill `POSTMORTEM.md` Attempt 9. | 0.25 |
| **Total** | | **~4.75 person-days** |

Phase 4 (LLM) is the highest-risk; if it doesn't reach 3/3 in the spike, fall
back to "ship 1+7+4 and keep `__POCHE_CLOSE__` as the documented escape for
the residual ~3% of layers."

---

## What this report does NOT prove

The three problem layers were not loaded into a Python REPL during this
research session — the geometry dump only exists alongside an Illustrator
session and the ARCH 202B `.ai` reference file. The pathology descriptions
above are reconstructed from `POSTMORTEM.md` Attempts 4-5, the layer-name
semantics (`WINDOW_FRAMES_REMAP`, `CLT_GAP_ROOF_CAP`,
`CU_CORR_SOLID_OPAQUE`), and the failure-mode signatures of the existing
strategies. The recommended approach is high-confidence on
`11_CU_CORR_SOLID_OPAQUE` (textbook greedy-bridger failure), medium-
confidence on `26_CLT_GAP_ROOF_CAP` (α-shape behavior on two-cluster inputs
is well-documented but layer-specific), and uncertain on
`23_WINDOW_FRAMES_REMAP` (the LLM-as-topology-inferer claim is the
weakest link in this chain).

**Concrete next step before E1 commit:** run `arch-lw poche` once with
`ARCH_LW_DUMP_RAW=1` on the reference drawing; checkpoint the three
layers' anchor JSONs into `tests/fixtures/`, and use them as the
regression set for any of the eight approaches. Estimated 60 minutes.
This is the single most valuable thing a follow-up spike can do.

---

## Sources

- [scikit-learn DBSCAN docs](https://scikit-learn.org/stable/modules/generated/sklearn.cluster.DBSCAN.html)
- [scikit-learn SpectralClustering docs](https://scikit-learn.org/stable/modules/generated/sklearn.cluster.SpectralClustering.html)
- [scipy.spatial.Voronoi](https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.Voronoi.html)
- [`alphashape` PyPI](https://pypi.org/project/alphashape/)
- [Anthropic Haiku 3.5 pricing](https://www.anthropic.com/pricing)
- [Anthropic prompt caching](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching)
- [Shapely STRtree](https://shapely.readthedocs.io/en/stable/strtree.html)
- `docs/research/disconnected-loops.md` (v0.4 strategy ladder)
- `docs/POSTMORTEM.md` Attempts 4-5 (per-layer pathology evidence)
