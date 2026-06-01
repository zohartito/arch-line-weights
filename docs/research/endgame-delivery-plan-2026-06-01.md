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
  validation. A later compatibility update at `911bcd5` removes a retired proof
  phrase from the retrospective so the expanded launch-safety scanner can pass
  in the combined stack.
- #36 is green and draft: W3 verification core, layout-jsx reports, Rhino bridge.
  A later status-contract update at `8f00e18` gates inferred
  concrete/foundation poché output on W5/W7 visual acceptance in the durable
  report itself: injected helper-backed output can remain `inferred`, but
  `review.visual_acceptance_required` is true and standalone `arch-lw poche`
  summaries report `needs_review` instead of `passed` while any such layer is
  review-gated.
- #37 is green and draft at the last completed check: input diagnostics and
  proof report harness. It now includes proof-packet validation that fails
  closed on missing artifacts, failed/no-go raw reports, review layers, missing
  payloads, missing report identity, incomplete rendered-view evidence, and raw
  local/private path references. Proof packets must now identify input, output,
  command, a full-board rendered view, and at least one cut-mass/opening
  close-up before they can pass. A technically passed packet still keeps
  `public_safe` false until explicit W5/W7 public-proof acceptance metadata is
  present. It also gates inferred concrete/foundation fills on explicit W5/W7
  visual acceptance, so those reports stay `needs_review` even when the
  geometric strategy improves. Later updates carry helper-backed poché evidence
  through reports as `used_structural_helpers` plus `structural_helper_count`
  while preserving the proof gate. Later updates add opt-in review-region
  pixel checks, then connect the committed synthetic manifest's
  `review_regions` to that gate so synthetic proof packets fail when a declared
  cut-mass close-up region stays light or lacks a matching rendered `after`
  view. A later proof-truth update tightens those review regions with
  per-region `min_dark_ratio` and `min_dark_delta` gates, so outline/dot
  artifacts and already-dark before views cannot pass as newly added solid
  poché.
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
  does not close #30. A later update adds a repo-owned C2/C3-shaped synthetic
  regression for a vertical concrete stem plus foundation footing: target-family
  helper evidence recovers concrete/foundation cut mass, helper layers are not
  filled directly, and unrelated structural helpers do not leak into poché
  output. Later updates record structural helper counts in poché reports, expose
  those counts downstream, and mirror the W5/W7 concrete/foundation review gate
  in #42 so helper-backed inference is never treated as acceptance. A later
  update adds concrete/foundation-only tiny collinear fragment-gap bridging for
  C2/C3-like Make2D edge fragments: small same-line gaps can be normalized into
  one cut face, while larger voids remain open.
- #37 + #42 temp integration was tested locally. The stack had one small import
  conflict in `poche.py`; after resolving it, focused tests and ruff passed,
  and a private USC `poche --report` probe reported `TEC_CONCRETE_BASE` as
  `inferred` / `structural_open_loop` instead of `low_confidence`, with output
  and report artifacts created in temp storage only. After the #37 report gate
  update, the same combined stack reports `TEC_CONCRETE_BASE` and
  `TEC_FOUNDATION` as requiring W5/W7 visual acceptance. That is the desired
  no-go behavior: geometry progress is captured, but proof status remains
  review-gated until human visual acceptance exists.
- #37 + #42 integration was rechecked after the latest #42 C2/C3 synthetic
  regression. #42 now avoids the prior `poche.py` import conflict by keeping
  the Make2D-completion import local to `polygonize_dump`, and #37 adds a
  proof-level regression showing helper-backed synthetic concrete poché reports
  remain `needs_review` / `public_safe: false` when validated as proof packets.
  The combined temp stack merged without conflicts, passed focused
  proof/report/geometry tests, and passed the feasible full suite.
- #37 + #42 integration was rechecked again after the helper-evidence reporting
  update. #37 records helper-backed evidence in both apply-saas and proof-style
  reports, and #42 records structural helper counts from runtime helper paths.
  The refreshed temp merge remained conflict-free. Combined focused
  proof/report/geometry tests passed, ruff passed, the touched-file
  private/no-claim scan had no hits, and the feasible full suite passed.
- #37 + #42 integration was rechecked again after adding
  `structural_helper_count`, mirroring the concrete/foundation W5/W7 gate into
  #42, and rearranging overlapping report tests so the stack merges cleanly.
  The refreshed temp merge was conflict-free. Combined focused
  proof/report/geometry tests passed, ruff passed, the touched-file
  private/no-claim scan had no hits, and the feasible full suite passed.
