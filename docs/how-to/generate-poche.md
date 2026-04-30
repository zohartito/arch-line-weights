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
    - snap-tolerance sweep (4 increasing tolerances)
    - **auto-bridge** inference (greedy nearest-endpoint pairing for sub-50pt gaps)
    - `concave_hull(ratio=0.3)` fallback
    - axis-aligned `bbox` fallback
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

Available strategies: `linemerge` (default), `snap`, `concave_hull`, `bbox`, `skip`.

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
