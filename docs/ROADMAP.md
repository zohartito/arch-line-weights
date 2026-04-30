# Roadmap

This is the long-form companion to the table in [README.md](../README.md).
Each phase has a "why ambitious" note so future maintainers can see what
we're optimizing for.

## Status legend
- ✅ shipped
- 🚧 in progress
- ⏸️ planned
- ❓ exploratory

---

## Phase 1 — MVP color-classify (✅ shipped 0.1.0)
Working `inspect` + `apply` (pikepdf) + auto-by-luminance classifier +
section/plan/elevation/detail presets + Claude Code skill. Validated on
a 24 MB / 340 K-stroke section drawing in 110 s.

## Phase 2 — Layer preservation + semantic classify (✅ shipped 0.2.0)
Two key shifts:
- **Default for `.ai` is now `apply-jsx`** — hands a JSX to Illustrator,
  preserves all layers, slower but correct.
- **Semantic layer-name classifier** — Rhino's `Visible::ClippingPlaneIntersections::*`
  always = cut tier; material suffix table for Curves layers.

This phase fixed the v0.1 layer-flattening bug. See `POSTMORTEM.md`.

## Phase 3 — Poché (🚧 in progress, target 0.3.0)
Architectural sections aren't done at line weights — the "cut" reads as
**solid black fill** (poché) on cut structural elements. v0.3 adds:
- A `--poche` flag on `apply-jsx` that fills closed paths in
  `ClippingPlaneIntersections` layers with solid black.
- `vpype linemerge` (Python) pre-pass to chain open Make2D output
  endpoints into closed loops at ~0.05 mm tolerance, before handing to JSX.
- Compound-path handling for donut shapes (CLT panel cut showing
  inside-out) using even-odd fill.
- Material-class overrides: glass layers stay blank/outline; concrete /
  CLT / steel get black fill; insulation gets hatch (defer to 3.1).

**Why ambitious**: this is the move that turns "pretty good line weights"
into "the cut reads from across the room" — the single highest-impact
visual upgrade for an architectural section.

## Phase 4 — Standards-compliant presets (⏸️ planned 0.4.0)
Tier weight values cited from authoritative sources rather than first-
principles guessing:
- Ramsey/Sleeper Architectural Graphic Standards
- Francis Ching, *Architectural Graphics* (6th ed)
- AIA standard practice
- NCARB ARE study guides
- USC / GSD / MIT studio reference docs

Per-scale (1/4"=1', 1/8"=1', 1/16"=1', 3/8"=1') tier sets, with print-vs-
screen variants. Sub-agent research already returned candidate values.

## Phase 5 — Hybrid classifier (⏸️ planned 0.5.0)
Score every available signal per stroke / per layer and pick the most
confident:
- (a) layer-name pattern (Phase 2)
- (b) layer position in document (top-of-stack often = front)
- (c) color luminance / saturation / hue
- (d) frequency
- (e) stroke geometry (long-and-straight vs short-and-curvy)

Returns a confidence score per assignment so the user can review only
the ambiguous ones.

## Phase 6 — Visual preview generator (⏸️ planned 0.6.0)
Pipeline: `pikepdf` modifies → `pymupdf` renders side-by-side before/after
PNG at multiple plot scales (1/4", 1/8", 1/16"). Per-tier color overlay
(cut=red, profile=orange, etc.) so the user can verify each tier is going
where they expect. Ghostscript `-dNOMINLINEWIDTH` fallback for hairline
accuracy.

## Phase 7 — Multi-format input (⏸️ planned 0.7.0)
Priority order from sub-agent research:
1. **PDF with OCGs** (covers AutoCAD, Vectorworks, ArchiCAD, Revit-via-DWG)
2. **Native SVG** (lxml, sub-second on 340K nodes)
3. **IL-native PieceInfo decoder** (niche but high-value)
4. **Color-only fallback** for flat PDFs (Revit native, Inkscape SVG→PDF)
5. **Affinity** — defer until they ship an API

Each format gets its own classifier where Rhino conventions don't apply.

## Phase 8 — Workflow integration (⏸️ planned 0.8.0)
- **Watch mode** — re-apply on Rhino re-export (use `watchdog`)
- **Batch mode** — process whole folders
- **`--scale` flag** — adjust weights for plot scale
- **`--for-print` / `--for-screen`** — different weight ranges

## Phase 9 — Studio template system (⏸️ planned 0.9.0)
YAML templates contributed by users:
- USC ARCH 202B / 502 conventions
- GSD studio standards
- AIA construction docs (NCS pen weights)
- NCARB ARE conventions

The first repo-user-contributed format. Goal: become the de-facto portable
preset format (analogous to `.editorconfig`).

## Phase 10 — GUI (⏸️ planned 1.0.0)
- Web app with drag-drop + live preview
- VS Code / Cursor extension wrapper
- Polished Claude Code skill (already exists; refine)
- Optional Eto.Forms toolbar button **inside Rhino** (see Phase 11)

## Phase 11 — Distribution & quality (⏸️ planned 1.1.0)
- PyPI: `pip install arch-line-weights`
- Homebrew tap: `brew install arch-line-weights`
- CI with GitHub Actions (mypy / pytest / coverage / benchmark)
- Notarized macOS .pkg installer
- Docker image for CI use

## Phase 12 — Rhino integration (❓ exploratory, target 1.2.0)
Most-leverage approach (per sub-agent research): **GhPython 3 component**
that shells out to `arch-lw`. Ships as a single `.gh` file, runs on
Win + Mac, no plugin install. Long-term: an Eto.Forms toolbar button
inside Rhino itself.

Smarter trick: inject `__TIER:cut` into Rhino layer names *at export time*
so the downstream classifier never has to guess. Requires a tiny RhinoScript
or GhPython script that runs before PDF/AI export.

## Phase 13 — Smart classification (LLM-assisted) (❓ exploratory)
When layer names are missing or ambiguous, send the inspection JSON to an
LLM (Claude API) to suggest a mapping. The LLM examines layer names + colors
+ path-geometry summary and proposes a tier per path-class with reasoning.
User confirms or edits.

## Phase 14 — Multi-drawing consistency (❓ exploratory)
Apply the same hierarchy across plan / section / elevation set so a sheet
reads as one drawing. Detect that all three are present (filename heuristic
or user input), use the same color-or-layer mapping across all of them.

## Phase 15 — Style transfer (❓ exploratory)
"Make my drawing look like this reference" — extract weight ratios + poché
style from a reference PDF, apply to the user's drawing. Reference can be a
canonical published section (Tatiana Bilbao, OFFICE KGDVS, SO-IL, etc.).

---

## Sub-agent research artifacts to fold into the code

This roadmap synthesizes findings from 6 sub-agents launched on 2026-04-29:

| Agent | Phase consumed |
|---|---|
| ExtendScript performance | 2 (validated `maximumUndoDepth`) |
| UXP from CLI | dead end — explicit non-goal documented |
| Alternative vector tools | 6 (visual preview), 7 (multi-format) |
| Visual preview / PDF rendering | 6 (PyMuPDF + Ghostscript fallback) |
| Rhino-Grasshopper integration | 12 (GhPython 3 shell-out path) |
| Multi-format compatibility | 7 (priority order) |
| Rhino layer naming conventions | 2 (semantic classifier patterns) |
| Architectural standards | 4 (preset values per source) |
| Competitive landscape | positioning + risks (no direct competitor; closest = Auto Line Weight on Food4Rhino, `creold/illustrator-scripts`) |
| Poché conventions | 3 (material→treatment table, vpype+JSX outline) |

Full sub-agent reports live in `docs/research/` (TODO: stash transcripts).
