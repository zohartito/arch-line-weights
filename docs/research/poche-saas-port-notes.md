# Porting `poche.py` to operate on the AI native payload — implementation notes

> 2026-04-30. Companion document to `apply-saas-port-notes.md`. Records the
> design decisions and edge cases encountered while implementing
> `src/arch_line_weights/poche_saas.py` — the headless poché injector that
> writes filled black polygons directly into the decompressed AI native
> PostScript payload, eliminating the JSX dependency.

## What got built

| File | Purpose |
|------|---------|
| `src/arch_line_weights/poche_saas.py` | New module — pure-Python headless poché injector. Re-uses `poche.polygonize_layer()` for the compute step; replaces the JSX apply step with byte-level surgery. |
| `src/arch_line_weights/cli.py` | Added `--poche` and `--poche-overrides` flags to the existing `apply-saas` subcommand. |
| `tests/test_apply_saas_poche.py` | 17 unit tests covering synthesis, envelope location, injection, round-trip, and end-to-end via `apply_saas_with_poche`. |
| `docs/research/poche-saas-port-notes.md` | This file. |

`poche.py` and `apply_jsx.py` were *not* modified — the new module is
strictly additive.

## Design

The pipeline mirrors the existing `apply_saas.py` rewrite-payload pattern, but
extends it with a second pass that *inserts* (rather than replaces) bytes:

```
read .ai → concat AIPrivateData<i> streams → strip 20-byte prefix
                                            → zstd-decompress
                                            ↓
                                            
        [enumerate cut-layer paths from payload]
                                            ↓
                                            
        [polygonize_layer per cut layer (poche.py)]
                                            ↓
                                            
        rewrite_payload(payload, mapping)  ←  width rewrite (B6)
                                            ↓
                                            
        inject_poche_polygons(payload, polys_by_layer)
                                            ↓
                                            → zstd-compress (level 19)
                                            → prepend prefix
                                            → 64 KB chunk → write streams
```

### AI native PostScript fragment for a filled polygon

For each shapely.Polygon we emit:

```
\r0 0 0 1 1 0 0 0 Xa\r       # fill color = CMYK 0 0 0 K=1, RGB 0 0 0 (black)
0 R\r                         # render-mode reset
<x0> <y0> m\r                 # moveto first vertex
<x1> <y1> L\r                 # lineto
<x2> <y2> L\r
... 
<xN-1> <yN-1> L\r
f\r                           # closepath + fill
```

Notes:

* `Xa` (lowercase `a`) is the *fill* color setter. It takes 8 floats:
  CMYK (`<C> <M> <Y> <K>`) followed by RGB (`<R> <G> <B>`) and a
  composite-alpha indicator (`<...> Xa`). Black uses `0 0 0 1 1 0 0 0`.
  This is distinct from `XA` (uppercase) which sets *stroke* color — the
  same operator family the B6 stroke-width rewriter already touches.
* `f` is the closepath-and-fill operator from the legacy AI3-AI8 file
  format spec. It closes the current subpath (regardless of whether the
  caller emitted a duplicate first/last vertex) and fills it.
* The fragment starts and ends with `\r` so it can be spliced into any
  AI layer block without disturbing the surrounding tokens.
* Duplicate consecutive vertices and the closing-vertex duplicate that
  shapely adds to `Polygon.exterior.coords` are stripped before emission
  to keep the payload terse.

### Locating a layer's `%AI5_BeginLayer ... LB` envelope

The decompressed payload structure for one layer is:

```
%AI5_BeginLayer\r
<flags...> Lb\r
(<full layer name>) Ln\r
... layer attribute setup ...
... path data, S / f / B operators ...
LB\r
%AI5_EndLayer--\r
```

`find_layer_envelope(payload, name)` searches for the
`(<name>) Ln` marker (this disambiguates layers that happen to share path
data shapes), then walks backward to the nearest `%AI5_BeginLayer` and
forward to the matching `LB`. Returns `(begin_offset, ln_offset, lb_offset)`.

The injection point is the `lb_offset` — new path operators are spliced
*before* `LB` so the fills become the last children of the layer. In AI's
drawing model, "later in the stream" = "drawn on top", so this gives the
classic poché look (fill on top of strokes, cut reads black).

### Reusing `polygonize_layer()`

The compute step (segments → polygons) is unchanged from the existing
`poche.py` JSX pipeline. We import `polygonize_layer` and run the same
rescue ladder (linemerge → snap-tolerance sweep → auto-bridge →
concave_hull → bbox), so any layer that polygonized correctly under the
JSX apply path will polygonize identically here.

The only divergence is at the apply step: instead of baking polygons into
JSX as `setEntirePath()` calls, we synthesize the equivalent AI native
PostScript and splice it in.

### Right-to-left splicing

