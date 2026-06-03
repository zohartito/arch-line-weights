# Current-Head Rehearsal - e923721 (2026-06-03)

## STATE

This is a preservation record for the current-head rehearsal from PR #37 at
`e923721`. It is not a merge request to land the rehearsal wholesale.

No public proof posting is cleared. Posting/public proof is NO-GO. #29 and #30
remain open. Synthetic proof does not close #30. Private USC regression stays
private.

## INPUT STACK

Rehearsed order:

1. `origin/main`
2. #37, `origin/codex/open-issue-verification-core`, head `e923721`
3. #39
4. #38
5. #42
6. #34
7. #41

## CONFLICT FILES AND RESOLUTIONS

- #37 merged cleanly from the current head.
- #39 conflicted in `README.md` and `src/arch_line_weights/cli.py`.
  Resolution kept the #37 input matrix and imports, then added the cleanup
  command surface and cleanup documentation.
- #38 merged cleanly.
- #42 was already in #37 ancestry, so a normal post-#37 merge was a no-op.
  Useful #42 deltas still had to be reconciled manually because current #37
  overwrote portions of them. Reconciled deltas covered slim concrete base
  completion, fragmented concrete edge recovery, JSX structural helpers, and
  helper-count evidence bookkeeping.
- #34 conflicted in `docs/ROADMAP.md`. Resolution kept #37 as the spine and
  preserved the NO-GO/#29/#30 gating language.
- #41 conflicted in `README.md`, `RELEASE_NOTES.md`, `SHIP_CHECKLIST.md`,
  `docs/ROADMAP.md`, `docs/research/human-landing-plan-2026-06-01.md`, and
  `tests/test_launch_safety_docs.py`. Resolution kept newer #37/#34 public
  surfaces, added the endgame delivery research plan, and extended launch-safety
  coverage for that research doc.

No conflict markers remained after the final reconciliation.

## SUPERSEDED PR CHECK

- #36 is safe to close without merge after #37. Its patch is absorbed by the
  current spine.
- #44 is safe to close without merge after #37. Its webapp cockpit work is
  absorbed by the current spine.
- #45 is safe to close without merge after #37. Its quarantined proof handling
  is absorbed and no public proof asset path is introduced.
- #40 is safe to close without merge after #37, with one caveat: a direct cherry
  comparison still shows the original diagnose commit because current #37 carries
  a hardened superset rather than the exact original patch.

## VERIFICATION

Commands run in the rehearsal worktree:

- `PYTHONPATH=src .venv/bin/python -m pytest tests/test_launch_safety_docs.py tests/test_cleanup.py tests/test_entourage.py tests/test_architectural_mode.py tests/test_apply_saas_poche.py tests/test_run_report.py tests/test_input_format.py tests/test_cli_input_preflight.py tests/test_diagnose_report.py -q`
- `PYTHONPATH=src .venv/bin/python -m compileall -q src/arch_line_weights`
- `git diff --check`
- `rg -n "^(<<<<<<<|=======$|>>>>>>>)" .`

Result: `147 passed, 5 warnings`.

## BLOCKED CHECKS

- `tests/test_cli_proof_check.py` collected but failed because `yaml`/PyYAML is
  not installed in the available environment.
- `webapp/tests/test_console_routes.py` did not collect because `fastapi` is not
  installed in the available environment.
- Ruff was not available in the available environment.

## FINAL VERDICT

Green-with-caveats.

The practical landing caveat is #42: after #37, a normal #42 merge is a no-op,
but useful #42 evidence/fix deltas still need to be rebuilt, rebased, or
cherry-picked into the landing stack.

## EXACT NEXT ACTION

Use #37 as the canonical integration spine. Land useful follow-on work after
#37 in this order unless a fresh rehearsal changes the result: #39, #38, rebuilt
#42 deltas, #34, then #41. Keep posting/public proof blocked until real #30
evidence clears it.
