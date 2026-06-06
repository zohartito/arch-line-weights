# Agent Workflow Archive - 2026-06-04

This note preserves the agent operating model that worked during the
verification-core / designer-console push. It is a historical workflow archive,
not release clearance and not a claim that any referenced branch head is still
current.

The value here is the method:

- inspect live state before trusting a prior summary;
- keep one lead agent responsible for judgment;
- let Cursor/Codex work for hours from explicit goals;
- use disposable no-merge rehearsals before changing the real stack;
- keep private studio evidence local;
- verify proof/report claims with tests and scans before writing PR summaries.

## Standing Boundaries

Repeat these at the start and end of every agent wave:

- Do not merge PRs unless the human explicitly asks.
- Do not close #29 or #30 from synthetic proof or local-only evidence.
- Posting/public proof is NO-GO unless W5/W7 explicitly accepts a public-safe
  packet.
- Synthetic proof does not close #30.
- Private USC / studio regression evidence stays private.
- Do not commit private drawings, screenshots, PDFs, raw reports, proof assets,
  local machine paths, or handoff files that contain local paths.
- Do not claim App Store, Windows desktop, Rhino plugin, Illustrator panel,
  PyPI, hosted-cloud, or Bluebeam readiness unless that surface is implemented
  and tested.
- Never mark proof passed when output is missing, reports say `failed` /
  `no_go`, review gates remain, rendered views are unchanged, or private paths
  leak.

## The Pattern That Worked

### 1. Start With Authoritative State

Do not trust the chat transcript by itself. Run:

```bash
git fetch --all --prune
git status --short --branch
git log --oneline -12
gh pr view <number> --json number,title,state,isDraft,headRefName,mergeStateStatus,statusCheckRollup,url
```

If an old worktree path is gone or marked prunable, use remote refs as the
source of truth.

### 2. Preserve Before Improving

When the human says "save this so it does not get lost," prefer a docs-only
preservation branch:

```bash
git switch -c codex/preserve-<topic>
```

Capture:

- current branch heads;
- what was proven;
- what was not proven;
- tests and scans actually run;
- conflicts and resolutions;
- prompts that produced useful long-running work;
- remaining human-only gates.

Avoid changing engine behavior during preservation.

### 3. Rehearse The Stack Without Merging PRs

Use disposable rehearsal branches from `origin/main`:

```bash
git switch -c codex/tmp-current-head-landing-rehearsal-YYYYMMDD origin/main
git merge --no-ff origin/<branch>
```

After each merge:

- record conflicts;
- resolve toward the stricter proof/report/private-safety behavior;
- run focused tests;
- commit the rehearsal merge;
- keep the branch archival, not a PR to merge wholesale.

The rehearsal branch answers "can this stack integrate?" It does not answer
"is public posting safe?"

### 4. Make The Human Merge Packet

The merge packet should be short enough to use during review:

- merge order;
- PRs to close without merge;
- expected conflicts;
- preferred resolution for each conflict;
- tests after each step;
- manual W5/W7 review gates;
- explicit NO-GO language.

Useful companion docs:

- `docs/research/human-landing-plan-*.md`
- `docs/research/merge-readiness-packet-*.md`
- `docs/research/pr-overlap-audit-*.md`
- `docs/how-to/private-studio-dogfood-runbook.md`

### 5. Separate Public-Safe Summaries From Raw Local Reports

Raw local reports can exist in temp/local proof directories. They should not be
committed. Public-safe summaries should be path-free and must repeat the NO-GO
status until W5/W7 accepts a public-safe packet.

Proof and console outputs should carry:

- `posting_clearance: "NO-GO"` unless explicit public acceptance exists;
- `synthetic_proof_closes_issue_30: false`;
- W5/W7 acceptance state as explicit labels, not vague "accepted" copy;
- generated handoff templates with generic layer names.

### 6. Use Tests As Claim Guards

Good proof/report tests catch false confidence:

- missing `report.json` fails proof-check;
- missing artifacts fail;
- `failed` / `no_go` raw reports fail;
- unchanged before/after rendered views fail;
- review-gated foundation/concrete layers stay `needs_review`;
- local paths and private fixture tokens fail public-safe validation;
- launch docs cannot reintroduce retired proof assets or premature posting
  claims.

### 7. Update PR Bodies After Verification

PR bodies should show:

- branch head;
- local verification commands and results;
- rehearsal branch/head if relevant;
- safety scan result;
- what remains blocked;
- explicit boundaries.

Do not let a green CI badge imply #29/#30 closure or public launch.

## Long-Running Cursor Prompt Shape

Short prompts produce five-minute patches. The effective prompt format was:

```text
Set this as a long-running goal. Do not stop after a small patch.

Objective:
[one concrete end state]

Known state:
- [branch heads]
- [open blockers]
- [NO-GO boundaries]

First inspect:
1. git fetch --all --prune
2. git status --short --branch
3. gh pr view ...
4. Read these files: [...]

Non-negotiable rules:
- no PR merges
- #29/#30 stay open
- posting NO-GO
- private regression stays private
- no private assets or local paths
- do not weaken validators

Phases:
1. [audit]
2. [implementation or reconciliation]
3. [docs/runbook]
4. [tests/scans]
5. [push/report]

If one phase finishes quickly, continue to the next. The goal is to exhaust the
useful safe work, not to make one tiny change and stop.
```

## Useful Agent Stack

Parallelize inside waves, sequence between waves.

Good parallel lanes:

- PR overlap audit;
- proof false-pass audit;
- console copy/status audit;
- launch-safety/private-path scan;
- docs/runbook reconciliation;
- current-head rehearsal;
- CI/PR body refresh.

Bad parallel lanes:

- multiple agents editing `cli.py` at once;
- multiple agents changing report schema at once;
- one agent changing console API while another changes frontend assumptions;
- any agent committing private proof artifacts.

The lead agent should integrate, verify, and push.

## Verification Commands

Use the repo's current paths, but this was the useful verification shape:

```bash
export PYTHONPATH=src

.venv/bin/python -m pytest --ignore=tests/test_hatch_v05.py -q
.venv/bin/python -m pytest webapp/tests -q
.venv/bin/ruff check src/ tests/ webapp/backend/ webapp/tests/
npm --prefix webapp/frontend run check
npm --prefix webapp/frontend run build
git diff --check
```

Tracked-file safety scan pattern. Fill the placeholders from the current
launch-safety test rather than hard-coding private fixture names into new docs:

```bash
git grep -n -I -E '(<local-path-prefix>|<private-fixture-token>|<retired-proof-token>|<premature-public-claim>)' -- ':!tests/test_launch_safety_docs.py' ':!tests/test_proof.py' ':!webapp/tests/*' ':!src/arch_line_weights/proof.py'
```

Treat scanner regexes and test fixtures as expected hits only after inspecting
them.

## Failure Modes To Remember

- A stale chat summary can be wrong after another agent pushes.
- A local temp worktree can disappear; remote refs are more durable.
- "Already green" can become queued again after a push.
- A branch can contain docs that are safe in context but unsafe as public launch
  copy.
- A rehearsal branch can be good evidence but a bad merge vehicle.
- "Accepted" UI copy is dangerous without W5/W7 context.
- Synthetic proof can exercise the harness while still leaving #30 open.
- Store/desktop/plugin talk creates product claims before engineering evidence.

## Where To Preserve Future Lessons

Project-specific process notes belong in `docs/research/`.

Reusable multi-agent workflow notes can also be preserved in the tools-dashboard
repo under `docs/agent-workflows/`, because that repo already archives general
Codex/Cursor/Claude operating models.
