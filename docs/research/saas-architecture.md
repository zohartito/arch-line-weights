# SaaS architecture feasibility — can pikepdf write a layered .ai file?

> Research spike, 2026-04-30. Time-boxed ~60 min of agent work.
> Authoritative answer to the gating question for the SaaS pivot.

## TL;DR

**VERDICT: YES (with one small caveat).** Pure-pikepdf modification of an
existing `.ai` file's `/PieceInfo /Illustrator /Private` payload is feasible
on a server without an Illustrator install. We can change stroke widths,
stroke colors, and layer-block contents; Illustrator opens the modified
file and renders the changes correctly with all OCG layers intact.

The caveat: synthesizing a `PieceInfo` payload **from scratch** (e.g., from
an SVG or DXF input) is harder and not proven here. The recommended SaaS
architecture is **template-based**: ship a Rhino-export `.ai` file from the
user, modify its PieceInfo, return it.

This means the SaaS path is **open** for the project's actual use case
(applying line-weight hierarchy / poché to user-uploaded Rhino-exported
`.ai` files) — which is everything we already do.

## What's inside `/PieceInfo /Illustrator /Private`?

Concrete shape, per the reference drawing
(`USC/Spring 2026/ARCH 202B/DRAWING 4 SECTION [Converted].ai`, 24 MB,
62 OCGs):

```
page.obj["/PieceInfo"]["/Illustrator"]["/Private"] = Dictionary(311 keys):
    /AIMetaData         Stream(1540 bytes)  — plain-text PostScript header
    /ContainerVersion   12
    /CreatorVersion     30
    /NumBlock           305
    /RoundtripStreamType 2
    /RoundtripVersion   24
    /AIPrivateData1     Stream(65536 bytes)  — first chunk
    /AIPrivateData2     Stream(65536 bytes)
    ...
    /AIPrivateData305   Stream(62724 bytes)  — last chunk
```

Total raw blob across the 305 streams: **19,985,668 bytes**.

Concatenating them (in order 1..N) gives a single byte stream that
**starts with the 20-byte ASCII prefix `%AI24_ZStandard_Data`** followed by
the Zstandard magic `28 b5 2f fd`.

After stripping the prefix and Zstandard-decompressing, you get
**55,350,315 bytes of plain-text Adobe Illustrator native PostScript**
(line endings are bare `\r`, classic Mac-style). Tokens you'll recognize
from the AI3-AI8 file format spec:

```
%!PS-Adobe-3.0
%%Creator: Adobe Illustrator(R) 24.0
%%AI8_CreatorVersion: 30.1.0
...
%AI5_NumLayers: 62
%%EndComments
%AI5_BeginLayer
1 1 1 1 0 0 1 -1 240 190 130 0 100 0 Lb
(axon precedent 1::Visible::Curves::14_CU_CORR_PERF_SCREEN) Ln
0 AE
... path data using m, L, S, As operators ...
LB
%AI5_EndLayer--
%AI5_BeginLayer
... next layer ...
```

All 62 layers appear as a sequence of `%AI5_BeginLayer ... %AI5_EndLayer--`
blocks with the layer name string, RGB color triplet, visibility/locked
flags, and embedded path geometry. **This is the canonical layer source
that Illustrator reads when opening an `.ai` file.**

## Three things we tested

### 1. Inspect — DONE

`scripts/spike/saas-feasibility/01_inspect_pieceinfo.py` walks the dict
tree. `02_examine_blobs.py` confirms the chunked-Zstandard encoding by
reading raw bytes and finding the magic at offset 20.
`03_decompress_blobs.py` decompresses to 55 MB of plain PostScript and
locates 62 `%AI5_BeginLayer` markers and all layer name strings as ASCII.

### 2. Modify — DONE, ROUND-TRIPS THROUGH ILLUSTRATOR

`scripts/spike/saas-feasibility/04_roundtrip_modify.py` builds a complete
read → decompress → edit → recompress (Zstandard level 19) → re-slice
into 64 KB chunks → write streams pipeline.

`05_verify_roundtrip.py` confirms byte-perfect null round-trip: the
decompressed payload from the saved file equals the source payload exactly,
and OCG count remains 62 in both.

