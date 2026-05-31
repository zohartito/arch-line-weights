# Release Notes — arch-line-weights

## Day-1 source release — 2026-05-30

A deterministic Python CLI (`arch-lw`) that takes a Rhino/Make2D vector export
(`.ai` or `.pdf`) and gives it an architectural line-weight hierarchy — heavier
cut/profile lines, lighter visible/hidden/surface lines — plus optional
solid-black poché on the section-cut mass. All original layers are preserved on
the layer-aware paths. No LLM calls in the core path; classification and weight
rules are rule-based and testable.

This is a **source / GitHub install** release on `main`. It is not a PyPI
package, not a hosted service, and not validated on every possible Rhino export.

### What it does

- **`inspect`** — report the stroke-color / stroke-width distribution of a
  `.ai` or `.pdf` so you can see what the classifier is working with.
- **`apply`** — fast per-color stroke-width rewrite. Rewrites the PDF stream
  directly; it is the quickest path but **can flatten Illustrator layers**.
- **`apply-jsx`** — layer-preserving hierarchy via an Illustrator JSX bridge.
  Slower, but keeps the original layer structure intact.
- **`apply-saas`** — headless, layer-preserving rewrite that edits the
  Illustrator native private payload directly. Requires a native `.ai`
  (see caveats). `--poche` adds solid-black cut fill on this path.
- **`poche`** — generate solid-black poché on cut layers via shapely
  topology recovery (linemerge → snap sweep → auto-bridge → fallbacks).
- Ships presets for `section`, `plan`, `elevation`, `detail`, and the `usc`
  studio-board workflow. The `usc` weight ladder follows `CONVENTIONS.md`.

### Install

Source checkout (primary):

```bash
git clone https://github.com/zohartito/arch-line-weights
cd arch-line-weights
python -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/arch-lw --help
```

Optional global install if `pipx` is available:

```bash
pipx install git+https://github.com/zohartito/arch-line-weights
```

PyPI is **not** the install path for this release. `v1.0.0` was briefly
published to PyPI and then yanked, so install from source or GitHub as above.

### The three working paths (pick by input format)

| Input file | Use | Notes |
|---|---|---|
| **PDF-only export** (`.pdf`, or PDF with no Illustrator native data) | `inspect`, then `apply` | Fastest. Stroke-weight rewrite only; `apply` can flatten Illustrator layers. |
| **Native Illustrator `.ai`** (has the AI private payload `/NumBlock`) | `apply-saas` (optionally `--poche`) | Headless, layer-preserving. This is the path the 98 MB axon stress-test ran on. |
| **Converted / section `.ai`** (`[Converted]`, PDF-only lineage, **no** `/NumBlock`) | `apply-jsx`, then `arch-lw poche` | The Illustrator-bridge path. This is the path the section proof ran on. |

Converted-section example (the dogfood section-proof commands):

```bash
.venv/bin/arch-lw apply-jsx "WALL SECTION [Converted].ai" \
  --preset usc --source rhino --for-print
.venv/bin/arch-lw poche "WALL SECTION [Converted] HIERARCHY-jsx.ai" \
  --source rhino --style solid --bridge-strategy best
```

### Known input-format caveats

- **`apply-saas --poche` needs a native `/NumBlock`.** On a PDF-only or
  `[Converted]` `.ai` there is no `/NumBlock`, so `apply-saas` cannot edit it —
  use the `apply-jsx` → `arch-lw poche` bridge for those files instead.
- **Legacy Rhino PostScript `.ai` must be re-saved first.** Files like
  `wall section iso cut .ai` / `wall section cut make2d.ai` fail to open in both
  pikepdf and PyMuPDF ("unable to find trailer dictionary"). Open the file in
  Adobe Illustrator, use **File → Save As** to write a modern / PDF-compatible
  `.ai`, then rerun `arch-lw`. The CLI prints this hint on the failure.
- **`apply` can flatten layers.** If you need the original layer structure
  preserved, use `apply-jsx` or `apply-saas`, not the fast `apply` path.
- The Illustrator-bridge paths (`apply-jsx`, `arch-lw poche` with
  `--source rhino`) require Adobe Illustrator installed locally.

### Dogfood results (2026-05-30)

- **Axon stress-test** — `macro_for_archlw.ai`, 98 MB, 1.28M strokes,
  `apply-saas` exit 0, ~1:53 runtime. This is large-file / performance evidence,
  **not** section/poché proof: the axon file has no `ClippingPlaneIntersections`.
- **Section proof** (Illustrator bridge, `WALL SECTION [Converted].ai`):
  - `apply-jsx` hierarchy: 25 leaf layers, 512 paths modified, 0 errors;
    Illustrator opens the output.
  - `arch-lw poche`: 30 poché polygons, 8 cut layers, 0 failed layers;
    Illustrator opens the final output.
- Release-gate checks passed for the source/GitHub handoff.

Proof assets are committed under `docs/img/day1-proof/`:

- [Before: raw Rhino/Make2D export](docs/img/day1-proof/01-before-raw.png)
- [After: hierarchy + solid-black poché](docs/img/day1-proof/03-after-poche-full.png)
- [Close-up: cut mass solid, openings left white](docs/img/day1-proof/05-closeup-cut-mass-windows-white.png)
- [Final poché PDF](docs/img/day1-proof/section-HIERARCHY-jsx-POCHE.pdf)

### What to file issues for

Test on a **copy** of your drawing first, then open an issue with the file
characteristics (source app, export type, layer names) if:

- the classifier puts linework in the wrong tier for your Rhino/Make2D layer
  naming or stroke-color conventions;
- a `.ai`/`.pdf` fails to open even after an Illustrator **Save As**;
- poché misses a cut region, leaks past openings, or fills the wrong mass;
- `apply` flattened layers you needed preserved (note which command you ran);
- `apply-saas` reports a missing `/NumBlock` on a file you believe is a native
  Illustrator `.ai`;
- runtime or memory is unreasonable on a large file (include size + stroke count).

### Not in this release

- No PyPI package for this release.
- No hosted cloud product. `apply-saas` is a local CLI command name for the
  native-payload rewrite path; the `webapp/` directory is a local experimental
  scaffold, not a deployed service.
- No workflow tested in Bluebeam.
- Not yet proven on a real studio pin-up board, and not validated on every
  Rhino/Illustrator export shape. Day-1 section-proof screenshots are committed
  in `docs/img/day1-proof/`.
