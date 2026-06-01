# Private Studio Dogfood Runbook

Public-safe steps for reviewing a **private** USC / Make2D export locally. This
document does not contain private filenames, paths, screenshots, or proof assets.

## What you must provide locally (never commit)

- A **copy** of your Rhino / Illustrator Make2D export (`.ai` or `.pdf`).
- Optional: native Illustrator `.ai` with `/NumBlock` if using `apply-saas`.
- A writable **local proof directory** (e.g. a folder named `proof/` under your
  project checkout — path is your choice; do not paste machine paths into public issues).

## Posture (read first)

- **Posting/public proof is NO-GO** unless W5/W7 explicitly accepts a public-safe packet.
- **Synthetic proof does not close GitHub issue #30.**
- **Private USC regression stays private** — keep raw reports and drawings off GitHub.
- Console and `proof-check` outputs are **local review aids**, not launch clearance.

## Suggested local workflow

### 1. Inspect input

```bash
arch-lw inspect path/to/your-export.ai
```

Confirm the file opens. If you see trailer / damaged-PDF errors, re-save from
Illustrator as a modern PDF-compatible `.ai`, then retry.

### 2. Apply line weights (pick path by input type)

**Converted / section `.ai` (typical Make2D):**

```bash
arch-lw apply-jsx path/to/your-export.ai --preset section --source rhino
```

**Native Illustrator `.ai` with `/NumBlock`:**

```bash
arch-lw apply-saas path/to/your-export.ai --architectural --preset usc --source rhino
```

Always work on a **copy**, not your only studio file.

### 3. Poché (section workflows)

```bash
arch-lw poche "your-export HIERARCHY-jsx.ai" --source rhino --style solid --report report.json
```

Keep `report.json` in your **local proof directory** only.

### 4. Diagnose the durable report

```bash
arch-lw diagnose report.json
arch-lw diagnose report.json --json   # machine-readable summary
```

Use this for a review checklist. Diagnose does **not** mean posting is allowed.

### 5. Validate a proof packet (when artifacts exist)

Build a local packet directory per `tests/fixtures/make2d/manifest.yml` layout
(before/after/diff images, `report.json`, geometry JSON, etc.) — all **local paths**.

```bash
arch-lw proof-check tests/fixtures/make2d/manifest.yml \
  --output-dir path/to/your/local/proof \
  --fixture public_foundation_window_section_synthetic
```

`proof-check` fails on missing `report.json`, `failed` / `no_go` reports, unchanged
renders, private path leaks, and count mismatches. A passing synthetic fixture does
**not** close #30.

### 6. Designer console (optional local UI)

```bash
cd webapp
arch-lw-web-console
```

Use **Synthetic proof / demo** only to exercise the harness. The UI shows
`posting_clearance: NO-GO` until W5/W7 acceptance is recorded (not implemented in
the prototype store). Export zip includes `W5-W7-ACCEPTANCE-HANDOFF.json` / `.md`
as **NO-GO** templates.

## Where raw vs public-safe outputs go

| Output | Location | Commit? |
|--------|----------|---------|
| Raw `report.json`, local logs | Your local proof directory | **Never** |
| `proof-check --write` JSON | Local only | **Never** |
| Console proof zip | Downloaded locally | **Never** |
| Public-safe summaries in issues | Path-free text only | OK with gates stated |

## What counts as W5/W7 acceptance

Acceptance means **named reviewers** explicitly approve a **public-safe** proof
packet after visual review of real studio output — not:

- green CI,
- synthetic demo,
- `proof-check` on public fixtures only,
- or console `overall_status: passed` on a local run.

Record acceptance in your **private** review workflow first. Public posting stays
**NO-GO** until that acceptance is scoped to a redacted, path-free public packet.

## What still keeps posting NO-GO

- Open #29 / #30.
- Foundation/concrete gaps or launch-blocking limitations in reports.
- Any `needs_review`, `failed`, or `no_go` in raw reports.
- Missing rendered views or unchanged before/after images in proof validation.
- Private path leaks in handoff or summaries.
