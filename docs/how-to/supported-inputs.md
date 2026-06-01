# Supported inputs

`arch-lw` works with vector exports that can be read as PDF-like drawing data,
native Illustrator private data, or through a local Illustrator bridge. Pick the
path from the file you actually have, not just from the extension.

This release is source/GitHub-first. It is not a PyPI package, not a hosted
service, and does not yet make a Bluebeam workflow claim.

## Input kinds

| Input kind | How to recognize it | Best path |
|---|---|---|
| Native Illustrator `.ai` | Modern Illustrator file with private Illustrator payload metadata, including `/NumBlock` | `inspect`, `apply-saas`; optionally `apply-saas --poche` |
| PDF-only or converted `.ai` | Opens in Illustrator as converted, often shown with `[Converted]`; lacks `/NumBlock` | `inspect`, `apply-jsx`, then `poche` if needed |
| Plain `.pdf` | PDF export without Illustrator private data | `inspect`, `apply` |
| Legacy Rhino PostScript `.ai` | Older Rhino/Make2D-style `.ai` that PDF readers may reject as missing a trailer dictionary | Open in Illustrator and Save As a modern `.ai` first |
| Reference/report/image-only `.pdf` | Opens as a PDF but `inspect` finds no vector drawing marks or rewriteable strokes | Treat as unsupported for line-weight output; export the drawing sheet/vector file instead |

The extension alone is not enough. A file named `.ai` can be native
Illustrator, PDF-only/converted, or legacy PostScript-style data.

## Command matrix

| Command | Native Illustrator `.ai` with `/NumBlock` | PDF-only or converted `.ai` | Plain `.pdf` | Legacy Rhino PostScript `.ai` |
|---|---|---|---|---|
| `inspect` | Supported for diagnostics | Supported when the file can be read as PDF-like data | Supported | Save As first if the parser cannot open it |
| `apply` | Supported, but may flatten Illustrator layers | Supported, but may flatten Illustrator layers | Supported | Save As first |
| `apply-jsx` | Supported when Illustrator can open the file; layer-preserving bridge | Preferred for converted `.ai`; layer-preserving bridge | Not the primary PDF path | Save As first, or use against an already-open Illustrator conversion when appropriate |
| `apply-saas` | Preferred headless layer-preserving path | Not supported without native `/NumBlock` | Not supported | Save As first to create a modern native `.ai` |
| `poche` | Supported on readable layer-aware output; usually use `apply-saas --poche` directly for native files | Supported after `apply-jsx` output when cut layers are present | Not the primary path | Save As first |

## Non-drawing or no-op PDFs

Some PDFs open cleanly but are not useful drawing exports: slides, reports,
image-only references, and blank sheets can have no vector marks for
`arch-lw` to rewrite. `arch-lw inspect` now labels those cases with
`input_format.has_drawings`, `input_format.is_no_op`, and
`input_format.no_drawing_reason`.

If `apply` or `apply-saas` sees no rewriteable stroked geometry, it stops
before writing an output file. That is intentional: a clean no-op PDF should
not look like a successful line-weight transformation.

## What `/NumBlock` means

Native Illustrator `.ai` files can include a private Illustrator payload. In
this project, `/NumBlock` is the practical signal that the headless
native-payload path has data to edit.

`apply-saas` uses that native payload so it can preserve Illustrator layer data
without driving Illustrator. If `/NumBlock` is missing, the file may still look
like an `.ai`, but it is not the right input for `apply-saas`.

## Converted and PDF-only `.ai`

Some `.ai` files are really PDF-lineage files from Illustrator's point of view.
They may open as `[Converted]`, or they may lack the native private payload even
though the extension is `.ai`.

For these files, use the Illustrator bridge:

```bash
arch-lw apply-jsx drawing.ai --preset usc --source rhino
arch-lw poche "drawing HIERARCHY-jsx.ai" --source rhino --style solid
```

Use `poche` only when the drawing has section-cut layers that the topology pass
can reason about. For line weights alone, `apply-jsx` is the layer-preserving
step.

## Legacy Rhino PostScript `.ai`

Older Rhino exports can be PostScript-style `.ai` files rather than modern
Illustrator/PDF-compatible `.ai`. PDF parsers may fail before `arch-lw` can
inspect or rewrite the drawing.

Convert these files in Illustrator:

1. Open the legacy `.ai` in Adobe Illustrator.
2. Choose **File -> Save As**.
3. Save a new `.ai` copy with PDF-compatible Illustrator data.
4. Run `arch-lw inspect` on the saved copy.
5. Choose `apply-saas` for native `/NumBlock` files, or `apply-jsx` for files
   Illustrator opens as converted.

Work on a copy. Keep the original Rhino export untouched until the converted
file opens cleanly and the output is visually checked.

## v0.2 diagnostics

The v0.2 diagnostic work is intended to preflight the input kind and recommend a
next step when a command receives the wrong file shape. Treat those diagnostics
as guidance, not as a stable contract for exact wording or final command
behavior.

Common recommendations are:

| Diagnostic situation | Recommended next step |
|---|---|
| Missing native `/NumBlock` on an `.ai` passed to `apply-saas` | Use `apply-jsx`, then `poche` if poché is needed |
| Parser cannot open an older Rhino `.ai` | Open in Illustrator and Save As a modern `.ai` copy |
| Plain PDF has no vector drawing marks | Export the actual vector drawing sheet instead of a reference/report PDF |
| You need preserved Illustrator/Rhino layers | Use `apply-jsx` or `apply-saas`, not the fast `apply` path |
| You only need a fast final stroke-weight rewrite | Use `inspect`, then `apply` |
