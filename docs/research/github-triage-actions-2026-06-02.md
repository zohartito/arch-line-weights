# GitHub Triage Actions - 2026-06-02

Purpose: record the comments and state changes applied after GitHub write auth
was restored. This is a companion to
`github-triage-queue-2026-06-02.md`.

Authoritative current integration branch:

- PR: #37
- Branch: `codex/open-issue-verification-core`
- Applied checkpoint: `86d302bdeb60ddf0236c14bc62a73ae5bf82e1d9`
- PR head checked before this final audit note was committed:
  `0769ee7d2fa3f5477927850d66b37700c7a26b19`
- Pre-note final audit PR state: draft, mergeable, with GitHub CI and Vercel
  checks green on head `0769ee7d2fa3f5477927850d66b37700c7a26b19`.
- Latest local verification:
  - `.venv/bin/python -m pytest -q` -> `681 passed, 7 skipped, 1 xfailed`
  - `.venv/bin/python -m pytest webapp/tests -q` -> `44 passed`
  - `.venv/bin/python -m ruff check src tests webapp/backend` -> pass
  - `.venv/bin/python -m ruff format --check src tests webapp/backend webapp/tests` -> pass
  - `.venv/bin/arch-lw proof-check tests/fixtures/make2d/manifest.yml --fixture public_foundation_window_section_synthetic --fixture public_false_fill_void_expected_fail_synthetic --fixture public_unsupported_payload_synthetic --materialize-synthetic --output-dir /tmp/archlw-public-proof-sentinels --no-pretty` -> pass
  - `.venv/bin/arch-lw proof-check tests/fixtures/make2d/manifest.yml --materialize-synthetic --output-dir /tmp/archlw-proof-materialized-all-sentinels --no-pretty` -> expected fail only on the private/manual-review fixture
  - `git branch --contains 86fca6a5ee52d15a671d2072acbf47e813dc9ae6 --all` -> current branch contains PR #44 head
  - tracked-file retired proof asset check -> no retired Day-1 proof asset tree or stale proof `.gitattributes` entry at HEAD
  - `.venv/bin/mkdocs build` -> pass
  - `git diff --check` -> pass

## Preflight Used

These checks were used before making GitHub state changes:

```bash
gh auth status
git fetch origin
git rev-parse origin/codex/open-issue-verification-core
git merge-base --is-ancestor 86d302bdeb60ddf0236c14bc62a73ae5bf82e1d9 origin/codex/open-issue-verification-core
```

The branch should contain this applied checkpoint:

```text
86d302bdeb60ddf0236c14bc62a73ae5bf82e1d9
```

Applied on 2026-06-02 after `gh auth status` reported a valid token.

## Final Audit After Applying Actions

After the GitHub comments and closures were applied, three bounded subagent
audits checked the remaining open issue groups:

- #29, #30, #31, and #32: keep open until accepted W5/W7/private reference proof or
  review-packet/report-contract acceptance exists.
- #7, #19, #21, and #33: keep open; they still require real Illustrator/private
  visual acceptance, broad geometry-repair evidence, or an explicit unpause of
  the Rhino export-assistant spike.
- #1, #2, #3, and #4: keep open as user/product/legal-gated work.

The audits found no additional low-risk code cleanup or GitHub state change
that would close any remaining issue. The historical comment transcripts below
still mention `86d302b` because that was the integration head cited when the
actions were posted.

## PR Comments And Closures Applied

Each PR received a closing comment and was closed without merging.

### #34 - Close As Subset Absorbed

Comment:

```text
Closing this PR as superseded by #37 / codex/open-issue-verification-core.

The safe fixture-sourcing research subset was absorbed via 58aafb6 and ed45c89,
and the current integration head is 86d302b. I did not fold the broader roadmap
or retrospective edits wholesale; those remain human-gated/product-context work.

Verification on #37: root pytest 681 passed, 7 skipped, 1 xfailed; webapp tests
44 passed; ruff check and format check pass; mkdocs build passes; git diff
check passes.
```

Action: close PR #34.

### #36 - Close As Superseded

Comment:

```text
Closing this PR as superseded by #37 / codex/open-issue-verification-core.

The verification-core, layout-jsx report, and Rhino bridge work are now on the
current #37 stack. Current integration head: 86d302b.

Verification on #37: root pytest 681 passed, 7 skipped, 1 xfailed; webapp tests
44 passed; ruff check and format check pass; mkdocs build passes; git diff
check passes.
```

Action: close PR #36.

### #38 - Close As Superseded

Comment:

