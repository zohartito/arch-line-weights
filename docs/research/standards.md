# Architectural line-weight standards (ISO 128 / Ramsey-Sleeper / Ching / NCS)

> Sub-agent research, 2026-04-30. This is the authoritative source for the
> tier-weight values shipped in `arch_line_weights.presets`. Cited from real
> published references where possible.

## Core finding: ISO 128 geometric series

Each tier is **√2 ≈ 1.414×** the previous. The full ISO 128-20 series:

| mm   | pt (× 2.835) | NCS label    |
|------|--------------|--------------|
| 0.13 | 0.37         | Extra Fine   |
| 0.18 | 0.51         | Fine         |
| 0.25 | 0.71         | Thin         |
| 0.35 | 0.99         | Medium       |
| 0.50 | 1.42         | Wide         |
| 0.70 | 1.98         | Extra Wide   |
| 1.00 | 2.84         | XX Wide      |
| 1.40 | 3.97         | XXX Wide     |
| 2.00 | 5.67         | XXXX Wide    |

Wide:medium:narrow within a single drawing should follow the **4:2:1** rule
(per ISO 128).

## Tier mapping by drawing type (mm / pt)

| Tier role | Section (1/4"=1') | Plan | Elevation | Detail (1/2"=1' or larger) |
|---|---|---|---|---|
| Section cut (heaviest) | **0.70 / 1.98** | 0.50 / 1.42 | — | **1.00 / 2.84** |
| Profile / silhouette | 0.50 / 1.42 | 0.50 / 1.42 | **0.50 / 1.42** | 0.70 / 1.98 |
| Object edges | 0.35 / 0.99 | 0.35 / 0.99 | 0.35 / 0.99 | 0.50 / 1.42 |
| Hidden / centerline | 0.25 / 0.71 (dashed) | 0.25 / 0.71 | 0.25 / 0.71 | 0.35 / 0.99 |
| Material hatch | **0.13–0.18 / 0.37–0.51** | 0.13 / 0.37 | 0.18 / 0.51 | 0.25 / 0.71 |
| Dimension / construction | 0.18 / 0.51 | 0.18 / 0.51 | 0.18 / 0.51 | 0.25 / 0.71 |
| Background poché | 0.13 / 0.37 (50% screen) | 0.13 / 0.37 | 0.13 / 0.37 | 0.18 / 0.51 |

## Per-scale offsets (Ching, NCS)

- **1/16"=1'-0"** → shift one ISO step thinner than baseline
- **1/8"=1'-0"** → as shown above
- **1/4"=1'-0"** → baseline (table values)
- **1/2"=1' or larger** → shift one ISO step heavier

## Print vs screen

ISO 128-2 specifies print only. Screens at ≤96 dpi can't resolve below ~0.18
mm. For on-screen review, multiply target weights by **1.5–2×** to keep the
hierarchy readable. AutoCAD/Revit decouple `LWDISPLAY` from plot output for
this reason.

## Implication for arch-line-weights

The current `presets.SECTION` tier values were derived from first principles
and chosen for **screen review** at the user's current zoom level:

```
cut: 1.0  profile: 0.5  edges: 0.3  material: 0.18  texture: 0.08  special: 0.25
```

For **plotted print at 1/4"=1'**, these should shift to ISO-aligned values:

```
cut: 1.98  profile: 1.42  edges: 0.99  material: 0.51  texture: 0.37  special: 0.71
```

**v0.4 should add `--for screen|print --scale 1/4` flags** that select the
right tier table. See `presets.py` for the current values; v0.4 adds an ISO
preset family.

## Revit 16-pen mapping (consensus from Engipedia / BIM Pure)

| Pen | mm | pt | Role |
|---|---|---|---|
| 1 | 0.10 | 0.28 | Reserved: hatch fill |
| 3 | 0.15 | 0.43 | Background poché |
| 4 | 0.20 | 0.57 | Material hatching |
| 5 | 0.25 | 0.71 | Dimensions |
| 6 | 0.10 | 0.28 | Centerlines, hidden |
| 7 | 0.35 | 0.99 | Object edges in elevation |
| 8 | 0.50 | 1.42 | Profile / foreground |
| 9 | 0.70 | 1.98 | Section cut (standard) |
| 10 | 1.00 | 2.84 | Heavy section cut (detail) |
| 11 | 1.40 | 3.97 | Title block, sheet border |

## Sources

- [ISO 128-20:1996 sample](https://cdn.standards.iteh.ai/samples/1408/f62555427b87436eafe1e6abc5271860/ISO-128-20-1996.pdf)
- [ISO 128-2:2020 sample](https://cdn.standards.iteh.ai/samples/69129/38e651842df746fd990d29679e3c2e98/ISO-128-2-2020.pdf)
- [NCS v5 Plotting Guidelines](https://www.nationalcadstandard.org/ncs5/pdfs/ncs5_pg.pdf)
- [Ching, *Architectural Graphics* 6th ed.](https://archive.org/details/FrancisD.K.ChingArchitecturalGraphics6thEd2015)
- [Life of an Architect — Architectural Graphics 101: Line Weight](https://www.lifeofanarchitect.com/architectural-graphics-101-line-weight/)
- [Engipedia — Revit Line Weights](https://www.engipedia.com/revit-line-weights/)
- [Revit Pure Pamphlet #12 — Line Weights](https://static1.squarespace.com/static/5605a932e4b0055d57211846/t/5c92e1c8b208fc0cdfa22bf4/1553129929112/RP-Pamphlet12-Line-Weights.pdf)
- [AISC AASHTO/NSBA G 1.3 Shop Drawing Guidelines](https://www.aisc.org/globalassets/nsba/aashto-nsba-collab-docs/g-1.3-2002-shop-detail-drawing-presentation-guidelines.pdf)
- [AIA CAD Layer Guidelines (Duke Facilities)](https://facilities.duke.edu/sites/default/files/AIA%20CAD%20Layer%20Guidelines.pdf)
- [Ramsey/Sleeper *Architectural Graphic Standards* 12th ed.](https://www.amazon.com/Architectural-Graphic-Standards-Ramsey-Sleeper/dp/111890950X)
