# Retrospective

This file records program lessons from the Day-1 public-release and
verification-core reset. It is intentionally blunt: the goal is to avoid
repeating the same proof, coordination, and launch mistakes.

## 2026-05-31 - Verification Core Reset

### What worked

- The source/GitHub release posture became honest: MIT core, no PyPI claim,
  local experimental webapp only, Bluebeam unverified, and no hosted-service
  claim.
- GitHub became the durable coordination surface. Issues #29-#35 and PRs #34
  and #36 now carry the launch state, branch state, blockers, and decisions.
- W2 correctly reframed the product value: trustworthy verification for messy
  Rhino / Illustrator / PDF exports, not one-click prettification.
- W3 turned that direction into a real verification-core branch with a Day-1
  Make2D manifest, proof harness, structured poché report work, cut-geometry
  summary work, and an Illustrator layout JSX bridge.
- The strict xfail for the foundation/concrete miss is useful. It keeps a real
  product defect visible instead of smoothing it into a marketing story.
- The sanitation gate worked. A public branch initially exposed private/local
  paths, GitHub issue #35 caught it, and the latest branch was re-reviewed
  before PR #36 was opened as draft.
- The W5 recapture gate prevented premature posting. It retired the original
  screenshot pack as internal failure evidence instead of public proof.

### What didn't

- The original Day-1 proof pack over-weighted screenshots and under-weighted
  verifier evidence. It looked plausible before it was actually trustworthy.
- We treated "some poché polygons were produced" too much like "the section is
  correct." The foundation/concrete miss proves those are different claims.
- Public proof copy drifted ahead of evidence. Phrases implying full cut-mass
  coverage were not safe while C2/C3 foundation areas still failed.
- The first W3 branch carried private absolute paths in a public fixture
  manifest and harness assertion. That should have been caught before pushing.
- Issue mappings and commit references drifted across windows. Some comments
  cited the wrong W7 commit before correction to `e69bfcd`.
- PR #36 reached a useful draft state while CI still had a ruff failure. A
  draft PR is acceptable as a savepoint, but it must not become release
  clearance by accident.
- The Rhino export assistant idea kept trying to become attractive too early.
  It does not solve verifier trust and stays deferred.

### Why

- The program had two different definitions of success competing at once:
  "ship a compelling public post" and "prove the drawing transformation is
  true." The first can be satisfied with curated images; the second requires
  structured evidence.
- Architecture drawing outputs are visually deceptive. A full-board screenshot
  can improve while a critical cut mass remains wrong.
- Legacy Rhino/Illustrator/PDF workflows are messy enough that input class,
  provenance, command path, layer behavior, and fallback behavior must be
  reported explicitly.
- Private proof artifacts were created before public-fixture boundaries were
  formalized. That made local paths and source context leak into branch content.
- Multi-agent work created real progress, but without a single ledger it also
  created stale commit references, stale issue mappings, and unclear ownership.

### What we'd do differently

- Start every release proof with a verifier contract before making screenshots:
  input provenance, command manifest, changed/skipped/failed/why, stroke delta,
  raster diff, poché coverage, missed-fill detection, false-fill detection, and
  an exportable review packet.
- Keep social/posting copy locked until the verifier is green or explicitly
  reports known limitations. Do not imply complete cut-mass coverage without
  C2/C3 evidence.
- Split proof lanes earlier:
  - public gallery from a repo-safe synthetic Make2D fixture;
  - private USC wall section as regression evidence until it passes or is
    documented as a limitation.
- Gate every public fixture branch with a privacy scan before pushing or
  opening a PR. Manifests should use fixture ids, relative paths, hashes, and
  file sizes, not local source paths.
- Treat draft PRs as savepoints only. A draft PR with a useful branch and a
  failing lint check is coordination progress, not release readiness.
- Keep #30 as the root decision until it is closed by evidence:
  - fix the foundation/concrete poché behavior; or
  - document partial foundation/concrete coverage as a product limitation and
    make the report/copy say so.
- Keep #33 deferred until verification is boring. Export automation should
  serve the verifier, not distract from it.
- Update GitHub issues/PRs immediately when control-plan commits or branch
  heads change. The GitHub ledger should be the source of truth, not chat.

## 2026-05-31 - Live GitHub Ledger Reconciliation

### What worked

- W3 reacted to the proof-gate feedback with concrete follow-up commits: the
  branch now starts encoding the foundation/concrete no-go limitation,
  stabilizes the Rhino bridge verification path, and normalizes `layout-jsx`
  runtime reports.