```text
Closing this PR as superseded by #37 / codex/open-issue-verification-core.

The entourage SVG asset generator was absorbed via aec7674 and remains covered
by focused entourage tests on the current #37 stack. Current integration head:
86d302b.
```

Action: close PR #38.

### #39 - Close As Superseded

Comment:

```text
Closing this PR as superseded by #37 / codex/open-issue-verification-core.

The conservative single-layer cleanup mode was absorbed via 585fcc4 and remains
covered by focused cleanup tests on the current #37 stack. Current integration
head: 86d302b.
```

Action: close PR #39.

### #40 - Close As Superseded

Comment:

```text
Closing this PR as superseded by #37 / codex/open-issue-verification-core.

The diagnose/report slice is present on the current #37 stack, including
`arch-lw diagnose` and report tests. Current integration head: 86d302b.
```

Action: close PR #40.

### #41 - Close As Subset Absorbed

Comment:

```text
Closing this PR as superseded by #37 / codex/open-issue-verification-core.

The safe endgame delivery control plan subset was absorbed via 52f16c2. I did
not fold broader product/roadmap material wholesale; that remains human-gated.
Current integration head: 86d302b.
```

Action: close PR #41.

### #42 - Close As Superseded, Keep #30 Open

Comment:

```text
Closing this PR as superseded by #37 / codex/open-issue-verification-core.

The concrete-base synthetic regression behavior was ported via 9b2efd0, the
public proof sentinels were strengthened via 2c12a9f, and both are present on
the current #37 head, 86d302b: same-component visible/tangent helper routing,
fragmented concrete edge recovery, and slim concrete-base completion above the
previous static area cap.

Focused verification: tests/test_apply_saas_poche.py and
tests/test_architectural_mode.py -> 86 passed.

Important boundary: this synthetic evidence does not close issue #30. #30 stays
open until the private reference foundation/concrete proof packet is reviewed and
accepted.
```

Action: close PR #42.

### #43 - Close As Superseded

Comment:

```text
Closing this PR as obsolete/replaced by #37 / codex/open-issue-verification-core.

The earlier local designer-console prototype was not absorbed file-for-file; it
was replaced by the current #37 webapp console stack. Current integration head:
86d302b.

Boundary remains unchanged: public proof is NO-GO without W5/W7 acceptance.
```

Action: close PR #43.

### #44 - Close As Superseded After Review

Comment:

```text
Closing this PR as superseded by #37 / codex/open-issue-verification-core after
reviewing that the designer-console stack is present on #37. Current integration
head: 86d302b.

Review evidence: PR #44 head 86fca6a is an ancestor of current integration head
86d302b, so the designer-console prototype changes are already included and
then superseded by the current console/W5-W7 proof-packet stack.

Verification on #37 includes webapp tests -> 44 passed. Boundary remains
unchanged: public proof is NO-GO without W5/W7 acceptance.
```

Action: close PR #44.

### #45 - Close As Superseded After Review

Comment:

```text
Closing this PR as superseded by #37 / codex/open-issue-verification-core after
reviewing that private-proof quarantine and launch-safety guardrails are present
on #37. Current integration head: 86d302b.

Review evidence: PR #45 head fa5524a is not an ancestor of current integration
head 86d302b, but its quarantine intent is superseded on the current branch via
9a81755, 737a7dc, 07c65fb, 30b6951, 49f4932, 63f451e, and 5532292. The retired
Day-1 proof asset tree and stale proof `.gitattributes` entry are absent at
HEAD, and current launch-safety coverage is stricter than #45 because it scans
core public docs, research docs, and committed helper scripts.

Boundary remains unchanged: no private drawings, screenshots, PDFs, raw reports,
proof assets, or local paths should be committed; synthetic proof does not close
#30.
```

Action: close PR #45 without merging.

## Issue Comments And Closures Applied

### #20 - Close If Accepted Scope Is Generator Support

Comment:

```text
Closing this as implemented for the accepted generator/library-support scope.

The #37 integration branch includes the entourage SVG asset generator via
aec7674, plus classifier/test coverage that keeps entourage light and out of
cut/poché treatment. Current integration head: 86d302b.

If the desired scope becomes a broader product asset pack or placement UI, that
should be a new follow-up issue.
```

Action: close issue #20 if the accepted scope is the first generator/library
slice.

### #23 - Close If Accepted Scope Is Conservative First Cleanup Command

Comment:

```text
Closing this as implemented for the conservative first cleanup command.

The #37 integration branch includes conservative single-layer cleanup mode via
585fcc4, CLI/docs coverage, and tests for the safe first-pass behavior. Current
integration head: 86d302b.

This does not claim full general geometry repair; broad Make2D repair remains
tracked separately in #21.
```

