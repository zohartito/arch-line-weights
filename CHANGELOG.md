# Changelog

All notable changes to this project are documented here. Format loosely follows
[Keep a Changelog](https://keepachangelog.com).

## [0.6.0] — 2026-04-30

### Added
- **`arch_line_weights.bridge` module** — auto-bridge inference. For
  near-but-not-touching segment soup (typical Make2D output), greedy
  nearest-endpoint pairing inserts short bridge segments to close gaps,
  then re-runs `linemerge + polygonize`. Replaces a lossy
  `concave_hull` fallback with topology-correct polygon recovery for most
  disconnected layers. STRtree-accelerated, O(n log n).
- **`arch-lw poche` rescue ladder updated** to:
  1. bare linemerge (conf 1.00)
  2. snap-tolerance sweep (conf 0.7–0.95)
  3. **auto-bridge inference** (conf 0.7–0.92) ← new
  4. concave_hull fallback (conf 0.55)
  5. bbox last resort (conf 0.30)
- **Full MkDocs Material documentation site** in `docs/` with Diátaxis structure:
  tutorial, 5 how-to guides, CLI + Python API reference, 3 explanation pages.
  Auto-deploys to GitHub Pages on push to main and on tag via `.github/workflows/docs.yml`.
- **Launch / announcement content** in `docs/announce/`: Show HN draft,
  r/architecture post, r/Python Showcase Saturday post, blog post outline.
- **`CONTRIBUTING.md`** + **`CODE_OF_CONDUCT.md`** for incoming PRs.
- **`pyproject.toml` converted to hatchling + hatch-vcs** — version derived
  from git tags. PEP 639 `license` + `license-files`. SPDX-compliant.
  `[docs]` extra installs MkDocs Material + mkdocstrings.
- **Build verified locally**: `python -m build` produces sdist + wheel,
  `twine check --strict` passes both, wheel installs cleanly in a fresh
  venv. v1.0 PyPI publish is unblocked code-side; only PyPI account +
  Trusted Publishing setup remain.

### Improved
- Reference-run results on USC ARCH 202B section drawing:
  - **v0.5**: 14 / 6 / 1 (clean / imperfect / failed)
  - **v0.6**: **18 / 2 / 1** — auto-bridge rescued TEC_FOUNDATION,
    TEC_CONCRETE_BASE, 03d_WINDOW_ALUM_FRAME, TEC_STAIRS, and partially
    11_CU_CORR_SOLID_OPAQUE. The 7 imperfect layers from v0.5 are now down
    to 2 imperfect + 1 failed.

### Tests
- 26/26 passing (was 23). Added 3 bridge-specific tests.

## [0.5.0] — 2026-04-30

### Added
- **`arch_line_weights.hatch` module** — material-specific architectural hatch
  generation. 14 material recipes (concrete, CLT cross-grain, solid timber,
  steel, mineral wool insulation, rigid insulation, earth, brick, glass,
  gypsum, aluminum, plus solid-fill aliases). Built on shapely + numpy +
  Bridson Poisson-disk sampler.
- **`arch-lw poche --style material`** — generates per-material hatch
  geometry on top of solid black fills. `--scale` parameter selects drawing
  scale (0.02 = 1:50, 0.01 = 1:100).
- **`arch-lw preview` CLI subcommand** — wraps the existing preview module.
  Three modes: `side-by-side`, `tier-overlay`, `diff`. Optional
  `--ghostscript` flag for sub-0.25pt hairline accuracy.
- **GitHub Actions CI + release workflows**, issue templates, SECURITY.md.
- **23 tests** total.

### Fixed
- `poisson_disk` caps generated sample count and enlarges `min_dist`
  proportionally to prevent hangs on pathologically-large polygons.

## [0.4.0] — 2026-04-30

### Added
- `arch-lw poche` CLI command (full pipeline in one shot).
- `arch_line_weights.poche` module with confidence scoring and
  `__POCHE_CLOSE__` user-marked closing-layer support.
- `arch_line_weights.preview` module.
- `arch_line_weights.presets.select_preset()` — ISO 128 standards-aligned
  ladders with `--scale` + `--for-print` flags.
- `integrations/rhino/` — GhPython component, Eto toolbar button,
  pre-export tagger.

## [0.3.0-alpha] — 2026-04-29

Poché pipeline scripts (`scripts/poche/`) — first working two-stage approach
+ comprehensive POSTMORTEM.

## [0.2.0] — 2026-04-29

`apply-jsx` command (layer-preserving), `arch_line_weights.layer_classify`
semantic classifier, `explain-layer` command. Default for `.ai` is now
`apply-jsx`.

## [0.1.0] — 2026-04-29

Initial release. `inspect` + `apply` (pikepdf, color-classify) +
auto-by-luminance classifier + section/plan/elevation/detail presets +
Claude Code skill.
