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

## Current Launch Gate

Posting/public proof is **NO-GO** unless W5/W7 explicitly accepts the packet.
Synthetic proof can exercise the harness, but it does not close #30. The
private USC regression stays private and is not represented by committed
screenshots, PDFs, raw reports, or local file paths.

The retired Day-1 proof pack is internal failure evidence, not public promotion
material. It exposed a real quality gap: foundation/concrete cut mass can remain
unfilled while other poché evidence looks plausible. That failure is tracked as
the root launch blocker in GitHub issue #30. Issue #29 remains blocked behind
#30 and proof-truth review.

Current durable GitHub coordination points:

- W2 verifier/research PR: #34
- W3 verification-core draft PR: #36
- Root launch blocker: #30
- Proof-truth blocker: #29
- Fixture/visual regression work: #31
- Verification report work: #32
- Rhino export assistant: #33, deferred

PR #36 is a draft savepoint, not release clearance. Its current branch includes
structured poché report work, cut-geometry summary work, an Illustrator layout
JSX bridge, and follow-up work to encode the foundation/concrete no-go
limitation, stabilize the Rhino bridge verification path, and normalize
`layout-jsx` runtime reports. That is useful progress toward honest report
semantics, but it does not close #30: the foundation/concrete path still needs
either a real visual fix or a documented limitation that proof QA explicitly
accepts.

Prior private dogfood showed useful bridge and large-file signals, but those
private filenames, counts, timings, and artifacts are intentionally not public
proof claims. See `RETROSPECTIVE.md` for the current wins, failures, causes,
and operating changes.

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
