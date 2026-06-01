# Merge-Readiness Packet — 2026-06-01

Terse checklist for a human merging the endgame stack. **Not posting clearance.**

## Preconditions

- #29 and #30 stay **open**.
- Posting/public proof **NO-GO** until W5/W7 records acceptance on a **public-safe** packet.
- No private assets or local paths in git.

## Merge order (updated — #36 already on #37)

| Step | PR | Action |
|------|-----|--------|
| 1 | **#37** | Merge to `main` (or integration branch) |
| 2 | — | Close **#36**, **#40**, **#44**, **#45** as superseded (no merge) |
| 3 | **#39** | Merge cleanup |
| 4 | **#38** | Merge entourage |
| 5 | **#42** | Merge issue30 synthetic regression (resolve `make2d_completion.py`) |
| 6 | **#34** | Merge w2 docs |
| 7 | **#41** | Merge endgame ledger docs |

## Expected conflicts and resolutions

### Already resolved on #37

| PR pair | Files | Resolution used in rehearsal |
|---------|-------|------------------------------|
| #36 → #37 | `cli.py`, `run_report.py`, `test_run_report.py` | Keep proof-check, diagnose, console on `cli.py`; keep #36 layout-jsx + bridge reports |

### Step 3 — #39 cleanup

| File | Resolution |
|------|------------|
| `cli.py` | Keep all #37 subcommands; add `cleanup` command/import from #39 |
| `docs/reference/cli.md` | Add `arch-lw cleanup` section (see rehearsal `d457acb`) |
| `README.md` | Keep #37 proof posture; add cleanup paragraph if #39 adds one |

### Step 5 — #42 issue30

| File | Resolution |
|------|------------|
| `src/arch_line_weights/make2d_completion.py` | Keep #37 `TEC_CONCRETE_BASE` guard in `_large_candidate_is_plausible`; port #42 strip-recovery branch + tests |
| `src/arch_line_weights/run_report.py` | Keep #37 foundation/concrete **launch-blocking** limitations |
| `tests/test_apply_saas_poche.py` | Take #42 new tests; ensure existing #37 tests still pass |

### Step 6 — #34 w2

| File | Resolution |
|------|------------|
| `docs/ROADMAP.md` | Combine NO-GO proof posture + verifier gate + #37 PR references (see landing plan) |

## Tests after each merge

```bash
export PYTHONPATH=src

# After step 1 (#37 only — current head)
.venv/bin/python -m pytest --ignore=tests/test_hatch_v05.py -q
.venv/bin/python -m pytest webapp/tests/test_console_routes.py webapp/tests/test_routes.py webapp/tests/test_dev_console.py -q
.venv/bin/python -m pytest tests/test_launch_safety_docs.py tests/test_cli_proof_check.py tests/test_proof.py -q
.venv/bin/ruff check src/ tests/ webapp/backend/ webapp/tests/

# After step 3 (#39)
.venv/bin/python -m pytest tests/test_cleanup.py tests/test_cli_proof_check.py -q

# After step 4 (#38)
.venv/bin/python -m pytest tests/test_entourage.py -q

# After step 5 (#42)
.venv/bin/python -m pytest tests/test_apply_saas_poche.py tests/test_architectural_mode.py tests/test_run_report.py -q

# After steps 6–7 (docs only)
.venv/bin/python -m pytest tests/test_launch_safety_docs.py -q
git diff --check
```

Frontend (if webapp touched):

```bash
npm --prefix webapp/frontend run check
npm --prefix webapp/frontend run build
```

## PRs to close without merge

| PR | Reason |
|----|--------|
| **#36** | Absorbed by #37 (`7794528`) |
| **#40** | Diagnose identical to #37 |
| **#44** | Console on #37 |
| **#45** | Quarantine on #37 |

## Archival reference

`codex/tmp-integration-rehearsal-20260601b` @ `d457acb` — full stack proof; **do not merge** as one PR.