- #37 + #42 integration was rechecked again after #37 added opt-in proof
  review-region pixel gates and connected the committed synthetic manifest's
  `review_regions` to the gate. The refreshed temp merge was conflict-free.
  Combined focused proof/report/geometry tests passed with 77 passing tests,
  ruff passed, the touched-file private/no-claim scan had no hits, and the
  feasible full suite passed with 556 passing tests and 1 skipped test.
- #37 + #42 integration was rechecked again after #37 tightened review-region
  gates with manifest-level `min_dark_ratio` and `min_dark_delta` thresholds.
  The refreshed temp merge was conflict-free. Combined focused
  proof/report/geometry tests passed with 80 passing tests, ruff passed,
  `git diff --check` was clean, the changed-diff private-path/name scan had no
  hits, and the feasible full suite passed with 559 passing tests and 1 skipped
  test.
- #37 + #42 integration was rechecked again after #42 added fragmented
  concrete/foundation edge recovery. The refreshed temp merge was conflict-free.
  Combined focused proof/report/geometry tests passed with 122 passing tests,
  ruff passed, `git diff --check` was clean, and the feasible full suite passed
  with 562 passing tests and 1 skipped test. The changed-diff scan had one
  intentional proof-validator regex hit for detecting local paths; it was not a
  leaked path.
- #36 was then refreshed with the report-status gate at `8f00e18`, and a
  disposable full-stack rehearsal merged it into the current local stack. The
  report/proof slice passed with 45 tests, ruff passed, and a private local
  regression rerun produced 42 injected poché polygons with 0 failed layers
  while correctly summarizing the durable report as `needs_review` for 2
  W5/W7-gated foundation/concrete layers. Raw reports and paths stayed local.
- #43 is draft and stacked on #36: the local designer-console prototype. It has
  local full-test verification, but no GitHub checks are reported on the
  stacked branch yet.
- #44 is draft: a repo-native `webapp/` FastAPI + SvelteKit designer-console
  prototype based on `main`. It preserves the existing webapp scaffold shape and
  is the preferred path if the team wants the console to live in `webapp/`. It
  now includes a one-command local launcher, `arch-lw-web-console`, that starts
  the backend and frontend together, chooses open ports, coordinates CORS/API
  URL settings, and opens the console. Rendered QA confirmed both a normal
  fallback URL and an outside-default frontend port can load the console and
  run the synthetic-demo inspect stage without browser console errors. A later
  update gates console proof exports on the same W5/W7 acceptance posture as
  the proof harness: exported packets are local review packets, the UI shows
  Public proof `NO-GO` and W5/W7 acceptance status, packet summaries carry
  `public_safe: false`, and the export stage remains `needs_review` without
  explicit W5/W7 acceptance. A later update keeps the stage action row
  synchronized with completed stage status and adds the same `public_safe:
  false`, W5/W7 acceptance state, no-go guardrails, and local-artifact proof
  notice to the legacy `/api/jobs` response and job detail UI, closing a
  plausible operator-confusion path where old done/download flows lacked proof
  clearance context.
- #45 is draft: launch-safety quarantine for private proof assets and public
  posting drafts. It removes committed Day-1 proof media from the public tree
  and redacts inherited local/private paths. A later update also quarantines
  retired Day-1 proof wording in release notes and adds a docs regression test
  that rejects old proof-asset links, private fixture names, and "all cut mass"
  style proof overclaims in public-facing docs. A later update expands that
  safety regression to cover `SHIP_CHECKLIST.md`, `docs/CHANGELOG.md`, docs-site
  index/how-to/tutorial pages, and stale proof-asset `.gitattributes` entries;
  replaces the README private-derived command sample with a synthetic workflow
  example; removes local-path and submit-quality wording from the dogfood
  checklist; and sanitizes changelog validation entries so private fixture
  names, output artifact names, and proof-like private counts do not appear in
  public surfaces. A later update at `fa5524a` expands the safety scanner to
  every markdown file under `docs/`, `RETROSPECTIVE.md`, `mkdocs.yml`, and
  `webapp/README.md`, then redacts stale research/postmortem references to
  private-derived filenames, local paths, and private run artifact names.

## Full-Stack No-Merge Rehearsal - 2026-06-01

A disposable local integration branch was built from `origin/main` and no PRs
were merged. The rehearsal tested this branch order:

