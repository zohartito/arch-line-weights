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

## Proof Posture

- Section-bridge and large-file stress runs have been exercised locally.
  Public proof assets are not committed. Posting/public proof is **NO-GO**
  unless W5/W7 explicitly accepts the packet. Synthetic proof does not close
  #30.
- The private USC regression stays private and is not represented by committed
  screenshots, PDFs, raw reports, or local file paths.
- Prior private dogfood showed useful bridge and large-file signals, but those
  private filenames and artifacts are intentionally not public proof claims.

## Known Input Caveats

- `apply-saas --poche` needs a native Illustrator `/NumBlock`.
- PDF-only or converted `.ai` files should use `apply-jsx`, then
  `arch-lw poche`.
- Legacy Rhino PostScript `.ai` exports may need to be opened and re-saved or
  converted before the current v1 tools can process them.
- The fast `apply` path can flatten Illustrator layer structure because it
  rewrites the PDF stream instead of the Illustrator native payload.

## Near-Term Technical Work

- Improve reports for low-confidence poché candidates.
- Add clearer diagnostics when `/NumBlock` is missing.
- Expand fixtures for Make2D layer naming variants.
- Keep the source install path and CLI help honest until PyPI publishing is
  deliberately re-enabled.
- Continue improving local preview tooling without presenting it as proof for
  native-payload edits.
