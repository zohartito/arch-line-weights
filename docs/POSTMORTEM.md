# Postmortem — How v0.1 shipped a layer-flattening bug

> Written 2026-04-29, the day v0.1 shipped, after the user opened the output
> file in Illustrator and saw all 62 Rhino layers collapsed into a single
> "Layer 1". This document exists so future contributors don't repeat the
> same chain of reasoning.

## What we set out to do

User had a 24 MB Rhino-exported `.ai` (USC ARCH 202B section drawing). Every
stroke was 1.0 pt; the only differentiator between a "section cut" line and a
"material hatch" line was the stroke RGB color. We needed to apply
architectural line-weight hierarchy to it.

## What we tried, in order

| # | Approach | Outcome |
|---|----------|---------|
| 1 | ExtendScript `do javascript` over `app.documents[0].pathItems` setting `strokeWidth` per item | Exponential slowdown: first 10K paths in 79 s, second 10K in 132 s, third 10K in 280 s. ETA ~2 hours and rising. Killed Illustrator. |
| 2 | Spawned three sub-agents in parallel: ExtendScript performance research, UXP-from-CLI viability, alternative vector tools | Findings: no `suspendHistory` in IL ExtendScript; UXP not exposed for Illustrator in 2026; pikepdf is the right Python tool for the job. |
| 3 | pikepdf rewrites the PDF content stream — inject `<width> w` before every stroke operator, color-keyed via the most recent `RG`. Strip `/PieceInfo` so Illustrator re-parses from the modified PDF. | **Worked in 110 s. Shipped as v0.1.** |
| 4 | User opens the result in Illustrator. **All 62 Rhino layers gone — file shows 1 layer.** | Bug filed against ourselves. |

## Root cause

`.ai` files are PDF files with extras. The extra is `/PieceInfo /Illustrator
/Private` — a per-page dictionary of `AIPrivateData###` streams that contain
Illustrator's native representation of the artwork (layers, groups, swatches,
appearances). When Illustrator opens an `.ai`, it reads PieceInfo and **ignores
the PDF content stream** for everything except rendering preview.

We stripped PieceInfo to force Illustrator to honor our PDF-stream stroke-width
edits. That worked for stroke widths but destroyed layer metadata, because:

- The PDF *does* still have an `/OCProperties /OCGs` block listing all 62
  Rhino layers (we never touched it). `pikepdf` confirms it's there in both
  the BACKUP and the v0.1-output file.
- But Illustrator's PDF parser (used when there's no PieceInfo) treats OCGs
  as visibility groups *unless* the user opens via `File > Open` with
  `pDFPreserveLayers` enabled. Without that, it flattens every OCG into the
  default Layer 1.

So our v0.1 file had:
- The **right stroke widths** (in the PDF stream)
- The **right OCG metadata** (in `/OCProperties`)
- But no signal to Illustrator on `app.open()` to honor either

## Why we missed it

The README's "Limitations" section did mention layer flattening as a trade-off
of stripping PieceInfo. We just decided wrong on the default. Two anti-patterns
in our reasoning:

1. **We optimized for our test case, not the user's workflow.** Our test was
   "does the file open and show new stroke widths in Illustrator?" — pass.
   The user's test was "can I still click a layer to refine its weight?" —
   fail. The user's mental model came from the Layers panel, not from a
   visual diff.

2. **We dismissed the slow-but-correct path too quickly.** ExtendScript's
   exponential slowdown looked unbounded in our first run because we hadn't
   tried `maximumUndoDepth=1`. With that single pref change + Outline-view
   toggle + per-layer iteration (62 chunks instead of 340K monolithic), the
   JSX path completes in 11 min — entirely acceptable for a one-off render.

## The fix (v0.2)

Two-mode tool:

- **`arch-lw apply-jsx`** (now the recommended default for `.ai`): hands a JSX
  to Illustrator, walks each layer, applies the semantic-classifier weight to
  every `pathItem` in that layer, saves. Slow but **preserves every layer**.
- **`arch-lw apply`** (still there): pikepdf path. Faster. Use when layer
  fidelity doesn't matter (e.g., you're rendering a final PNG, not editing
  further).

Plus a **semantic layer-name classifier** (`arch_line_weights.layer_classify`)
that recognizes Rhino's `Visible::ClippingPlaneIntersections::*` as the cut
tier regardless of material — this is much stronger signal than color.

## Lessons we want to keep

1. **Layer fidelity > raw speed**, for any tool whose users will iterate on
   the output. A 10-min run that preserves the user's mental model beats a
   2-min run that destroys it.
2. **The user's verification ritual matters.** "Open in Illustrator and look
   at the Layers panel" should have been part of our acceptance test.
3. **Sub-agents in parallel are how we move fast on unknowns.** The five
   research agents this session (ExtendScript perf, UXP, alternative tools,
   visual preview, Rhino integration, multi-format compatibility,
   architectural standards, competitive landscape, poché conventions) gave
   us in 90 minutes the kind of survey that takes a solo dev a week.
4. **Document failed approaches in the repo.** This file exists so v0.3+
   contributors don't try `pikepdf + strip PieceInfo` again, blame
   themselves when it flattens layers, and burn another afternoon.
5. **Two modes is fine; one default is required.** Tools with `--method`
   options that have sharp foot-guns must pick a safe default. Layer-aware
   is the safe default for arch students; pikepdf is opt-in.