Action: close issue #23 if the accepted scope is the first conservative cleanup
slice.

### #29 - Keep Open

Comment:

```text
Keeping this open.

#37 now has a proof manifest, proof-check command, visual artifact validation,
W5/W7 handoff packet generation, report guardrails, and NO-GO public-proof
posture. Current integration head: 86d302b.

Closure still requires the final accepted proof packet: full-board plus close-up
before/after/diff evidence, explicit skipped/failed/ambiguous regions, and W5/W7
acceptance. Public posting remains NO-GO until that acceptance is recorded.
```

Action: leave issue #29 open.

### #30 - Keep Open

Comment:

```text
Keeping this open.

#37 now includes public-safe synthetic regressions for concrete/foundation
helper-backed poché, including the fragmented concrete edge tail port at
9b2efd0, present on current head 86d302b. That improves the algorithm and report
coverage, but it does not prove the private reference wall-section result.

Closure still requires private reference proof evidence showing the
foundation/concrete region before/after/diff and whether expected cut-mass layers
were filled, skipped, failed, or intentionally ignored. Synthetic proof does not
close #30.
```

Action: leave issue #30 open.

### #31 - Keep Open Until Accepted Review Packet Exists

Comment:

```text
Keeping this open as a close-candidate, not closing yet.

#37 includes the Make2D fixture manifest, proof-check command, rendered artifact
paths, review-region pixel gates, public synthetic pass/expected-fail/unsupported
sentinels, and tests. Current integration head: 86d302b.

The remaining closure gate is accepted W5/W7 review-packet evidence, especially
for the private reference fixture. Without that accepted packet, the suite is present
but the launch proof is not final.
```

Action: leave issue #31 open unless W5/W7 acceptance is recorded.

### #32 - Keep Open Until Accepted Review Packet Exists

Comment:

```text
Keeping this open as a close-candidate, not closing yet.

#37 includes durable machine-readable reports for changed/skipped/failed/why,
input diagnostics, no-op/missing-payload warnings, poché status, completion
candidates, visual artifact paths, and W5/W7 review gates. Current integration
head: 86d302b.

The remaining closure gate is accepted W5/W7 review-packet evidence. Until that
exists, the report machinery is implemented but the proof QA decision is not
accepted.
```

Action: leave issue #32 open unless W5/W7 acceptance is recorded.

### #19 - Keep Open

Comment:

```text
Keeping this open.

#37 adds diagnose/report/proof machinery and makes PDF-preview limitations
explicit, but the issue asks for Illustrator-backed visual QA. That still needs
an Illustrator-backed smoke check on a real drawing or a deliberately scoped
follow-up acceptance decision.
```

Action: leave issue #19 open.

### #7 - Keep Open

Comment:

```text
Keeping this open.

The repo has stronger synthetic and report verification now, but this issue asks
for a real Illustrator visual comparison between apply-saas --poche and
apply-jsx --poche on the same drawing. That real Illustrator validation has not
been accepted yet.
```

Action: leave issue #7 open.

### #21 - Keep Open

Comment:

```text
Keeping this open.

#37 and the #42 tail improve concrete/foundation and cleanup-specific behavior,
but they do not claim full general Make2D completion / geometry repair. Keep
this as the broader geometry-repair tracker.
```

Action: leave issue #21 open.

### #33 - Keep Open Deferred

Comment:

```text
Keeping this deferred.

The verifier/proof loop is stronger on #37, but #29 and #30 are still open and
public proof remains NO-GO. A Rhino Make2D export assistant should wait until
the proof QA loop is accepted or be explicitly rescoped as a small export-helper
spike.
```

Action: leave issue #33 open.

### #1, #2, #3, #4 - Keep Open User/Product/Legal Gated

Comment for #1:

```text
Keeping this open as user-side validation.

The agent can improve tooling and proof guardrails, but this issue requires use
on a fresh real reference drawing and a personal-use-log entry. That remains a
human validation step.
```

Comment for #2:

```text
Keeping this open as user-side marketing validation.

Public posting is still NO-GO until #29/#30 proof acceptance is recorded, and
the actual before/after post plus organic reaction count is a human/product
step.
```

Comment for #3:

```text
Keeping this open as customer-development work.

The repository work does not replace scheduling and running real interviews.
This should remain open until the interview is completed and recorded.
```

Comment for #4:

```text
Keeping this open as legal/product-timing work.

The license/EULA swap should happen only when the product is ready for the
planned publication window and after appropriate legal review. No repository
automation should close it early.
```

Action: leave issues #1, #2, #3, and #4 open.
