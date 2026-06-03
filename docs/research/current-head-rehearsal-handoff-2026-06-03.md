# Current-Head Rehearsal Handoff - 2026-06-03

This is an archival engineering handoff for the current-head landing rehearsal.
It is not posting clearance, not a merge instruction for agents, and not a claim
that #29 or #30 are fixed.

## Scope

Rehearsed the requested stack from `origin/main`:

1. #37 `codex/open-issue-verification-core` at `e923721be00f7d99719db87068d8c24f1bce0a51`
2. #39 `codex/issue23-single-layer-cleanup` at `aab7db9e0362df9b370d69e8c99b63aa6bb477eb`
3. #38 `codex/issue20-entourage-assets` at `4153778d4e2c67e9c0b18b1ebe421df29fa38bbf`
4. #42 `codex/issue30-concrete-base-synthetic-regression` at `1719223ccf6bad562d9ecd93d4dbf9a96ebb6347`
5. #34 `w2-verification-fixture-sourcing` at `911bcd58acfdd18d358a0f0ac21fb6febfc075f8`
6. #41 `codex/endgame-delivery-ledger` at `6362d7993c24554f87fb50bb424b8c3088ef175b`

Final local rehearsal head before this handoff commit:
`3e5341fff51b8387717bd89d376ec364852777e8`.

## Stack Result

- #37 merged first.
- #39 merged with conflicts, resolved by preserving #37 input/proof guardrails
  and adding #39 cleanup docs/imports.
- #38 merged cleanly.
- #42 was already contained by ancestry at this rehearsal head. Treat that as
  ancestry evidence only; future rehearsals must still run the concrete-helper
  behavior tests directly.
- #34 merged with a `docs/ROADMAP.md` conflict, resolved toward #37's NO-GO and
  W5/W7 proof posture while preserving #34 research context.
- #41 merged last with documentation and launch-safety test conflicts, resolved
  toward the current #37/#34 landing map and preserving #41's endgame ledger doc.

## Conflict Files

- #39: `README.md`, `src/arch_line_weights/cli.py`
- #34: `docs/ROADMAP.md`
- #41: `README.md`, `RELEASE_NOTES.md`, `SHIP_CHECKLIST.md`,
  `docs/ROADMAP.md`, `docs/research/human-landing-plan-2026-06-01.md`,
  `tests/test_launch_safety_docs.py`

## Verification

- Full pytest excluding known hatch test:
  - Command: `pytest --ignore=tests/test_hatch_v05.py -q -p no:cacheprovider`
  - Result: failed only on missing PyYAML-dependent proof manifest tests:
    9 failed, 635 passed, 7 skipped, 1 xfailed.
- Non-PyYAML pytest subset:
  - Command: `pytest --ignore=tests/test_hatch_v05.py --ignore=tests/test_cli_proof_check.py --ignore=tests/test_proof.py -q -p no:cacheprovider`
  - Result: 602 passed, 7 skipped, 1 xfailed.
- Webapp tests:
  - Command: `pytest webapp/tests -q -p no:cacheprovider`
  - Result: blocked by missing `fastapi`.
- Ruff:
  - Command: `python -m ruff check src/ tests/ webapp/backend/ webapp/tests/`
  - Result: blocked by missing `ruff`.
- Whitespace:
  - Command: `git diff --check`
  - Result: passed.
- Launch-safety path scan:
  - Command: `pytest tests/test_launch_safety_docs.py -q -p no:cacheprovider`
  - Result: 4 passed.

## Guardrails

- #29 remains open.
- #30 remains open.
- Posting/public proof remains NO-GO.
- Synthetic proof does not close #30.
- Private regression evidence stays private and out of git.
- This rehearsal branch must not be merged wholesale without human review.

## Next Action

When W3 publishes a newer #37 head, rerun the rehearsal from that new SHA:

`origin/main -> updated #37 -> #39 -> #38 -> #42 -> #34 -> #41`

Do not accept "already up to date" as sufficient for #42 in that future run.
Run the concrete-helper behavior tests directly and verify the preservation
plan before making a human-gated landing recommendation.
