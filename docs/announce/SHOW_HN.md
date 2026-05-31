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

- Release-gate checks were green for the source/GitHub handoff.
- Install is source/GitHub only; PyPI is not live yet.
- The webapp is a local experimental scaffold, not a hosted product.
- Axon stress-test passed on `macro_for_archlw.ai`: 98 MB, 1.28M strokes,
  `apply-saas` exit 0, about 1:53 runtime.
- That is not section/poché proof; the axon file has no
  `ClippingPlaneIntersections`.
- Section proof passed via Illustrator bridge on `WALL SECTION [Converted].ai`:
  `apply-jsx --preset usc --source rhino --for-print`, then
  `arch-lw poche --source rhino --style solid --bridge-strategy best`.
- `apply-jsx` hierarchy: 25 leaf layers, 512 paths modified, 0 errors,
  Illustrator opens the output.
- Poché (`arch-lw poche`): 30 poché polygons, 8 cut layers, 0 failed layers,
  Illustrator opens the final output.
- Known v1 input caveat: legacy Rhino PostScript `.ai` may need to be opened in
  Illustrator and re-saved as modern/PDF-compatible `.ai` before rerunning.
- `apply-saas --poche` is not usable on this PDF-only/converted lineage because
  there is no `/NumBlock`; use the Illustrator bridge path for those files.
- Proof screenshots captured in `docs/img/day1-proof/`.

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

Screenshots (in `docs/img/day1-proof/`):

![Before — raw Rhino export, uniform line weights](../img/day1-proof/01-before-raw.png)
![After poché — solid-black section-cut mass](../img/day1-proof/03-after-poche-full.png)
![Layers preserved with black poché fills](../img/day1-proof/04-layers-panel-clipping-poche.png)
![Close-up — cut mass solid, openings white](../img/day1-proof/05-closeup-cut-mass-windows-white.png)

Repo: https://github.com/zohartito/arch-line-weights

Feedback welcome, especially around PDF/AI edge cases and Rhino Make2D layer
naming conventions.
