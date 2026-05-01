# α-shape rescue rung — implementation notes (v0.5.2, GitHub Issue #6)

> Implementation log for the α-shape rung added to
> `polygonize_layer`'s rescue ladder. Companion to
> `docs/research/stubborn-layers-deep-dive.md` (which evaluated 8 approaches
> and recommended a stacked solution including this rung) and
> `docs/research/disconnected-loops.md` (the original v0.4 ladder).

## What landed

A new module `src/arch_line_weights/alpha_shape.py` exposes:

- `alpha_shape(points, alpha)` — α-shape for a fixed alpha threshold.
- `alpha_shape_best(points, alpha_grid)` — adaptive alpha sweep returning
  the largest-area polygon component plus alpha + region count.
- `alpha_shape_all_regions(points, alpha_grid)` — same sweep but returns
  every region of the winning α-complex (used by the rescue ladder when
  multi-component topology like 26_CLT_GAP_ROOF_CAP needs preserving).

The rescue ladder in `poche.py:polygonize_layer` is now:

    linemerge_bare → snap+linemerge → auto_bridge → alpha_shape → concave_hull → bbox

with confidence values 1.0 / 0.95–0.7 / 0.75-bridge / **0.55** / 0.55 / 0.30
respectively. The α-shape rung is opt-in via `use_alpha_shape` (default
True for v0.5.2) and the CLI flag `--alpha-shape / --no-alpha-shape`
(also default True). `--no-alpha-shape` reverts the ladder to v0.5.1.

## Implementation choice: hand-rolled, not the `alphashape` PyPI package

`alphashape` was *not* added as a dependency. The package is fine but:

- `scipy.spatial.Delaunay` is already in the transitive dep tree (shapely
  pulls scipy via wheels), so a ~120-line implementation is dependency-free.
- The package's default scoring criterion (perimeter-to-area ratio) is
  not the right metric for our use case — we want "preserve multi-component
  topology when present". Hand-rolling lets us implement the correct
  scoring explicitly.

The algorithm itself is textbook (Edelsbrunner & Mücke, 1994): compute
the Delaunay triangulation, keep triangles whose circumradius ≤ alpha,
take the union of kept triangles. Recovery of multi-component topology
comes for free from `shapely.ops.unary_union` returning a `MultiPolygon`
when the kept triangles fall into disconnected clusters.

## Adaptive alpha selection — the tricky part

The naive criterion "maximize distinct closed regions" (per the task
spec) breaks on perimeter-only point clouds: small alpha picks up only
isolated corner triangles, which technically count as "more regions" but
represent zero of the actual cut shape's interior.

The implemented criterion has three layers:

1. **Coverage floor.** An alpha-shape qualifies only if its total area
   is ≥ 40% of the convex-hull area of the input points. Below that,
   the alpha is too tight (sliver corners only).
2. **Sliver filter.** Within a qualifying alpha-shape, only regions
   whose absolute area ≥ 5% of the bounding-box area count toward the
   region count. Tiny chunks — even at "well-covered" alpha — don't
   count as real components.
3. **Maximize qualifying regions, tie-break by total area.** Among all
   alphas that pass both filters, pick the one with the most regions;
   if tied, pick the one with the largest total area.

This gives the spec-intended behavior on real cut-layer geometry (which
gets densified by `segmentize(max_segment_length=2.0)` before the rung
runs, providing interior points for Delaunay), without false positives
on degenerate perimeter-only inputs.

## Densification matches `concave_hull` rung

`_try_alpha_shape` densifies inputs via `segmentize(max_segment_length=2.0)`
before feeding points to scipy. This mirrors what `_try_concave_hull`
already does. Without it, Delaunay on Make2D output (which is segments
of polylines, often with only the corner anchor points) gets too few
interior triangles to recover the cut shape.

## Wiring through the codebase

- `polygonize_layer(..., use_alpha_shape=True)` — new keyword-only argument.
- `polygonize_dump(..., use_alpha_shape=True)` — threads through.
- `apply_poche(..., use_alpha_shape=True)` — threads through to dump→ladder.
- `compute_polygons_for_layers(..., use_alpha_shape=True)` (poche_saas).
- `apply_saas_with_poche(..., use_alpha_shape=True)`.
- `arch-lw apply-saas --alpha-shape / --no-alpha-shape` — CLI flag (default ON).
- `arch-lw poche --alpha-shape / --no-alpha-shape` — CLI flag (default ON).