1. #34 `w2-verification-fixture-sourcing` at `911bcd5`.
2. #37 `codex/open-issue-verification-core` at `7784f7b`.
3. #36 `v0.2-verification-core` at `a3a7e6a`.
4. #38 `codex/issue20-entourage-assets` at `4153778`.
5. #39 `codex/issue23-single-layer-cleanup` at `aab7db9`.
6. #40 `codex/issue19-diagnose-report` at `2733120`.
7. #42 `codex/issue30-concrete-base-synthetic-regression` at `e8450b0`.
8. #44 `codex/webapp-designer-console-prototype` at `fb7db78`.
9. #45 `codex/quarantine-day1-proof-assets` at `fa5524a`.
10. #41 `codex/endgame-delivery-ledger` at `e98b183`.

Conflict findings:

- #36/#37 overlap in CLI and report contracts. Local resolution kept input
  preflight, proof/report identity, rendered artifact requirements, and the
  layout/report-json interfaces.
- #39 overlapped cleanup CLI/readme wiring. Local resolution kept the cleanup
  command path plus the supported-input preflight imports.
- #42 overlapped report semantics. Local resolution kept concrete/foundation
  W5/W7 visual acceptance gates and structural helper evidence.
- #45 overlapped roadmap/report-safety wording. Local resolution kept the
  NO-GO posture, synthetic-proof caveat, private-regression caveat, and #29/#30
  blockers.
- #36 carried stale fake-PDF `poche --report-json` tests that #37 correctly
  rejected under input preflight. The rehearsal fixed those tests locally by
  generating valid minimal PDF-compatible `.ai` fixtures and asserting the
  fuller `arch-lw poche ...` command identity.
- The expanded #45 safety scan found stale private-derived references in
  research/postmortem docs; #45 was updated and pushed at `fa5524a`.
- The expanded #45 safety scan then found one retired proof phrase in #34's
  retrospective; #34 was updated and pushed at `911bcd5`.

Final rehearsal verification:

- Focused integrated Python/backend tests:
  `tests/test_run_report.py tests/test_proof.py tests/test_launch_safety_docs.py
  tests/test_apply_saas_poche.py webapp/tests/test_console_routes.py
  webapp/tests/test_routes.py webapp/tests/test_dev_console.py` -> 123 passed,
  1 Starlette/httpx deprecation warning.
- Feasible full Python suite:
  `pytest --ignore=tests/test_hatch_v05.py -q` -> 627 passed, 6 skipped,
  1 xfailed, 5 warnings.
- `ruff check src/ tests/ webapp/backend webapp/tests` -> pass.
- `git diff --check` -> clean.
- Public-surface private-path / retired-proof / premature-claim scan across
  README, release notes, retrospective, ship checklist, docs, MkDocs config,
  and webapp README -> no hits.
- `npm run check` in `webapp/frontend` -> 0 Svelte errors, 0 warnings.
- `npm run build` in `webapp/frontend` -> pass; Vite/SvelteKit emitted
  dependency export warnings but exited successfully.

Result: the current active green stack has no unresolvable integration blocker,
but it has real sequencing requirements. #45 must be included before any
public-surface clearance, and the #36/#37/#42 report-contract overlaps need an
explicit merge resolution if the PRs are landed separately. This rehearsal does
not close #29 or #30 and does not change posting/public proof from NO-GO.

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
- Proof packet contract names input, output, command, full-board rendered view,
  and at least one cut-mass/opening close-up.
- Public-safe proof status requires explicit W5/W7 acceptance metadata; clean
  artifacts alone are not posting clearance.
- Status never reports passed when outputs are missing, report says failed/no_go,
  raw proof contains private paths, report identity is missing, or rendered-view
  evidence is incomplete.
- Visual sentinels catch blank output, false fills, missing cut mass, weak
  outline/dot artifacts, unchanged before/after poché regions, and materially
  changed linework.

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
- Exported local review packets stay `needs_review` and `public_safe: false`
  until W5/W7 acceptance exists.

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
- Proof packet export is sanitized, raw reports are isolated, and public-proof
  status remains no-go without W5/W7 acceptance.
- Verification catches missing outputs, no-go reports, private paths, and false
  pass states.
- Geometry/poche produces accepted results on the private USC regression.
- #29 and #30 are resolved by real accepted evidence, not by synthetic demos.
- Packaging/desktop/plugin claims are limited to actually tested surfaces.

Until then, the correct status is: local engineering progress, no public launch.
