# PR Overlap Audit — 2026-06-01

Audit base: `codex/open-issue-verification-core` at `7794528` (includes merge of
`v0.2-verification-core` / PR **#36**). Compare with open stacked PRs. **No merges
performed by this doc.**

## Overlap table

| PR | Branch | vs #37 `7794528` | Classification | Recommendation |
|----|--------|------------------|----------------|----------------|
| **#37** | `codex/open-issue-verification-core` | — | Canonical stack base | Land first (draft until human ready) |
| **#36** | `v0.2-verification-core` | `layout_jsx`, `bridge_rhino_ai`, report expansions: **0-line diff** vs #37 after merge | **Duplicate** (absorbed) | **Close #36 without separate merge** after #37 lands; verify CI archive only |
| **#40** | `codex/issue19-diagnose-report` | `diagnose_report.py`, `test_diagnose_report.py`: **identical**; landed on #37 as `c2c1500` | **Duplicate** | **Close #40 without merge** |
| **#39** | `codex/issue23-single-layer-cleanup` | `cleanup.py` **missing** on #37; `cli.py` differs (+proof-check, diagnose, console) | **Complementary** | Merge **after #37**; expect `cli.py` conflict — keep #37 commands + add `cleanup` |
| **#38** | `codex/issue20-entourage-assets` | `entourage.py` **missing** on #37 | **Complementary** | Merge **after #37** (+ #39 if desired); usually clean |
| **#42** | `codex/issue30-concrete-base-synthetic-regression` | `make2d_completion.py` **differs** (stricter concrete guard on #37); **6 tests** only on #42 | **Partial overlap** | Merge **after #37** for tests + algorithm tweaks; **resolve** `make2d_completion` — keep #37 launch-blocking + port regression tests |
| **#34** | `w2-verification-fixture-sourcing` | Mostly docs (`RETROSPECTIVE`, fixture research); not ancestor | **Complementary (docs)** | Merge **after** code stack; resolve `docs/ROADMAP.md` — use combined NO-GO posture |
| **#41** | `codex/endgame-delivery-ledger` | Control docs only; `human-landing-plan` mirrored at `6362d79` | **Complementary (docs)** | Merge **last** |
| **#45** | quarantine (if open) | Quarantine largely on #37 | **Duplicate** | Close when #37 lands |
| **#44** | designer console prototype | Superseded by #37 webapp | **Duplicate** | Close without merge |

## #37 vs #40 diagnose (detail)

| Artifact | #40 branch | #37 `7794528` |
|----------|------------|---------------|
| `src/arch_line_weights/diagnose_report.py` | same | same |
| `tests/test_diagnose_report.py` | same | same |
| `arch-lw diagnose` in `cli.py` | present on older base | present (+ proof-check, layout-jsx, etc.) |
| `docs/reference/cli.md` | diagnose section | diagnose section |

**Verdict:** #40 is fully superseded. Do not merge #40 on top of #37.

## #37 vs #36 (detail)

Merge commit `7794528` on #37 already integrates #36. `layout_jsx.py` and
`bridge_rhino_ai.py` match `v0.2-verification-core` head.

**Verdict:** Treat #37 as **#36 + verification core**. Close #36 to avoid double-merge.

## #37 vs #42 issue30 (detail)

#37 blocks broad `TEC_CONCRETE_BASE` large-candidate repairs; #42 adds targeted
concrete strip recovery rules and synthetic regression tests (`test_polygonize_dump_*`,
`test_structural_completion_accepts_slim_concrete_base_*`).

**Verdict:** **Complementary** — not duplicate. Merge #42 after #37 with manual
`make2d_completion.py` resolution and re-run `tests/test_apply_saas_poche.py`.

## Unsafe / stale

- None of the stacked PRs should re-introduce retired Day-1 committed proof images or private paths.
- Do not merge rehearsal `d457acb` wholesale to `main`.
- Synthetic / console proof **does not** close #30.
