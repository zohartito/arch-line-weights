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
