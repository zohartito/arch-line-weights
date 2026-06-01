# Poché pipeline (work in progress, v0.3.0-alpha)

This directory holds the working scripts for the architectural-poché feature.
The pipeline is **not yet wired into the `arch-lw` CLI** — these are the
prototypes that produced the reference-drawing result in v0.3.0-alpha.

## Pipeline

```
HIERARCHY.ai
    │
    │  (1) Illustrator JSX dumps every path's anchor points per layer
    ↓
dump_cut_geometry.jsx    →    /tmp/cut_geometry.json
    │
    │  (2) Python reads anchors, runs shapely linemerge + polygonize
    │      with a per-layer best-tolerance sweep + concave_hull fallback
    ↓
polygonize.py            →    /tmp/poche_polygons.json
    │
    │  (3) Python bakes the polygons into a JSX file
    ↓
build_apply_jsx.py       →    /tmp/apply_poche_shapely.jsx
    │
    │  (4) Illustrator runs the JSX, creates new closed path-items
    │      filled with black on the matching cut layers, saves as POCHE.ai
    ↓
POCHE.ai
```

## Status (current run on a local reference drawing)

| Outcome | Layers | Notes |
|---|---|---|
| ✅ Clean polygons | 13 / 21 | bare linemerge produced N separate closed loops, exactly as expected |
| ⚠️  Concave-hull fallback | 7 / 21 | `linemerge` gave 0 polys → fell back to `concave_hull(ratio=0.3)` which produces ONE lumpy polygon instead of N proper cut shapes |
| ❌ Failed | 1 / 21 | `23_WINDOW_FRAMES` — too few points even for concave_hull |

## Why some layers fail

Rhino's `Make2D` + ClippingPlane outputs each cut shape as a *bag of short
polyline segments* (typically 1–2 anchor points per pathItem). For most
materials the segments share endpoints exactly, so `shapely.ops.linemerge`
chains them into closed loops correctly. But for some layers (notably
foundations, concrete bases, certain window frames) the segments are
**topologically disconnected**: there are gaps the section plane never
filled, or the cut profile is rendered with multiple disconnected component
strokes. For those, `concave_hull` is a quick rescue that gives *something*
but not *the right thing*.

## Known fixes (future work)

See `docs/POSTMORTEM.md` for the full story. Short version of fixes to try:

1. **Increase snap tolerance per-layer** — current "best tolerance" search tries
   bare linemerge first, then snap at 0.5/1/2/5pt. The disconnected layers may
   need user-tuned tolerance.
2. **`__POCHE_CLOSE__` user-marked closing layer** — let the user draw a few
   short segments in Rhino on a special layer that bridges the known gaps. The
   tool merges them in before polygonize. Highest-fidelity option.
3. **Rhino-side fix** — re-run `Make2D` then `Join` with
   `Tolerance=AbsoluteTolerance` before exporting; or enable
   "Group output by source object" in Make2D options.
4. **Per-layer JSON override** — accept `{"TEC_FOUNDATION": "bbox"}` to force
   a specific strategy on known-bad layers.
5. **Material-specific hatching** instead of solid black for concrete / CLT
   (see `docs/research/material-hatching.md`).

## Files

- `dump_cut_geometry.jsx` — JSX that walks `ClippingPlaneIntersections::*` layers and writes `/tmp/cut_geometry.json`
- `polygonize.py` — shapely linemerge + polygonize with layered fallback
- `build_apply_jsx.py` — bakes the polygons into an Illustrator JSX (no I/O at runtime)
- `extract_geometry_from_pdf.py` — alternate extractor that walks the PDF content stream directly (kept for reference; the JSX extractor is more reliable)
- `apply_join_NAIVE.jsx` — **broken approach kept for the postmortem**: tried `app.executeMenuCommand("join")` to chain endpoints. Illustrator's Join is not topology-aware, produced one tangled self-intersecting polygon per layer. See `docs/POSTMORTEM.md` for the full story.