Because every splice inserts new bytes (no deletion), naively splicing
left-to-right would invalidate the offsets of every subsequent layer. We
collect all (lb_offset, name, polys) triples, sort them by `lb_offset`
descending, and splice from the end of the payload to the start. Each
splice only changes offsets *forward* of itself, which we've already
processed.

### Layer-path enumeration without JSX

`enumerate_layer_paths_from_payload(payload)` walks the decompressed
payload directly and dumps `{layer_name: [[[x, y], ...], ...]}` — exactly
the shape `polygonize_layer()` expects. This replaces the JSX-side
`dump_cut_geometry.jsx` for the SaaS code path. Implementation:

* Match every `(<name>) Ln\r` marker via regex
* For each match, take the bytes from the marker to the next `\rLB\r`
* Split on `\r`, walk tokens, and build a polyline per `S`-terminated
  sub-path (the same termination logic the AI native format uses)

Curve operators (`C`, `c`) are approximated by their endpoint, mirroring
what JSX dumps as `pathPoint.anchor` (the on-curve point). This is
sufficient for poché since the cut layers we care about contain only
straight-line segments from Rhino exports.

### `_is_cut_layer` filter

Mirrors the `shouldDump` heuristic in `poche.py`'s JSX template:

```python
"CLIPPINGPLANEINTERSECTIONS" in name.upper()
    and "GLASS" not in name.upper()
    and "IGU" not in name.upper()
```

This excludes window/glazing layers, which we never poché.

## Edge cases discovered during implementation

### 1. Shapely's auto-closed exterior

`shapely.Polygon.exterior.coords` always returns a closed ring (last
vertex == first). AI's `f` operator already does closepath; emitting the
duplicate would produce a zero-length segment that some renderers don't
like. We strip the duplicate before emission.

Tested via `test_synthesize_square_emits_4_vertices` — a 4-vertex input
emits 1 `m` + 3 `L` (4 distinct vertices, not 5).

### 2. Consecutive-duplicate vertex dedup

The synthesize path dedupes consecutive duplicates explicitly. This is
defensive for shapely outputs that pass through `simplify(tolerance=0)`
or similar pipelines that can leave coincident points.

### 3. Lookbehind-with-alternation regex

I initially wrote a `(?<!GLASS|_IGU)` regex for the cut-layer filter,
which Python rejects because lookbehind needs fixed-width patterns. The
fix is the simpler `_is_cut_layer()` function with explicit substring
checks, which is also clearer.

### 4. Right-to-left splice ordering

Inserting bytes shifts all subsequent offsets. Sorting `(lb_offset, ...)`
tuples descending and splicing back-to-front avoids the recompute.

### 5. `\r LB \r` boundary

The synthesized fragment ends with `f\r`, and `LB` is preceded by `\r`
in the original payload. So when we splice the fragment in, the
`\r` of `f\r` and the `\r` of `\rLB\r` *do not* combine — the result is
`f\r\rLB\r` (a blank line between them). AI's tokenizer treats blank
`\r`-delimited lines as no-ops, so this is harmless. The test
`test_inject_poche_polygons_splices_before_lb` verifies the `f` byte sits
exactly one `\r` before the `LB` marker.

### 6. End-to-end round-trip via pikepdf

The synthetic `.ai` test fixture (`write_synthetic_test_ai`) uses
`pikepdf.Pdf.new()` + manual `/PieceInfo /Illustrator /Private` dict
construction. `pdf.make_stream(c)` may apply a `/FlateDecode` filter on
save (this was caught earlier during the B6 port and fixed via
`read_bytes()` instead of `read_raw_bytes()` in `_read_payload`). The
fixture goes round-trip through that same code path — the
`test_apply_saas_with_poche_end_to_end_on_synthetic_fixture` test exercises
the full pipeline.

## Limitations / known gaps

