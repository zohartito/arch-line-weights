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

## Verification Posture

- Prior private dogfood produced useful bridge, poché, and large-file signals.
- Those private filenames and artifacts are intentionally omitted from this
  public technical archive.
- Posting/public proof remains NO-GO unless W5/W7 explicitly accepts it.
- Synthetic proof does not close #30, and the private USC regression stays
  private.

## Lessons Kept

- Converted `.ai` and native Illustrator `.ai` need different processing paths.
- Legacy Rhino PostScript `.ai` may require Illustrator re-save/conversion
  before v1 can process it.
- Large-file performance proof is not the same as section-cut proof.
- The local web app scaffold is useful for experiments, but the public release
  path is still the CLI from source/GitHub.
