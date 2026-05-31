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
- `arch-lw designer-console` is a local prototype only. It wraps the existing
  engine in a browser UI, but it is not posting clearance, not App Store work,
  and not a Windows support claim.
- Bluebeam review is unverified. Use Illustrator and Acrobat for the validated
  Day-1 review loop.

## Validated Proof Points

- Section proof passed through the Illustrator bridge path:
  `apply-jsx` on `WALL SECTION [Converted].ai` modified 512 paths across
  25 leaf layers with 0 errors, then `arch-lw poche` produced 30 poché
  polygons across 8 cut layers with 0 failed layers.
- Axon stress proof passed on `macro_for_archlw.ai`: 98 MB / 1.28M strokes,
  `apply-saas` exit 0, about 1:53 runtime.

The axon run is large-file performance evidence. It is not section evidence,
because that fixture had no `ClippingPlaneIntersections` cut layers.

## Known Input Caveats

- `apply-saas --poche` needs a native Illustrator `/NumBlock`.
- PDF-only or converted `.ai` files should use `apply-jsx`, then
  `arch-lw poche`.
- Legacy Rhino PostScript `.ai` exports may need to be opened and re-saved or
  converted before the current v1 tools can process them.
- The fast `apply` path can flatten Illustrator layer structure because it
  rewrites the PDF stream instead of the Illustrator native payload.

## Near-Term Technical Work

- Local web prototype: keep improving the designer console around explicit
  stage actions, public-safe summaries, and existing report validators.
- Signed Mac desktop beta: future packaging/signing/notarization work after
  the local workflow is accepted.
- Windows desktop beta: future packaging/testing work; do not claim Windows
  support until this path is tested on Windows.
- Rhino plugin / Illustrator panel: later native surfaces should reuse the
  console's stage/report contracts instead of inventing a separate proof gate.
- Improve reports for low-confidence poché candidates.
- Add clearer diagnostics when `/NumBlock` is missing.
- Expand fixtures for Make2D layer naming variants.
- Keep the source install path and CLI help honest until PyPI publishing is
  deliberately re-enabled.
- Continue improving local preview tooling without presenting it as proof for
  native-payload edits.
