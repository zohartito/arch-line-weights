# Reviewer Packet — Current-Head Landing Rehearsal (2026-06-01)

**Audience:** Human merging the endgame stack. **Not** posting clearance.

## Rehearsal artifact

| Item | Value |
|------|--------|
| Branch | `codex/tmp-current-head-landing-rehearsal-20260601` |
| Base | `origin/main` @ `bdf23c2` |
| Head | `5ac29aa` (after full stack merge) |
| Prior archival rehearsal | `codex/tmp-integration-rehearsal-20260601b` @ `d457acb` — **stale** (predates #37 `f281604` landing docs, console NO-GO labels, proof-check `report.json` regression) |

## Current PR heads (open)

| PR | Branch | Head (approx) | CI | Merge? |
|----|--------|---------------|-----|--------|
| **#37** | `codex/open-issue-verification-core` | `f281604` | green | **Yes — land first** |
| **#39** | `codex/issue23-single-layer-cleanup` | `aab7db9` | green | After #37 |
| **#38** | `codex/issue20-entourage-assets` | `4153778` | green | After #39 |
| **#42** | `codex/issue30-concrete-base-synthetic-regression` | `1719223` | green | After #38 (see #42 notes) |
| **#34** | `w2-verification-fixture-sourcing` | `911bcd5` | green | After #42 (docs) |
| **#41** | `codex/endgame-delivery-ledger` | `6362d79` | green | Last (docs) |

## Close without merge (superseded)

| PR | Branch | Verification vs rehearsal `5ac29aa` | Recommendation |
|----|--------|-------------------------------------|----------------|
| **#36** | `v0.2-verification-core` | 0 commits ahead; layout-jsx/bridge identical after #37 `7794528` | **Close** |
| **#40** | `codex/issue19-diagnose-report` | Diagnose landed on #37 as `c2c1500`; #37 adds `posting_reminder` | **Close** |
| **#44** | `codex/webapp-designer-console-prototype` | 0 commits ahead; console on #37 | **Close** |
| **#45** | `codex/quarantine-day1-proof-assets` | 0 commits ahead; quarantine on #37 | **Close** |

Do **not** cherry-pick from these unless a future audit finds a regression-only test missing from #37 (none found in this rehearsal).

## Merge order (human GitHub merges)

1. **#37** → `main`
2. Close **#36, #40, #44, #45** (no merge)
3. **#39** → `main`
4. **#38** → `main`
5. **#42** → `main` (resolve `make2d_completion.py` + `poche.py` per below)
6. **#34** → `main` (`docs/ROADMAP.md` combined NO-GO + W2 gate)
7. **#41** → `main` (prefer #37 landing/merge docs; take #41 `endgame-delivery-plan` if not already on main)

## Rehearsal merge log (local only)

| Step | Result | Conflicts | Resolution |
|------|--------|-----------|------------|
| #37 | Fast-forward to `f281604` | none | — |
| #39 | Merge commit `e7dbf62` | `cli.py`, `README.md` | Both imports; keep input matrix + cleanup section |
| #38 | Merge `3997109` | none | — |
| #42 | Cherry-pick `1719223` + reconcile `ac263ef` | `test_apply_saas_poche.py` | Port tests; slim `TEC_CONCRETE_BASE` rules; full `polygonize_dump` helper path |
| #34 | Merge `c133f41` | `docs/ROADMAP.md` | Combined launch gate + proof posture; #37 as stack base |
| #41 | Merge `5ac29aa` | README, RELEASE, SHIP, ROADMAP, landing plan, launch-safety | Keep rehearsal (#37) surfaces; add `endgame-delivery-plan` from #41 |

## #42 risk focus

**Git note:** Plain `git merge` of #42 reported “already up to date” because `1719223` is an ancestor of the merged stack — but #37 had **diverged** poche/`make2d_completion` after that point. Rehearsal **re-applied** #42 via cherry-pick + manual reconciliation.

**Conflicts / resolution (production merge):**

| File | Keep from #37 | Port from #42 |
|------|---------------|---------------|
| `make2d_completion.py` | Do not blanket-block all `TEC_CONCRETE_BASE` large candidates | Slim strip rules (`area ≤ 6500`, aspect, shared-length gates) |
| `poche.py` | `input_format` import, launch-safe paths | `_uses_jsx_structural_helpers`, `polygonize_dump` helper wiring, JSX `shouldDump` for Curves/Tangents, fragment-gap bridges, helper-before-bridge rung |
| `run_report.py` | Foundation/concrete **no-go** limitations, W5/W7 visual gates | — |
| `tests/test_apply_saas_poche.py` | Existing #37 tests | Polygonize + slim-concrete regression tests |

**NO-GO preserved:**

- Synthetic / manifest proof does **not** close #30.
- `public_safe` remains false without explicit W5/W7 acceptance metadata.
- Console `posting_clearance` stays **NO-GO** on public summary.
- Inferred concrete/foundation fills still require W5/W7 visual acceptance in reports.

## Tests after each merge (from rehearsal)

```bash
export PYTHONPATH=src

# After #37
.venv/bin/python -m pytest --ignore=tests/test_hatch_v05.py -q
.venv/bin/python -m pytest webapp/tests -q
.venv/bin/python -m pytest tests/test_launch_safety_docs.py tests/test_cli_proof_check.py -q

# After #39
.venv/bin/python -m pytest tests/test_cleanup.py -q

# After #38
.venv/bin/python -m pytest tests/test_entourage.py -q

# After #42
.venv/bin/python -m pytest tests/test_apply_saas_poche.py tests/test_architectural_mode.py tests/test_run_report.py -q

# After #34 / #41
.venv/bin/python -m pytest tests/test_launch_safety_docs.py -q
```

**Full stack (rehearsal head `5ac29aa`):** 652 passed, 7 skipped, 1 xfailed; webapp 43 passed; ruff clean; frontend check/build pass.

## Manual human review (cannot be automated)

- Private USC Make2D drawing: run `docs/how-to/private-studio-dogfood-runbook.md` locally (no assets in git).
- W5/W7 visual acceptance on foundation/concrete inferred fills — only human can accept a **public-safe** packet.
- Illustrator smoke-check on real studio export (PDF preview not authoritative).

## Still blocked / NO-GO

- **Do not merge** this rehearsal branch to `main` as one PR.
- **Do not close** #29 or #30.
- **Do not post** public proof or claim App Store / Windows desktop / Rhino plugin / Illustrator panel readiness.
- Posting/public proof: **NO-GO** until W5/W7 explicitly accepts a public-safe packet.
- Synthetic proof does **not** close #30.
- Private USC regression stays **private**.

## Related docs

- `docs/research/pr-overlap-audit-2026-06-01.md`
- `docs/research/merge-readiness-packet-2026-06-01.md`
- `docs/research/human-landing-plan-2026-06-01.md`
- `docs/how-to/private-studio-dogfood-runbook.md`
