# GitHub Triage Queue - 2026-06-02

This note records the issue/PR state after the current verification-core
checkpoint because GitHub write access is blocked in this session. Exact
auth-restored comment bodies and state changes are queued in
`docs/research/github-triage-actions-2026-06-02.md`.

## Current Checkpoint

- Active branch: `codex/open-issue-verification-core`
- Active integration PR: #37
- Reviewed checkpoint: `18f85a50deba3f1e601c932d754cc16bf28cbcb4`
- Additional absorbed commits now on the local #37 stack:
  - `aec7674` absorbs #38 / #20, entourage SVG asset generator.
  - `585fcc4` absorbs #39 / #23, conservative single-layer cleanup mode.
  - `52f16c2` absorbs the safe #41 endgame delivery control plan subset.
  - `58aafb6` and `ed45c89` absorb the safe #34 W2 fixture-sourcing research
    doc subset.
  - This worktree update ports the remaining #42 concrete-base synthetic
    regression behavior: same-component visible/tangent helper routing,
    fragmented concrete edge recovery, and slim concrete-base completion above
    the old static area cap.
  - `987e58f` adds deterministic public synthetic proof-packet materialization.
  - `2c12a9f` adds proof-check expectation semantics for public pass,
    expected-fail, and unsupported synthetic sentinels.
  - `18f85a5` refreshes the GitHub triage checkpoint and corrects
    `proof-check --materialize-synthetic` help text.
- Local dirty file intentionally left unstaged: `webapp/frontend/vercel.json`
  changes `installCommand` from `npm ci` to `npm install`; do not commit it
  without the Vercel failure context.

## Live Open Items Refreshed

Public GitHub API refresh on 2026-06-02 after pushing `18f85a5` still shows
these open items:

- Open PRs: #34, #36, #37, #38, #39, #40, #41, #42, #43, #44, #45.
- Open issues: #1, #2, #3, #4, #7, #19, #20, #21, #23, #29, #30, #31,
  #32, #33.
- PRs queued for close-as-superseded/subset-absorbed after auth returns:
  #34, #36, #38, #39, #40, #41, #42, #43, #44, #45.
- Issues queued as possible closures after auth returns and scope is accepted:
  #20 and #23.
- Issues intentionally kept open: #1, #2, #3, #4, #7, #19, #21, #29, #30,
  #31, #32, #33.

## Verification Evidence

Verification evidence for the current branch checkpoint:

- `.venv/bin/python -m pytest -q` -> `681 passed, 7 skipped, 1 xfailed`
- `.venv/bin/python -m ruff check src tests webapp/backend` -> pass
- `.venv/bin/python -m ruff format --check src tests webapp/backend webapp/tests` -> pass
- `.venv/bin/mkdocs build` -> pass
- `.venv/bin/python -m pytest webapp/tests -q` -> `44 passed`
- `.venv/bin/arch-lw proof-check tests/fixtures/make2d/manifest.yml --fixture public_foundation_window_section_synthetic --fixture public_false_fill_void_expected_fail_synthetic --fixture public_unsupported_payload_synthetic --materialize-synthetic --output-dir /tmp/archlw-public-proof-sentinels --no-pretty` -> pass
- `.venv/bin/arch-lw proof-check tests/fixtures/make2d/manifest.yml --materialize-synthetic --output-dir /tmp/archlw-proof-materialized-all-sentinels --no-pretty` -> expected fail only on the private/manual-review fixture
- `git branch --contains 86fca6a5ee52d15a671d2072acbf47e813dc9ae6 --all` -> current branch contains PR #44 head
- tracked-file retired proof asset check -> no retired Day-1 proof asset tree or stale proof `.gitattributes` entry at HEAD
- Earlier frontend gate on this #37 stack, before the backend/doc-only #42 tail:
  - `npm --prefix webapp/frontend run check` -> 0 errors, 0 warnings
  - `npm --prefix webapp/frontend run build` -> pass, with existing SvelteKit
    export warnings
- Focused new-feature tests: `tests/test_entourage.py tests/test_cleanup.py` -> `12 passed`
- After adding the #34 fixture-sourcing research doc:
  - `tests/test_launch_safety_docs.py` -> `4 passed`
  - `.venv/bin/mkdocs build` -> pass
