# Professional-Grade Roadmap

Date: 2026-05-05

This is the roadmap addendum after the `private section regression drawing` debugging
session. The main correction is philosophical: the program must behave like an
architectural drawing assistant, not a color-sorting script plus polygonizer.

## Product Thesis

`arch-line-weights` should become a professional-grade architectural graphics
engine:

```text
input drawing -> semantic diagnosis -> line hierarchy -> poché/material treatment -> reviewable output
```

After the iso axon poché failures, the engine order is sharper:

```text
input drawing
-> parse AI/Rhino layer geometry
-> infer architectural components
-> complete broken Make2D topology
-> apply line-weight hierarchy
-> generate structural poché/material graphics
-> visual QA + reviewable uncertainty report
```

The completion step must be shared. It is not a poché-only trick: the same
component knowledge that says "this is a missing slab cut face" also prevents
connectors, facade screens, and secondary steel from becoming too visually
heavy in the hierarchy.

The competitive advantage is not "make strokes thicker." The advantage is
encoding architectural graphic judgment:

- cut mass vs projection
- structural vs secondary vs surface systems
- foreground/middleground/background hierarchy
- poché only where solid material is truly cut
- explicit uncertainty and review points

## What We Have Done

### Working

- Headless AI-native payload pipeline via pikepdf + zstd.
- Layer-preserving `.ai` outputs.
- `apply-saas` line-weight rewrite.
- `apply-saas --poche` native poché injection.
- Progress feedback for long runs.
- `bridge-best` strategy selector.
- Per-layer bridge timeout/cap.
- Conservative low-confidence poché policy.
- RGB and CMYK native stroke-color support.
- Private reference-library plan for Ching/graphics books.
- Initial standards docs for ISO 128, Ching, NCS, poché conventions.

### Not Working Well Enough

- Poché still misses structural cut areas when Rhino exports open/partial loops.
- Hierarchy still relies too much on color for converted AI files.
- Steel connectors can become too heavy.
- Screens/cladding can still receive too much visual emphasis.
- No automated visual QA in Illustrator.
- No review UI for "I skipped these uncertain layers."
- Roadmap/docs were behind the real code state.

## Updated North Star

A student or architect should be able to drop in a Rhino/Illustrator drawing and
get a file that looks like it was cleaned by a careful human draftsperson:

- cut solid material reads immediately
- major section/profile edges dominate
- secondary structure is legible but not loud
- facade screens and panel texture recede
- glass stays light
- connectors are precise, not dominant
- uncertain geometry is flagged instead of faked

## Current Goal

The goal at the end of the current local-engine roadmap is not merely "the
command runs." It is:

```text
For a real Rhino/Illustrator section drawing, arch-lw produces a layer-preserved
.ai file whose line hierarchy and poché are good enough to print, and any
remaining uncertainty is reported clearly enough that the user can approve or
repair only the exact disputed components.
```

That means the current roadmap is done only when all of these are true:

- The engine handles RGB and CMYK Illustrator payloads.
- Structural cut mass is filled when the section truly cuts it, including
  beams/slabs/walls/roof/foundation with incomplete Make2D loops.
- Incomplete cut geometry is completed locally and plausibly, or reported as a
  specific repair candidate. Silent misses are failures.
- Non-solid cut elements get strong cut strokes without black poché.
- Facade texture, screens, connectors, glass, annotation, and entourage stay
  subordinate.
- The output has a review report: what was filled, inferred, skipped, and why.
- A real Illustrator/Computer Use visual check agrees with the report.

The web app belongs after this gate, not before it. A web app around an
untrustworthy engine only makes the wrong answer easier to upload.

## Immediate Test Gate

Yes, we need to test what we have made so far, but the sequence matters:

1. Unit/regression tests: already passing after the latest rules.
2. Real-file test: rerun `private section regression drawing.ai` with
   `--architectural --poche`.
