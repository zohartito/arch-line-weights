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
  reports known limitations. No "full section poché" language without C2/C3
  evidence.
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
