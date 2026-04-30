---
name: apply-arch-hierarchy
description: |
  Apply an architectural line-weight hierarchy to a Rhino-exported .ai or .pdf
  drawing. Trigger when the user asks to "fix line weights", "apply line weight
  hierarchy", "set up line weights for my section/plan/elevation", or hands you
  a Rhino-exported vector file and asks for proper architectural rendering.
  Backed by the `arch-lw` CLI from https://github.com/zohartito/arch-line-weights.
---

# Apply architectural line-weight hierarchy

## When to use

- A vector drawing (.ai or .pdf) where every stroke is currently the same width
  and the only differentiator is stroke color (Rhino → Illustrator export pattern).
- The user wants conventional architectural line-weight hierarchy:
  cut > profile > edges > material > texture (lightest).

## What it does

Rewrites the PDF content stream so each stroke gets a width based on its
stroke RGB color. Strips the `.ai` `/PieceInfo` cache so Illustrator honors
the new widths. Original file is never modified — output is `<src> HIERARCHY.<ext>`.

## How to invoke

1. **Inspect first** to see the color distribution:
   ```bash
   arch-lw inspect "path/to/drawing.ai" > /tmp/inspect.json
   ```
   Read the file and report top colors + counts to the user.

2. **For Rhino-exported `.ai` files: use `apply-jsx` (preserves layers)**:
   ```bash
   arch-lw apply-jsx "path/to/drawing.ai"
   ```
   Uses semantic layer-name classifier (`Visible::ClippingPlaneIntersections::*`
   = cut tier, etc.). Slow (3–15 min on 340K paths) but layer-fidelity-preserving.

3. **For non-Rhino files or when layer fidelity doesn't matter: use `apply`**:
   - `--auto --preset section|plan|elevation|detail` (auto-bucket by luminance)
   - `--mapping mapping.json` (user-defined)
   - `--scale 1/16|1/8|1/4|1/2 --for-print` for ISO 128 / Ramsey-Sleeper plotted weights
   ```bash
   arch-lw apply "drawing.ai" --auto --preset section --scale 1/4 --for-print
   ```

4. **For poché (solid black on cut elements)** — after applying line weights:
   ```bash
   arch-lw poche "path/to/drawing HIERARCHY.ai"
   ```
   Two-stage pipeline (Illustrator dump → shapely polygonize → Illustrator apply).
   Reports per-layer confidence; concave_hull fallback for disconnected
   geometry. Some layers may need `--overrides poche-overrides.json` for
   foundations / concrete bases that don't auto-close.

5. **Always run apply commands with `--dry-run` first** if the file has many
   unique colors — the dry run prints the planned mapping.

## Rules of engagement

- Never write to the source path. Output defaults to `<src> HIERARCHY.<ext>`.
- For files with `/PieceInfo` (most Illustrator-saved .ai), the script strips
  it. The user should be told that on first save inside Illustrator the file
  size will balloon as Illustrator rebuilds its private cache.
- If the user has Adobe Illustrator open with the source file, that's fine —
  `arch-lw` doesn't touch it. Tell them to close+reopen the new HIERARCHY file.
- For files with CMYK or Gray strokes (not RGB), those strokes get
  `--default-width` and a warning. RGB-only is the supported sweet spot.

## Common drawing presets (pt)

| Preset    | Cut  | Profile | Edges | Material | Texture | Special |
|-----------|------|---------|-------|----------|---------|---------|
| section   | 1.0  | 0.5     | 0.3   | 0.18     | 0.08    | 0.25    |
| plan      | 1.0  | 0.5     | 0.3   | 0.18     | 0.08    | 0.25    |
| elevation | 1.0  | 0.5     | 0.3   | 0.18     | 0.08    | 0.25    |
| detail    | 1.5  | 0.7     | 0.4   | 0.25     | 0.13    | 0.3     |
