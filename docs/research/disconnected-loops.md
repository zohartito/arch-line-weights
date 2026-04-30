# Closing disconnected polyline boundaries (Make2D rescue)

> Sub-agent research, 2026-04-30. Strategies for cut-shape polylines that
> Rhino's Make2D + ClippingPlane outputs as topologically disconnected
> segments — `linemerge + polygonize` returns 0 polygons.

## Concrete failure case

USC ARCH 202B reference drawing, layer
`Visible::ClippingPlaneIntersections::TEC_FOUNDATION`: 10 line segments,
should form one closed cut boundary of the building foundation. Bare
`shapely.ops.linemerge` chains 0 of them — endpoints don't share within any
sane tolerance.

## Strategy ladder

| # | Strategy | Confidence | When to use |
|---|---|---|---|
| 1 | `linemerge` (no snap) + `polygonize` | 1.00 | Default — works for ~70% of layers |
| 2 | `snap`(tol=0.5pt) → `linemerge` | 0.90 | Small float-precision gaps |
| 3 | `snap`(tol=2.0pt) → `linemerge` | 0.70 | Sloppy Make2D output |
| 4 | `snap`(tol=5.0pt) → `linemerge` | 0.60 | Risk: over-snapping merges separate shapes |
| 5 | `__POCHE_CLOSE__` user-marked closing layer | 0.95 | **Highest-fidelity escape hatch** — user draws a few segments in Rhino on a special layer that bridges known gaps |
| 6 | `concave_hull(densified, ratio=0.3-0.5)` | 0.55 | One lumpy polygon, OK for visual mass |
| 7 | Per-layer JSON override | 0.80 | `{"TEC_FOUNDATION": "bbox"}` |
| 8 | Axis-aligned bounding box | 0.30 | Last resort, never empty |

Empirical Make2D tolerance per McNeel forum thread: gaps from clipping-plane
intersections can reach **2–5 pt** when curves are near-parallel. Match
`Join` tolerance to `AbsoluteTolerance × 10`.

## Library notes

- **Shapely 2.x** native — covers strategies 1, 2, 3, 4, 6, 8
- **`alphashape`** PyPI — richer alpha control than shapely's `concave_hull`
- **`shapely.segmentize(line, max_segment_length=2.0)`** — densify before
  concave_hull so endpoints aren't sparse

Densify all segments before concave_hull; otherwise sparse points produce a
bad hull.

## Rhino-side fix (push to user before tool runs)

Best Rhino settings, in order of effectiveness:

1. Run `Make2D` then `Join` with `Tolerance=AbsoluteTolerance` on output
   curves before export
2. In `Make2D` options, enable **"Maintain source layers"** + **"Group output
   by source object"** ([McNeel docs](http://docs.mcneel.com/rhino/8/help/en-us/commands/make2d.htm))
3. For DXF export use the `2D Curves` scheme; PDFs lose join info
4. `SelDup` + `Join` as a cleanup macro after Make2D

This is a **prerequisite improvement**, not a fallback — push users to do
this first.

## Proposed `arch-lw` API (v0.4)

```python
# tool reports per-layer confidence + strategy used
arch-lw poche drawing.ai --report

# user supplies overrides for known-bad layers
arch-lw poche drawing.ai --override poche-overrides.json

# enable __POCHE_CLOSE__ layer merging
arch-lw poche drawing.ai --close-layer __POCHE_CLOSE__
```

The output JSON would emit per-fill metadata:

```json
{
  "layer": "TEC_FOUNDATION",
  "strategy": "concave_hull_0.3",
  "confidence": 0.55,
  "polygon_count": 1,
  "segment_count": 10
}
```

so the user's UI can flag low-confidence fills as warnings.

## Sources

- [Shapely 2.x docs — concave_hull](https://shapely.readthedocs.io/en/stable/reference/shapely.concave_hull.html)
- [Shapely 2.x docs — segmentize](https://shapely.readthedocs.io/en/stable/reference/shapely.segmentize.html)
- [`alphashape` on PyPI](https://pypi.org/project/alphashape/)
- [McNeel forum — Make2D curves not joining](https://discourse.mcneel.com/t/make2d-curves-not-joining/106677)
- [McNeel docs — Make2D (Rhino 8)](http://docs.mcneel.com/rhino/8/help/en-us/commands/make2d.htm)
