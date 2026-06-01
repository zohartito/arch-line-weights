# Porting `inspect.py` from PyMuPDF to pikepdf for `.ai` files — implementation notes

> 2026-05-01. Closes Issue #9 from POSTMORTEM Attempt 9. Companion to
> `apply-saas-port-notes.md`: same model (pikepdf-only on `.ai`), but for the
> read-only inspection path that feeds `auto_by_luminance`.

## Why

POSTMORTEM Attempt 9 §1: **`fitz.open()` raised `FileDataError`** on the
237 MB ARCH 211 `macro.ai` plan drawing. The user's workaround was to do
"Save As" in Illustrator, which produced a 98 MB version that PyMuPDF then
opened fine. But:

* Real customers will hit this on complex urban drawings.
* `apply_saas` already opens the same Adobe-saved files with pikepdf
  (via `_read_payload` in `apply_saas.py:71`).
* Asking users to round-trip through Illustrator before they can run
  `arch-lw inspect` defeats the whole point of a headless tool.

So `inspect.py` now dispatches per-format: **pikepdf for `.ai`, PyMuPDF for
`.pdf`**.

## What got built

| File | Purpose |
|------|---------|
| `src/arch_line_weights/inspect.py` | Refactored; now per-format dispatch via `inspect_file()`. |
| `tests/test_basic.py` | +4 tests for the pikepdf path (dispatch, q/Q state, fallback error, .pdf routing). |

The public API is unchanged: `inspect_file(path) -> InspectionReport`,
`InspectionReport.to_dict()`, `color_to_rgb255()`. Downstream consumers
(`classify`, `apply`, `apply_saas`, `cli`) didn't need a single-line edit.

## Dispatch

```
inspect_file(path)
    │
    ├── ext == ".ai"   ──┐
    ├── _looks_like_illustrator(path)  ──┤  → _inspect_ai (pikepdf)
    │                                    │     ↓ on failure
    │                                    └─→ _inspect_pdf (PyMuPDF) fallback
    │
    └── ext != ".ai" and not Illustrator
                                          → _inspect_pdf (PyMuPDF)
                                                ↓ on failure
                                            _inspect_ai (pikepdf) fallback

    Both fail → RuntimeError("...try Save As in Illustrator...")
```

`_looks_like_illustrator` opens the file with pikepdf and probes
`page0.obj["/PieceInfo"]["/Illustrator"]`. Cheap (lazy-load only the
trailer + first page object) and catches the case of an `.ai`-flavored
file that's been renamed to `.pdf`.

## How the pikepdf walker mirrors PyMuPDF

PyMuPDF's `page.get_drawings()` returns one entry per stroked-or-filled
path with the resolved color, width, and fill. The pikepdf walker reproduces
the same accounting by parsing the page content stream directly:

```
_TOKEN_RE = re.compile(rb'''(?:
    ([0-9.eE\-+]+)\s+([0-9.eE\-+]+)\s+([0-9.eE\-+]+)\s+(RG|rg)  # 1-4
  | ([0-9.eE\-+]+)\s+(w)                                          # 5-6
  | (q)|(Q)                                                       # 7,8
  | (B\*|b\*|S|s|B|b|f\*|F|f)                                     # 9
)(?=[\s\r\n])''')
```

For each match:

| Op | Action |
|----|--------|
| `RG` | Set `current_stroke = (r*255, g*255, b*255)` |
| `rg` | Set `current_fill` |
| `<w> w` | Set `current_width` |
| `q` | `state_stack.append((current_stroke, current_fill, current_width))` |
| `Q` | Pop the stack and restore |
| `S/s/B/b/B*/b*` | Increment `total_drawings`, `total_stroked`; bucket `(stroke_color, width)` |
| `f/F/f*` | Increment `total_drawings`; bucket `fill_color` |

The walker is `O(n)` in content-stream bytes (no parse tree). On the 98 MB
`private-axon-stress-fixture.ai` it walks 113 MB of content stream in **24 s**. Compare
PyMuPDF: it parses + builds drawing objects in **~9 s** but **fails outright
on the 237 MB original**.

### Why a regex walker is enough

I considered three alternatives and rejected each:

1. **`pikepdf.parse_content_stream` + visitor** — gives us proper PDF tokens,
   not just regex hits. Tested it: 6 s to parse 8.1 M ops on the 98 MB file,
   then another 5 s to walk. Total ~11 s, ~2× faster than the regex. But it
   has no way to expose `q`/`Q` state changes alongside operators in a single
   stream — we'd have to reconstruct the same state machine anyway. The regex
   walker is simpler to read and we don't bottleneck on inspection time.