- The issue structure kept the important decisions visible: #30 remains the
  root proof decision, #29 stays blocked behind proof truth, #31 owns fixtures,
  #32 owns report semantics, and #33 stays deferred.
- Updating the roadmap and retrospective in the repo makes the program memory
  reviewable in GitHub instead of leaving it buried in chat.

### What didn't

- GitHub comments and PR bodies drifted as the branch moved. Several live
  comments still described PR #36 at the older layout-bridge head after newer
  W3 commits landed.
- PR #34's body also lagged its own branch by still naming the earlier research
  head after the roadmap/retrospective commit was pushed.
- There are too many duplicate state ledgers. The same NO-GO decision appears
  across PR bodies, issue comments, strategy notes, roadmap text, and chat,
  which makes stale references likely.
- CI is still not clean on the current draft PR. A ruff failure is easy to
  dismiss during coordination, but it must remain a merge blocker.

### Why

- Multiple workers were writing snapshots while the W3 branch was still moving.
  A comment that was correct at 04:35Z became stale after later commits.
- Comments are append-only operational notes, but we treated them like current
  state. The PR body is the better live place for head, scope, and check status.
- The team was trying to preserve every finding, which is good, but did not
  clearly separate durable decisions from moment-in-time observations.

### What we'd do differently

- Use the PR body as the canonical live branch ledger: current head, scope,
  check state, merge blockers, and launch blockers.
- Use issue comments for durable decisions and acceptance criteria, not every
  intermediate branch snapshot.
- Every snapshot comment should include "observed at" language or avoid exact
  heads entirely unless it will be maintained.
- When a new W3 commit addresses a W2/W5 finding, immediately update the PR body
  and the roadmap before adding more issue comments.
- Keep ruff and test state in the merge-readiness checklist so coordination
  success cannot accidentally become technical clearance.

## 2026-05-31 - Bridge Contract Follow-Up

### What worked

- The latest W3 commits moved the bridge toward honest report semantics:
  failed/no-go `layout-jsx` runs no longer look like clean success in the
  normalized runtime report path.
- Reviewing PR #36 against its live remote head kept the audit grounded. The
  useful conclusion is not "the bridge is bad"; it is "the bridge needs a
  stage contract before W5 can trust it as proof infrastructure."
- The existing issue split still helps: #31 owns fixture/provenance, #32 owns
  report semantics, #30 owns proof truth, and #33 stays deferred.

### What didn't

- The Rhino export manifest on the PR head is still too thin. It records
  selection count, layer counts, and view state, but not the selected export
  artifact, units, object-type evidence, hashes, warnings, or privacy-safe
  provenance needed for repeatable proof.
- `layout-jsx` still silently drops some Illustrator movement failures. Locked,
  hidden, unusable, resize-failed, and translate-failed items need counts and
  reasons in the report.
- `bridge-rhino-ai` can lose the most useful artifact when a stage raises:
  the bridge report is written only after stages complete. A failed bridge
  should still leave a report with `failed` / `no_go`, `why`, and
  `next_action`.
- Layout success kept trying to sound like proof success. Centering artwork on
  a board is valuable, but it does not prove C2/C3 foundation/concrete poché.

### Why

- The implementation was growing from happy-path orchestration outward, while
  proof QA needs failure-first contracts. The report has to survive the exact
  moments where the command cannot finish normally.
- Rhino, Illustrator, PDF-compatible `.ai`, converted `.ai`, and legacy
  PostScript `.ai` are different input classes. If the manifest and report do
  not preserve that distinction, reviewers will infer more than the evidence
  can support.
- Multi-stage bridge work creates multiple ways to produce a plausible output
  and still miss the launch blocker. The only reliable answer is structured
  stage evidence, not screenshots or exit codes alone.

### What we'd do differently

- Define the bridge report schema before adding more bridge stages. Every
  stage should emit the same basic facts: input, output, artifact existence,
  hash/size when real, status, why, and next action.
- Treat skipped/failed Illustrator movement as first-class report data from
  the start. Silent catches are acceptable only if they become visible counts.
- Make the Rhino manifest prove the selected export: selected-only state,
  object/layer/type counts, units, view/projection, export settings, artifact
  hash/size, and redacted source identity.
- Require an error-path artifact test for every happy-path bridge test. If a
  command can fail, there should be a report that explains that failure.
- Keep saying explicitly that bridge/layout progress supports the verifier but
  does not close #30. Proof acceptance belongs to the verifier and W5, not the
  existence of a new bridge command.
