# Changelog

All notable changes to this project are documented here. Format loosely follows
[Keep a Changelog](https://keepachangelog.com).

## [0.2.0] — 2026-04-29

### Added
- **`apply-jsx` command** — layer-preserving apply path. Hands a JSX to Adobe
  Illustrator via `osascript`. Walks the document's leaf layers, derives a
  weight from the layer name using the new semantic classifier, applies it to
  every `pathItem` in that layer, and saves to `<src> HIERARCHY.<ext>`. Slower
  than `apply` (3–15 min for ~340K paths) but **preserves all layers** —
  critical for Rhino-exported drawings where the layer structure encodes
  semantic meaning.
- **`arch_line_weights.layer_classify`** — semantic classifier for OCG layer
  names. Recognises Rhino's `<view>::Visible|Hidden::Curves|ClippingPlaneIntersections::<src>`
  pattern and a long suffix table (`TEC_*`, `CU_*`, `CLT_*`, `SHS_*`, `EPDM_*`,
  `WINDOW_*`, `FLOOR_DATUMS`, etc). The classifier is also emittable as
  ExtendScript JS so the same logic runs inside Illustrator.
- **`explain-layer` command** — quick diagnostic: print the tier+weight a
  given layer name will get.
- **CHANGELOG, POSTMORTEM, ROADMAP** — see `docs/`.

### Changed
- **Default approach for `.ai` is now `apply-jsx`, not `apply`.** The old
  pikepdf path strips `/PieceInfo` (Illustrator's private layer cache), which
  forces Illustrator to re-parse from the PDF stream and **flattens 60+ Rhino
  layers into 1 Illustrator layer**. This was the right speed call but the
  wrong default — users almost always want the layers preserved so they can
  click a layer to refine its weight further. `apply` is still available for
  files where layer fidelity doesn't matter.
- README rewritten to document both modes and when to use which.

### Fixed
- Auto-classifier no longer puts dominant texture colors in mid-tiers due to
  count-weighted bucketing. Now buckets by color-index in luminance order, so
  the lightest colors land in the lightest tier regardless of frequency.

### Known limits
- `apply-jsx` requires Adobe Illustrator 2024+ at the standard install path.
  Path is hard-coded for 2026 but trivially overridable.
- Per-item iteration in ExtendScript is the bottleneck (~500 paths/sec on
  340K-stroke files). `maximumUndoDepth=1` + Outline view brought us from
  exponential degradation to linear, but it's still 11 min for the reference
  drawing. See `docs/POSTMORTEM.md` for the failed alternatives.

## [0.1.0] — 2026-04-29

Initial release. `inspect` + `apply` (pikepdf, color-classify) + auto-by-luminance
classifier + section/plan/elevation/detail presets + Claude Code skill.
