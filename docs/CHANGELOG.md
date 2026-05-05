# Changelog

All notable changes to `arch-line-weights` are documented here. Format
follows [Keep a Changelog](https://keepachangelog.com/) and the project
versioning follows [Semantic Versioning](https://semver.org/).

> The root-level `CHANGELOG.md` is the v0.2-vintage abbreviated log; this
> file is the authoritative, comprehensive history. See `docs/POSTMORTEM.md`
> for narrative context on why each release happened the way it did, and
> `docs/LESSONS_LEARNED.md` for the durable lessons each one contributed.

## [Unreleased]

### In flight

- **Issue #5** — wire `infer_bridges_best` as the default bridge strategy
  (currently opt-in via `--bridge-strategy=best` / `ARCH_LW_BRIDGE_STRATEGY`).
  Default is still greedy auto-bridge for backwards compatibility.
- **Issue #7** — real-Illustrator visual validation pass (partially closed
  by the v0.6.x real-world runs on `macro.ai` and `wall section iso cut .ai`).
- **Issue #4** — B9 commercial license swap, deferred until ~3 days before
  v1.0.1 publish (per LESSONS_LEARNED #36).
- **Phase A1/A2 personal-use validation** (Issues #1, #2) — accumulating
  drawings in `docs/research/personal-use-log.md` toward the ≥5-drawings
  decision gate.
- **Phase C1** (Issue #3) — webapp from scaffold to deployable.

### Recently closed (carry-over from v0.6.x)

- **Issue #6** — α-shape rescue rung shipped in v0.6.0; LLM topology
  rescue rung shipped in v0.6.3.
- **Issue #8** — JSX heartbeat polling (v0.6.1).
- **Issue #10** — `[Converted]` doc-state detection (v0.6.1, properly
  fixed in v0.6.4 after AppleScript syntax error).
- **Issue #11** — configurable JSX timeout (v0.6.1).
- **Issue #12** — distinct default output paths per pipeline (v0.6.3).
- **Issue #13** — `--preset` flag on `apply-jsx` (v0.6.1).
- **Issue #14** — `[Converted]` matcher trailing-whitespace edge case
  (v0.6.3).

## [0.6.6] — 2026-05-05

### Fixed

- CI failure on v0.6.5 macOS runners without Illustrator installed:
  `osacompile` could not resolve Illustrator's dictionary classes, so the
  AppleScript syntax-compile test failed instead of skipping. Split the
  skip predicate into `_illustrator_installed()` (checks `/Applications`)
  and `_illustrator_running()` (checks active process); the syntax test
  now needs only the former, while the live-doc test still needs the
  latter.

## [0.6.5] — 2026-05-01

### Added

- Integration test suite at `tests/integration/test_apply_jsx_applescript.py`
  exercises `query_active_doc()` against real `osascript` and verifies the
  embedded AppleScript literal compiles via `osacompile`. This closes the
  regression-class gap that allowed v0.6.1 + v0.6.3 to ship with broken
  AppleScript twice (both prior fixes mocked `subprocess.run`).
- Skip predicates degrade gracefully on CI runners without macOS or
  Illustrator: `@pytest.mark.skipif(not _osascript_available())` and the
  Illustrator-running predicate keep CI green where the bridge can't be
  exercised.

## [0.6.4] — 2026-05-01

### Fixed

- AppleScript syntax error in `query_active_doc()` on Illustrator 2026
  (build 30.x). `name of active document` raised
  `Expected end of line, but found class name (-2741)` because
  Illustrator's dictionary has both a `name` property and a `name` class
  and the parser couldn't disambiguate at that token sequence. Two
  combined adjustments fix it: use `current document` instead of
  `active document`, and wrap the property access in
  `(get name of current document)` so the receiver is bound explicitly.
  Without this fix the v0.6.1 / v0.6.3 `[Converted]` detection never
  fired in production. (See `src/arch_line_weights/apply_jsx.py`.)

## [0.6.3] — 2026-05-01

### Added

- **Issue #6** — LLM topology inference rescue rung 5 in
  `src/arch_line_weights/llm_topology.py` (~400 LOC). Calls Anthropic
  Claude Haiku 3.5 with a prompt-cached system prompt, strict JSON via
  `tool_use`, and schema-validated output. Inserted into the rescue
  ladder at confidence 0.65, strategy name `llm_topology`. Gated DEFAULT
  OFF behind `ARCH_LW_LLM_FALLBACK=1` (no surprise costs). New
  `--llm-fallback` CLI flag on `apply-saas` and `poche`. Optional
  `[llm]` extra (`anthropic>=0.40`).

### Changed

- `apply-jsx` default output: `<src> HIERARCHY-jsx.<ext>`
- `apply-saas` default output: `<src> HIERARCHY-saas.<ext>`
- Legacy `apply` (pikepdf, layer-flattening) keeps `<src> HIERARCHY.<ext>`
  for back-compat. Closes Issue #12 (output-path collision when running
  both pipelines on the same source).

### Fixed

- **Issue #14** — `[Converted]` matcher missed disk filenames with
  trailing whitespace (e.g. `wall section iso cut .ai`, which Illustrator
  surfaces as `wall section iso cut  [Converted].ai`). `_is_converted_match`
  now peels the `[Converted]` decoration via regex, normalizes both sides
  with full-Unicode `str.rstrip()`, and compares stems. `query_active_doc()`
  uses `rstrip("\r\n")` so internal trailing whitespace survives the
  osascript round-trip. 24 new test cases.

## [0.6.2] — 2026-04-30

### Fixed

- CI failure on Linux: `zstandard` and `scipy` were imported at runtime by
  `apply_saas.py` / `poche_saas.py` / `alpha_shape.py` but missing from
  `[project.dependencies]`. They were transitive deps via pikepdf / shapely
  on macOS so local builds passed; Linux runners surfaced the gap. Both
  now explicit.

## [0.6.1] — 2026-05-01

### Added

- **Issue #8** — per-layer heartbeat in `apply-jsx`. JSX writes
  `<idx>/<total>: <layer> (<n> paths)` lines to
  `/tmp/arch_lw_jsx_progress.txt`; Python `_HeartbeatPoller` polls every
  2 s, prints new lines, and surfaces a one-time warning when the file
  goes stale for >5 min (informational only — never aborts).
- **Issue #11** — configurable JSX timeout via `--timeout MINUTES`
  (default 30, max 240) and `ARCH_LW_JSX_TIMEOUT_MIN` env var. Replaces
  the hardcoded 60-min that was wrong both ways.
- **Issue #13** — `--preset {section|plan|elevation|detail}` on
  `apply-jsx` for parity with `apply-saas`. Wired through
  `tier_weights_for_preset()` in `layer_classify.py`. Default
  `preset=None` preserves v0.5.1 hardcoded weights byte-for-byte.

### Fixed

- **Issue #9** — `inspect_file()` now per-format dispatches `.ai` files
  to a new pikepdf backend (`_inspect_ai`) and keeps PyMuPDF for plain
  `.pdf`. Verified on the 98 MB `macro.ai` (1.28M drawings, 41 colors)
  in 25 s, matching the PyMuPDF baseline. The 237 MB `macro.ai` is also
  trailer-corrupt; pikepdf can't recover, requiring an Illustrator
  Save-As.
- **Issue #10** — `[Converted]` doc-state detection in `apply-jsx`.
  Pre-flight active-doc query; when the active doc matches `src` modulo
  the `[Converted]` decoration, the wrapper sets `USE_OPEN_DOC=true` and
  the JSX runs against `app.activeDocument` directly. Otherwise it
  raises a clear save-and-close instruction.

### CI

- Ruff format pass, removed `×` ambiguity, MkDocs no longer strict.
  (Also part of v0.6.1 in the original commit timeline.)

## [0.6.0] — 2026-05-01

### Added

- **Phase D webapp scaffold** in `webapp/`. FastAPI backend wires existing
  `apply_saas` + `poche_saas` behind `POST /api/jobs`; SvelteKit + Tailwind
  frontend has upload + job-detail pages with status polling. 15 backend
  tests including end-to-end upload→process→download. `LocalStorage` stub
  ready to swap for S3/R2.
- **`infer_bridges_best`** strategy selector (closes Issue #5 partially —
  opt-in via `--bridge-strategy=best` or `ARCH_LW_BRIDGE_STRATEGY`).
  Wired through `polygonize_layer`, `polygonize_dump`, `apply_poche`,
  `compute_polygons_for_layers`, and `apply_saas_with_poche`. Default
  routing remains greedy auto-bridge.
- **α-shape rescue rung** in `src/arch_line_weights/alpha_shape.py`.
  Hand-rolled α-complex over `scipy.spatial.Delaunay`; adaptive
  `alpha_shape_best` sweeps a 9-value alpha grid and picks the
  max-coverage non-sliver result. Inserted into the rescue ladder
  between `auto_bridge` and `concave_hull` at confidence 0.55.
  `--alpha-shape` / `--no-alpha-shape` CLI flag (default ON).
- **Demo gallery + benchmark suite** under `scripts/`: `demo_gallery.py`
  produces side-by-side PNGs over a directory of `.ai` files;
  `benchmark.py` records timing metrics to
  `docs/research/benchmarks.{md,json}`.
- **MkDocs Material documentation site** with Diátaxis structure
  (tutorial, 5 how-to guides, CLI + Python API reference, 3 explanation
  pages); auto-deploys to GitHub Pages on push to main and on tag.
- **`pyproject.toml` migrated to hatchling + hatch-vcs.** Version is
  derived from git tags. PEP 639 `license` + `license-files`.
  SPDX-compliant. New `[docs]` extra installs MkDocs Material +
  mkdocstrings.
- `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, launch drafts in
  `docs/announce/`.
- 23 bridge-strategy + 28 α-shape tests.

### Changed

- Auto-bridge inference is now in the default rescue ladder. On the USC
  ARCH 202B reference: v0.5 was 14 / 6 / 1 (clean / imperfect / failed);
  v0.6 is 18 / 2 / 1.

## [0.5.1] — 2026-04-30

### Changed

- Code-quality pass over the v0.5 Wave 4 outputs by three review
  sub-agents. No behavior changes; ruff-clean, dead-code stripped,
  docstring polish. 23/23 tests still pass.

## [0.5.0] — 2026-04-30

### Added

- **`arch_line_weights.hatch` module** — material-specific architectural
  hatch generation. 14 material recipes (concrete diagonal + stipple,
  CLT cross-grain, solid timber, steel, mineral wool zigzag, rigid
  insulation, earth, brick stretcher bond, glass, gypsum, aluminum,
  solid-fill aliases). Pure shapely + numpy with a Bridson-style
  `poisson_disk` sampler.
- **`arch-lw poche --style material`** generates per-material hatch
  geometry on top of solid black fills. `--scale` selects drawing scale
  (0.02 = 1:50, 0.01 = 1:100). Custom materials registerable via
  `register_material()`.
- **`arch-lw preview` CLI subcommand** wraps the v0.4 preview module:
  `side-by-side`, `tier-overlay`, `diff`. Optional `--ghostscript` for
  sub-0.25 pt hairline accuracy.
- **GitHub Actions CI matrix** (ubuntu + macOS × Python 3.11/3.12/3.13)
  with pytest + ruff. Release workflow builds sdist + wheel on tag push
  and publishes to PyPI via OIDC Trusted Publishing. Issue templates,
  `SECURITY.md`.
- AutoCAD/AIA NCS layer-name parsing; bridge improvements; preset
  family expansion. (Wave 4 engineering deliverables — see
  `docs/research/preset-families.md`.)

### Fixed

- `poisson_disk` caps generated sample count and enlarges `min_dist`
  proportionally on pathologically-large polygons so it doesn't hang.

### Reference run

- USC ARCH 202B drawing: `arch-lw poche HIERARCHY.ai --style material
  --scale 0.02` → 233 black polygons + ~5,000 hatch lines across 14
  cut layers in ~30 s. 23/23 tests passing.

## [0.4.0] — 2026-04-30

### Added

- **`arch-lw poche` CLI command** wires the full poché pipeline into one
  shot. Two-stage execution: Illustrator JSX dumps cut-layer geometry →
  shapely linemerge + polygonize per layer with confidence scoring →
  second JSX creates new closed `pathItem`s with black fill. 16 s
  end-to-end on the reference drawing (vs 30+ min of manual gymnastics
  in v0.3.0-alpha).
- **`arch_line_weights.poche`** module with confidence scoring and
  `__POCHE_CLOSE__` user-marked closing-layer support.
- **`arch_line_weights.preview`** — `side_by_side` / `tier_overlay` /
  `diff_image` via PyMuPDF + Ghostscript fallback.
- **`arch_line_weights.presets.select_preset()`** — ISO 128
  standards-aligned ladders with per-scale shifts.
- **`apply` accepts `--scale {1/16,1/8,1/4,1/2}` and `--for-print`** —
  switches to standards-aligned weights (0.13–1.98 pt at 1/4"=1' per
  Ramsey/Sleeper) vs default screen-review weights (0.08–1.0 pt).
- **Per-layer override JSON** for poché:
  `arch-lw poche file.ai --overrides {"TEC_FOUNDATION": {"strategy": "bbox"}}`.
- **Confidence scoring per fill**: 1.00 bare linemerge → 0.95–0.7
  snap+linemerge → 0.55 concave_hull → 0.30 bbox.
- **Rhino integration scaffolding** in `integrations/rhino/`:
  `apply_arch_hierarchy.py` (GhPython 3 component),
  `arch_lw_button.py` (Rhino 8 toolbar with Eto progress dialog),
  `tag_rhino_layers_for_poche.py` (pre-export `__TIER:*` injection).

### Dependencies

- `shapely>=2.0`, `numpy>=1.26`, `Pillow>=10.0`.
- 16/16 tests passing including poché + preset coverage.

## [0.3.0-alpha] — 2026-04-30

### Added

- **First working two-stage poché pipeline** in `scripts/poche/`. Not yet
  wired into the `arch-lw` CLI — see `scripts/poche/README.md`.
- Pipeline shape (Postmortem Attempt 5):
  `HIERARCHY.ai → dump_cut_geometry.jsx → cut_geometry.json →
  polygonize.py (linemerge + polygonize, per-layer best-tolerance sweep,
  concave_hull/bbox fallback) → poche_polygons.json →
  build_apply_jsx.py (bakes polygons into JSX) → JSX adds new filled
  pathItems, saveAs POCHE.ai`.
- **`docs/POSTMORTEM.md`** — every poché attempt with what worked, what
  failed, and durable lessons. The most important artifact in the repo.
- **`docs/research/standards.md`** — ISO 128 √2 series, Ramsey/Sleeper,
  Ching, NCS, Revit-pen mapping.
- **`docs/research/poche-conventions.md`**, `disconnected-loops.md`,
  `pypi-ci-starter.md`.
- **`scripts/poche/apply_join_NAIVE.jsx`** kept as a warning marker —
  shows why naive Join + fill produces tangled blobs (Postmortem
  Attempt 3).

### Status

- 13 / 21 cut layers get clean per-shape polygons; 7 / 21 fall back to
  concave_hull (lumpy single polygon); 1 / 21 fails entirely.

## [0.2.0] — 2026-04-29

### Added

- **`apply-jsx` command** (now the default for `.ai`). Hands a JSX to
  Illustrator, walks each leaf layer, derives weight from the new
  semantic layer-name classifier, applies to every `pathItem`. Preserves
  all original layers. Slower (3–15 min on 340 K paths) but correct.
- **`arch_line_weights.layer_classify`** — semantic layer-name
  classifier. Recognizes Rhino's
  `Visible::ClippingPlaneIntersections::*` as the cut tier regardless of
  trailing material code (huge improvement over color classification).
  Material-suffix table for Curves layers (`TEC_*`, `CU_*`, `CLT_*`,
  `SHS_*`, `EPDM_*`, `WINDOW_*`, `FLOOR_DATUMS`, …). Same logic emits as
  ExtendScript for the JSX runner.
- **`explain-layer` command** for quick classifier diagnostics.
- `docs/POSTMORTEM.md` and `docs/ROADMAP.md` so future contributors know
  why v0.1's pikepdf default was wrong and what's planned next.

### Changed

- **Default for `.ai` is now `apply-jsx`** (layer-preserving). The
  pikepdf path is still available as `apply` but no longer the default.

### Reference run

- Same 24 MB / 340 K-stroke / 62-layer USC ARCH 202B section drawing:
  11 min, 0 errors, all 62 layers preserved.

## [0.1.0] — 2026-04-29

### Added

- Initial release. `arch-lw` CLI (`inspect`, `apply`) built on click.
- pikepdf-backed `apply` with per-color stroke widths via PDF
  content-stream rewrite.
- PyMuPDF-backed `inspect` (color histogram, stroke counts).
- Auto-by-luminance classifier (5 main tiers + special).
- 4 presets: `section` / `plan` / `elevation` / `detail`.
- `examples/sample-mapping.json`.
- 3 unit tests (passing).
- Claude Code skill `apply-arch-hierarchy`.

### Known issue

- **Stripping `/PieceInfo` flattens 60+ Rhino layers into a single
  Illustrator layer.** Fixed in v0.2.0 by introducing the
  layer-preserving JSX path. (Postmortem Attempt 1.)

### Reference run

- 24 MB / 340,323-stroke / 37-color section drawing processed in ~110 s
  with no Illustrator interaction.

---

## Yanked

### [1.0.0] — 2026-04-30 (yanked same day)

Published to PyPI under MIT via OIDC Trusted Publishing; build verified;
clean-venv install confirmed (`arch-lw, version 1.0.0`). Yanked ~15
minutes later when the project pivoted to a SaaS-first commercial model.
Repository made private. Trusted Publisher removed; release workflow
disabled. The yank semantics keep `pip install arch-line-weights==1.0.0`
working for anyone who explicitly pins it; it's hidden from plain
`pip install`. The MIT license on that exact version is irrevocable. See
`docs/POSTMORTEM.md` Attempt 7 and `docs/LESSONS_LEARNED.md` #22–#26.
