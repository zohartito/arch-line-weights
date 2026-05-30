# Show HN Draft

Current source of truth: [`LAUNCH_KIT.md`](LAUNCH_KIT.md). Use this only after
adding real Cursor screenshots and confirming the GitHub repo is public.

## Title

`Show HN: arch-line-weights - Apply architectural line hierarchy to Rhino exports`

## Body

I built `arch-line-weights`, a Python CLI for a narrow architecture workflow:
Rhino/Make2D exports that land in Illustrator as dense vector drawings without
usable line-weight hierarchy.

It inspects `.ai`/`.pdf` exports, classifies linework into architectural tiers
like cut, profile, visible, hidden, and surface/texture, then applies a preset.
The current Day-1 release includes a `usc` studio-board preset documented in
`CONVENTIONS.md`.

Current status:

- Repo pushed at `18c589e`.
- Tests, docs, and build were green for that pushed state.
- Install is source/GitHub only; PyPI is not live yet.
- The webapp is a local experimental scaffold, not a hosted product.
- Axon stress-test passed on `macro_for_archlw.ai`: 98 MB, 1.28M strokes,
  `apply-saas` exit 0, about 1:53 runtime.
- That is not section/poché proof; the axon file has no
  `ClippingPlaneIntersections`.
- Known v1 input caveat: legacy Rhino PostScript `.ai` may need to be opened in
  Illustrator and re-saved as modern/PDF-compatible `.ai` before rerunning.
- Real-board dogfood is still pending.
- `WALL SECTION [Converted].ai` has cut layers and `inspect` works, but
  `apply-saas` fails on missing `/NumBlock` until re-saved.
- Section poché proof is still pending on an Illustrator 2026 re-save.

Install:

```bash
pipx install git+https://github.com/zohartito/arch-line-weights
```

Or from a source checkout:

```bash
git clone https://github.com/zohartito/arch-line-weights
cd arch-line-weights
python -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/arch-lw --help
```

Screenshots:

- Before: `[CURSOR_SCREENSHOT_1_BEFORE]`
- After: `[CURSOR_SCREENSHOT_2_AFTER]`
- Terminal: `[CURSOR_SCREENSHOT_3_TERMINAL]`
- Detail crop: `[CURSOR_SCREENSHOT_4_DETAIL]`

Repo: https://github.com/zohartito/arch-line-weights

Feedback welcome, especially around PDF/AI edge cases and Rhino Make2D layer
naming conventions.
