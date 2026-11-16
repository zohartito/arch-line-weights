# Generate poché

You have a `HIERARCHY.ai` (or any layered Illustrator file) where the cut layers live under `Visible::ClippingPlaneIntersections::*`. You want them filled solid black.

## The command

```bash
arch-lw poche "drawing HIERARCHY.ai" --style solid
```

Writes `drawing POCHE.ai`. Original strokes are preserved; new closed `pathItem`s with a black fill are inserted into each cut layer.

## What happens

1. Illustrator opens the file.
2. A JSX dumps the path geometry of every `ClippingPlaneIntersections::*` layer to JSON.
3. Python runs `shapely.ops.linemerge` to join coincident endpoints, then `polygonize` to recover closed regions.
4. If a layer's lines don't cleanly form polygons, the rescue ladder kicks in:
    - tolerance sweep at **0, 0.1, 0.5, 1, 2, 5 pt** (bare polygonization plus five snap tolerances)
    - structural helper/open-loop recovery for eligible structural layers
    - **auto-bridge**, default `best`: choose among greedy, backtracking, DBSCAN endpoint collapse, and DBSCAN + backtracking; `--bridge-strategy greedy` selects the legacy bridger
    - structural open-loop recovery after bridging when applicable
    - **alpha-shape** rescue (on by default; `--no-alpha-shape` disables it)
    - optional LLM topology rescue only with explicit opt-in and external consent
    - `concave_hull(ratio=0.3)` fallback
    - axis-aligned `bbox` fallback

   Low-confidence hull/alpha/bbox results remain review-gated; recovery does not
   automatically mean a fill is eligible for injection.
5. A second JSX writes the resulting polygons back into Illustrator and saves the file.

## Per-layer overrides

When the auto-strategy gets a layer wrong, override it:

```bash
arch-lw poche drawing.ai --overrides overrides.json
```

`overrides.json`:

```json
{
  "axon::Visible::ClippingPlaneIntersections::TEC_FOUNDATION": {
    "strategy": "bbox"
  },
  "axon::Visible::ClippingPlaneIntersections::TEC_CONCRETE_BASE": {
    "strategy": "concave_hull",
    "ratio": 0.4
  }
}
```

Available overrides: `linemerge` (bare polygonization only), `snap` (snap
tolerances only), `concave_hull`, `bbox`, `skip`. Omit `strategy` to use the
full automatic ladder. Forced `linemerge`/`snap` return `failed` when no
polygon is recovered; they never fall through to bridging or hulls. Unknown
strategy names are rejected.

## Read the report

```text
✓ TEC_CONCRETE_WALL          linemerge_bare     polys=  4  conf=1.00
✓ TEC_TIMBER_BEAMS           auto_bridge        polys= 10  conf=0.92
~ TEC_FOUNDATION             concave_hull       polys=  1  conf=0.55
✗ TEC_CLT_PANELS             failed             polys=  0  conf=0.00
```

## Related

- [Material hatching](material-hatching.md)
- [Explanation: how poché works](../explanation/how-poche-works.md)
- [Troubleshoot](troubleshoot.md)
