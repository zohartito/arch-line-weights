# Material hatching

Solid black is fine for diagrams. For final drawings, every cut material wants its own hatch.

## The command

```bash
arch-lw poche drawing.ai --style material --scale 0.02
```

`0.02 = 1:50`. The hatch density and stroke weight scale with this value.

## Scale cheat-sheet

| Scale | `--scale` value |
|---|---|
| 1:25 | `0.04` |
| 1:50 | `0.02` |
| 1:100 | `0.01` |
| 1:200 | `0.005` |

## Built-in material patterns

| Layer name keyword | Pattern | Notes |
|---|---|---|
| `CONCRETE` | 45° diagonal + Poisson stipple | Baseline, used for sitecast and precast |
| `CLT` / `TIMBER` | Cross-grain ticks alternating per lamella | Layered ply pattern |
| `STEEL` / `SHS` | Solid black | No hatch — just dense black |
| `BRICK` | Stretcher bond pattern | Horizontal joint lines |
| `INSULATION` (mineral) | Sine-wave zigzag | Batt symbol |
| `INSULATION` (rigid/XPS/PIR) | 45° + 135° crosshatch | |
| `EARTH` / `GROUND` | Dense Poisson stipple | |
| `GLASS` / `IGU` | 2-3 thin parallel lines | Blue tint optional |
| `GYPSUM` / `GWB` | Dotted Poisson stipple | |

The keyword search is case-insensitive and walks the layer name segments.

## Custom materials

Register your own recipe in Python:

```python
from arch_line_weights.hatch import MaterialRecipe, parallel_hatch, mm_to_pt, register_material

def hatch_terrazzo(poly, scale, **kw):
    return parallel_hatch(poly, mm_to_pt(0.7, scale), 30.0)

register_material(MaterialRecipe("terrazzo", hatch_terrazzo))
```

Then add `TERRAZZO` to your Rhino layer name and re-run `arch-lw poche --style material`.

## Related

- [Generate poché](generate-poche.md)
- [API reference: `arch_line_weights.hatch`](../reference/python-api.md#hatch)