Existing `concave_hull` and `bbox` rungs are untouched. The α-shape rung
sits *between* `auto_bridge` (greedy bridger output) and `concave_hull`,
so it only fires when bridging fails to produce any polygon — exactly
where the lossy fallback used to fire.

## Test coverage

`tests/test_alpha_shape.py` (28 tests):

- Algebraic helpers: `_circumradius` for known triangles + collinear edge.
- Basic `alpha_shape`: returns None for sparse/collinear/too-small inputs;
  recovers a square at large alpha; produces a polygon for a U-shape.
- Adaptive selection: `alpha_shape_best` picks a sensible alpha for a
  filled square; recovers ≥ 2 regions for a CLT-gap fixture (two
  20×20 clusters separated by 50pt).
- Integration with `polygonize_layer`: the flag-off path matches v0.5.1
  (no `alpha_shape` strategy used); the flag-on path produces ≥ as many
  polygons as flag-off; clean layers still pick `linemerge_bare`;
  α-shape rung confidence is 0.55.
- Edge cases: duplicate points, empty grid, scipy unavailability.

Pre-existing 202 tests (poché, bridge, hatch, presets, layer-classify,
etc.) all still pass — no regression.

## Behavior on the 3 stubborn cut layers

Per `stubborn-layers-deep-dive.md`'s analysis, expected α-shape impact:

