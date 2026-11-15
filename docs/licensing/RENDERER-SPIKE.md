# PDFium preview spike

Recorded 2026-11-15. Technical feasibility evidence only; no production renderer change.

## Reproduce

From the repository root, using its venv:

```bash
.venv/bin/python -m pip install pypdfium2
.venv/bin/python scripts/spike_pdfium_preview.py
```

The optional package is not added to `pyproject.toml` or `uv.lock`. Output stays under ignored
`.venv/pdfium-spike/`: `fixture/` and `control/` each hold PNGs for both renderers, a side-by-side
comparison and a difference image; `results.json` contains versions, samples and pixel metrics.
Only the committed synthetic fixture and a generated synthetic control are read.

## Licensing evidence

Installed `pypdfium2==5.15.2` metadata states
`License: BSD-3-Clause, Apache-2.0, dependency licenses`; no License-Expression or license
classifier was supplied. The [upstream licensing documentation](https://pypdfium2.readthedocs.io/en/stable/readme.html#licensing),
accessed 2026-11-15, describes pypdfium2 under Apache-2.0 / BSD-3-Clause, PDFium under a BSD-style
license, and additional licenses for its bundled dependencies. Binary redistribution requires
review of the notices shipped with the selected build. This does not establish that every
component of a PDFium wheel has only Apache/BSD terms.

## Method and results

Python 3.11.7, macOS arm64; PyMuPDF 2.1 and pypdfium2 5.15.2.
Page 1, 144 DPI, RGB on white, 4x supersampling followed by Pillow Lanczos downsampling,
400 x 400 output. The PyMuPDF side uses the existing `PyMuPDFRenderer.render_page` directly,
including its validation overhead. Each renderer gets one warm-up and five measured calls,
alternating order. Timings include open/render/RGB conversion/downsampling and exclude imports,
PNG encoding and comparison. These are local measurements, not a speed guarantee.

| Input | PyMuPDF median | PDFium median | Mean absolute channel difference (0-255) | Pixels with any channel difference >12 | Ink pixels (<240 in any channel), PyMuPDF / PDFium |
| --- | --- | --- | --- | --- | --- |
| `tests/fixtures/eval/synthetic-cut.ai` | 0.010109 s | 0.008877 s | 0 | 0% | 0 / 0 |
| Generated visible control | 0.010240 s | 0.008545 s | 0.115081 | 0.400000% | 23,100 / 23,101 |

The requested fixture has an empty public PDF content stream. Both renderers therefore return
blank white images. Equality here verifies opening/page sizing only; it cannot establish stroke
or poché fidelity. The script explicitly records `blank_output: true` for that case.

The separate generated control contains 0.08/0.25/0.5/1.0 pt strokes, black and gray rectangles,
and a curve. Both outputs were visually inspected: all these marks were present and aligned;
pixel differences remain around rasterized edges. The script exits non-zero if the
generated control renders blank. If the two renderers return different dimensions it records the
mismatch and skips the pixel comparison, rather than rescaling to hide it; that case still exits 0.

Assessment: PDFium is a plausible preview candidate for this narrow synthetic case. The test
does not cover text/fonts, image masks, transparency, crop/rotation, OCG visibility, complex
color spaces, large pages, malformed files, or multi-page resource limits. Preview budget
validation also currently uses PyMuPDF. A complete replacement needs those cases and the
validation path addressed before a renderer swap can be proposed.

## Could pikepdf alone cover `inspect.py`?

Partially, with more implementation and validation required for general PDFs. The existing
`_inspect_ai` already reads page dimensions, document information and OCG names, scans basic
RGB stroke/fill operators with `q`/`Q` state, and has an Illustrator payload fallback.

On the generated control, `_inspect_ai` and `_inspect_pdf` returned matching dimensions,
7 drawings, 5 strokes, width/color distributions and two fill colors. On the requested `.ai`
fixture, the pikepdf path reports one native-payload stroke while the PyMuPDF public-page path
reports zero drawings. These paths do not inspect identical representations for that file.

The regex walker is not equivalent to `page.get_drawings()`: general PDFs need interpretation
of nested Form XObjects and their resources/transforms, graphics state, clipping/transparency,
and non-RGB colors. pikepdf can expose the underlying objects and operators, but that semantic
walker and its parity tests would be project work. It also cannot replace the preview renderer;
[pikepdf's documentation](https://pikepdf.readthedocs.io/en/latest/topics/images.html#data-first-rendering-second)
states that it does not rasterize vector drawing or composite transparency. Text/outline
indexing is another replacement task; this spike tests neither PDFium inspection nor text
extraction. No complete PyMuPDF replacement is established.
