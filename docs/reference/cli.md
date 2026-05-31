# CLI reference

`arch-lw` is the entry point. All subcommands accept `--help`.

## `arch-lw inspect`

Report color / stroke-width distribution of a `.ai` or `.pdf`.

```bash
arch-lw inspect SRC [--pretty/--no-pretty]
```

## `arch-lw apply`

Rewrite via `pikepdf` (fast, but flattens layers).

```bash
arch-lw apply SRC [OPTIONS]
```

| Option | Default | Description |
|---|---|---|
| `-o, --output PATH` | `<src> HIERARCHY.<ext>` | Output path |
| `--mapping FILE` | — | JSON: `{"RGB(r,g,b)": weight_pt}` |
| `--preset {section,plan,elevation,detail,usc}` | `section` | Tier ladder for `--auto` |
| `--scale {1/16,1/8,1/4,1/2}` | `1/4` | Plot scale for ISO 128 weights |
| `--for-print` | off | Use ISO 128 print weights |
| `--auto` | off | Auto-bucket colors |
| `--default-width FLOAT` | `0.25` | Width for unmatched colors |
| `--keep-pieceinfo` | off | Don't strip AI cache |
| `--dry-run` | off | Preview mapping only |

## `arch-lw apply-jsx`

Layer-preserving via Illustrator JSX.

```bash
arch-lw apply-jsx SRC [-o OUTPUT]
```

## `arch-lw layout-jsx`

Illustrator layout bridge for Rhino Make2D exports. Sets the requested artboard,
centers or fits visible unlocked artwork, saves a PDF-compatible `.ai`, and can
write a structured layout report.

```bash
arch-lw layout-jsx SRC [OPTIONS]
```

| Option | Default | Description |
|---|---|---|
| `-o, --output PATH` | `<src> LAYOUT-jsx.<ext>` | Output path |
| `--artboard WIDTHxHEIGHT` | `24x36in` | Target artboard. Bare numbers are inches; `pt` is also supported |
| `--fit {center,fit}` | `center` | Keep scale and center, or scale down to fit within the margin |
| `--margin LENGTH` | `0.5in` | Margin used by `--fit` |
| `--allow-enlarge` | off | Let `--fit` scale small artwork up |
| `--report-json PATH` | `/tmp/arch_lw_layout_report.json` | Structured layout report |
| `--jsx-path PATH` | `/tmp/arch_lw_layout.jsx` | Generated JSX path |
| `--timeout MINUTES` | `30` | Illustrator JSX timeout |
| `--dry-run` | off | Render JSX/report without opening Illustrator or writing output artwork |

## `arch-lw apply-saas`

Headless AI-native payload rewrite. Preserves Illustrator layers and can also
inject poché without opening Illustrator.

```bash
arch-lw apply-saas SRC [OPTIONS]
```

| Option | Default | Description |
|---|---|---|
| `-o, --output PATH` | `<src> HIERARCHY-saas.<ext>` | Output path |
| `--mapping FILE` | — | JSON: `{"RGB(r,g,b)": weight_pt}` |
| `--preset {section,plan,elevation,detail,usc}` | `section` | Tier ladder for `--auto` |
| `--scale TEXT` | `1/4` | Plot scale for `--for-print` |
| `--for-print` | off | Use ISO 128 print weights |
| `--auto` | off | Auto-bucket native RGB/CMYK stroke colors |
| `--architectural` | off | Use semantic layer rules for hierarchy, poché eligibility, cut-stroke color, and solid cut dashes |
| `--default-width FLOAT` | `0.25` | Width for unmatched colors |
| `--poche` | off | Inject high-confidence structural poché fills |
| `--poche-overrides FILE` | — | Per-layer poché strategy overrides JSON |
| `--poche-overlay / --inline-poche` | architectural: overlay | Write generated fills to a top `ARCH_LW_POCHE` layer, or inline into source cut layers |
| `--bridge-strategy {greedy,best}` | `best` | Bridge selector for the poché auto-bridge rung |
| `--progress / --no-progress` | auto | Stage/layer progress feedback |

Architectural mode separates black poché from cut-line styling. A layer can be
`poche=False` and still receive a strong cut stroke, for example glazing,
frames, SHS/HSS, rainscreen returns, or panel cuts.

## `arch-lw poche`

Generate poché on cut layers via shapely linemerge + polygonize + auto-bridge + fallback.

```bash
arch-lw poche SRC [OPTIONS]
```

| Option | Default | Description |
|---|---|---|
| `-o, --output PATH` | `<src> POCHE.<ext>` | Output |
| `--overrides FILE` | — | Per-layer strategy overrides JSON |
| `--style {solid,material}` | `solid` | Solid black or material hatch |
| `--scale FLOAT` | `0.02` | Plot scale (1/N as decimal) for material mode |

## `arch-lw preview`

Generate visual before/after preview PNG.

```bash
arch-lw preview BEFORE AFTER -o OUTPUT [OPTIONS]
```

| Option | Default | Description |
|---|---|---|
| `--mode {side-by-side,tier-overlay,diff}` | `side-by-side` | Mode |
| `--dpi INT` | `96` | Render DPI |
| `--ghostscript` | off | Ghostscript fallback for hairline accuracy |

## `arch-lw explain-layer`

Show what tier+weight the classifier assigns.

```bash
arch-lw explain-layer 'axon::Visible::ClippingPlaneIntersections::TEC_TIMBER_BEAMS'
```
