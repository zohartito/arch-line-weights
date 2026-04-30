# Changelog

All notable changes to this project are documented here. Format loosely follows
[Keep a Changelog](https://keepachangelog.com).

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
  `__POCHE_CLOSE__` user-marked closing layer support — draw bridging lines
  in Rhino on a layer with that name and we'll merge them in before
  polygonizing.
- **`arch_line_weights.preview` module** — `side_by_side()`, `tier_overlay()`,
  `diff_image()`. PyMuPDF primary renderer + Ghostscript fallback (with
  `-dNOMINLINEWIDTH` for sub-0.25pt hairline accuracy).
- **`arch_line_weights.presets.select_preset()`** — ISO 128 / standards-aligned
  tier ladders. `--scale 1/16|1/8|1/4|1/2` shifts weights per Ramsey/Sleeper
  and Ching scale conventions. `--for-print` switches from screen-review
  weights (0.08–1.0 pt) to plotted-print weights (0.13–1.98 pt at 1/4"=1').
  See `docs/research/standards.md` for the full source citations.
- **`integrations/rhino/`** — three drop-in scripts:
  - `apply_arch_hierarchy.py` — GhPython 3 component wrapping the CLI
  - `arch_lw_button.py` — Rhino 8 toolbar button with Eto progress dialog
  - `tag_rhino_layers_for_poche.py` — pre-export tagger that injects
    `__TIER:cut`, `__TIER:profile`, etc. into Rhino layer names so the
    classifier becomes deterministic at export time
- **`docs/research/`** added 4 sub-agent reports:
  - `standards.md` — ISO 128 + Ramsey/Sleeper + Ching + NCS + Revit pen mapping
  - `poche-conventions.md` — material→treatment table + 4 implementation paths
  - `disconnected-loops.md` — strategy ladder for Make2D rescue
  - `pypi-publishing.md` — concrete PyPI checklist for v1.0
- **Dependencies**: `shapely>=2.0`, `numpy>=1.26`, `Pillow>=10.0`

### Changed
- `arch-lw apply` now accepts `--scale` and `--for-print` flags. Defaults are
  unchanged (screen-review weights at any scale).

### Fixed
- v0.3.0-alpha poché reduced 7 imperfect layers to 1 weird polygon each via
  `concave_hull`. v0.4 best-effort sweep + `__POCHE_CLOSE__` recovers
  most of these. Foundation, concrete base etc. now have either correct
  polygons (when bridge segments exist) or honest bbox fills with confidence
  flagged in the report.

## [0.3.0-alpha] — 2026-04-29

### Added
- Poché pipeline scripts (`scripts/poche/`) — first working two-stage
  approach: Illustrator JSX dumps geometry → shapely linemerge+polygonize
  → JSX bakes filled polygons into Illustrator. 13/21 cut layers worked
  cleanly, 7 fell back to imperfect concave hulls, 1 failed.
- `docs/POSTMORTEM.md` — every poché attempt with what worked, what failed
- 4 sub-agent research transcripts in `docs/research/`
- `scripts/poche/apply_join_NAIVE.jsx` kept as a warning marker

## [0.2.0] — 2026-04-29

### Added
- **`apply-jsx` command** — layer-preserving apply path. Hands a JSX to
  Adobe Illustrator via `osascript`. Walks document's leaf layers, derives
  weight from the new semantic classifier, applies to every `pathItem` in
  that layer, saves to `<src> HIERARCHY.<ext>`. Slower than `apply` (3-15
  min for ~340K paths) but **preserves all layers** — critical for
  Rhino-exported drawings.
- **`arch_line_weights.layer_classify`** — semantic classifier for OCG
  layer names. Recognises Rhino's `<view>::Visible|Hidden::Curves|ClippingPlaneIntersections::<src>`
  pattern. The classifier is also emittable as ExtendScript JS so the same
  logic runs inside Illustrator.
- **`explain-layer` command** — quick diagnostic.
- CHANGELOG, POSTMORTEM, ROADMAP — see `docs/`.

### Changed
- **Default for `.ai` is now `apply-jsx`, not `apply`.** v0.1's pikepdf
  approach stripped `/PieceInfo` and flattened layers — wrong default for
  Rhino-export workflows.
- Auto-classifier no longer puts dominant texture colors in mid-tiers
  (was: count-weighted bucketing → over-merged). Now buckets by color-index
  in luminance order.

## [0.1.0] — 2026-04-29

Initial release. `inspect` + `apply` (pikepdf, color-classify) +
auto-by-luminance classifier + section/plan/elevation/detail presets +
Claude Code skill.
