# Rhino Make2D Export Assistant Recommendation

Issue: #33
Date: 2026-06-06

## Recommendation

Build no new Rhino app surface for the current release. Keep the existing
`integrations/rhino/export_selected_make2d_manifest.py` helper as the
recommended thin assistant, and evolve it only after the proof and visual QA
loop catches real failures reliably.

The assistant should remain optional. Its job is reproducible source capture,
not proof acceptance and not a replacement for `proof-check`, `diagnose`, or
`visual-check`.

## What The Assistant Should Do Later

### Standardize Export Settings

The helper should guide users toward a repeatable Rhino export path:

- require an orthographic/layout/detail view when model scale matters
- export selected Make2D curves only
- prefer PDF-compatible `.ai` or `.pdf` handoff paths that Illustrator and
  `arch-lw` can inspect
- record the intended sheet/artboard target so `layout-jsx` can normalize it
- warn when selection, view, or export result is likely incomplete

This can be incremental around the existing script. A toolbar, panel, or
Grasshopper surface is not required before the source/proof loop is trusted.

### Record Source Metadata

The manifest should keep public-safe operational metadata:

- Rhino app/version when available
- source model units
- active view name and orthographic state
- selected object count
- per-layer object counts
- export path basename plus local full path in the local-only manifest
- next command hint for `layout-jsx` or `bridge-rhino-ai`

Do not commit local manifests from private drawings. Public fixtures can commit
redacted manifests or synthetic manifests that contain no private paths.

### Flag Legacy PostScript Exports

Legacy PostScript `.ai` exports should be detected as early as possible.

If a selected export starts with `%!PS`, the assistant should warn that this is
not a supported modern PDF-compatible Illustrator container and should hand the
user to one of these paths:

- open in Illustrator and Save As a modern PDF-compatible `.ai`
- export as PDF, then use `layout-jsx` or `apply-jsx` as appropriate
- rerun Rhino export with settings that produce a PDF-compatible file

This matches the current `arch-lw` unsupported-input behavior and avoids
sending unreadable legacy files into later proof steps.

### Hand Off To Illustrator And `arch-lw`

The handoff should remain explicit and auditable:

```bash
arch-lw bridge-rhino-ai \
  --input selected-make2d.ai \
  --artboard 24x36in \
  --fit fit \
  --margin 0.5in \
  --preset section \
  --source rhino \
  --apply-jsx \
  --poche \
  --report-dir proof
```

For hierarchy-only runs, use `layout-jsx` followed by `apply-jsx`. For
foundation/concrete or USC launch proof, continue to `poche`, `diagnose`,
`proof-check`, and `visual-check`.

## Do Not Build Yet

Do not build a new Rhino panel/app before these are true:

- proof-check can validate the relevant public fixtures
- private visual QA has a redacted `visual-check` summary
- #29/#30 launch proof limitations are either accepted or explicitly documented
- legacy PostScript and unsupported input diagnostics remain visible

A larger assistant would otherwise hide unfinished verification work behind a
more comfortable workflow.

## Close Criteria For #33

#33 can close when this recommendation is merged and linked from the issue.
Future implementation should be tracked in a new issue only after proof
acceptance or an explicit scope cut.
