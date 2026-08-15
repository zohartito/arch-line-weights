# arch-line-weights — apply architectural line-weight hierarchy + poché to Rhino-exported .ai/.pdf drawings via the `arch-lw` CLI.

## Run & test
- Install (source): `python -m venv .venv && .venv/bin/python -m pip install -e ".[test]"` — the `[test]` extra pulls PyYAML, without which the proof tests fail. Use `.[dev]` for ruff + mypy + pytest.
- CLI entry point: `.venv/bin/arch-lw --help` (`arch_line_weights.cli:cli`).
- Tests: `pytest` (testpaths = `tests`, `-v` by default). CI runs `pytest --tb=short --ignore=tests/test_hatch_v05.py`.
- Integration tests (need Illustrator, skipped in CI): `pytest -m integration`.
- Live LLM evals (metered Anthropic calls, self-skip by default): `ARCH_LW_LLM_FALLBACK=1 ANTHROPIC_API_KEY=sk-... pytest tests/eval_llm_topology.py -m eval -s`.
- Eval gate (deterministic quality diff vs `benchmarks/ci-baseline.json`): `python scripts/eval_gate.py` (`--update-baseline` to re-record).
- Benchmark suite (writes `benchmarks.json`): `python scripts/benchmark.py`.
- Visual judge (deterministic, no LLM/network): `python scripts/visual_judge.py --after <ai|pdf|png> [--report-json ...]` → JSON scores + `pass`/`review` on 5 axes (false_poche, band_continuity, hierarchy_spread, fixture_weight, tonal_recede); thresholds cite `benchmarks/visual-rubric.md`. `tonal_recede` and `fixture_weight` return `null` (never a guess) when the needed layer/stroke info is unavailable. Self-correcting loop: `python scripts/judge_loop.py <src> --overrides ov.json --run-dir runs/ --baked-after <baked.ai>`. Score the Illustrator-BAKED file — raw `apply-saas` payload edits are not in the live PDF stream (pre-bake reads as weight-flat). Opt-in vision judge (metered): `ARCH_LW_LLM_FALLBACK=1 ANTHROPIC_API_KEY=sk-... pytest tests/eval_visual_judge_llm.py -m eval -s`.

## Structure
- `src/arch_line_weights/` — package; `cli.py` is the Click entry, `apply.py` (pikepdf PDF-stream rewrite), `apply_jsx.py` / `apply_saas.py` (layer-preserving Illustrator paths), `poche.py` / `poche_saas.py`, `tonal_recede.py` (opt-in `--tonal-recede` value ramp for beyond-cut geometry), `llm_topology.py` (opt-in rescue rung).
- `tests/` — offline suite + `eval_llm_topology.py` (scored `pass@k` / `pass^k` / Cohen's kappa eval) + `fixtures/`.
- `scripts/` — `benchmark.py`, `eval_gate.py`, `build_reference_index.py`, `demo_gallery.py`, `visual_judge.py` (deterministic 4-axis scorer), `judge_loop.py` (self-correcting iteration loop), `visual_judge_llm.py` (opt-in vision rung). `benchmarks/visual-rubric.md` is the committed judgment standard both judges read.
- `skills/apply-arch-hierarchy/` + `.claude-plugin/plugin.json` — Claude Code plugin packaging that bundles the skill driving `arch-lw`.
- `examples/` — reproducible synthetic demo (`generate_demo_section.py`); `docs/` — mkdocs site incl. `POSTMORTEM.md`.

## Conventions & danger zones
- `apply` (pikepdf) strips `/PieceInfo` and can FLATTEN Illustrator layers — irreversible. Use `apply-jsx` / `apply-saas` when layers must survive.
- `benchmarks.json` + `eval_gate.py` gate on exact-match metrics (`weights_applied`, `polygons_injected`, `layers_injected`, `layers_targeted`, `skipped`, `error`); output_bytes / seconds are info-only. A quality change must update the baseline in the same commit.
- LLM topology inference (`llm_topology.py`, `[llm]` extra) is an opt-in rescue rung only — never the primary geometry path. `-m eval` tests make real, metered API calls; keep them opt-in.
- Public proof is deliberately NO-GO: do not commit proof images or large real USC `.ai` samples. Only the tiny PDF smoke fixture + synthetic demo ship.
- Line-length 110; ruff select E/F/I/B/UP/RUF/SIM; double-quote format. Requires Python ≥3.11.

## Agent rules (all harnesses)
- Determinism boundary: anything that must be EXACT (money, geometry, safety limits, scoring, pricing) lives in code; the model only orchestrates and judges.
- Keep this file current: when you change how this repo is run, tested, or structured, update AGENTS.md in the same commit. Keep it under ~150 lines.
