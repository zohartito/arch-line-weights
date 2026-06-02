# GitHub Triage Queue - 2026-06-02

This note records the issue/PR state after the current verification-core
checkpoint. GitHub write access was restored on 2026-06-02, and the planned
comment/closure actions were applied.

## Current Checkpoint

- Active branch: `codex/open-issue-verification-core`
- Active integration PR: #37
- Applied checkpoint: `86d302bdeb60ddf0236c14bc62a73ae5bf82e1d9`
- PR head checked before this final audit note was committed:
  `0769ee7d2fa3f5477927850d66b37700c7a26b19`
- Pre-note final audit PR state: draft, mergeable, with GitHub CI and Vercel
  checks green on head `0769ee7d2fa3f5477927850d66b37700c7a26b19`.
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
  - `86d302b` refreshes the GitHub triage checkpoint and corrects
    `proof-check --materialize-synthetic` help text.
- Local dirty file intentionally left unstaged: `webapp/frontend/vercel.json`
  changes `installCommand` from `npm ci` to `npm install`; do not commit it
  without the Vercel failure context.

## Live Open Items After Applied Triage

Public GitHub API / CLI refresh on 2026-06-02 after applying triage shows these
open items:

- Open PRs: #37.
- Open issues: #1, #2, #3, #4, #7, #19, #21, #29, #30, #31, #32, #33.
- Closed PRs: #34, #36, #38, #39, #40, #41, #42, #43, #44, #45.
- Closed issues: #20 and #23.
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

## Applied GitHub Actions

- `gh auth status` reported a valid token on 2026-06-02.
- Closed superseded PRs: #34, #36, #38, #39, #40, #41, #42, #43, #44, #45.
- Closed narrow implemented issues: #20 and #23.
- Posted keep-open comments on #1, #2, #3, #4, #7, #19, #21, #29, #30, #31,
  #32, and #33.
- Posted checkpoint comment on #37:
  https://github.com/zohartito/arch-line-weights/pull/37#issuecomment-4605309036

## Final Subagent Audit - 2026-06-02

Three bounded subagent audits checked the remaining open issue groups after
GitHub triage was applied. They found no additional low-risk code cleanup or
tracker action that would close a remaining issue.

- #29 and #30 are not closeable without accepted W5/W7/private USC proof.
- #31 and #32 are close-candidates only after the W5/W7 review-packet and
  report contract are accepted.
- #7 and #19 still need Illustrator-backed/private visual acceptance.
- #21 remains the broad Make2D/component-graph geometry repair tracker; the
  current #37/#42 work improves concrete/foundation behavior but does not prove
  general completion.
- #33 remains intentionally deferred until the verifier/proof loop is accepted.
- #1, #2, #3, and #4 remain human/product/legal-gated; their labels and
  keep-open comments are adequate.

## Closed/Superseded PRs

These PRs were closed as superseded by #37 after posting comments that cite the
current pushed head and verification evidence:

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
- #44: designer-console prototype is contained by current head `86d302b`
  (`86fca6a` is an ancestor of the current branch) and superseded by the
  current #37 console/W5-W7 proof-packet stack. Close as superseded.
- #45: private-proof quarantine and launch-safety guardrails are present on
  current head `86d302b`. The exact PR commits are not ancestors, but the
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

## Closed Implemented Issues And Remaining Close Candidates

- #20: closed for the accepted generator/library-support scope. Broader product
  asset-pack or placement UI scope should become a follow-up issue.
- #23: closed for the conservative first cleanup command. Full general geometry
  repair remains tracked separately in #21.
- #31 and #32 remain close-candidates only after W5/W7 accepts the review-packet
  contract; prior comments intentionally kept them open.

## Suggested PR #37 Checkpoint Comment

Posted to #37 after GitHub auth was restored:

```text
Checkpoint after integrating the current verification-core stack.

Latest #37 stack now also absorbs #38, #39, the safe #34/#41 subsets, and the
#42 concrete-base synthetic regression behavior. Current branch head: 86d302b.

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
