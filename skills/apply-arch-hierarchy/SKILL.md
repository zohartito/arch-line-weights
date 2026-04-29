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

2. **Apply** with one of:
   - `--auto --preset section|plan|elevation|detail` (auto-bucket by luminance)
   - `--mapping mapping.json` (user-defined, see `examples/sample-mapping.json`)
   ```bash
   arch-lw apply "path/to/drawing.ai" --auto --preset section
   ```

3. **Always run with `--dry-run` first** if the file is more than a few MB or
   has many unique colors — the dry run prints the planned mapping so the user
   can sanity-check before committing.

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
