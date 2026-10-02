# Research note: PaddleOCR for arch-line-weights

**Status:** reference / not adopted. **Captured:** 2026-06-05.
**Relevant to:** the raster/scanned-drawing input path · v2 "designer's eye" (label-driven role signal) · the verification-suite.

## What it is
[PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) (Baidu, open-source) is a full OCR toolkit: text
**detection** (DBNet-family), **recognition** (CRNN/SVTR), plus **PP-Structure** for layout analysis, table
recognition, and key-information extraction. Multilingual, with both lightweight (mobile) and server models.
Generally stronger than Tesseract on dense, small, structured text.

## Why it matters to arch-line-weights
The engine assigns line weights by **role**, keyed today on stroke **color** or **AIA layer names**. OCR is the
path to reading the **text on the drawing itself**, which unlocks:

1. **Label-driven role inference (v2 moat assist).** Title blocks, material tags ("CONCRETE", "CMU"), room
   labels, window/door tags ("W1", "D3"), dimension strings. When color/layer signals are absent, on-drawing
   text is another role signal (e.g. a hatch labelled "CONCRETE" → cut-mass poché).
2. **Raster / scanned / flattened input — the real niche.** Vector `.ai`/`.pdf` exports already carry
   machine-readable text (PyMuPDF extracts text + bounding boxes directly — **no OCR needed**). OCR earns its
   place only when the drawing is **rasterized, scanned, or text-outlined/flattened**, i.e. the input path
   where vector text is gone.
3. **Verification ground-truth (verification-suite).** OCR can check that expected labels/dimensions survive
   weight application (text not broken, moved, or obscured), and help build labeled test fixtures.

## Honest scope / caveats
- **Don't reach for OCR on vector input.** For the primary `.ai`/`.pdf` path, PyMuPDF already gives text +
  positions deterministically — faster, exact, no model. PaddleOCR is *specifically* for the raster path.
- **Heavy dependency.** It pulls in the PaddlePaddle deep-learning stack — a large, non-trivial dependency for
  an otherwise lightweight, deterministic tool. Only justified if raster/scanned-drawing support becomes a real
  product requirement.
- **Phase fit:** this is a **Phase-2 / v2 input-expansion** capability, not a Phase-0/1 need. The current moat
  plan (geometric role inference via shapely/opencv on vector geometry) does **not** require OCR.

## If/when we adopt
- Gate it behind an optional extra (`pip install arch-line-weights[ocr]`) so the core stays lightweight.
- Use PP-Structure for layout (separate title block / drawing area / legend), then run recognition only on the
  regions that matter.
- Start with the **label → role** assist on raster inputs; keep vector inputs on the PyMuPDF text path.

## Comparison context
- Sits alongside the other drawing-vision research in the repo: a **vision-LLM** route (MechVQA/MechVL — eval
  taxonomy + fine-tune baseline) vs the **deterministic geometry** route (doc 49 v2). PaddleOCR is a third,
  narrower tool: **text extraction**, not geometry or reasoning. It complements either moat route rather than
  replacing them.

## Links
- Repo: https://github.com/PaddlePaddle/PaddleOCR
