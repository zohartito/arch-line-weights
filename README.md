# arch-line-weights

Apply architectural line-weight hierarchy to a Rhino-exported `.ai` or `.pdf`
in seconds, without ever opening Illustrator.

If you've ever exported a section, plan, or elevation from Rhino and watched
all 340,000 strokes come out at a uniform 1.0 pt — and then tried to fix it
inside Illustrator only to have ExtendScript hang for hours — this is for you.

```
$ arch-lw apply "DRAWING 4 SECTION [Converted].ai" --auto --preset section
# 37 colors mapped using auto:section
--- 1.0 pt ---
  RGB( 40, 40, 40)    5,862 strokes
  ...
applied 340,323 strokes across 49 color changes
   0.08 pt  →  298,443 strokes
   0.18 pt  →    6,381 strokes
   0.25 pt  →      494 strokes
    0.3 pt  →   25,120 strokes
    0.5 pt  →    3,967 strokes
    1.0 pt  →    5,918 strokes

wrote DRAWING 4 SECTION [Converted] HIERARCHY.ai  (4,081,388 bytes)
```

Total runtime: under 2 minutes for a 24 MB / 340 K-stroke file.

---

## Install

```
git clone https://github.com/zohartito/arch-line-weights
cd arch-line-weights
pip install -e .
```

This installs the `arch-lw` CLI.

To wire up the Claude Code skill:

```
ln -s "$(pwd)/skills/apply-arch-hierarchy" ~/.claude/skills/apply-arch-hierarchy
```

After the symlink, ask Claude Code to "apply line weights to my section" and
the skill will fire.

---

## Usage

### Inspect first

Always look at the color distribution before applying. Most Rhino-export
files have ~10–50 unique stroke colors, one per Rhino layer:

```
arch-lw inspect drawing.ai > inspect.json
```

The JSON contains every stroke RGB and how many strokes use it. The dominant
colors (highest counts) are almost always **material hatch / texture** — they
should land in the lightest tier.

### Apply with auto-classification

Auto-mode buckets every color into the preset's tier ladder by luminance
(darker → heavier) with frequency as a tie-breaker (more common → lighter).
Good first pass:

```
arch-lw apply drawing.ai --auto --preset section
arch-lw apply drawing.ai --auto --preset plan
arch-lw apply drawing.ai --auto --preset elevation
arch-lw apply drawing.ai --auto --preset detail
```

Add `--dry-run` to print the planned mapping without writing the file.

### Apply with a hand-edited mapping

When auto-mode misclassifies (e.g., it sticks "structural framing" in
the texture tier because it's the most common color), copy
`examples/sample-mapping.json`, edit, and pass it:

```
arch-lw apply drawing.ai --mapping my-mapping.json
```

A mapping file is just `{"RGB(r,g,b)": weight_pt, ...}`. Any color absent
from the mapping gets `--default-width` (0.25 pt unless overridden).

---

## How it works (and why it's fast)

A `.ai` file is a PDF with extra. The PDF content stream has all the path
geometry; the `.ai` adds an `/PieceInfo /Illustrator /Private` block that
caches the same geometry in Adobe's native format. Illustrator reads from
the private block, ignoring the PDF stream when it can.

`arch-lw apply` does two things:

1. **Rewrites the PDF content stream:** for every stroke operator (`S`, `s`,
   `B`, `B*`, `b`, `b*`) it injects `<width> w` ahead, where `<width>` comes
   from the per-color mapping. Tracks the most recent `RG` (set stroke RGB)
   to know which color the stroke is.
2. **Strips `/PieceInfo`:** so Illustrator has no choice but to re-parse the
   modified PDF stream. Illustrator rebuilds its private cache on first save.

This sidesteps ExtendScript entirely. Per-item iteration in ExtendScript on
340 K paths exhibits exponential slowdown from undo-history bloat — the same
work in pikepdf is a single linear pass.

---

## Tier presets (pt)

| Preset    | Cut  | Profile | Edges | Material | Texture | Special |
|-----------|------|---------|-------|----------|---------|---------|
| section   | 1.0  | 0.5     | 0.3   | 0.18     | 0.08    | 0.25    |
| plan      | 1.0  | 0.5     | 0.3   | 0.18     | 0.08    | 0.25    |
| elevation | 1.0  | 0.5     | 0.3   | 0.18     | 0.08    | 0.25    |
| detail    | 1.5  | 0.7     | 0.4   | 0.25     | 0.13    | 0.3     |

The "Special" tier is for glazing / water / sky — anything not architectural
that you want held back at a mid weight regardless of darkness.

---

## Limitations

- Only RGB stroke colors are remapped. CMYK and Gray strokes get
  `--default-width`. (Most Rhino exports are RGB.)
- The PDF stream rewrite is for stroked geometry only. Filled paths are not
  touched (Rhino exports rarely have fills).
- Stripping `/PieceInfo` means Illustrator opens the file as if it were a
  generic PDF — flat, single-layer. If your `.ai` had carefully organized
  layers/groups (rare for Rhino exports), `--keep-pieceinfo` preserves them
  but Illustrator will then ignore the new widths. Pick your poison.
- Multi-page documents are supported; every page gets the same treatment.

---

## Roadmap

- [x] Phase 1 — MVP: inspect + apply, auto-by-luminance, JSON mappings, presets
- [ ] Phase 2 — Claude Code skill: install once, invoke via slash command
- [ ] Phase 3 — Smarter classify: use saturation + hue family + frequency
      to detect glazing/water/structural/texture automatically
- [ ] Phase 4 — Per-drawing-type defaults; preview generator
- [ ] Phase 5 — SVG support; native PDF input alongside .ai
- [ ] Phase 6 — Batch + watch mode for live Rhino-export workflows
- [ ] Phase 7 — `pip install arch-line-weights` from PyPI

---

## License

MIT.
