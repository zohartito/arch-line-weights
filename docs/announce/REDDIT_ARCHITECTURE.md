# r/architecture post draft

> Drafts from the marketing sub-agent (2026-04-30). Edit before posting.

## Title

`[OC][Tool] I built a free CLI that applies line-weight hierarchy + poché to Rhino PDF exports automatically`

## Body

Hey all — sharing a free, open-source tool I've been using on my own studio
sets. Not selling anything, no paywall, MIT license.

**The problem:** You export a plan or section from Rhino. Every line is the
same weight. You open it in Illustrator and spend half an hour selecting
layers, assigning weights, pathfinding closed regions, dropping in poché. The
model changes. You do it again.

**What it does:** `arch-lw apply-jsx drawing.ai` reads your file, classifies
strokes by Rhino layer name (`Visible::ClippingPlaneIntersections::*` =
section cut, `TEC_TIMBER_BEAMS` = profile, etc. — fully configurable),
applies a hierarchy that matches the conventions in *Architectural Graphic
Standards* (Ramsey/Sleeper) and Ching's *Architectural Graphics*. Then
`arch-lw poche` adds solid-black poché on cut elements.

**ISO 128 standards-aligned** at any plot scale:
- 1/4"=1' section cut: 0.70 mm = 1.98 pt
- Profile: 0.50 mm = 1.42 pt
- Object edges: 0.35 mm = 0.99 pt
- Material hatch: 0.13–0.18 mm = 0.37–0.51 pt

Per Ramsey/Sleeper / NCS / Ching cited in `docs/research/standards.md`.

Repo + install: https://github.com/zohartito/arch-line-weights

There's also a Claude Code skill (`apply-arch-hierarchy`) and a Rhino 8
GhPython component + toolbar button in `integrations/rhino/`.

Genuinely want feedback. If your school or office uses different layer naming
conventions, open an issue or PR — I'd like the defaults to cover more
workflows. Bug reports especially welcome from anyone whose Rhino setup
breaks it.
