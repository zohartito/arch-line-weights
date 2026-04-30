# Apply line weights

You have a Rhino `.ai` or `.pdf`. You want a proper hierarchy. Pick a recipe.

## Fastest — auto, screen review

```bash
arch-lw apply drawing.ai --auto --preset section
```

Writes `drawing HIERARCHY.ai`. Buckets every color into the `section` tier ladder by luminance + frequency.

## Standards-aligned — print, ISO 128

```bash
arch-lw apply drawing.ai --auto --preset section --for-print --scale 1/4
```

Selects the ISO-128 weight set (0.13, 0.18, 0.25, 0.35, 0.50, 0.70, 1.00 mm) for a printed quarter-inch section.

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
| `section` | Building section, wall section |
| `plan` | Floor plan, roof plan, site plan |
| `elevation` | Elevation, axon, perspective frame |
| `detail` | Wall detail, connection detail |

## Dry-run to check the mapping first

```bash
arch-lw apply drawing.ai --auto --preset section --dry-run
```

## Related

- [CLI reference](../reference/cli.md)
- [Explanation: how poché works](../explanation/how-poche-works.md)
