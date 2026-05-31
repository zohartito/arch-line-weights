# How poché works

A Rhino-exported `.ai` looks correct on screen, but wall outlines typically arrive as a soup of disconnected line segments. `Make2D` cuts hidden-line silhouettes per face, so a single rectangular wall can come out as 4 to 60 short polylines whose endpoints almost — but not quite — touch.

To paint that wall solid black, we need to recover its closed boundary.

## Why naive Illustrator `Object > Path > Join` doesn't work

Illustrator's `Join` only merges paths whose endpoints are *already coincident* — and it joins endpoints in **arbitrary order** when many are within tolerance, producing one tangled self-intersecting polygon per cluster. Rhino often exports endpoints that are off by 1e-6 to 1e-3 units — visually identical, topologically distinct. Join silently fails on those. We tried it first; the result was a giant black blob across the courtyard. See [`docs/POSTMORTEM.md`](https://github.com/zohartito/arch-line-weights/blob/main/docs/POSTMORTEM.md) for the screenshot.

We need per-cluster, tolerance-aware merging that respects topology. That's what `shapely` is for.

## The pipeline

1. **Illustrator JSX dumps cut-layer geometry to JSON.**
2. **shapely `linemerge`** chains compatible LineStrings.
3. **shapely `polygonize`** walks the merged graph, yields closed faces.
4. If yield is below expected, **snap-tolerance sweep** at increasing tolerances.
5. If snap-sweep fails, **auto-bridge inference** — greedy nearest-endpoint pairing inserts short bridges between near-but-not-touching endpoints, then re-runs linemerge.
6. If auto-bridge fails, **`concave_hull(ratio=0.3)`** as a lossy single-polygon fallback.
7. If concave_hull fails, **axis-aligned `bbox`** as last resort.
8. **Confidence score** (0.0 → 1.0) per fill so the user knows which layers were guessed.

## The confidence score

| Score | Strategy | Meaning |
|---|---|---|
| 1.00 | `linemerge_bare` | clean topology, polygons match strokes exactly |
| 0.85–0.95 | `linemerge_snap` | minor endpoint cleanup (tolerance ≤1pt) |
| 0.7–0.92 | `auto_bridge` | gaps inferred and bridged; usually correct shape |
| 0.55 | `concave_hull` | shape inferred, may not match cut exactly |
| 0.30 | `bbox` | geometry implied, almost certainly wrong |
| 0.00 | `failed` | no polygon recovered |

The CLI prints these alongside layer names so you know where to focus your overrides.

## Related

- [How-to: generate poché](../how-to/generate-poche.md)
- [Reference: `arch_line_weights.poche`](../reference/python-api.md)
- [Postmortem](the-postmortem.md)
