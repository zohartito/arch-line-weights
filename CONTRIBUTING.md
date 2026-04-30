# Contributing to arch-line-weights

Thank you for considering a contribution. This document covers how to set up,
what we're looking for, and how to ship a PR.

## Setup

```bash
git clone https://github.com/zohartito/arch-line-weights
cd arch-line-weights
pip install -e ".[dev]"
pytest
```

Optional but recommended:

```bash
pre-commit install   # ruff + format hooks (if you've installed pre-commit)
```

You'll need Python 3.11+. For the `apply-jsx` and `poche` commands you also
need Adobe Illustrator (currently 2024–2026 are tested) on macOS.

## What we'd like help with

Roadmap items in `docs/ROADMAP.md` are tagged by phase. The currently-open
buckets:

- **Per-source classifiers** — AutoCAD, Vectorworks, ArchiCAD, Revit-via-DWG
  (Rhino works; the others have flat OCGs and need their own handlers — see
  `docs/research/disconnected-loops.md` and `multi-format` research transcript)
- **`__POCHE_CLOSE__` workflow polish** — e.g. a `--inspect` mode for
  `arch-lw poche` that shows confidence per layer without writing the file
- **Material hatching extensions** — more recipes (slate, terrazzo, tile),
  loading AutoCAD `acad.pat` via `ezdxf`
- **Tests on real-world files** — if you have a Rhino-export with weird
  layer naming conventions and want to share, open an issue
- **Documentation / examples** — especially before/after PNGs of real work

## Style

- `ruff check src/ tests/` should be clean
- `ruff format src/ tests/` should be a no-op
- `pytest` should be green
- Type hints encouraged; not yet strict (mypy is configured non-strict)

## Pull requests

1. Open an issue first for non-trivial changes — saves effort if the design
   needs discussion
2. Branch from `main`, name it `<topic>-<short-desc>` (e.g. `material-hatch-slate`)
3. Add tests for new functionality
4. Update `CHANGELOG.md` under `## [Unreleased]`
5. PR with a description that explains the *why*, not just the *what*

CI runs on every PR (Linux + macOS × Python 3.11/12/13). Both must pass.

## Decision-making

This is a personal project that became open-source. Maintainer decisions
prioritize:

1. **Layer fidelity** — never destroy user work
2. **Reproducibility** — same input + same flags = same output
3. **Honesty** — confidence-scored output beats silently-wrong output
4. **Architectural correctness** — when in doubt, defer to Ramsey/Sleeper /
   Ching / NCS conventions

When these conflict, layer fidelity wins.

## Code of conduct

See `CODE_OF_CONDUCT.md`. Short version: be kind, attack ideas not people,
the maintainer reserves the right to enforce.

## License

By contributing you agree your contributions are licensed under MIT, the
project's license.