3. Visual QA: inspect the known zones in Illustrator/Computer Use:
   - left retaining wall blob
   - rain screen/top roof blob
   - first-floor beam/slab black squares
   - right retaining wall/foundation
   - roof cut solidity/white stripes
   - connector/steel hierarchy
4. If it still misses true cut material, add a new rule/test before trying the
   same fix again.
5. Log the result to GitHub and the debug log.

The immediate acceptance target is not perfection on every possible drawing; it
is a print-credible result on Zohar's current ARCH 202B drawings with honest
review notes for any unresolved candidate.

## Phase 0 — Deadline-Safe Local Mode

Goal: make Zohar's current drawings usable now.

- [x] Stop hangs from `bridge-best`.
- [x] Stop low-confidence blobs from being injected.
- [x] Support RGB and CMYK native stroke colors.
- [x] Add first-pass `--architectural` mode.
- [x] Add structural poché whitelist/blacklist.
- [x] Add first-pass structural open-loop closure.
- [x] Add semantic hierarchy override for Rhino layer names.
- [x] Add first reusable Make2D completion module with candidate accept/reject
  metadata.
- [x] Add guardrails for helper-only false blobs and concrete/foundation
  over-expansion.
- [x] Add cut-stroke styling separate from poché eligibility, including RGB/CMYK
  stroke-color overrides and solid dash normalization for strong cut layers.
- [x] Add manual Illustrator poché workflow spec and map it to engine stages.
- [x] Add first rectangularity/fragment guards learned from prior private run/prior private run:
  large roof/slab/foundation candidates must look like material strips; tiny
  backup-wall fragments and large triangular roof surfaces are rejected.
- [x] Re-enable timber beam completion in a narrow way: small cut-anchored
  beam-end rectangles may be completed/pochéd, while large timber blobs remain
  rejected.
- [x] Add deadline workflow notes for hierarchy-only, safe poché, report
  generation, and manual `ARCH_LW_POCHE_CLEANUP` repair.
- [x] Preserve raw timber beam cells before union so repeated small beam-end
  rectangles can pass without admitting one large timber blob.
- [x] Add a per-run report that says:
  - injected
  - skipped
  - inferred closures
  - needs manual review

## Phase 1 — Architectural Rule Engine

Goal: encode the architectural graphics standard explicitly.

- [x] Create `docs/research/architectural-graphics-rulebook.md`.
- [x] Create `docs/research/lineweight-rulebook.md`.
- [x] Create `docs/research/poche-rulebook.md`.
- [x] Create `docs/research/entourage-rulebook.md`.
- [x] Create `docs/research/manual-illustrator-poche-workflow.md`.
- [x] Build first-pass layer semantic classifier independent of color.
- [x] Enforce blacklist-before-whitelist precedence so glazing, membranes,
  connectors, and cladding/rainscreen layers cannot become black poché because
  they also contain structural-looking tokens.
- [ ] Make color classifier fallback-only for known source types.
- [ ] Add fixture tests using real layer names from ARCH 202B and ARCH 211.

Core rules:

```text
true cut solid mass > foreground/profile > object edge > secondary structure > connector/detail > surface/cladding > texture/reference
```

## Phase 2 — Poché Geometry Engine

Goal: improve coverage without false positives.

- [x] Implement first-pass structural open-loop closure for simple open chains.
- [x] Add same-component visible/tangent completion evidence with accept/reject
  metadata.
- [x] Add anchored strip acceptance for large real roof/slab/foundation repairs.
- [x] Add morphology guards for triangular caps, compact foundation blobs, tiny
  backup-wall debris, and large irregular roof surfaces.
- [ ] Expand structural closure beyond simple open chains.
- [ ] Reject global `bbox` except explicit overrides.
- [ ] Add polygon plausibility scoring:
  - area
  - aspect ratio
  - layer material
  - endpoint topology
  - self-intersection risk
  - relation to neighboring structural layers
