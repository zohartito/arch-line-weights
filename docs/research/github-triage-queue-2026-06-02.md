# GitHub Triage Queue - 2026-06-02

This note records the issue/PR state after the current verification-core
checkpoint because GitHub write access is blocked in this session.

## Current Checkpoint

- Active branch: `codex/open-issue-verification-core`
- Active integration PR: #37
- Last pushed head before this note was updated: `8bc429f25251c7e930f850386ac303ec2dad1d99`
- Additional absorbed commits now on the local #37 stack:
  - `aec7674` absorbs #38 / #20, entourage SVG asset generator.
  - `585fcc4` absorbs #39 / #23, conservative single-layer cleanup mode.
  - `52f16c2` absorbs #41, endgame delivery control plan.
  - `58aafb6` and `ed45c89` absorb the #34 W2 fixture-sourcing research doc.
- Local dirty file intentionally left unstaged: `webapp/frontend/vercel.json`
  changes `installCommand` from `npm ci` to `npm install`; do not commit it
  without the Vercel failure context.

## Verification Evidence

Fresh verification on the current branch before this note:

- `.venv/bin/python -m pytest -q` -> `667 passed, 7 skipped, 1 xfailed`
- `.venv/bin/python -m ruff check src tests webapp/backend` -> pass
- `.venv/bin/python -m ruff format --check src tests webapp/backend webapp/tests` -> pass
- `.venv/bin/mkdocs build` -> pass
- `.venv/bin/python -m pytest webapp/tests -q` -> `44 passed`
- `npm --prefix webapp/frontend run check` -> 0 errors, 0 warnings
- `npm --prefix webapp/frontend run build` -> pass, with existing SvelteKit export warnings
- Focused new-feature tests: `tests/test_entourage.py tests/test_cleanup.py` -> `12 passed`
- After adding the #34 fixture-sourcing research doc:
  - `tests/test_launch_safety_docs.py` -> `4 passed`
  - `.venv/bin/mkdocs build` -> pass

## Write Blocker

- `gh auth status` reports the default `zohartito` token is invalid.
- GitHub connector comment attempt on PR #36 returned `403 Resource not accessible by integration`.
- Because both write paths are blocked, comments/closures below still need to be
  applied by a GitHub-authenticated session.

## Close/Supersede PRs

Close these PRs as superseded by #37 after posting a short comment that cites
the current pushed head and verification evidence:

- #34: fixture-sourcing research doc absorbed via `58aafb6` and `ed45c89`.
  The later broad roadmap/retrospective edits from that branch were not folded
  wholesale.
- #36: absorbed into #37 via merge commit `7794528`; verification-core,
  layout-jsx, report, and Rhino bridge work now live on the current #37 stack.
- #38: absorbed into #37 via cherry-pick `aec7674`; entourage SVG asset
  generator and tests are now on the current branch.
- #39: absorbed into #37 via cherry-pick `585fcc4`; conservative single-layer
  cleanup mode, CLI command, README docs, and tests are now on the current branch.
- #40: diagnose/report slice absorbed via `c2c1500`; `arch-lw diagnose` and
  tests are present on the current branch.
- #41: absorbed into #37 via cherry-pick `52f16c2`; endgame delivery control
  plan is now present under `docs/research/`.
- #42: concrete-base synthetic regression absorbed into #37; close the PR only.
  Do not close issue #30 from this synthetic evidence.
- #43: older local designer-console prototype is superseded by the current #37
  console/webapp stack.
- #44: designer-console prototype is present on #37/current branch; close as
  superseded after review.
- #45: private-proof quarantine and launch-safety guardrails are present on
  #37/current branch; close as superseded after review.

## Keep Open / Human-Gated

Keep these open:

- #29: proof-pack truth remains the launch blocker.
- #30: private foundation/concrete acceptance is still required; synthetic
  regressions do not close it.
- #31 and #32: close-candidates after #37 verification, but prior comments left
  them open pending accepted W5/W7 review-packet contract. Keep open unless that
  acceptance criterion is explicitly satisfied.
- #19 and #7: still need Illustrator-backed/private visual evidence.
- #1, #2, #3, #4: user-side validation, posting, customer discovery, and legal
  licensing decisions.
- #21: broad Make2D/geometry repair remains open; #42 is not enough.
- #33: deferred Rhino export assistant/product workflow unless the accepted
  scope is only the current bridge/export helper.

## Close Candidates After GitHub Auth Is Restored

- #20: code for the isometric entourage SVG generator is now on #37 via
  `aec7674`; close if the accepted scope is generator/library support rather
  than a broader product asset pack.
- #23: conservative single-layer cleanup mode is now on #37 via `585fcc4`; close
  if the accepted scope is the first conservative cleanup command, not full
  general geometry repair.
- #31 and #32 remain close-candidates only after W5/W7 accepts the review-packet
  contract; prior comments intentionally kept them open.

## Suggested PR #37 Checkpoint Comment

Post to #37 after GitHub auth is restored:

```text
Checkpoint after integrating the current verification-core stack.

Latest #37 stack now also absorbs #38, #39, and #41.

Verified locally:
- root pytest: 667 passed, 7 skipped, 1 xfailed
- ruff check: pass
- ruff format check: pass
- mkdocs build: pass
- webapp tests: 44 passed
- frontend check/build: pass
- focused entourage/cleanup tests: 12 passed

Superseded PRs to close against this stack: #34, #36, #38, #39, #40, #41, #42, #43, #44, #45.
Important boundaries remain unchanged: #29 and #30 stay open; synthetic proof
does not close #30; posting/public proof remains NO-GO without W5/W7 acceptance.
```
