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
| `CONCRETE` | Solid black (`concrete_solid`) | Explicit API recipe `concrete` gives diagonal + stipple |
| `CLT` | Solid black (`clt_solid`) | Explicit API recipe `clt_cross_grain` gives alternating lamellae |
| `TIMBER` / `GLULAM` / `LVL` | Grain lines (`solid_timber`) | |
| `STEEL` / `SHS` | Solid black | No hatch — just dense black |
| `BRICK` | Stretcher bond pattern | Horizontal joint lines |
| `INSULATION` (mineral) | Sine-wave zigzag | Batt symbol |
| `XPS` / `EPS_RIGID` / `EPS_BOARD` | 45° + 135° crosshatch | `insulation_rigid` |
| `POLYISO` / `PIR_BOARD` / `PIR ` (trailing space) | Parallel hatch + foil-face triangles | `insulation_polyiso` |
| `EARTH` / `GROUND` | Dense Poisson stipple | |
| `GLASS` / `IGU` | 2-3 thin parallel lines | Blue tint optional |
| `GYPSUM` / `GWB` | Dotted Poisson stipple | |

The keyword search is case-insensitive: the first matching substring in the
code's ordered table wins. Bare `PIR` falls back to `concrete_solid`;
`INSULATION_PIR` matches `INSUL` and selects the mineral-wool zigzag.
Concrete and CLT therefore remain solid even with `--style material`.
For an explicit recipe in Python, use `hatch_polygon(poly, "concrete", scale=0.02)`
or `hatch_polygon(poly, "clt_cross_grain", scale=0.02)`. The CLI has no recipe-name flag.

## Custom materials

Registration is process-local and does not add a layer keyword. Use the recipe
explicitly in the same Python process:

```python
from shapely.geometry import box
from arch_line_weights.hatch import (
    MaterialRecipe, hatch_polygon, parallel_hatch, mm_to_pt, register_material,
)

def hatch_terrazzo(poly, scale, **kw):
    return parallel_hatch(poly, mm_to_pt(0.7, scale), 30.0)

register_material(MaterialRecipe("terrazzo", hatch_terrazzo))
lines = hatch_polygon(box(0, 0, 10, 10), "terrazzo", scale=1.0)
assert lines
```

A subsequent CLI process does not inherit this registration. `TERRAZZO` alone
still selects the fallback; this example produces geometry through the Python API.

## Related

- [Generate poché](generate-poche.md)
- [API reference: `arch_line_weights.hatch`](../reference/python-api.md)
