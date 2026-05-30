# r/Python Showcase Saturday Draft

Current source of truth: [`LAUNCH_KIT.md`](LAUNCH_KIT.md). Keep the install
language source/GitHub-only until PyPI is actually live.

## Title

`[Showcase] arch-line-weights - a Python CLI for architectural vector linework`

## Body

Hi r/Python. Sharing a niche project: `arch-line-weights`, a CLI that
post-processes Rhino/Make2D `.ai` and `.pdf` exports so architectural drawings
get a usable cut/profile/visible/hidden/surface line hierarchy.

The Day-1 release is source/GitHub install only. Repo is pushed at `18c589e`,
and tests/docs/build were green for that pushed state.

Latest dogfood: an axon stress-test passed on `macro_for_archlw.ai` at 98 MB,
1.28M strokes, `apply-saas` exit 0, about 1:53 runtime. That proves a large
axon path, not section/poché behavior, because the file has no
`ClippingPlaneIntersections`.

Stack:

- `pikepdf` for PDF/AI stream work.
- `shapely` for poché geometry and polygon recovery.
- `click` for the CLI.
- `pytest`, MkDocs, hatchling/hatch-vcs for project plumbing.

The current user-facing addition is a `usc` studio-board preset, with the
line-weight convention documented in `CONVENTIONS.md`.

Install:

```bash
pipx install git+https://github.com/zohartito/arch-line-weights
```

Or:

```bash
git clone https://github.com/zohartito/arch-line-weights
cd arch-line-weights
python -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/arch-lw --help
```

Not claiming PyPI yet, not a hosted SaaS product, and not Bluebeam-verified.
The webapp directory is only a local experimental scaffold right now.

Known v1 input caveat: `wall section iso cut .ai` is legacy Rhino PostScript
`.ai`, not PDF-compatible Illustrator `.ai`, and needs Illustrator Save As
before rerun. `WALL SECTION [Converted].ai` has cut layers and `inspect` works,
but `apply-saas` fails on missing `/NumBlock` until re-saved. Section poché
proof is still pending on an Illustrator 2026 re-save.

Screenshots:

- Terminal: `[CURSOR_SCREENSHOT_3_TERMINAL]`
- Before/after: `[CURSOR_SCREENSHOT_1_BEFORE]` / `[CURSOR_SCREENSHOT_2_AFTER]`

Repo: https://github.com/zohartito/arch-line-weights

Happy to talk through PDF/AI edge cases, Make2D layer semantics, or geometry
recovery for poché.
