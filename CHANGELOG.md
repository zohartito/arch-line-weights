# Changelog

All notable changes to this project are documented here. Format loosely follows
[Keep a Changelog](https://keepachangelog.com).

## [0.5.0] — 2026-04-30

### Added
- **`arch_line_weights.hatch` module** — material-specific architectural hatch
  generation. 14 material recipes (concrete, CLT cross-grain, solid timber,
  steel, mineral wool insulation, rigid insulation, earth, brick, glass,
  gypsum, aluminum, plus solid-fill aliases). Built on shapely `parallel_hatch`,
  `crosshatch`, `sine_zigzag`, `brick_pattern`, `clt_layers`, and a
  Bridson-style `poisson_disk` sampler. Custom materials registerable via
  `register_material(MaterialRecipe(...))`.
- **`arch-lw poche --style material`** — generates per-material hatch
  geometry on top of the solid black fills. `--scale` parameter selects
  drawing scale (0.02 = 1:50, 0.01 = 1:100). Layer-name → material mapping
  via `material_for_layer()` (substring match against TEC_CONCRETE / TIMBER /
  STEEL / etc.).
- **`arch-lw preview` CLI subcommand** — wraps the existing
  `arch_line_weights.preview` module. Three modes:
  - `side-by-side` — both files at multiple plot scales, stacked
  - `tier-overlay` — `after` rendered with each weight tier in unique color
  - `diff` — pixel diff (red = added strokes, blue = removed)
  Optional `--ghostscript` flag for sub-0.25pt hairline accuracy via
  `-dNOMINLINEWIDTH`.
- **GitHub Actions CI** (`.github/workflows/ci.yml`) — pytest matrix on
  ubuntu + macOS × Python 3.11/3.12/3.13. ruff lint + format check.
- **GitHub Actions release workflow** (`.github/workflows/release.yml`) —
  builds sdist + wheel on tag push, publishes to PyPI via OIDC Trusted
  Publishing (when set up), creates GitHub Release with auto-generated notes.
- **GitHub issue templates** — bug report + feature request YAML forms.
- **`SECURITY.md`** — security policy with private reporting email.
- **23 tests** total (was 16): added 7 hatch tests including a safety-cap
  test for `poisson_disk` against pathological inputs.

### Fixed
- `poisson_disk` now caps generated sample count (`max_samples=50_000` default,
  enlarges `min_dist` proportionally if needed) so it doesn't hang or OOM on
  pathologically-large polygons with tiny spacing.

## [0.4.0] — 2026-04-30

### Added
- **`arch-lw poche` command** — full poché pipeline wired into the CLI. Two
  stages: dump cut-layer geometry from Illustrator → polygonize via shapely
  with per-layer best-tolerance sweep + `concave_hull`/`bbox` fallback →
  apply via JSX that creates new closed black-filled `pathItem`s in each cut
  layer. Layers preserved, strokes preserved, new fills added.
- **`arch_line_weights.poche` module** — production-quality poché. Confidence
  scoring per fill (`linemerge_bare` = 1.0, `linemerge_snap` = 0.7-0.95,
  `concave_hull` = 0.55, `bbox` = 0.3). Per-layer JSON overrides accepted.
  `__POCHE_CLOSE__` user-marked closing layer support.
- **`arch_line_weights.preview` module** — `side_by_side()`, `tier_overlay()`,
  `diff_image()`. PyMuPDF primary renderer + Ghostscript fallback.
- **`arch_line_weights.presets.select_preset()`** — ISO 128 / standards-aligned
  tier ladders. `--scale` shifts weights per scale; `--for-print` switches
  from screen-review weights to plotted-print weights.
- **`integrations/rhino/`** — three drop-in scripts:
  - `apply_arch_hierarchy.py` — GhPython 3 component
  - `arch_lw_button.py` — Rhino 8 toolbar button + Eto progress dialog
  - `tag_rhino_layers_for_poche.py` — pre-export `__TIER:*` injection
- **Dependencies**: `shapely>=2.0`, `numpy>=1.26`, `Pillow>=10.0`

### Changed
- `arch-lw apply` now accepts `--scale` and `--for-print` flags.

## [0.3.0-alpha] — 2026-04-29

### Added
- Poché pipeline scripts (`scripts/poche/`) — first working two-stage approach.
- `docs/POSTMORTEM.md` — every poché attempt with what worked/failed.
- 4 sub-agent research transcripts in `docs/research/`.

## [0.2.0] — 2026-04-29

### Added
- `apply-jsx` command — layer-preserving apply path via Illustrator JSX.
- `arch_line_weights.layer_classify` — semantic classifier for OCG layer names.
- `explain-layer` command.

### Changed
- Default for `.ai` is now `apply-jsx`, not `apply` (preserves layers).

## [0.1.0] — 2026-04-29

Initial release. `inspect` + `apply` (pikepdf, color-classify) +
auto-by-luminance classifier + section/plan/elevation/detail presets +
Claude Code skill.
