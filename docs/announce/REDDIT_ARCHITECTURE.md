# r/architecture Draft

Current source of truth: [`LAUNCH_KIT.md`](LAUNCH_KIT.md). Add screenshots
before posting.

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

- Repo pushed at `18c589e`.
- Tests/docs/build were green for that pushed state.
- Install is source/GitHub only right now; PyPI is not live.
- The webapp is local experimental only, not a hosted app.
- Axon stress-test passed on `macro_for_archlw.ai`: 98 MB, 1.28M strokes,
  `apply-saas` exit 0, about 1:53 runtime.
- That axon run is not section/poché proof because it has no
  `ClippingPlaneIntersections`.
- `wall section iso cut .ai` is legacy Rhino PostScript `.ai`, not
  PDF-compatible Illustrator `.ai`; it needs Illustrator Save As.
- `WALL SECTION [Converted].ai` has cut layers and `inspect` works, but
  `apply-saas` fails on missing `/NumBlock` until re-saved.
- v1 input note: if a Rhino legacy `.ai` fails, open it in Illustrator, Save As
  modern/PDF-compatible `.ai`, then rerun.
- Real-board dogfood is next, so this is not a "trust it five minutes before
  pinup" claim yet.
- Section poché proof is still pending on an Illustrator 2026 re-save.

Install from source:

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

I am looking for feedback from people with different Rhino layer conventions
and messy Make2D outputs. Test on a copy of your file and open an issue if the
classifier gets the hierarchy wrong.