- After porting the #42 behavioral tail:
  - `.venv/bin/python -m pytest tests/test_apply_saas_poche.py tests/test_architectural_mode.py -q`
    -> `86 passed`
  - `.venv/bin/python -m pytest tests/test_run_report.py tests/test_proof.py tests/test_launch_safety_docs.py -q`
    -> `63 passed`
  - `.venv/bin/python -m ruff check src tests webapp/backend` -> pass
  - `.venv/bin/python -m ruff format --check src tests webapp/backend webapp/tests`
    -> pass
  - `.venv/bin/mkdocs build` -> pass
  - `.venv/bin/python -m pytest webapp/tests -q` -> `44 passed`
  - `git diff --check` -> pass

## Write Blocker

- `gh auth status` reports the default `zohartito` token is invalid.
- GitHub connector comment attempt on PR #36 returned `403 Resource not accessible by integration`.
- Because both write paths are blocked, comments/closures below still need to be
  applied by a GitHub-authenticated session.

## Close/Supersede PRs

Close these PRs as superseded by #37 after posting a short comment that cites
the current pushed head and verification evidence:

- #34: safe fixture-sourcing research doc subset absorbed via `58aafb6` and
  `ed45c89`. The later broad roadmap/retrospective edits from that branch were
  not folded wholesale.
- #36: absorbed into #37 via merge commit `7794528`; verification-core,
  layout-jsx, report, and Rhino bridge work now live on the current #37 stack.
- #38: absorbed into #37 via cherry-pick `aec7674`; entourage SVG asset
  generator and tests are now on the current branch.
- #39: absorbed into #37 via cherry-pick `585fcc4`; conservative single-layer
  cleanup mode, CLI command, README docs, and tests are now on the current branch.
- #40: diagnose/report slice absorbed via `c2c1500`; `arch-lw diagnose` and
  tests are present on the current branch.
- #41: safe endgame delivery control plan subset absorbed into #37 via
  cherry-pick `52f16c2`; the full broad branch remains human-gated.
- #42: concrete-base synthetic regression behavior is now ported and pushed on
  #37 via `9b2efd0`, with later proof sentinel verification through `2c12a9f`;
  close the PR only. Do not close issue #30 from this synthetic evidence.
- #43: older local designer-console prototype is obsolete/replaced by the
  current #37 console/webapp stack, not literally absorbed file-for-file.
- #44: designer-console prototype is contained by current head `18f85a5`
  (`86fca6a` is an ancestor of the current branch) and superseded by the
  current #37 console/W5-W7 proof-packet stack. Close as superseded.
- #45: private-proof quarantine and launch-safety guardrails are present on
  current head `18f85a5`. The exact PR commits are not ancestors, but the
  current branch carries the quarantine/redaction via `9a81755`, `737a7dc`,
  `07c65fb`, `30b6951`, `49f4932`, `63f451e`, and `5532292`; current HEAD also
  removes the retired Day-1 proof asset tree and strengthens research/script
  launch-safety scans. Close as superseded; do not merge.

## Keep Open / Human-Gated

Keep these open:

- #29: proof-pack truth remains the launch blocker.
- #30: private foundation/concrete acceptance is still required; synthetic
  regressions do not close it.
- #31 and #32: close-candidates after #37 verification. `2c12a9f` adds public
  pass/expected-fail/unsupported proof-check sentinels, but prior comments still
  leave them open pending accepted W5/W7 review-packet contract. Keep open unless
  that acceptance criterion is explicitly satisfied.
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

Latest #37 stack now also absorbs #38, #39, the safe #34/#41 subsets, and the
#42 concrete-base synthetic regression behavior. Current branch head: 18f85a5.

Verified locally:
- root pytest: 681 passed, 7 skipped, 1 xfailed
- ruff check: pass
- ruff format check: pass
- mkdocs build: pass
- webapp tests: 44 passed
- previous frontend check/build on this stack: pass
- focused entourage/cleanup tests: 12 passed
- focused #42 tail tests: 86 passed
- report/proof/doc nearby tests after #42 tail: 63 passed
- public proof-check pass/expected-fail/unsupported sentinels: pass
- all-fixtures proof-check: expected fail only on private/manual-review fixture
- PR #44 head is an ancestor of current branch
- PR #45 quarantine is superseded by current branch and stricter launch-safety tests

Superseded PRs to close against this stack: #34, #36, #38, #39, #40, #41, #42, #43, #44, #45.
Important boundaries remain unchanged: #29 and #30 stay open; synthetic proof
does not close #30; posting/public proof remains NO-GO without W5/W7 acceptance.
```
