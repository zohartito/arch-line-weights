# Poché conventions and material-specific treatments

> Sub-agent research, 2026-04-30. Synthesizes Ching, OFFICE KGDVS, SO-IL,
> Tatiana Bilbao, Show It Better, AutoCAD `acad.pat` patterns.

## What is poché

Per Ching: "Darkening of cut walls, columns and other solid matter" to
contrast solid vs. void. Two flavors:

- **Structural poché** — fill only the cut structural elements
- **Figure-ground poché** — fill the entire mass behind the cut as well
  (Nolli-plan style)

Contemporary architectural-school practice (USC, GSD, MIT) leans toward
**structural poché in pure black at small scale** (1:200, 1:100). At detail
scale (1:50, 1:20) **material-specific hatches** replace solid black so
layered assemblies stay legible.

Practitioner caution: solid black at detail scale obscures linework; "dark
grey" or 80% screen often substitutes.

## Material → treatment table

For a vertical section at ~1:50 to 1:100:

| Material | Treatment | Spacing (mm @ 1:50) | Angle | Stroke |
|---|---|---|---|---|
| Cast concrete | solid black (small scale) / 45° diagonal hatch + dot/triangle stipple (detail) | 1.5 / 0.8 dots | 45° | 0.13 |
| CLT | solid black at section / cross-grain hatch (parallel lines per lamella, alternating) at detail | match lamella thickness | 0/90 | 0.18 |
| Solid timber | solid black + grain lines along long axis | 0.6–1.2 var | along grain | 0.13 |
| Steel section | **solid black** (filled section profile) | — | — | — |
| Mineral wool insulation | zigzag (sine wave) | 2.0 wave, 1.5 amp | — | 0.18 |
| Rigid XPS / PIR | 45° crosshatch | 1.0 | 45°+135° | 0.13 |
| Earth / ground | dense stipple OR solid black + random white dots | 0.4 dot | — | — |
| Brick | stretcher bond (215×65mm tile) | tile-based | 0° | 0.18 |
| Stone | irregular Voronoi polygons | 30–80mm cells | — | 0.20 |
| Glass / glazing | thin parallel lines, blue tint or blank | 1.0 | along pane | 0.10 blue |
| Gypsum / GWB | dotted / Poisson stipple | 1.5 | — | 0.10 |
| Aluminum | 45° hatch, tighter than steel | 0.8 | 45° | 0.10 |

## Implementation approaches

### Approach A: Solid black fill (current v0.3-alpha)

Pure shapely `linemerge` + `polygonize` + `pathItem.filled = true,
fillColor = black`. Works at section scale for simple structural cuts. Fails
when geometry is disconnected or material requires hatch.

### Approach B: SVG `<defs><pattern>` fills

`svgwrite.dwg.defs.add(dwg.pattern(...))`. Set `patternUnits="userSpaceOnUse"`
so spacing is in mm not relative to the polygon. Print RIPs occasionally
rasterize patterned fills at 300dpi, blurring fine hatches — test with the
target plotter before shipping.

### Approach C: Generated hatch geometry (recommended for production)

For each filled polygon, rotate by −θ, scan with horizontal lines spaced `s`,
intersect each scanline with the polygon, rotate back. ~30 lines of code with
shapely. Pros: prints exactly as drawn, every line is a real path,
layer-bookable in Illustrator. Cons: 1k–5k segments per wall poché — keep
below 10k per page or AI slows.

### Approach D: AutoCAD `acad.pat` hatches via `ezdxf`

[`ezdxf`](https://ezdxf.mozman.at/) reads/writes AutoCAD DXF including native
HATCH entities with `acad.pat` patterns (`AR-CONC`, `AR-BRSTD`, `AR-RROOF`,
`INSUL`, `EARTH`). This is the production answer if we add a DXF output.
Render to SVG/PDF via `ezdxf.addons.drawing`.

`acad.pat` lives in AutoCAD's Support folder. Format documented at
[Autodesk help](https://help.autodesk.com/view/ACD/2024/ENU/?guid=GUID-1BAB5B5C-D8AC-4729-AB69-9DA92B7204A3). `ezdxf.tools.pattern.load_pattern_file`
parses it directly.

## Proposed `arch-lw` API (v0.4)

```bash
# default — solid black for everything
arch-lw poche drawing.ai

# material-aware: dispatch hatch based on layer name
arch-lw poche drawing.ai --style material

# explicit per-material override
arch-lw poche drawing.ai \
    --hatch concrete=solid_black,clt=cross_grain,steel=hatch_45

# load AutoCAD pattern definitions
arch-lw poche drawing.ai --pattern-source acad.pat

# global angle override
arch-lw poche drawing.ai --hatch-angle global=30
```

## Recommended Python stack

- **`shapely`** — geometry (already a core dep)
- **`svgwrite`** — SVG output for pattern fills
- **`ezdxf`** — AutoCAD `acad.pat` loader + DXF round-trip (new dep)

## Sources

- [Architect Wisdom — What Does Poché Mean](https://architectwisdom.com/poche/)
- [Minimal Drawing — Poché Technique](https://minimaldrawing.com/poche-technique-in-architectural-drawings/)
- [Ching, *Architectural Graphics* 6th ed.](https://archive.org/details/FrancisD.K.ChingArchitecturalGraphics6thEd2015)
- [Designing Buildings Wiki — Standard hatching styles](https://www.designingbuildings.co.uk/wiki/Standard%20hatching%20styles%20for%20drawings)
- [Show It Better — Master Sections](https://www.showitbetter.co/courses/master-sections/)
- [vpype-hatched](https://github.com/abey79/hatched)
- [ezdxf — DXF + acad.pat](https://ezdxf.mozman.at/)
- [svgwrite — Python SVG generator](https://svgwrite.readthedocs.io/)
- [Samolevsky — Close Open Paths JSX](https://www.samolevsky.com/blogs/adobe-illustrator-scripts/close-open-paths)