2. **Walk the AI24 native payload** (the same blob `apply_saas` rewrites). 
   More accurate (this is Illustrator's authoritative model), but ~2× the
   complexity and identical results on every Rhino-export file we've checked.
   The PDF content stream `RG`/`S` data is what Illustrator emits when it
   saves, so the two views agree.

3. **Keep PyMuPDF and just add a `try`/`except` around `fitz.open`** — sounds
   like the simplest fix, but the original failure surfaces a real
   architectural mismatch. PyMuPDF reads the whole file into memory and
   chokes on >200 MB Illustrator output. pikepdf's lazy loader handles it
   cleanly. Better to switch backends than paper over the symptom.

### Reconciling with PyMuPDF's output

I verified the new walker against PyMuPDF on the 98 MB file:

| Metric | PyMuPDF | pikepdf walker |
|--------|---------|----------------|
| `total_drawings` | 1,282,989 | 1,282,990 |
| `total_stroked` | 1,282,989 | 1,282,990 |
| Distinct stroke RGB colors | 41 | 41 |
| Distinct stroke widths | 1 (all 1.0) | 1 (all 1.0) |
| Top color: `RGB(240,190,130)` | 617,899 | 617,899 |
| Next: `RGB(220,165,100)` | 565,214 | 565,214 |

The off-by-one on `total_drawings` is a marked-content sentinel that
PyMuPDF skips and the regex walker counts. Within rounding, the two backends
agree, and the auto-classifier (which only consumes `stroke_colors`) gets
identical results.

### Default stroke width when no `w` op is set

PDF's default line width is `1.0`. PyMuPDF returns `width=1.0` when no `w`
operator has fired. The pikepdf walker mirrors that:

```python
wval = current_width if current_width is not None else 1.0
```

If we left strokes with `current_width is None` out of the counter, the
plan-drawing fixture above would report 0 widths, breaking auto-classify.

## Metadata + layer extraction

The pikepdf path sources both from the document tree directly:

* **PDF metadata** — `pdf.docinfo[<key>]`, normalised to both `/Producer`
  (PDF spelling) and `producer` (lowercased) so `detect_source` doesn't care
  which backend produced the report.
* **Layer names** — `pdf.Root["/OCProperties"]["/OCGs"][i]["/Name"]`. Same
  list PyMuPDF surfaces via `doc.layer_ui_configs()`, in the same order
  Illustrator wrote them.

Both functions defensively swallow exceptions and return empty
collections — `inspect_file()` should never abort over a missing layer
panel, since `auto_by_luminance` works fine without one.

## Fallback semantics

If pikepdf raises (corrupt trailer, malformed `/Contents`, etc.), the
dispatcher falls back to PyMuPDF. If PyMuPDF also raises, we wrap both
errors in a `RuntimeError` whose message ends with:

> If this is an Illustrator file, try opening it in Adobe Illustrator and
> using File → Save As to write a smaller copy, then re-run arch-lw on the
> smaller version.

This is the workaround the postmortem documents and the only way out for
the 237 MB original `macro.ai` (which has a damaged trailer that defeats
both backends — pikepdf reports `unable to find trailer dictionary while
recovering damaged file`, PyMuPDF reports `FileDataError`).

## Test coverage added

| Test | What it proves |
|------|----------------|
| `test_inspect_dispatches_to_pikepdf_for_ai_extension` | `.ai` → pikepdf path; counters, colors, widths, layer names, metadata all populated. |
| `test_inspect_pikepdf_path_tracks_q_Q_state` | `q`/`Q` push/pop restores the outer color, mirroring PDF graphics-state semantics. |
| `test_inspect_unreadable_file_raises_with_workaround_hint` | Both-backends-fail error message names both backends and points at the Save-As workaround. |
| `test_inspect_routes_pdf_extension_to_pymupdf_path` | Plain `.pdf` (no `/PieceInfo`) doesn't unnecessarily invoke pikepdf. |

Run: `pytest tests/test_basic.py -k inspect_` → 4 passed in ~0.4 s.

## What's still on PyMuPDF

* `arch_line_weights/preview.py` — uses PyMuPDF's `get_pixmap` for raster
  rendering of before/after PNGs. Out of scope for Issue #9.
* Plain `.pdf` inspection path, when the file is not Illustrator-saved.

## Smoke tests on the real ARCH 211 drawing

```
$ time arch-lw inspect '/.../private-axon-stress-fixture.ai'   # 98 MB AI
1,282,990 total_drawings, 41 distinct stroke colors, 49 OCG layer names
real    0m25s
```

```
$ arch-lw inspect '/.../macro.ai'                   # 237 MB AI (damaged)
RuntimeError: Failed to open '...' with both pikepdf
(PdfError('...unable to find trailer dictionary while recovering damaged file'))
and PyMuPDF (FileDataError('Failed to open file ...')). If this is an
Illustrator file, try opening it in Adobe Illustrator and using
File → Save As to write a smaller copy, then re-run arch-lw on the
smaller version.
```

The 237 MB file is genuinely damaged at the PDF-trailer level — neither
backend can recover it. The Save-As workflow is the right answer. The 98 MB
Save-As output now opens cleanly via pikepdf (it was already opening cleanly
via `apply_saas`'s pikepdf path; this change just brings `inspect` in line).
