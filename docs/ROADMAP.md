# Roadmap

This is a public engineering roadmap for the MIT-licensed CLI in this
repository. It is not a product plan, pricing plan, or hosted-service
commitment.

## Release Posture

- The core CLI is MIT-licensed. See `LICENSE` and `NOTICE.md`.
- Current install path is source/GitHub only:
  `pipx install git+https://github.com/zohartito/arch-line-weights`.
- PyPI auto-publish is deferred. Any disabled release workflow concerns PyPI
  automation only; it does not change the MIT license for the source here.
- The `webapp/` directory is a local experimental scaffold. There is no hosted
  public service for this release.
- Bluebeam review is unverified. Use Illustrator and Acrobat for the validated
  Day-1 review loop.

## Proof Posture / Launch Gate

Posting/public proof is **NO-GO** unless W5/W7 explicitly accepts a public-safe
proof packet. Synthetic proof does not close #30. The private USC regression
stays private and is not represented by committed screenshots, PDFs, raw reports,
or local file paths.

Foundation/concrete cut mass can remain unfilled while other poché evidence
looks plausible. That gap is the root launch blocker in GitHub issue #30.
Issue #29 remains blocked behind #30 and proof-truth review.

Current durable GitHub coordination points:

- W2 verifier/research PR: #34
- Verification-core draft PR: #37 (input diagnostics, proof-check, console)
- Verification-core draft PR: #36 (layout-jsx, bridge reports)
- Root launch blocker: #30
- Proof-truth blocker: #29
- Fixture/visual regression work: #31
- Verification report work: #32
- Rhino export assistant: #33, deferred

Draft PRs are savepoints, not release clearance. Useful report and bridge work
does not close #30 until foundation/concrete coverage is fixed or explicitly
accepted by W5/W7 with path-free public evidence.

See `RETROSPECTIVE.md` for wins, failures, causes, and operating changes.

## Evidence That Still Holds

- The Illustrator bridge path can modify a converted section file and preserve
  enough layer structure for review.
- The poché path can produce fills on high-confidence cut layers with structured
  reporting.
- A local-only large axon stress run showed `apply-saas` could process a very
  large stroke count in about 1:53. That is performance evidence only, not
  section/poché proof.

## Known Input Caveats

- `apply-saas --poche` needs a native Illustrator `/NumBlock`.
- PDF-only or converted `.ai` files should use `apply-jsx`, then
  `arch-lw poche`.
- Legacy Rhino PostScript `.ai` exports may need to be opened and re-saved or
  converted before the current v1 tools can process them.
- The fast `apply` path can flatten Illustrator layer structure because it
  rewrites the PDF stream instead of the Illustrator native payload.

## Near-Term Technical Work

- Decide #30 before any new posting: either fix foundation/concrete poché or
  document partial foundation/concrete coverage as a known limitation that is
  visible in report JSON, tests, and public copy.
- Keep #29 blocked until #30 has verifier-backed proof truth.
- Treat W3's current limitation/report work as implementation evidence, not
  acceptance. W5 still needs to re-QA the proof packet before the blocker moves.
- Keep PR #36 ruff/tests green before any merge-readiness decision; treat every
  new branch head as requiring fresh checks.
- Finish the verification report contract: changed, skipped, failed, why,
  input provenance, command manifest, stroke delta, raster diff, poché
  coverage, missed-fill detection, false-fill detection, and an exportable
  review packet.
- Keep the Day-1 USC wall section as a private regression fixture until its
  C2/C3 foundation crops are fixed or explicitly documented.
- Build public proof from a repo-safe synthetic Make2D fixture instead of
  private course drawings.
- Keep PR #36 draft until the layout/report bridge, CI, and #30 decision are
  reconciled.
- Keep GitHub as the live ledger: PR bodies should be refreshed when the branch
  head changes, and issue comments should say when they are snapshots.
- Expand fixtures for Make2D layer naming variants only after the verifier can
  explain current proof failures.
- Keep the source install path and CLI help honest until PyPI publishing is
  deliberately re-enabled.
- Continue improving local preview tooling without presenting it as proof for
  native-payload edits.

## Bridge Contract Follow-Up

Current PR #36 has useful bridge work, but the contract still needs to be
tightened before it becomes proof infrastructure:

- The Rhino selected-export manifest should prove the export, not just describe
  the current selection. It needs selected-only evidence, object/layer counts,
  units, view/projection, export artifact path, file size/hash, warnings, and
  privacy-safe source identifiers.
- `layout-jsx` should report skipped and failed Illustrator movement work:
  locked/hidden/unusable items, resize failures, translate failures, final
  bounds, and whether the final artwork fits the requested margin.
- `bridge-rhino-ai` should always write a bridge report when a stage fails.
  If layout, hierarchy, or poché raises, the stage report should still exist,
  mark `failed` or `no_go`, include `why` / `next_action`, and exit nonzero.
- Dry-run and real-run reports should keep one stable top-level shape:
  `schema_version`, `source`, `summary`, `artifacts`, `stages`, `why`, and
  `next_action`.
- W5 still needs real Illustrator QA for the first-run converted `.ai` path.
  Mock tests and successful layout are useful, but they are not proof that
  foundation/concrete poché is correct.

This bridge contract supports #31 and #32. It does not change the launch gate:
#30 remains the root proof decision, and #29 stays blocked behind W5 acceptance.
