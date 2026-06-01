# Endgame Delivery Plan - 2026-06-01

This plan tracks the path from the current verification-core draft PRs to a
human-usable local designer console and, later, a launchable desktop/plugin
product. It is an engineering control document, not a public launch claim.

## Non-Negotiable Gates

- Posting/public proof is **NO-GO** unless W5/W7 explicitly accepts it.
- Synthetic proof does not close #30.
- Private USC regression stays private.
- Do not merge PRs from this plan.
- Do not close #29 or #30 from synthetic or local-only evidence.
- Do not commit private drawings, screenshots, PDFs, raw reports, local paths,
  or proof assets.
- Do not claim App Store, Windows, Rhino plugin, or Illustrator panel readiness
  until those surfaces are actually implemented and tested.

## Current Baseline

- #34 is green: verification fixture sourcing research. It was refreshed at
  `186531a` to remove a private axon filename from the public roadmap wording,
  update stale PR #36 CI language, and refresh the PR body with current local
  validation.
- #36 is green and draft: W3 verification core, layout-jsx reports, Rhino bridge.
- #37 is green and draft at the last completed check: input diagnostics and
  proof report harness. It now includes proof-packet validation that fails
  closed on missing artifacts, failed/no-go raw reports, review layers, missing
  payloads, and raw local/private path references.
- #38 is green and draft: entourage SVG asset generator.
- #39 is green and draft: conservative single-layer cleanup mode.
- #40 is green and draft: run-report diagnose command.
- #41 is draft: this control plan.
- #42 is draft: a public-safe synthetic concrete-base poché regression plus a
  JSX-poche runtime helper-path fix narrowed to the #30 concrete/foundation
  target family. Private visual probing rejected a broader helper attempt
  because it overfilled unrelated structural layers. The current narrowed probe
  moved `TEC_CONCRETE_BASE` from low-confidence `auto_bridge` evidence to
  `structural_open_loop` at confidence 0.88, with output created and the
  old-vs-new rendered diff localized to the previously white concrete pier/stem
  area. This is Exit-A progress, but it is still not W5 visual acceptance and
  does not close #30.
- #43 is draft and stacked on #36: the local designer-console prototype. It has
  local full-test verification, but no GitHub checks are reported on the
  stacked branch yet.
- #44 is draft: a repo-native `webapp/` FastAPI + SvelteKit designer-console
  prototype based on `main`. It preserves the existing webapp scaffold shape and
  is the preferred path if the team wants the console to live in `webapp/`.
- #45 is draft: launch-safety quarantine for private proof assets and public
  posting drafts. It removes committed Day-1 proof media from the public tree
  and redacts inherited local/private paths.

The repo has an existing local `webapp/` scaffold: FastAPI backend, SvelteKit
frontend, local filesystem storage, and tests. Designer-console work should
prefer this shape unless a smaller CLI-served page is demonstrably safer.

Safety scan note: inherited Day-1 proof media and README links remain a
posting-clearance risk on branches that do not include #45. PR #45 is the
current quarantine path; until it is reviewed and merged, public proof and
posting remain no-go.

## Phase Stack

### Phase 0 - Control Tower

Purpose: keep the work sequenced, green, and honest.

Outputs:

- Living delivery ledger.
- PR dependency order and conflict watch.
- Private-path/public-claim leak scans before every push.
- Clear "done / not done / blocked by human acceptance" reporting.

### Phase 1 - Mergeable Foundation

Purpose: keep already-produced draft PRs mergeable without merging them.

Candidate sequence:

1. #34 fixture sourcing.
2. #36 verification core.
3. #37 input diagnostics/proof harness.
4. #38 entourage, #39 cleanup, #40 diagnose as independent feature PRs.

This phase does not close #29/#30 by itself.

### Phase 2 - Verification Spine

Purpose: make proof packets trustworthy enough to prevent false launch claims.

Required capabilities:

- Fixture manifest reads Make2D source/export/report artifacts.
- Public-safe summaries are separated from raw local reports.
- Raw reports can live in temp/local output but must not be committed.
- Report contract states changed, skipped, failed, why, and next step.
- Status never reports passed when outputs are missing, report says failed/no_go,
  or raw proof contains private paths.
- Visual sentinels catch blank output, false fills, missing cut mass, and
  materially changed linework.

Key issues: #29, #31, #32.

### Phase 3 - Geometry and Poche Core

Purpose: fix the actual architectural result, not just the evidence wrapper.

Required capabilities:

- General Make2D completion / geometry repair stage for incomplete loops (#21).
- Structural open-loop closure for poché loops (#17).
- Conservative architectural mode keeps ambiguous geometry reviewable (#16).
- Foundation/concrete USC section regression becomes visibly acceptable (#30).

This phase cannot be declared complete without private review/acceptance for
the USC regression. Synthetic proof can support confidence, but it cannot close
#30.

### Phase 4 - Designer Console

Purpose: give a designer a local non-terminal surface.

Required MVP:

- Drag/select input file.
- Choose workflow: Section, Plan, Detail, Synthetic proof/demo.
- Clear actions: Inspect File, Run Layout, Apply Line Weights, Generate Poche,
  Export Proof Packet.
- Stage statuses: not run, running, passed, needs review, failed, no-go.
- Readable report: what changed, skipped, failed, why, next step.
- Explicit no-go notices:
  - Posting/public proof is NO-GO unless W5/W7 explicitly accepts it.
  - Synthetic proof does not close #30.
  - Private USC regression stays private.
- No terminal knowledge required for normal use.
- Local launch command and docs.
- Backend tests for status/report behavior.
- Browser render check of the main screen.

The existing `webapp/` scaffold is the first candidate host.

### Phase 5 - Illustrator/Rhino Automation

Purpose: reduce manual export friction after verification is reliable.

Later surfaces:

- Rhino Make2D/export assistant.
- Illustrator bridge/panel or scriptable review runner.
- Better direct diagnosis screenshots for per-layer QA.

This phase is intentionally after the verifier, not before it.

### Phase 6 - Launch Readiness

Purpose: decide what can be safely shown or shipped.

Prerequisites:

- #29 proof truth resolved.
- #30 private USC foundation/concrete regression accepted.
- Public-safe synthetic proof explicitly caveated.
- Install story chosen and tested.
- No private path/artifact leakage.
- Mac packaging and Windows packaging treated as future work until built and
  tested.

## Initial Parallel Agent Stack

- Verification Spine Agent: audit #31/#32/#29 gaps and produce or implement the
  smallest next testable proof-contract improvement.
- Geometry/Poche Agent: audit #21/#17/#16/#30 and identify the smallest synthetic
  regression that approximates the USC failure without exposing private assets.
- Designer Console Agent: inspect `webapp/` and the designer-console worktree,
  then make the local console render reliably with real status/report plumbing.
- Safety Gate Agent: scan active PRs/branches/docs for private-path leakage and
  overclaiming.
- PR Integrator Agent: monitor #34/#36/#37/#38/#39/#40 CI, mergeability, and
  likely conflict order without merging.

The main agent owns sequencing, review, integration, final verification, and
the decision to keep or reject subagent patches.

## Definition of Endgame Done

Engineering can call the endgame complete only when:

- Designer console opens locally and runs a representative proof workflow.
- Proof packet export is public-safe by default and raw reports are isolated.
- Verification catches missing outputs, no-go reports, private paths, and false
  pass states.
- Geometry/poche produces accepted results on the private USC regression.
- #29 and #30 are resolved by real accepted evidence, not by synthetic demos.
- Packaging/desktop/plugin claims are limited to actually tested surfaces.

Until then, the correct status is: local engineering progress, no public launch.
