# Why this tool exists

Many architecture students spend the better part of a weekend per drawing fixing line weights by hand in Illustrator. Multiply that across the sections, plans, elevations, and details in a final review, and you've burned days on something a computer should do.

## The Rhino-to-Illustrator pipeline pain

Rhino is a great modeller. `Make2D` produces clean hidden-line vector output. The problem is what comes after:

1. `Make2D` emits strokes at a uniform `0.25 pt`.
2. Layers carry semantic meaning (`TEC_CONCRETE_WALL`, `STR_BEAM_PRIMARY`) but no graphic distinction.
3. Cut elements aren't filled. They're just outlines.

In Illustrator, the manual recovery pipeline is:

1. `Select > Same > Stroke Color` per color, set weight, repeat.
2. For each cut layer: `Object > Path > Join`, watch it fail, manually trace closed regions, fill black.
3. Save. Print. The cut isn't black, it's striped because the join failed silently.

This is one section. A studio review needs ten. And a Rhino re-export starts the cycle over.

## Line weight conventions

Architectural drawing has been a profession for ~3000 years and the conventions are stable. ISO 128, NCS, Ramsey/Sleeper, Ching all converge on the same `√2` geometric series — `0.13, 0.18, 0.25, 0.35, 0.50, 0.70, 1.00 mm`. The whole `arch-lw` preset system encodes this convention.

You pick `--preset section --scale 1/4 --for-print` and you get the Ramsey/Sleeper weights for a quarter-inch print. No looking it up.

## Poché as a graphic device

[Poché](https://en.wikipedia.org/wiki/Poch%C3%A9) ("pocketed") is the architectural convention of filling cut elements solid, usually black. It does two jobs:

1. **Reads the section.** A line drawing of a wall is ambiguous. A black-filled wall says *this is mass; the section plane sliced it*.
2. **Communicates material.** Solid black is concrete or undifferentiated mass. Hatched poché names the material (diagonal = concrete, cross-grain = CLT, coursing = brick).

Beaux-Arts plates from 1880 already used the convention. AutoCAD/Vectorworks/Revit all support it natively. Rhino does not — so a Rhino-first studio loses the convention unless someone fixes it downstream.

`arch-lw poche` is that downstream fix.

## Why not Revit

Because Rhino is the modeller for buildings whose geometry isn't parametric. Anything ruled-surface, anything subdivided, anything sculpted, anything that started as Grasshopper. The Rhino → Illustrator pipeline is the right one. The graphic conventions are the only thing missing.

## Related

- [How-to: apply line weights](../how-to/apply-line-weights.md)
- [How poché works](how-poche-works.md)
- [Postmortem](the-postmortem.md)
