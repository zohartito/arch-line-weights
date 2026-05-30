# Apply line weights

You have a Rhino `.ai` or `.pdf`. You want a proper hierarchy. Pick a recipe.

## Fastest — auto, screen review

```bash
arch-lw apply drawing.ai --auto --preset usc
```

Writes `drawing HIERARCHY.ai`. Buckets every color into the `usc` studio tier ladder by luminance + frequency.
This is the fast stroke-weight output path; it is not the submit-quality path
when you need layer preservation or poché.

## Standards-aligned — print, ISO 128

```bash
arch-lw apply drawing.ai --auto --preset section --for-print --scale 1/4
```

Selects the ISO-128 weight set (0.13, 0.18, 0.25, 0.35, 0.50, 0.70, 1.00 mm) for a printed quarter-inch section.

## Submit-quality — layer-preserving hierarchy plus poché

```bash
arch-lw apply-saas drawing.ai --architectural --poche --preset usc --source rhino
```

This is the Day-1 Rhino 8 → Illustrator `.ai` dogfood path. It preserves the
Illustrator layer payload, applies semantic architectural line weights, and
injects conservative black poché where the cut-mass topology is high confidence.

## Layer-preserving — Adobe JSX path

When Rhino layer names matter (and they usually do):

```bash
arch-lw apply-jsx drawing.ai
```

Slower (Illustrator must open) but **every layer survives**. Use this default for any Rhino export that you'll continue editing.

## With a hand-edited mapping

```bash
arch-lw apply drawing.ai --mapping mapping.json
```

`mapping.json`:

```json
{
  "RGB(255,0,0)":   1.0,
  "RGB(0,0,0)":     0.5,
  "RGB(128,128,128)": 0.18,
  "RGB(200,200,200)": 0.08
}
```

## Choose a preset

| Preset | When to use |
|---|---|
| `usc` | USC studio sections and the ARCH 202B reference workflow |
| `section` | Building section, wall section |
| `plan` | Floor plan, roof plan, site plan |
| `elevation` | Elevation, axon, perspective frame |
| `detail` | Wall detail, connection detail |

## Dry-run to check the mapping first

```bash
arch-lw apply drawing.ai --auto --preset usc --dry-run
```

## Related

- [CLI reference](../reference/cli.md)
- [Explanation: how poché works](../explanation/how-poche-works.md)
