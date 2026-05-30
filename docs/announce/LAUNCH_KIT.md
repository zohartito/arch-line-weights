# Day-1 Launch Kit

Status source: pushed repository state at `18c589e` (`Prepare Phase 2 dogfood release`), 2026-05-30.

## Current Facts

- Repo is pushed at `18c589e`.
- `usc` preset landed and is documented.
- Tests, docs, and build were green for the pushed state.
- Public install path is source checkout or GitHub/pipx install only.
- Webapp is local experimental scaffold only, not a hosted product.
- Real-board dogfood is pending; do not imply this has passed a pinup board review yet.
- Do not claim PyPI availability, hosted SaaS, Bluebeam support, or paid product readiness.

## Latest Dogfood Facts

- Axon stress-test succeeded on `macro_for_archlw.ai`: 98 MB, 1.28M strokes,
  `apply-saas` exit 0, about 1:53 runtime.
- That axon file is large-file/performance evidence, not section/poché proof:
  it has no `ClippingPlaneIntersections`.
- `wall section iso cut .ai` is legacy Rhino PostScript `.ai`, not
  PDF-compatible Illustrator `.ai`; it needs Illustrator Save As before rerun.
- `WALL SECTION [Converted].ai` has cut layers and `inspect` works, but
  `apply-saas` fails on missing `/NumBlock` until the file is re-saved.
- v1 input-format note: if Rhino legacy `.ai` fails, open it in Illustrator,
  Save As modern/PDF-compatible `.ai`, then rerun.
- Section poché proof is still pending on an Illustrator 2026 re-save.

## Screenshot Placeholders

Use Cursor screenshots or screen captures from the real dogfood pass before posting:

- `[CURSOR_SCREENSHOT_1_BEFORE]` - Rhino/Illustrator export before hierarchy, ideally showing uniform line weights.
- `[CURSOR_SCREENSHOT_2_AFTER]` - same view after `--preset usc`, hierarchy visible.
- `[CURSOR_SCREENSHOT_3_TERMINAL]` - Cursor terminal running inspect/apply command and writing output.
- `[CURSOR_SCREENSHOT_4_DETAIL]` - close crop of cut/profile/visible/hidden/texture tiers.

Do not use webapp screenshots in Day-1 copy unless explicitly labeled "local experimental scaffold."

## Canonical Install Block

```bash
git clone https://github.com/zohartito/arch-line-weights
cd arch-line-weights
python -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/arch-lw --help
```

Optional global install if `pipx` is already available:

```bash
pipx install git+https://github.com/zohartito/arch-line-weights
```

## Canonical Dogfood Command

```bash
.venv/bin/arch-lw inspect path/to/rhino-export.ai
.venv/bin/arch-lw apply-saas path/to/rhino-export.ai \
  --architectural --poche --preset usc --source rhino
```

`apply-saas` is the local CLI command name for the AI-private rewrite path; it
does not mean a hosted SaaS product is available.

For fast stroke-weight-only output:

```bash
.venv/bin/arch-lw apply path/to/rhino-export.ai --auto --preset usc
```

## Day-1 Post

### Title Options

- I built a CLI that applies architectural line weights to Rhino exports
- arch-line-weights: Rhino-to-Illustrator line hierarchy from a source checkout
- Turning Rhino Make2D output into cleaner studio linework with one command

### Body

I built `arch-line-weights`, a small Python CLI for a very specific architecture-school pain: Rhino/Make2D exports that arrive in Illustrator with hundreds of thousands of strokes but no useful line-weight hierarchy.

It inspects `.ai`/`.pdf` exports, maps strokes into architectural tiers, and applies a practical hierarchy: cut, profile, visible, hidden, surface/texture, plus optional conservative poché. The new `usc` preset is tuned for studio-board linework, with the print convention documented in `CONVENTIONS.md`.

Current Day-1 status:

- Repo pushed at `18c589e`.
- `usc` preset is in the CLI and docs.
- Tests, docs, and build were green for the pushed state.
- Install is source/GitHub only right now; PyPI is not live.
- Webapp exists only as a local experimental scaffold.
- Latest dogfood: `macro_for_archlw.ai` axon stress-test succeeded at 98 MB /
  1.28M strokes with `apply-saas` exit 0 in about 1:53.
- That axon run is not section/poché proof because the file has no
  `ClippingPlaneIntersections`.
- A `wall section iso cut .ai` attempt exposed an input-format caveat: legacy
  Rhino PostScript `.ai` needs Illustrator Save As before rerun.
- `WALL SECTION [Converted].ai` has cut layers and `inspect` works, but
  `apply-saas` fails on missing `/NumBlock` until the file is re-saved.
- Real-board dogfood is the next proof point.

Install from source:

```bash
git clone https://github.com/zohartito/arch-line-weights
cd arch-line-weights
python -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/arch-lw --help
```

The current studio dogfood path:

```bash
.venv/bin/arch-lw inspect path/to/rhino-export.ai
.venv/bin/arch-lw apply-saas path/to/rhino-export.ai \
  --architectural --poche --preset usc --source rhino
```

`apply-saas` is local CLI behavior, not a hosted product.