| Layer | Pathology | α-shape result |
|---|---|---|
| `26_CLT_GAP_ROOF_CAP` | Two disconnected sub-shapes with intentional gap | **Likely fixes** — α-shape preserves the two clusters; `_try_alpha_shape` returns both polygons. Verified on the synthetic two-cluster fixture (`test_alpha_shape_best_recovers_two_regions_for_clt_gap`). |
| `23_WINDOW_FRAMES_REMAP` | Too few endpoints per stub for any geometric method | **Marginal** — α-shape on too-sparse stubs is degenerate. May still fall to `bbox` for many windows. The original POSTMORTEM analysis flagged this as the layer needing LLM topology inference (rung 5, deferred to Issue #6's later phases). |
| `11_CU_CORR_SOLID_OPAQUE` | Greedy bridge picks wrong endpoint pair | **No change** — α-shape on densified corrugation endpoints inherits the same sawtooth problem; `auto_bridge_backtrack` (already wired via `infer_bridges_best`) is the right rung for this layer. |

The α-shape rung is specifically designed to win on `26_CLT_GAP_ROOF_CAP`,
which the spec called out as the headline target for v0.5.2.

## Real-drawing verification

The CLI was tested via:

    arch-lw apply-saas --auto --poche --alpha-shape /tmp/arch-lw-smoke/test.ai \
        -o /tmp/test_alpha.ai 2>&1 | grep -E "26_CLT_GAP|23_WINDOW|11_CU_CORR"

Output (with `--alpha-shape`):

    ~ 11_CU_CORR_SOLID_OPAQUE          auto_bridge  polys=  4  conf=0.59
    ~ 26_CLT_GAP_ROOF_CAP_REMAP_49FT_V68  bbox    polys=  1  conf=0.30
    ✗ 23_WINDOW_FRAMES_REMAP_49FT_V68    failed   polys=  0  conf=0.00

Output with `--no-alpha-shape` is **identical**, which surfaced an
important finding documented below.

### Why none of the 3 stubborn layers actually hit the α-shape rung

Inspecting the raw geometry of each stubborn layer in `test.ai`:

| Layer | Anchor count | Geometry | Why α-shape doesn't help |
|---|---|---|---|
| `26_CLT_GAP_ROOF_CAP_REMAP_49FT_V68` | 4 anchors across 2 paths (one shared) | A single near-straight polyline of 3 distinct points spanning ~150×85 source units | Points are nearly collinear; Delaunay produces only sliver triangles with circumradii > 100. Even at α=100, the recovered polygon has area ~0.05 — far below the coverage threshold. The "two roof caps with a gap" assumption from the research doc doesn't match the actual file. The current `bbox` outcome is correct given the data. |
| `23_WINDOW_FRAMES_REMAP_49FT_V68` | 28 anchors, 14 paths | All 28 points lie at x=480.3 (zero-width bbox) — perfectly collinear | Delaunay can't triangulate collinear points; α-shape returns None for any α. Per the deep-dive, this layer needs LLM topology inference (rung 5, deferred). |
| `11_CU_CORR_SOLID_OPAQUE` | 288 anchors, 144 paths | A long thin corrugated ribbon (2pt wide × 213pt tall) | `auto_bridge` already produces 4 polygons at confidence 0.59 — the α-shape rung never gets a chance to run because bridge succeeds first. |

### What the α-shape rung *does* fix

A synthetic fixture with two short-stub clusters >300pt apart (too far
for `auto_bridge`, with each cluster only 4 stubs of 5pt each) is the
canonical "α-shape wins" case:

    paths = [4 corner stubs around (0..100, 0..100), 4 around (400..500, 0..100)]

    With --alpha-shape:    strategy=alpha_shape, conf=0.55, polys=2
    Without --alpha-shape: strategy=concave_hull, conf=0.55, polys=1

The α-shape preserves the two-cluster topology (2 polys); concave_hull
collapses both into a single blob spanning the gap (1 poly). This is
the 26_CLT_GAP_ROOF_CAP-style win condition the rung was designed for —
just not realized in the current reference drawing.

### Implication

The α-shape rung is correctly implemented and validated against
synthetic fixtures matching the design intent. On the actual reference
drawing the rung never fires because:

1. `26_CLT_GAP_ROOF_CAP` doesn't have the "two clusters with gap"
   topology in this file (it's effectively a single polyline).
2. `23_WINDOW_FRAMES_REMAP` is collinear, defeating any 2-D rescue.
3. `11_CU_CORR_SOLID_OPAQUE` is solved by an earlier rung (auto_bridge).

This is a useful finding — it tells us:

- The "two roof caps" mental model from the research doc may have been
  inferred from the layer name (`26_CLT_GAP_ROOF_CAP`) rather than from
  the actual geometry. The geometry shows it's a single thin polyline
  representing the cap profile, not two separate caps.
- For the WINDOW_FRAMES layer, no geometric rescue (α-shape, DBSCAN,
  Voronoi, …) can recover collinear stub data. Only LLM inference using
  the layer name as a prior or `__POCHE_CLOSE__` user-marked closing
  segments will help here.

The α-shape rung remains the right tool for layers with the canonical
"two clusters separated by an intentional gap" pattern. Future drawings
exhibiting that pattern will use it instead of falling to bbox.

## Future work

- LLM topology inference (rung 5 in the deep-dive) for
  `23_WINDOW_FRAMES_REMAP` — deferred to a separate phase per the task
  constraints.
- Adaptive `alpha_grid` sizing based on the input bounding box. Current
  grid `(1.0, 2.5, 5.0, 10.0, 20.0, 35.0, 50.0, 75.0, 100.0)` is in
  source units (typically points) and tuned for plot-scale architectural
  geometry. A future spike could auto-scale the grid to the layer's
  intrinsic spacing (similar to `_adaptive_eps` in `bridge.py`).
- Multi-region polygon list flowing through `poche_saas.inject_poche_polygons`.
  The injection path already accepts `list[Polygon]` per layer, so the
  α-shape rung's multi-component output round-trips through unmodified —
  no further wiring needed.

## Source files touched

| File | Change |
|---|---|
| `src/arch_line_weights/alpha_shape.py` | **New.** ~370 lines. Hand-rolled α-complex over scipy Delaunay; adaptive sweep with coverage floor + sliver filter. |
| `src/arch_line_weights/poche.py` | Added `_try_alpha_shape` helper; inserted `alpha_shape` rung between `auto_bridge` and `concave_hull` in `polygonize_layer`; threaded `use_alpha_shape` flag through `polygonize_layer`, `polygonize_dump`, `apply_poche`. New strategy literal `"alpha_shape"` added. |
| `src/arch_line_weights/poche_saas.py` | Threaded `use_alpha_shape` flag through `compute_polygons_for_layers` and `apply_saas_with_poche`. |
| `src/arch_line_weights/cli.py` | Added `--alpha-shape / --no-alpha-shape` flag to `apply-saas` and `poche` commands. Default ON for both. |
| `tests/test_alpha_shape.py` | **New.** 28 tests covering the helpers, adaptive selection, edge cases, and `polygonize_layer` integration. |
| `docs/research/alpha-shape-impl-notes.md` | **New.** This file. |

Time budget for the implementation: under the 75-minute box stated in the
task brief.