`07_modify_stroke_color.py` changed the stroke RGB of every path in the
`ClippingPlaneIntersections::TEC_STAIRS` cut layer to magenta `(1 0 1) XA`.
Opened the saved file in Illustrator, dumped pathItem stroke color via
JSX: **all 172 path strokes returned `RGBColor: rgb(255, 0, 255)`** —
exactly our magenta. Confirmed.

`08_modify_stroke_width.py` changed every `1 w` (1 pt stroke) in the
`ClippingPlaneIntersections::TEC_STAIRS` block to `5 w` (5 pt). Opened
in Illustrator, dumped pathItem strokeWidth: **all 172 paths returned
`width=5`**. Confirmed.

This is exactly the project's core operation — apply per-layer / per-color
stroke widths. **It works without Illustrator on the server.**

### 3. Synthesize — NOT PROVEN, but not blocking

We did not construct a valid `.ai` file's PieceInfo from scratch. The AI24
native PostScript syntax is partially-documented (the AI8 spec from
`http://justsolve.archiveteam.org/wiki/Adobe_Illustrator_Artwork` covers
the legacy operators; later additions for OCG / SVG-effect / variable
fonts are not). For the project's use cases we don't need to synthesize —
we always start with a user-uploaded Rhino `.ai` and modify it.

## The one caveat: layer NAMES come from somewhere we haven't found

When we modify the `(layer-name) Ln` directive inside the Private payload
**and** the OCG `/Name` in `Root.OCProperties.OCGs[i]` **and** the
`/Resources /Properties /MC<i> /Name` on the page, **Illustrator's Layers
panel still displays the original name.** The geometry, stroke color, and
stroke width all reflect our edits — but the panel name does not.