| # | Limitation | Impact | Possible follow-up |
|---|------------|--------|--------------------|
| 1 | Curve segments approximated by endpoint | Poché on Rhino-exported drawings is straight-segment-only, so curves don't appear. If Illustrator-edited cut layers contain curves, the polygon shape will be slightly wrong. | Walk `c` / `C` operators with a Bezier flattener (e.g. `shapely.segmentize` after constructing a CubicBezier). Not in scope — Rhino exports never produce curves. |
| 2 | Paren-escaping in layer names | A layer with `(` or `)` in the name would have those chars backslash-escaped in the AI payload. Our exact-byte search would miss it. | Rhino exports never use parens, so this is theoretical. If hit, escape the layer name byte-string the same way AI does before searching. |
| 3 | No layer-name-by-OCG validation | We trust that the layer name we got from `enumerate_layer_paths_from_payload` matches the layer name in `find_layer_envelope`. If they diverge (e.g. the spike's "4th name reference" caveat), polygons would land in the wrong layer. | Cross-check against the OCG `/Name` entries. Out of scope. |
| 4 | Single-pass injection | We don't merge multiple polygon batches for the same layer — the caller must aggregate. | The current `compute_polygons_for_layers` already does this; just a note for direct callers of `inject_poche_polygons`. |
| 5 | No fill-color customization | Always emits `0 0 0 1 1 0 0 0 Xa` (black). | Add a `fill_color` argument to `synthesize_polygon_block` if someone wants gray poché or a different convention. |
| 6 | No multi-page support | Reads `pdf.pages[0]` only, like `apply_saas.py`. | Loop over pages. Rhino exports are always single-page. |
| 7 | Validation against real Rhino-export `.ai` | Not run during this port (per the time-box constraint and the user's instruction not to touch their real ARCH 202B file). The synthetic fixture proves the byte mechanics work. | Smoke-test against a small representative Rhino export in a separate session. |

## Verification

End-to-end smoke test against the synthetic fixture:

```
$ python -c 'from arch_line_weights.poche_saas import write_synthetic_test_ai; \
             write_synthetic_test_ai("/tmp/test_poche_cli.ai", \
             layer_name="axon::Visible::ClippingPlaneIntersections::TEST")'

$ arch-lw apply-saas /tmp/test_poche_cli.ai --auto --preset section --poche \
      -o /tmp/test_poche_cli_OUT.ai

# 0 colors mapped using auto:section

rewrote 1 stroke-width ops across 1 stroke-color sets
payload: 343 → 404 bytes (1 → 1 chunks)
   0.25 pt  →        1 ops

unmatched (defaulted to 0.25 pt):
  RGB(0, 0, 0): 1

poché: injected 1 polygons across 1/1 cut layers (+58 bytes)
  ✓ TEST            linemerge_bare      polys=  1  conf=1.00

wrote /tmp/test_poche_cli_OUT.ai  (1,065 bytes)
```

The output decompresses to:

```
%!PS-Adobe-3.0
%%Creator: Adobe Illustrator(R) 24.0
%AI24_TestFixture
%%EndComments
%AI5_BeginLayer
1 1 1 1 0 0 1 -1 240 190 130 0 100 0 Lb
(axon::Visible::ClippingPlaneIntersections::TEST) Ln
0 AE
0 A
0 0 0 1 0 0 0 XA
1 J 1 j 0.25 w 4 M []0 d        ← B6 width rewrite (1 -> 0.25)
0 XR
0 0 m
100 0 L
S
... (4 stroked sides of square) ...
                                   ← splice point
0 0 0 1 1 0 0 0 Xa                ← injected: fill color black
0 R
0 0 m                              ← injected: polygon path
0 100 L
100 100 L
100 0 L
f                                  ← injected: fill + closepath
LB
%AI5_EndLayer--
%%EOF
```

* `%AI5_BeginLayer ... LB` envelope intact
* Original 4 stroked sides preserved
* Stroke-width op rewritten (B6 path)
* New `Xa` + `f` filled polygon path injected immediately before `LB`

Test coverage:

* 35 existing tests (`tests/test_basic.py`, `tests/test_apply_saas.py`) — unchanged, all pass
* 17 new tests (`tests/test_apply_saas_poche.py`) — synthesis, envelope
  location, injection, zstd round-trip, end-to-end via `apply_saas_with_poche`

Total: 52 tests, all green. Ruff: clean.

## What's gated on a real Rhino-export `.ai` file

The synthetic fixture proves:

1. The byte mechanics work — pikepdf reads, zstd decompresses, regex finds
   layer envelope, polygons synthesize, splice happens, recompress + chunk
   + write succeeds, and the output decompresses to a payload containing
   the injected operators.

2. The compute step works — `polygonize_layer()` from `poche.py` is reused
   verbatim and produces the same polygons it would produce in the JSX
   pipeline.

What's *not* yet proven (but should work given the spike-08 evidence on
stroke widths and the matching syntax pattern):

* That Adobe Illustrator opens the modified file and renders the injected
  fills correctly at the right Z-order. The B6 spike (`08_modify_stroke_width.py`)
  proves the format is round-trip-safe through Illustrator for syntactically
  identical edits; injected `Xa` / `m` / `L` / `f` operators use the same
  AI native PostScript syntax, so the same proof should extend.

* That a multi-layer real Rhino export with 60+ cut layers produces the
  correct fills at scale (no missed envelopes, no off-by-one offsets, no
  unicode-name escape issues).

The recommended next step is a single smoke test on a small
representative Rhino-export `.ai` (e.g. a 5-layer test export) before
scaling to the full ARCH 202B drawing.

## Time spent

Roughly 70 minutes of agent work, well under the 90-minute budget. Most
of that was understanding the AI native PostScript syntax for filled
polygons (the spike scripts hadn't yet exercised `Xa`/`f`) and reading the
existing `poche.py` + `apply_saas.py` modules to mirror their patterns.
The lookbehind regex bug cost ~5 minutes; the synthetic-fixture
`pikepdf.Dictionary` construction cost ~5 minutes. The end-to-end pipeline
ran clean on the first integration attempt after those two fixes.
