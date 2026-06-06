# Human Landing Plan — 2026-06-01

Engineering control doc for **how to land** the arch-line-weights endgame stack. This is
not posting clearance and not a merge instruction for agents.

**Companion docs:**

- **Reviewer packet (current-head rehearsal):** `docs/research/reviewer-packet-current-head-2026-06-01.md`
- Overlap audit: `docs/research/pr-overlap-audit-2026-06-01.md`
- Merge checklist: `docs/research/merge-readiness-packet-2026-06-01.md`
- Private dogfood (path-free): `docs/how-to/private-studio-dogfood-runbook.md`

## Non-negotiable gates (repeat every review)

- **No agent PR merges** — humans merge after review.
- **#29** and **#30** stay **open** until real W5/W7 public-proof acceptance.
- **Posting/public proof: NO-GO** unless W5/W7 explicitly records acceptance on a
  public-safe packet.
- **Synthetic proof does not close #30.**
- **Private USC regression stays private** — no private drawings, screenshots, PDFs,
  raw reports, proof assets, or machine paths in git.
- **Do not claim** App Store, Windows desktop, Rhino plugin, or Illustrator panel readiness.

## Branch heads (inspect with `git fetch` before acting)

| Role | Branch | PR | Notes |
|------|--------|-----|-------|
| **Stack base** | `codex/open-issue-verification-core` | **#37** | Includes **#36** via merge `7794528` |
| Reports/bridge (absorbed) | `v0.2-verification-core` | **#36** | Close after #37 — duplicate |
| Cleanup | `codex/issue23-single-layer-cleanup` | **#39** | Merge after #37 |
| Diagnose (duplicate) | `codex/issue19-diagnose-report` | **#40** | **Close** — on #37 since `c2c1500` |
| Entourage | `codex/issue20-entourage-assets` | **#38** | Merge after #37 |
| Issue30 synthetic | `codex/issue30-concrete-base-synthetic-regression` | **#42** | Merge after #37; resolve `make2d_completion` |
| W2 research | `w2-verification-fixture-sourcing` | **#34** | Docs; merge late |
| Endgame ledger | `codex/endgame-delivery-ledger` | **#41** | Docs; merge last |
| Archival rehearsal | `codex/tmp-integration-rehearsal-20260601b` | none | `d457acb` — do not merge wholesale |
| Quarantine / old console | #45 / #44 | — | Superseded on #37 |

## PR overlap summary

| PR | Verdict |
|----|---------|
| **#37** | **Land first** — proof-check, console, diagnose, #36 layout/bridge, quarantine |
| **#36** | **Duplicate** — already in #37 |
| **#40** | **Duplicate** — diagnose identical to #37 |
| **#39** | **Complementary** — `arch-lw cleanup` |
| **#38** | **Complementary** — entourage |
| **#42** | **Complementary** — concrete regression tests + algorithm delta |
| **#34**, **#41** | **Docs** — after code |
| **#44**, **#45** | **Close** without merge |

See `pr-overlap-audit-2026-06-01.md` for file-level detail.

## Recommended human merge sequence (updated)

### Wave 1 — #37 only

1. Merge **#37** to integration branch / `main`.
2. Close **#36**, **#40**, **#44**, **#45** without separate merges.

**Review focus:** `tests/test_proof.py`, `tests/test_cli_proof_check.py`,
`tests/test_launch_safety_docs.py`, `webapp/backend/console.py`, `tests/test_layout_jsx.py`,
`tests/test_bridge_rhino_ai.py`.

### Wave 2 — Stacked features (on top of landed #37)

3. **#39** cleanup — `cli.py` conflict: keep #37 + add cleanup.
4. **#38** entourage — usually clean.
5. **#42** issue30 — resolve `make2d_completion.py`; keep #37 launch-blocking limits.

### Wave 3 — Docs

6. **#34** w2 — `docs/ROADMAP.md` NO-GO merge.
7. **#41** endgame ledger.

## Human review checklist (before each merge)

- [ ] CI green (pytest + ruff; webapp if touched).
- [ ] `pytest tests/test_launch_safety_docs.py` — no private path / retired proof leaks.
- [ ] `arch-lw proof-check` tests pass.
- [ ] Console: `posting_clearance: NO-GO`; handoff in zip; synthetic does not close #30.
- [ ] `arch-lw diagnose` output includes posting NO-GO reminder.
- [ ] Do **not** close #29/#30 from synthetic proof.
- [ ] PR stays **draft** until human ready-to-merge.

## After landing (still not “launch”)

- Follow `docs/how-to/private-studio-dogfood-runbook.md` for local USC review.
- W5/W7 acceptance on **public-safe** packets only.
- Public posting remains **NO-GO** until then.
