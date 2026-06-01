# arch-line-weights

[![CI](https://github.com/zohartito/arch-line-weights/actions/workflows/ci.yml/badge.svg)](https://github.com/zohartito/arch-line-weights/actions/workflows/ci.yml)
[![Docs](https://img.shields.io/badge/docs-mkdocs--material-blue)](https://zohartito.github.io/arch-line-weights/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)

Apply architectural line-weight hierarchy, optional solid-black poché, and
material hatching to Rhino-exported `.ai` or `.pdf` drawings.

If you've ever exported a section, plan, or elevation from Rhino and watched
all 340,000 strokes come out at a uniform 1.0 pt — and then tried to fix it
inside Illustrator only to have ExtendScript hang for hours — this is for you.

## What it does

- Inspects exported `.ai`/`.pdf` drawings and reports stroke-color counts.
- Rewrites stroke widths from a preset or hand-edited color mapping.
- Preserves layers when you use `apply-jsx` or `apply-saas`; the fast legacy
  `apply` command rewrites the PDF stream and can flatten Illustrator layers.
- Adds conservative poché fills for high-confidence section-cut mass.
- Ships explicit presets for `section`, `plan`, `elevation`, `detail`, and
  `usc` studio workflows.

```
$ arch-lw apply "DRAWING 4 SECTION [Converted].ai" --auto --preset usc
# 37 colors mapped using auto:usc
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

Total runtime: under 2 minutes for the original 24 MB / 340 K-stroke USC
reference file.

---

## Install

Current source install:

```
git clone https://github.com/zohartito/arch-line-weights
cd arch-line-weights
python -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/arch-lw --help
```

Optional global install if `pipx` is available:

```
pipx install git+https://github.com/zohartito/arch-line-weights
```

This installs the `arch-lw` CLI.
Do not assume `arch-lw`, `uv`, or `uvx` are globally on `PATH` in a fresh
studio shell; use `.venv/bin/arch-lw` from a source checkout or install with
`pipx`.

For the local designer-console prototype:

```
python -m pip install -e ".[console]"
arch-lw designer-console
```

This opens a local browser UI for choosing a drawing, running Inspect File,
Run Layout, Apply Line Weights, Generate Poché, and Export Proof Packet. It is
not public posting clearance, does not close #29/#30, and is not App Store or
Windows desktop packaging.

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

### Put a Rhino export on a sheet

If a Rhino Make2D export opens off the Illustrator artboard, normalize the
layout before running hierarchy or poché. In Rhino, first select the Make2D
curves and run:

```
_-RunPythonScript "/path/to/integrations/rhino/export_selected_make2d_manifest.py"
```

That writes an `.ai` / `.pdf` export plus a `.manifest.json` sidecar. Then run:

```
arch-lw layout-jsx rhino-make2d.ai \
  --artboard 24x36in \
  --fit fit \
  --margin 0.5in \
  --report-json layout-report.json
```

This opens the export in Illustrator, sets the requested artboard size, centers
or fits visible unlocked artwork, saves `<src> LAYOUT-jsx.ai`, and writes a
layout report. Use `--dry-run --jsx-path layout.jsx` to inspect the generated
script without contacting Illustrator or writing output artwork.

For a single report that chains layout with optional hierarchy and poché:

```
arch-lw bridge-rhino-ai \
  --input rhino-make2d.ai \
  --artboard 24x36in \
  --fit fit \
  --margin 0.5in \
  --preset usc \
  --source rhino \
  --for-print \
  --apply-jsx \
  --poche \
  --report-dir proof
```

Layout success is not launch proof. The proof gate still depends on the
verification reports and visual QA acceptance.

### Two apply modes — pick by what you need

| Mode | Speed | Layers | Use when |
|---|---|---|---|
| `apply-jsx` (default for `.ai`) | 3–15 min on 340K paths | **preserves** the original Rhino layers as Illustrator layers | You'll keep editing the file in Illustrator (almost always the right choice for studio work). |
| `apply` | ~2 min on 340K paths | **flattens to 1 layer** (PieceInfo gets stripped) | You only need a final render and don't care about layer structure. |

```
# Layer-preserving (recommended for Rhino-export .ai files):
arch-lw apply-jsx drawing.ai

# pikepdf-fast (loses layer structure):
arch-lw apply drawing.ai --auto --preset usc
```

Day-1 layer-preserving dogfood path:

```
.venv/bin/arch-lw inspect drawing.ai
.venv/bin/arch-lw apply-saas drawing.ai \
  --architectural --poche --preset usc --source rhino
```

Use basic `apply` for fast stroke-weight output. Use `apply-saas
--architectural --poche` when Cursor 1 needs layer-preserving hierarchy plus
conservative black poché for Illustrator/Acrobat inspection.

Input caveats for that path:

- `apply-saas --poche` requires a native Illustrator `.ai` with `/NumBlock`.
- PDF-only or `[Converted]` `.ai` files use `apply-jsx`, then `arch-lw poche`
  on the `HIERARCHY-jsx` output.
- Legacy Rhino PostScript `.ai` exports may need Illustrator File > Save As /
  re-save before v1 can process them.

`apply-jsx` uses a **semantic layer-name classifier**: anything in a
`Visible::ClippingPlaneIntersections::*` OCG is the section cut (1.0 pt);
`TEC_TIMBER_*`, `TEC_CLT_*`, `TEC_FOUNDATION` etc. are structure (0.5 pt);
`SHS_*` are secondary steel (0.35 pt); `WINDOW_GLASS` is glazing (0.25 pt);
cladding (`CU_*`) is material (0.18 pt); EPDM and `FLOOR_DATUMS` are
reference (0.13 pt). See `docs/POSTMORTEM.md` for why this is better than
color-based classification for Rhino files.

`apply` (pikepdf mode) buckets colors into the preset's tier ladder by
luminance. Good fallback for non-Rhino files where layer names don't
encode semantics.

```
arch-lw apply drawing.ai --auto --preset usc --dry-run    # preview
arch-lw apply drawing.ai --auto --preset usc              # commit
```

Add `--dry-run` to either to print the planned mapping without writing.

### Apply with a hand-edited mapping

When auto-mode misclassifies (e.g., it sticks "structural framing" in
the texture tier because it's the most common color), copy
`examples/sample-mapping.json`, edit, and pass it:

```
arch-lw apply drawing.ai --mapping my-mapping.json
```

A mapping file is just `{"RGB(r,g,b)": weight_pt, ...}`. Any color absent
from the mapping gets `--default-width` (0.25 pt unless overridden).

### Try the tiny repo sample

From a source checkout:

```
.venv/bin/arch-lw inspect examples/sample-linework.pdf
.venv/bin/arch-lw apply examples/sample-linework.pdf \
  --mapping examples/sample-mapping.json \
  -o /tmp/sample-linework-HIERARCHY.pdf
```

### Day-1 proof images

The section proof uses the Illustrator bridge path (`apply-jsx` followed by
`arch-lw poche`) on `WALL SECTION [Converted].ai`.

![Day-1 section proof close-up: solid cut mass, openings left white](docs/img/day1-proof/05-closeup-cut-mass-windows-white.png)

Proof assets:

- [Before: raw Rhino/Make2D export](docs/img/day1-proof/01-before-raw.png)
- [After: hierarchy + solid-black poché](docs/img/day1-proof/03-after-poche-full.png)
- [Layers panel: preserved `ClippingPlaneIntersections` layers](docs/img/day1-proof/04-layers-panel-clipping-poche.png)
- [Final poché PDF](docs/img/day1-proof/section-HIERARCHY-jsx-POCHE.pdf)

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

## Tier Presets

| Preset | Use it for |
|---|---|
| `usc` | USC studio sections and the original ARCH 202B reference workflow. |
| `section` | General building sections and wall sections. |
| `plan` | Floor plans, roof plans, site plans. |
| `elevation` | Elevations and projected views with no cut tier. |
| `detail` | Wall details and connection details. |

Default screen-review weights:

| Preset | Cut / Heaviest | Profile | Edges | Material | Texture | Special |
|---|---:|---:|---:|---:|---:|---:|
| `usc` | 1.0 | 0.5 | 0.3 | 0.18 | 0.08 | 0.25 |
| `section` | 1.0 | 0.5 | 0.3 | 0.18 | 0.08 | 0.25 |
| `plan` | 0.71 | 0.5 | 0.35 | 0.25 | 0.18 | 0.35 |
| `elevation` | 1.0 | 0.71 | 0.5 | 0.25 | 0.18 | 0.35 |
| `detail` | 1.5 | 1.0 | 0.5 | 0.35 | 0.25 | 0.42 |

The "Special" tier is for glazing / water / sky — anything not architectural
that you want held back at a mid weight regardless of darkness.

USC 1/4-inch studio print table:

| Tier | mm | pt | Goes Here |
|---|---:|---:|---|
| `cut` | 0.70 | 1.985 | Section-cut walls, floors, roofs, ground. |
| `profile` | 0.50 | 1.417 | Foreground profiles and primary structure. |
| `edges` | 0.35 | 0.992 | Object edges, secondary structure, frames. |
| `material` | 0.18 | 0.510 | Material indication and surface breaks. |
| `texture` | 0.13 | 0.369 | Dense hatch, grain, surface texture. |
| `special` | 0.25 | 0.709 | Glazing, water, sky, and middle-weight exceptions. |

The public USC print convention uses 0.13 mm as the lightest standard
surface/hatch weight, matching the project convention in
[`CONVENTIONS.md`](CONVENTIONS.md). The screen-review `usc` preset still keeps
0.08 pt for dense on-screen texture because monitor review is not print proofing.

---

## Honest v1 Limits

- The legacy `apply` path rewrites the visible PDF stream and can flatten
  Illustrator layer structure when `/PieceInfo` is stripped.
- `apply-jsx` requires Adobe Illustrator on the machine running the command.
- The `apply-saas` path preserves Illustrator private layer data and supports
  native RGB `XA` and CMYK `K` stroke colors. It rewrites stroke operators only;
  fill operators are intentionally left alone except for generated poché fills.
- Automatic poché is conservative. It fills only high-confidence structural cut
  mass by default; ambiguous helper-only Make2D geometry is reported or left for
  review rather than turned into a black blob.
- Multi-page documents are supported by the PDF-stream path; the AI-private
  `apply-saas` path is focused on Illustrator-saved `.ai` drawings.
- The repo includes only a tiny PDF smoke fixture. Large real USC `.ai` samples
  are intentionally not committed.
- PyPI publishing is not done yet; install from source or GitHub for now.
- Bluebeam review is Windows-only and unverified for v1; use Illustrator and
  Acrobat for the current Mac dogfood loop.

---

## Roadmap

- [x] Phase 1 — MVP: inspect + apply, auto-by-luminance, JSON mappings, presets
- [ ] Phase 2 — Claude Code skill: install once, invoke via slash command
- [ ] Phase 3 — Smarter classify: use saturation + hue family + frequency
      to detect glazing/water/structural/texture automatically
- [ ] Phase 4 — Per-drawing-type defaults; preview generator
- [ ] Phase 5 — SVG support; native PDF input alongside .ai
- [ ] Phase 6 — Batch + watch mode for live Rhino-export workflows
- [ ] Phase 7 — plain PyPI install once publishing is deliberately re-enabled

---

## License

MIT.