v1 input-format note: if Rhino legacy `.ai` fails, open it in Illustrator,
Save As modern/PDF-compatible `.ai`, then rerun. `WALL SECTION [Converted].ai`
has cut layers and `inspect` works, but `apply-saas` currently fails on missing
`/NumBlock` until re-saved. Section poché proof is still pending on an
Illustrator 2026 re-save.

Screenshots:

- Before: `[CURSOR_SCREENSHOT_1_BEFORE]`
- After: `[CURSOR_SCREENSHOT_2_AFTER]`
- Terminal: `[CURSOR_SCREENSHOT_3_TERMINAL]`
- Detail crop: `[CURSOR_SCREENSHOT_4_DETAIL]`

What I am looking for now: real Rhino/Illustrator edge cases, layer naming conventions that break the classifier, and feedback from anyone who has had to clean up Make2D output under deadline.

Repo: https://github.com/zohartito/arch-line-weights

## Short Listing Copy

**Name:** arch-line-weights

**Tagline:** Apply architectural line-weight hierarchy to Rhino-exported drawings.

**Short description:**
Python CLI for post-processing Rhino/Make2D `.ai` and `.pdf` exports. It classifies linework into cut, profile, visible, hidden, and surface tiers, applies source-controlled presets including a USC studio-board preset, and can add conservative poché for high-confidence section cuts.

**Install:** Source checkout or GitHub/pipx install only. PyPI is not live yet.

**Status:** Day-1 source release at `18c589e`; tests/docs/build green; 98 MB /
1.28M-stroke axon stress-test passed in about 1:53; section poché proof still
pending on Illustrator 2026 re-save.

**Not yet:** Hosted SaaS, PyPI package install, Bluebeam-verified workflow.

## Longer Listing Copy

`arch-line-weights` is a source-install Python CLI for cleaning up architectural vector exports, especially Rhino/Make2D files opened in Illustrator. It gives exported drawings a readable architectural hierarchy without manually selecting every layer and stroke color.

Use it to inspect stroke colors and layer-derived categories, then apply presets for section, plan, elevation, detail, or USC studio-board output. The `usc` preset follows the project convention file for cut/profile/visible/hidden/surface hierarchy and uses a practical print-weight ladder.

The project is currently a Day-1 source/GitHub release. The CLI and documentation are green at commit `18c589e`, and the latest axon stress-test passed on a 98 MB / 1.28M-stroke file in about 1:53. That is not section/poché proof because the stress file had no `ClippingPlaneIntersections`. This is not yet a PyPI package, not a hosted SaaS product, and not Bluebeam-verified. The local webapp scaffold is experimental and is not the public install path.

Input-format caveat for v1: legacy Rhino PostScript `.ai` exports may fail. If
that happens, open the file in Illustrator, Save As modern/PDF-compatible `.ai`,
then rerun the CLI. `WALL SECTION [Converted].ai` confirms cut layers can be
detected because `inspect` works, but its `apply-saas` run is blocked on missing
`/NumBlock` until an Illustrator 2026 re-save.

## Channel Variants

### Hacker News / Dev Audience

`arch-line-weights` is a Python CLI that rewrites architectural vector linework after Rhino export. The technical bit is mapping PDF/AI stroke operators and Rhino/Make2D layer semantics into a small architectural hierarchy, then optionally generating conservative poché from high-confidence cut regions.

It is source/GitHub install only for now:

```bash
pipx install git+https://github.com/zohartito/arch-line-weights
```

No PyPI release yet, no hosted SaaS. The local webapp scaffold is experimental. I am looking for feedback on PDF/AI edge cases, Make2D layer naming, and better real-world fixtures.

Latest dogfood: `macro_for_archlw.ai` passed as a 98 MB / 1.28M-stroke axon
stress-test in about 1:53. It does not prove section poché because it has no
`ClippingPlaneIntersections`.

### Architecture / Studio Audience

This is for the boring but painful part after Rhino export: turning uniform Make2D linework into a drawing that reads like a section, plan, or elevation.

`arch-line-weights` applies an architectural hierarchy automatically: cut and poché get the strongest treatment, profiles sit below that, visible edges are lighter, hidden/overhead lines are dashed/light, and surface texture stays quiet. The `usc` preset is aimed at studio-board output.

It is still Day-1 source-install software. Real-board dogfood is next, so treat it as a tool to test on copies of your drawings, not as a guaranteed deadline workflow yet.

Known v1 input caveat: legacy Rhino PostScript `.ai` may need to be opened in
Illustrator and re-saved as modern/PDF-compatible `.ai` before rerunning.
`WALL SECTION [Converted].ai` has cut layers and `inspect` works, but
`apply-saas` is blocked on missing `/NumBlock` until re-saved. Section poché
proof is still pending on Illustrator 2026 re-save.

## Do-Not-Say List

- Do not say "pip install arch-line-weights" as the primary install path.
- Do not say "hosted app," "SaaS," "cloud upload," or "browser product" without "experimental local scaffold."
- Do not say "Bluebeam supported" or "Bluebeam verified."
- Do not say "production-ready" or "board-proven" before the real-board dogfood pass.
- Do not imply the CLI has been validated on every Rhino/Illustrator export shape.
- Do not use the axon stress-test as section/poché proof.
