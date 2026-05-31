# r/Python Showcase Saturday Draft

Current source of truth: [`LAUNCH_KIT.md`](LAUNCH_KIT.md). Keep the install
language source/GitHub-only until PyPI is actually live.

## Title

`[Showcase] arch-line-weights - a Python CLI for architectural vector linework`

## Body

Hi r/Python. Sharing a niche project: `arch-line-weights`, a CLI that
post-processes Rhino/Make2D `.ai` and `.pdf` exports so architectural drawings
get a usable cut/profile/visible/hidden/surface line hierarchy.

The Day-1 release is source/GitHub install only, with release-gate checks green
for the handoff.

Latest dogfood: an axon stress-test passed on `macro_for_archlw.ai` at 98 MB,
1.28M strokes, `apply-saas` exit 0, about 1:53 runtime. That proves a large
axon path, not section/poché behavior, because the file has no
`ClippingPlaneIntersections`.

Stack:

- `pikepdf` for PDF/AI stream work.
- `shapely` for poché geometry and polygon recovery.
- `click` for the CLI.
- `pytest`, MkDocs, hatchling/hatch-vcs for project plumbing.

Section proof passed via the Illustrator bridge path on `WALL SECTION [Converted].ai`:
`apply-jsx --preset usc --source rhino --for-print`, then
`arch-lw poche --source rhino --style solid --bridge-strategy best`.
Hierarchy touched 25 leaf layers, modified 512 paths, and reported 0 errors.
Poché (`arch-lw poche`) generated 30 poché polygons across 8 cut layers, had
0 failed layers, and Illustrator opens the final output.

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

Not claiming PyPI yet, not a hosted cloud product, and not tested in Bluebeam.
The webapp directory is only a local experimental scaffold right now.

Known v1 input caveat: `wall section iso cut .ai` is legacy Rhino PostScript
`.ai`, not PDF-compatible Illustrator `.ai`, and needs Illustrator Save As
before rerun. `apply-saas --poche` is not usable on the PDF-only/converted
section lineage because there is no `/NumBlock`; use the Illustrator bridge
path for those files. Proof screenshots are captured in `docs/img/day1-proof/`.

Screenshots (in `docs/img/day1-proof/`):

![Before — raw Rhino export](../img/day1-proof/01-before-raw.png)
![After poché — solid-black section-cut mass](../img/day1-proof/03-after-poche-full.png)
![Layers preserved with black poché fills](../img/day1-proof/04-layers-panel-clipping-poche.png)

Repo: https://github.com/zohartito/arch-line-weights

Happy to talk through PDF/AI edge cases, Make2D layer semantics, or geometry
recovery for poché.
