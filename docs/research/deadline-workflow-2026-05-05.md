# Deadline Workflow

Date: 2026-05-05

Use this when drawings are due and the local engine is good enough to create a
base sheet but not yet good enough to finish every poché face automatically.

## Current Best Iso Axon Base

For `iso axon section  [Converted].ai`, use:

```text
/Users/zohartito/SynologyDrive/USC/Spring 2026/ARCH 202B/iso axon section  [Converted] HIERARCHY-saas-ARCHITECTURAL-v0622-beam-cells.ai
```

Keep its report next to it:

```text
/Users/zohartito/SynologyDrive/USC/Spring 2026/ARCH 202B/iso-axon-v0622-beam-cells-report.json
```

Do not use the low-confidence roof-cap experiment for print:

```text
iso axon section  [Converted] HIERARCHY-saas-ARCHITECTURAL-v0620-lowconf-roofcap.ai
```

That file proves why low-confidence bbox fills remain diagnostic-only: it
creates a visible black roof/rainscreen blob.

## Hierarchy Only

Use this for drawings with no section cut poché, or when the drawing just needs
architectural line-weight hierarchy.

```bash
cd /Users/zohartito/SynologyDrive/Projects/arch-line-weights
PYTHONPATH=src pyenv exec python -m arch_line_weights.cli apply-saas \
  "/path/to/drawing.ai" \
  --architectural --auto --preset section --source rhino --no-progress
```

Swap `--preset section` for `plan`, `elevation`, or `detail` when the drawing
type changes.

## Current Best Stair Axon Base

For `stairs.ai`, the original file is old Rhino PostScript and cannot be read by
the headless native-payload path. Use the Illustrator JSX path or the already
generated deadline candidate:

```text
/Users/zohartito/SynologyDrive/USC/Spring 2026/ARCH 202B/stairs HIERARCHY-jsx-v0624-stair-path-clean.ai
```

What changed:

- `FIXED_STAIR_COHESIVE` is now recognized as stair structure.
- 30 sub-1 pt Make2D debris fragments were removed.
- 422 short/detail paths were set to 0.18 pt.
- 161 medium paths were set to 0.25 pt.
- 57 long/profile paths were set to 0.5 pt.
- All remaining stair paths were set to CMYK black.

This path-level cleanup is a prototype, not yet a general CLI feature. The next
engineering step is to turn it into a tested one-layer geometry hierarchy mode
so stair treads, stringers, landings, and stray Make2D fragments are handled
without a special Illustrator script.

## Hierarchy Plus Safe Poché

Use this for sections where structural cut mass should become black poché.

```bash
cd /Users/zohartito/SynologyDrive/Projects/arch-line-weights
ARCH_LW_BRIDGE_BEST_LAYER_BUDGET_SEC=60 \
ARCH_LW_BRIDGE_BEST_MAX_ENDPOINTS=1000 \
PYTHONPATH=src pyenv exec python -m arch_line_weights.cli apply-saas \
  "/path/to/drawing.ai" \
  --architectural --auto --preset section --source rhino \
  --poche --bridge-strategy=best \
  --report "/path/to/drawing.arch-lw-report.json" \
  --no-progress
```

If a file starts hanging or you need a faster batch pass, lower:

```bash
ARCH_LW_BRIDGE_BEST_LAYER_BUDGET_SEC=5
```

## Quick Diagnosis

Before running a new file, inspect whether layer/color detection makes sense:

```bash
PYTHONPATH=src pyenv exec python -m arch_line_weights.cli inspect \
  "/path/to/drawing.ai" --no-pretty > "/path/to/drawing.inspect.json"
```

Dry-run the hierarchy mapping:

```bash
PYTHONPATH=src pyenv exec python -m arch_line_weights.cli apply-saas \
  "/path/to/drawing.ai" \
  --architectural --auto --preset section --source rhino \
  --dry-run --no-progress
```

## Manual Cleanup Layer

When the automatic output misses a true cut face, do not edit original Rhino
layers directly.

1. Save a working copy with `_AI_CLEANUP` in the filename.
2. Lock all original imported layers.
3. Keep `ARCH_LW_POCHE` visible but locked.
4. Create a new top layer named `ARCH_LW_POCHE_CLEANUP`.
5. Put only manual poché fixes on that cleanup layer.

Turn on:

```text
View > Smart Guides
View > Snap to Point
View > Snap to Pixel: off
```

Use `Cmd+Y` for Outline mode when checking whether a shape is actually closed.

## Cleaning A Bad Poché Box

For a box that is almost right but not square:

1. Select the bad shape on `ARCH_LW_POCHE_CLEANUP`.
2. Use Direct Selection (`A`) to select the bad corner points.
3. If two endpoints should become one corner, use
   `Object > Path > Average...` and choose `Both`.
4. If the side is just skewed, drag the endpoint while holding `Shift` until it
   snaps horizontally or vertically to the opposite side.
5. If a fourth edge is missing, draw it with the Line Segment tool (`\`) between
   the two open endpoints.
6. Select the two open endpoints and use `Object > Path > Join` (`Cmd+J`) only
   when Illustrator will connect the correct endpoints.
7. If the imported geometry is messy, use Shape Builder (`Shift+M`) to drag
   through the region that should become one filled rectangle. Hold `Option` to
   remove accidental slivers.
8. For a final clean filled shape, duplicate the repaired outline and try
   `Pathfinder > Unite`. If Unite creates junk, undo and use Shape Builder.

The target is one closed black filled shape per true cut mass, not a pile of
overlapping strokes.

## Final Visual Pass

Check these zones on the iso axon:

- left retaining wall and small blob above it
- rain screen/top roof area
- first-floor slab/beam squares
- right retaining wall/foundation
- roof cut solidity and white stripes
- connector/secondary steel hierarchy

The output is acceptable for deadline use when true cut mass reads clearly,
false roof/rainscreen blobs are absent, and remaining fixes are isolated on
`ARCH_LW_POCHE_CLEANUP`.
