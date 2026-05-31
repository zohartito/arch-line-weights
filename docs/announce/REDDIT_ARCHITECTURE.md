# r/architecture Draft

Current source of truth: [`LAUNCH_KIT.md`](LAUNCH_KIT.md). Proof screenshots
are captured and committed under `docs/img/day1-proof/`.

## Title

`[OC][Tool] I built a CLI that applies architectural line weights to Rhino exports`

## Body

Hey all - sharing a Day-1 source release of a small tool I built for the
Rhino-to-Illustrator studio workflow.

**The problem:** Rhino/Make2D exports often arrive in Illustrator as dense
vector linework where everything reads too similarly. Then you spend deadline
time manually making cut lines heavier, profiles clear, hidden/overhead lines
lighter, and surface texture quiet.

**What it does:** `arch-line-weights` inspects `.ai`/`.pdf` exports and applies
an architectural hierarchy: cut, profile, visible, hidden, and surface/texture.
It also has optional conservative poché for high-confidence cut regions. The
new `usc` preset is tuned for studio-board output and documented in
`CONVENTIONS.md`.

Current status:

- Release-gate checks were green for the source/GitHub handoff.
- Install is source/GitHub only right now; PyPI is not live.
- The webapp is local experimental only, not a hosted app.
- Axon stress-test passed on `macro_for_archlw.ai`: 98 MB, 1.28M strokes,
  `apply-saas` exit 0, about 1:53 runtime.
- That axon run is not section/poché proof because it has no
  `ClippingPlaneIntersections`.
- `wall section iso cut .ai` is legacy Rhino PostScript `.ai`, not
  PDF-compatible Illustrator `.ai`; it needs Illustrator Save As.
- Section proof passed via Illustrator bridge on `WALL SECTION [Converted].ai`:
  `apply-jsx --preset usc --source rhino --for-print`, then
  `arch-lw poche --source rhino --style solid --bridge-strategy best`.
- `apply-jsx` hierarchy: 25 leaf layers, 512 paths modified, 0 errors,
  Illustrator opens the output.
- Poché (`arch-lw poche`): 30 poché polygons, 8 cut layers, 0 failed layers,
  Illustrator opens the final output.
- `apply-saas --poche` is not usable on this PDF-only/converted lineage because
  there is no `/NumBlock`; use the Illustrator bridge path for those files.
- v1 input note: if a Rhino legacy `.ai` fails, open it in Illustrator, Save As
  modern/PDF-compatible `.ai`, then rerun.
- Proof screenshots captured in `docs/img/day1-proof/`.

Install from source:

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

I am looking for feedback from people with different Rhino layer conventions
and messy Make2D outputs. Test on a copy of your file and open an issue if the
classifier gets the hierarchy wrong.
