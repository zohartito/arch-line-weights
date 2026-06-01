# Session Retro

This file is a technical archive. Business planning content was removed for the
Day-1 public source release.

## What Changed Technically

- The project moved from color-only PDF stream rewriting toward layer-aware
  Illustrator workflows.
- The `apply-jsx` bridge became the reliable path for converted `.ai` files
  that Illustrator can open but that lack native `/NumBlock` data.
- The `apply-saas` CLI command became the fast native-payload path for
  Illustrator-saved `.ai` files with `/NumBlock`.
- Poché generation became conservative: high-confidence cut layers get filled;
  ambiguous geometry is reported or left for review.

## Verified Results

- `apply-jsx` on a private section export modified 512 paths across
  25 leaf layers with 0 errors.
- `arch-lw poche` then produced 30 poché polygons across 8 cut layers with
  0 failed layers.
- `apply-saas` on `macro_for_archlw.ai` processed a 98 MB / 1.28M-stroke axon
  fixture with exit 0 in about 1:53.

## Lessons Kept

- Converted `.ai` and native Illustrator `.ai` need different processing paths.
- Legacy Rhino PostScript `.ai` may require Illustrator re-save/conversion
  before v1 can process it.
- Large-file performance proof is not the same as section-cut proof.
- The local web app scaffold is useful for experiments, but the public release
  path is still the CLI from source/GitHub.