- [ ] Add closure debug output.
- [ ] Add per-layer before/after thumbnails if possible.
- [ ] Add manual `__POCHE_CLOSE__` fallback docs for deadline workflows.

## Phase 3 — Visual QA and Review

Goal: stop trusting counters.

- [ ] Add Illustrator-backed visual smoke check when Illustrator is available.
- [ ] Add a review report:
  - green: clean
  - yellow: inferred/needs review
  - red: skipped/failed
- [ ] Add `arch-lw diagnose drawing.ai`.
- [ ] Add layer-level screenshots or isolated preview exports.
- [ ] Build a "compare old/new" workflow for Codex Computer Use.

## Phase 4 — Reference Library Brain

Goal: use Ching/Ramsey/NCS books as a private local source of standards.

- [x] Define reference-agent workflow.
- [x] Add local SQLite FTS index builder.
- [x] Run full local indexing pass on all manifest books.
- [x] Dispatch book research agents.
- [ ] Render selected pages for private visual review.
- [x] Distill page-cited rules into tracked docs.
- [ ] Convert rules into tests and classifier behavior.
- [ ] Keep source PDFs and extracted full text out of GitHub.

## Phase 5 — Entourage and Presentation Layer

Goal: add scale/life while respecting hierarchy.

- [ ] Create a small consistent vector entourage library.
- [ ] Add isometric standing/walking/seated people.
- [ ] Add `ENTOURAGE` layer convention.
- [ ] Ensure entourage is never poché and never heavy cut weight.
- [ ] Add placement guidance:
  - floor plates
  - roof/terrace
  - near facade for scale
  - avoid dense cut zones

## Phase 6 — Professional Product Experience

Goal: turn the engine into a product people trust.

- [ ] Local CLI remains the power-user/proving-ground path.
- [ ] Web app only after the engine reports confidence honestly.
- [ ] Upload/process/download flow with:
  - file privacy
  - auto-delete
  - job progress
  - downloadable `.ai` and `.pdf`
  - review report
- [ ] Optional local helper later for privacy-sensitive studio users.

## Phase 7 — Team/Subagent Operating Model

Use subagents like a real product team:

- Standards agent: Ching/Ramsey/NCS rulebook.
- Geometry agent: open-loop closure and topology tests.
- Hierarchy agent: semantic layer classifier.
- Visual QA agent: Illustrator/Computer Use screenshot comparison.
- Docs agent: tutorials, troubleshooting, issue hygiene.
- Product agent: web app scope, pricing, onboarding.
- Research agent: competitive landscape and user interviews.

Reference-library agents are described in
`docs/research/reference-agent-workflow.md`. Their job is not to upload or
reproduce books; it is to turn local reading into page-cited rules that the
program can execute.

Next recommended subagent wave:

| Agent | Mission | Output |
| --- | --- | --- |
| Geometry repair | Build component-graph rules for right retaining wall/foundation and split roof/slab loops. | Tests + patch proposal for Issue #21. |
| Visual QA | Compare prior private run/prior private run/next output in Illustrator with known failure zones. | Screenshot notes + pass/fail checklist for Issue #7/#19. |
| Hierarchy standards | Convert remaining Ching/reference rulebook hooks into classifier tests. | Tests for cut mass, thin cut lines, glass, connectors, cladding, entourage. |
| Report UX | Design `arch-lw diagnose` / run report format. | Markdown/JSON schema for filled/skipped/inferred/review candidates. |
| Deadline workflow | Write the fastest safe user workflow for current school drawings. | CLI recipes for hierarchy-only, poché, no-poché, and review modes. |
| Product/web | Keep web-app scope honest behind engine readiness. | Vercel/web roadmap only after local print gate passes. |

## Current Recommendation

Do not build the web app yet.

First ship `--architectural` locally and use it on Zohar's current drawings.
When the engine produces reviewable, trustworthy output on real studio work,
then the web app becomes worth building.
