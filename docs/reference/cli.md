# CLI reference

`arch-lw` is the entry point. All subcommands accept `--help`.

## Supported input paths

The command to use depends on the input kind, not only the file extension.
Native Illustrator `.ai` files with `/NumBlock` use the headless
`apply-saas` path. PDF-only or converted `.ai` files use the Illustrator bridge
with `apply-jsx`, followed by `poche` when section poché is needed. Plain PDFs
use `inspect` and `apply`. Legacy Rhino PostScript `.ai` files should be opened
in Illustrator and saved as a modern `.ai` copy before processing.

See [Supported inputs](../how-to/supported-inputs.md) for the full matrix and
conversion guidance.

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

## `arch-lw bridge-rhino-ai`

Bridge a Rhino Make2D export through layout and optional proof stages. The
first stage always runs `layout-jsx`; `apply-jsx` and `poche` are opt-in so the
layout bridge can be used without changing hierarchy or poché.

```bash
arch-lw bridge-rhino-ai --input SRC [OPTIONS]
```

| Option | Default | Description |
|---|---|---|
| `--input PATH` | required | Rhino Export Selected `.ai` or `.pdf` |
| `-o, --output PATH` | `<input> LAYOUT-jsx.<ext>` | Layout output path |
| `--artboard WIDTHxHEIGHT` | `24x36in` | Target artboard |
| `--fit {center,fit}` | `center` | Center at current scale, or fit within margin |
| `--margin LENGTH` | `0.5in` | Margin for `--fit` |
| `--allow-enlarge` | off | Let `--fit` scale small artwork up |
| `--preset {section,plan,elevation,detail,usc}` | `section` | Preset for optional `--apply-jsx` |
| `--source {auto,rhino,autocad}` | `rhino` | Layer-name convention for reports and optional poché |
| `--scale TEXT` | `1/4` | Plot scale for optional `--apply-jsx --for-print` |
| `--for-print` | off | Use print weights in optional `--apply-jsx` |
| `--apply-jsx` | off | Run hierarchy after layout |
| `--poche` | off | Run poché after `--apply-jsx` |
| `--poche-style {solid,material}` | `solid` | Poché output style |
| `--bridge-strategy {greedy,best}` | `best` | Poché bridge selector |
| `--report-dir DIR` | `<input> arch-lw-bridge` | Bridge, layout, poché, geometry, and JSX reports |
| `--timeout MINUTES` | `30` | Illustrator JSX timeout |
| `--dry-run` | off | Plan stages and render layout JSX/report without GUI work |

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
| `--report PATH` | — | Durable JSON report with input kind, command path, and filled/skipped/failed/why layer status |

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
| `--report PATH` | — | Durable JSON report for the Illustrator-backed poché pass |

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

## `arch-lw diagnose`

Summarize an `arch-lw --report` JSON file into a review checklist.

```bash
arch-lw diagnose run-report.json [--json]
```

The text output groups filled, inferred, low-confidence, skipped, failed, and
missing-payload layers, lists review reasons, and reminds the user that PDF
preview is not authoritative for AI-native Illustrator payloads.

## `arch-lw proof-check`

Read a Make2D proof manifest and emit proof-packet plan or validation JSON.

```bash
arch-lw proof-check tests/fixtures/make2d/manifest.yml \
  --output-dir proof \
  --plan-only
```

| Option | Default | Description |
|---|---|---|
| `--output-dir PATH` | `proof` | Directory containing, or planned to contain, per-fixture proof packet artifacts |
| `--fixture ID` | all fixtures | Limit output to one fixture id; may be passed multiple times |
| `--plan-only` | off | Emit manifest, expected artifact paths, commands, and guardrails without validating local files |
| `--write PATH` | — | Write the proof-check JSON report to disk as well as stdout |
| `--pretty / --no-pretty` | pretty | Pretty-print JSON output |

Validation mode checks the deterministic proof packet paths for `report.json`,
before/after/diff images, cut-geometry JSON, layer-audit JSON, rendered-view
coverage, report identity, no-go/review state, private path leaks, and configured
review-region pixel gates. It also compares manifest `expected_report.counts`
against the raw report summary and fails when rendered before/after views are
effectively unchanged. It fails nonzero for `failed` or `no_go` packets and keeps
`needs_review` visible for W5/W7 acceptance. Treat `--write` output as local
evidence: do not commit raw proof-check reports that contain machine-local paths.

## `arch-lw explain-layer`

Show what tier+weight the classifier assigns.

```bash
arch-lw explain-layer 'axon::Visible::ClippingPlaneIntersections::TEC_TIMBER_BEAMS'
```
