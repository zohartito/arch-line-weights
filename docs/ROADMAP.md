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

Public posting is **NO-GO** until proof QA is verifier-backed.

The Day-1 proof pack is now treated as internal failure evidence, not public
promotion material. The earlier screenshots exposed a real quality gap:
foundation/concrete cut mass can remain unfilled while other poché evidence
looks plausible. That failure is tracked as the root launch blocker in
GitHub issue #30. Issue #29 remains blocked behind #30 and proof-truth review.

Current durable GitHub coordination points:

- W2 verifier/research PR: #34
- W3 verification-core draft PR: #36
- Root launch blocker: #30
- Proof-truth blocker: #29
- Fixture/visual regression work: #31
- Verification report work: #32
- Rhino export assistant: #33, deferred

PR #36 is a draft savepoint, not release clearance. Its current branch includes
structured poché report work, cut-geometry summary work, and an Illustrator
layout JSX bridge, but CI still needs attention and the #30 product decision is
not resolved.

See `RETROSPECTIVE.md` for the current wins, failures, causes, and operating
changes.

## Evidence That Still Holds

- The Illustrator bridge path can modify a converted section file and preserve
  enough layer structure for review.
- The poché path can produce fills on high-confidence cut layers and now has
  a structured reporting direction.
- The axon stress proof passed on `macro_for_archlw.ai`: 98 MB / 1.28M
  strokes, `apply-saas` exit 0, about 1:53 runtime.

The axon run remains large-file performance evidence. It is not section or
poché evidence, because that fixture had no `ClippingPlaneIntersections` cut
layers.

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
  document partial foundation/concrete coverage as a known limitation.
- Keep #29 blocked until #30 has verifier-backed proof truth.
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
- Expand fixtures for Make2D layer naming variants only after the verifier can
  explain current proof failures.
- Keep the source install path and CLI help honest until PyPI publishing is
  deliberately re-enabled.
- Continue improving local preview tooling without presenting it as proof for
  native-payload edits.
