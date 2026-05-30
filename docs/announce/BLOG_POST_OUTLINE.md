# Day-1 Blog / Listing Outline

Current source of truth: [`LAUNCH_KIT.md`](LAUNCH_KIT.md). This is Day-1 copy,
not a SaaS launch post.

## Working Title

**I built a source-install CLI for Rhino-to-Illustrator line weights**

## Core Claim

`arch-line-weights` is a Python CLI that applies architectural line-weight
hierarchy to Rhino/Make2D `.ai` and `.pdf` exports. At Day 1 it is a
source/GitHub install, with `usc` preset support landed and real-board dogfood
pending.

## Required Facts

- Pushed state: `18c589e`.
- `usc` preset landed.
- Tests/docs/build green for the pushed state.
- Source/GitHub install only.
- Local webapp is experimental only.
- Axon stress-test passed on `macro_for_archlw.ai`: 98 MB, 1.28M strokes,
  `apply-saas` exit 0, about 1:53 runtime.
- That is large-file/performance evidence, not section/poché proof, because
  the axon file has no `ClippingPlaneIntersections`.
- `wall section iso cut .ai` is legacy Rhino PostScript `.ai`, not
  PDF-compatible Illustrator `.ai`; it needs Illustrator Save As.
- `WALL SECTION [Converted].ai` has cut layers and `inspect` works, but
  `apply-saas` fails on missing `/NumBlock` until re-saved.
- v1 input-format note: if Rhino legacy `.ai` fails, open it in Illustrator,
  Save As modern/PDF-compatible `.ai`, then rerun.
- Section poché proof is still pending on an Illustrator 2026 re-save.
- Do not claim PyPI, hosted SaaS, or Bluebeam support.

## Outline

### 1. The Workflow Problem

Open with the Rhino/Make2D to Illustrator workflow: exported vector drawings
need architectural hierarchy, but students often spend deadline time assigning
weights by hand.

Screenshot placeholder: `[CURSOR_SCREENSHOT_1_BEFORE]`.

### 2. What the Tool Does

Explain the hierarchy in plain architectural terms: cut/profile/visible/hidden/
surface, optional conservative poché, and presets for common drawing types.
Mention that `usc` is now the studio-board preset.

Screenshot placeholder: `[CURSOR_SCREENSHOT_2_AFTER]`.

### 3. Latest Dogfood Facts

Say that the latest axon stress-test succeeded on `macro_for_archlw.ai`: 98 MB,
1.28M strokes, `apply-saas` exit 0, about 1:53 runtime. Immediately qualify it:
this is not section/poché proof because the file has no
`ClippingPlaneIntersections`.

Also note the input-format lesson: `wall section iso cut .ai` is legacy Rhino
PostScript `.ai`, not PDF-compatible Illustrator `.ai`, and needs Illustrator
Save As. `WALL SECTION [Converted].ai` has cut layers and `inspect` works, but
`apply-saas` fails on missing `/NumBlock` until re-saved. For v1, if Rhino
legacy `.ai` fails, open it in Illustrator, Save As modern/PDF-compatible
`.ai`, then rerun.

### 4. The Day-1 Install Story

Show source install only:

```bash
git clone https://github.com/zohartito/arch-line-weights
cd arch-line-weights
python -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/arch-lw --help
```

Optional GitHub/pipx:

```bash
pipx install git+https://github.com/zohartito/arch-line-weights
```

### 5. The Current Dogfood Command

```bash
.venv/bin/arch-lw inspect path/to/rhino-export.ai
.venv/bin/arch-lw apply-saas path/to/rhino-export.ai \
  --architectural --poche --preset usc --source rhino
```

Note: `apply-saas` is the local CLI command name, not a hosted SaaS product.

Screenshot placeholder: `[CURSOR_SCREENSHOT_3_TERMINAL]`.

### 6. What Is Not Done Yet

Be explicit:

- PyPI is not live.
- The webapp is a local experimental scaffold, not a hosted SaaS product.
- Bluebeam is not verified.
- Real-board dogfood is pending.
- Section poché proof is still pending on an Illustrator 2026 re-save.

### 7. Ask

Ask for real Rhino/Illustrator edge cases, layer naming examples, and feedback
on the `usc` preset after users test on copies of their drawings.

Detail screenshot placeholder: `[CURSOR_SCREENSHOT_4_DETAIL]`.

## Listing Copy

- **Name:** arch-line-weights
- **Tagline:** Apply architectural line-weight hierarchy to Rhino-exported drawings.
- **Install:** Source checkout or GitHub/pipx install only.
- **Status:** Day-1 release at `18c589e`; tests/docs/build green; 98 MB /
  1.28M-stroke axon stress-test passed in about 1:53; section poché proof still
  pending on Illustrator 2026 re-save.
- **Not yet:** PyPI, hosted SaaS, Bluebeam verification.
