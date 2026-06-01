# Human Landing Plan — 2026-06-01

Engineering control doc for **how to land** the arch-line-weights endgame stack after
integration rehearsal `codex/tmp-integration-rehearsal-20260601b` (`d457acb`). This is
not posting clearance and not a merge instruction for agents.

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

| Role | Branch | Typical head (2026-06-01) | PR |
|------|--------|---------------------------|-----|
| Verification core | `codex/open-issue-verification-core` | `c2c1500`+ | **#37** draft |
| Verification core (reports/bridge) | `v0.2-verification-core` | `8f00e18` | **#36** draft |
| Endgame ledger | `codex/endgame-delivery-ledger` | `a86d268` | **#41** draft |
| Archival full stack | `codex/tmp-integration-rehearsal-20260601b` | `d457acb` | **none** (no merge) |
| W2 research | `w2-verification-fixture-sourcing` | — | **#34** |
| Cleanup | `codex/issue23-single-layer-cleanup` | — | **#39** |
| Diagnose | `codex/issue19-diagnose-report` | — | **#40** (may overlap #37 `diagnose`) |
| Entourage | `codex/issue20-entourage-assets` | — | **#42** |
| Concrete synthetic | `codex/issue30-concrete-base-synthetic-regression` | — | **#38** |
| Day-1 quarantine | `codex/quarantine-day1-proof-assets` | — | **#45** (largely on #37) |
| Designer console (old) | `codex/webapp-designer-console-prototype` | — | **#44** superseded by **#37** |

Rehearsal verified: **652** pytest (excl. hatch v05), **36** webapp tests, launch-safety **4**,
ruff clean, frontend check/build pass.

## Recommended human merge sequence

Land in **waves** so proof/console safety stays on the bottom of the stack.

### Wave 1 — Safety + proof truth (land first)

1. **#37** `codex/open-issue-verification-core` — input diagnostics, proof harness,
   `arch-lw proof-check`, designer console, W5/W7 NO-GO handoff, launch-safety scans,
   PR #45 quarantine on branch.
2. **#45** — close as superseded if #37 already contains quarantine; else merge quarantine-only.

**Human review focus:** `tests/test_proof.py`, `tests/test_cli_proof_check.py`,
`tests/test_launch_safety_docs.py`, `webapp/backend/console.py`, `src/arch_line_weights/proof.py`.

### Wave 2 — Report contracts + bridge (stack on Wave 1)

3. **#36** `v0.2-verification-core` — `layout_jsx`, `bridge_rhino_ai`, expanded
   `run_report`, Rhino integration scripts.

**Known conflicts (resolved in rehearsal `a482934`):** `cli.py`, `run_report.py`,
`test_run_report.py` — keep #37 proof-check + #36 report/bridge surfaces.

### Wave 3 — Focused features (stack on Wave 2)

4. **#39** cleanup — `cleanup.py`, `arch-lw cleanup` (conservative single-layer tool).
5. **#40** diagnose — skip if #37 already ships `diagnose_report.py` / `arch-lw diagnose`.
6. **#38** issue30 — synthetic concrete regression; **caveated only**, never closes #30.
7. **#42** entourage — `entourage.py` + tests (presentation layer, not proof clearance).
8. **#34** w2 — docs/RETROSPECTIVE/fixture-sourcing research; **ROADMAP** conflict resolved in rehearsal.

### Wave 4 — Control docs (last)

9. **#41** endgame ledger — `endgame-delivery-plan-2026-06-01.md` + checkpoints only.

## Superseded / duplicate work

| Item | Verdict |
|------|---------|
| **#44** designer console prototype | **Superseded** by console on **#37** |
| **#45** quarantine | **Superseded** on **#37** after `30b6951` / rehearsal `e8a5ac4` |
| **#40** vs #37 `diagnose` | **Duplicate** — merge one; prefer #37 if identical |
| Rehearsal branch | **Archival** — proves integration; do not merge wholesale to `main` |

## Rehearsal-only vs #37 delta (do not blind cherry-pick)

Code/docs present in rehearsal `d457acb` but **not** on #37 `c2c1500` (classify before port):

| Delta | Classification |
|-------|----------------|
| `layout_jsx.py`, `test_layout_jsx.py` | **Stacked PR #36** |
| `bridge_rhino_ai.py`, `test_bridge_rhino_ai.py`, Rhino integrations | **Stacked PR #36** |
| `cleanup.py`, `test_cleanup.py` | **Stacked PR #39** |
| `entourage.py`, `test_entourage.py` | **Stacked PR #42** |
| `make2d_completion.py` / `poche.py` issue30 tweaks | **Stacked PR #38** |
| `RETROSPECTIVE.md`, w2 research, ROADMAP merge | **Docs — #34 / rehearsal** |
| `endgame-delivery-plan-2026-06-01.md` | **Docs — #41** |
| Rehearsal safety commits on helper scripts | **Ported** to #37 per handoff (`63f451e`, `49f4932`) |
| `diagnose_report.py` on #37 `c2c1500` | **On #37** — reconcile with #40 before merge |

**Must not port:** private fixture binaries, raw proof images, local path examples, any
change that weakens validators or sets `public_clearance` / `posting_ready` to GO without
W5/W7 acceptance.

## Human review checklist (before each merge)

- [ ] CI green on the PR branch (pytest + ruff; webapp if touched).
- [ ] `pytest tests/test_launch_safety_docs.py` — no retired Day-1 / private path leaks.
- [ ] `arch-lw proof-check` tests pass; no false-pass on missing output / unchanged renders / `no_go` reports.
- [ ] Console export: handoff JSON/MD in zip; `public_safe: false`; `posting_clearance: NO-GO`.
- [ ] No private paths in tracked README, announce, how-to, reference, or handoff docs.
- [ ] Issue comments: only path-free evidence; do **not** close #29/#30 from synthetic proof.
- [ ] PR stays **draft** until explicit human ready-to-merge decision.

## After landing (still not “launch”)

- Run private USC regression **locally**; keep artifacts out of git.
- W5/W7 review of real packets — record acceptance only in approved private workflow first.
- Public posting remains **NO-GO** until that acceptance is explicitly for a **public-safe** packet.