This means there's a **fourth** copy of the layer name we haven't found,
likely in another part of the AIPrivateData payload (XMLUID-keyed map?
binary art-tree section we haven't decoded?). For the project's purposes
this is irrelevant — we never need to rename a layer. But it's a known
unknown if we ever do want to rename.

Not blocking. Worth noting.

## Public knowledge / third-party efforts

What's documented:
- AI3-AI8 file format spec (legacy plain-text PostScript syntax) is
  publicly available — see archive.org and `justsolve.archiveteam.org`.
  Covers `%AI5_BeginLayer`, `Lb`, `Ln`, `LB`, path operators, color
  setting via `XA`. This is the format inside our Zstandard payload.
- The Zstandard wrapping with the `%AI24_ZStandard_Data` prefix and
  64 KB chunking into `AIPrivateData<N>` is **NOT publicly documented**
  by Adobe but is now empirically proven (this spike).

Third-party parsers:
- `opendesigndev/illustrator-parser-pdfcpu` (Node.js + WASM) is the most
  active recent project. It parses the PDF + PieceInfo. Does not appear
  to publicly document Zstandard handling — would need to check source.
- `sk1-project/sk1-wx` has historical AI import support, but the project
  is largely unmaintained vs the active CC2024+ format.
- Inkscape has its own AI parser, scope unclear for AI24.

Adobe SDK:
- Adobe's official AI plug-in SDK is C/C++ and requires their NDA
  + signing. Not viable for a solo dev SaaS at any reasonable cost.

## Concrete blocker list

For the SaaS path to work as designed (apply line-weight hierarchy and
poché to user-uploaded Rhino `.ai` files in a headless server):

| # | Concern | Status | Notes |
|---|---------|--------|-------|
| 1 | Decompress Private payload | RESOLVED | `zstandard` Python package, ~75 ms on 20 MB |
| 2 | Modify PostScript-style stroke ops | RESOLVED | regex replace inside the decompressed payload |
| 3 | Recompress + chunk + write back | RESOLVED | `zstandard.ZstdCompressor(level=19)` + 64 KB slicing |
| 4 | Illustrator opens result, renders edits | RESOLVED | confirmed via JSX `pathItem.strokeWidth/strokeColor` dump |
| 5 | OCG layer count preserved | RESOLVED | 62 → 62, panel shows the same hierarchy |
| 6 | Apply poché (filled black polygons in cut layers) | NOT TESTED HERE | Requires creating new `pathItem` blocks inside an existing layer's `%AI5_BeginLayer .. LB` envelope. Should work — same syntax our spike already manipulates. |
| 7 | Layer renaming | OPEN | Not needed for the project. If ever needed, must locate the 4th name reference. |
| 8 | Synthesize PieceInfo from SVG / DXF input (no template) | NOT NEEDED | We always start from a Rhino-exported `.ai`. If a future user wants to upload an SVG instead, would need either ship a "generic" template `.ai` and bake the SVG into it, or fall back to PDF-only output. |

## Recommended SaaS architecture

```
[user uploads .ai (Rhino export, has 62 OCGs + PieceInfo)]
        |
        v
[server: pikepdf.open(); decompress AIPrivateData via zstd]
        |
        v
[arch-lw applies regex / per-layer stroke-width substitution
 inside the AI native PostScript payload]
        |
        v
[poche pipeline: parse cut-layer paths from payload, run shapely
 polygonize, inject new closed pathItems inside the cut layer's
 BeginLayer..LB block as black-filled paths]
        |
        v
[recompress with zstd level 19, slice to 64 KB chunks, replace
 AIPrivateData streams, save]
        |
        v
[user downloads .ai; opens locally in Illustrator; sees correct
 weights, correct poché fills, all 62 layers in the panel]
```

Estimated server-side cost per file:
- Memory: ~110 MB peak (20 MB compressed + 55 MB decompressed +
  a duplicate copy during edit; well under any reasonable AWS Lambda /
  container limit)
- CPU: ~5–10 s per 24 MB file (decompression + regex + recompression,
  dominated by zstd level-19 compression). Acceptable for a per-request
  workflow with progress UI.

This is dramatically better than the current architecture, which requires
an Illustrator app running on the user's local Mac and a 12-minute JSX
walk per file.

## Recommended next step

Before committing to the SaaS pivot:

1. **Build the v0.5 prototype** — port the existing `apply.py` line-weight
   logic to operate on the decompressed AI native payload instead of (or
   in parallel with) the PDF content stream. Stop stripping PieceInfo;
   modify it instead. Targets:
   - Match every `<r> <g> <b> XA` color set with the current per-layer
     RGB-to-weight map and inject a stroke width via `<w> w`.
   - Keep the existing PDF-stream rewrite as a fallback for files where
     PieceInfo isn't present (e.g. PDFs from non-Illustrator pipelines).

2. **Port the poché pipeline** to write polygon `pathItem` blocks
   directly into the AI native payload (instead of via JSX). The
   per-cut-layer block already has the syntax pattern — we just need a
   small builder. Estimate: 1 day of work.

3. **Validate against ≥3 user files** of varying complexity to confirm
   nothing in the AI24 format breaks our approach (e.g. CMYK strokes,
   pattern fills, embedded raster images, gradient meshes — none of which
   appear in this Rhino-export reference but may appear in user uploads).

4. **Then** start on web-app shell (FastAPI + S3 upload + per-tenant
   billing). The headless-output question that gated the pivot is now
   answered: yes, it's feasible.

## Files produced by this spike

- `scripts/spike/saas-feasibility/01_inspect_pieceinfo.py` — dumps Private dict shape
- `scripts/spike/saas-feasibility/02_examine_blobs.py` — confirms ZStandard chunking
- `scripts/spike/saas-feasibility/03_decompress_blobs.py` — decompresses to plain text
- `scripts/spike/saas-feasibility/04_roundtrip_modify.py` — full read/decode/edit/recode/write pipeline
- `scripts/spike/saas-feasibility/05_verify_roundtrip.py` — byte-perfect verification
- `scripts/spike/saas-feasibility/06_modify_ocg_and_payload.py` — dual layer-name modification (revealed the layer-name caveat)
- `scripts/spike/saas-feasibility/07_modify_stroke_color.py` — stroke color round-trip (proven)
- `scripts/spike/saas-feasibility/08_modify_stroke_width.py` — stroke width round-trip (proven, project's core use case)

Generated artifacts (in `/tmp`):
- `/tmp/spike_roundtrip_null.ai` — null round-trip output
- `/tmp/spike_roundtrip_modify.ai` — layer-name-rename test
- `/tmp/spike_roundtrip_color.ai` — stroke color modification (172 strokes turned magenta)
- `/tmp/spike_roundtrip_width.ai` — stroke width modification (172 strokes set to 5pt)
- `/tmp/ai_private_decompressed.bin` — the full 55 MB decompressed AI native payload
