# Porting `apply.py` to operate on the AI native payload — implementation notes

> 2026-04-30. Companion document to `saas-architecture.md`. Records the
> design decisions and edge cases encountered while implementing
> `src/arch_line_weights/apply_saas.py`.

## What got built

| File | Purpose |
|------|---------|
| `src/arch_line_weights/apply_saas.py` | New module — pure-pikepdf headless apply path. |
| `src/arch_line_weights/cli.py` | Added `arch-lw apply-saas` subcommand alongside `apply` and `apply-jsx`. |
| `tests/test_apply_saas.py` | 9 unit tests covering round-trip, rewrite, classification parity. |

## Design

The pipeline mirrors `scripts/spike/saas-feasibility/08_modify_stroke_width.py`
exactly. The only meaningful structural difference vs the spike is generality:
the spike hard-coded one layer name and one width substitution, whereas
`apply_saas.py` walks all `XA` (stroke-color set) tokens and rewrites the
following `<w> w` (stroke-width set) tokens per the same RGB → weight mapping
that `apply.py` consumes.

```
read .ai → concat AIPrivateData<i> streams → strip 20-byte prefix
                                            → zstd-decompress
                                            ↓
        rewrite_payload(payload, mapping)  ←  walk XA + w tokens, replace
                                            ↓
                                            → zstd-compress (level 19)
                                            → prepend prefix
                                            → 64 KB chunk → write streams
```

### Stroke-width op forms

The AI native PostScript payload uses two distinct shapes of `<w> w` operator:

1. **Bare form** — `\r<w> w\r` on its own CR-delimited line. Common for
   per-path width changes inside a layer block.
2. **Setup form** — `\r<cap> J <join> j <w> w 4 M []0 d` as part of a
   line-attribute setup line. Common at the start of a path with non-default
   join / cap / dash. The width is the third float.

Both forms are matched by their own regex (`_BARE_W_RE`, `_SETUP_W_RE`) and
both rewriters preserve the surrounding tokens (the `J`/`j` prefix, the
`4 M` miter, the `[]0 d` dash).

### Color tracking

`XA` sets the stroke color via `<C> <M> <Y> <K> <R> <G> <B> XA` — 7 floats.
The last three (RGB, 0..1) drive our mapping. We collect every `XA` position
in a single linear scan, then for each `<w> w` operator look up the most
recent prior `XA` position to decide the weight. This mirrors the
`current_rgb` tracking in `apply.py::_rewrite`.

### Edit ordering

Both regex passes emit `(start, end, replacement)` tuples into one list,
sorted by start offset, then applied left-to-right with overlap suppression.
The two regex shapes do not overlap (the bare form starts with `\r<f> w\r`,
the setup form starts with `\r<f> J `), so the dedup is purely defensive.

## Edge cases discovered during implementation

### 1. pikepdf auto-applies `/FlateDecode` to new streams

When you do `pdf.make_stream(c)` and save, pikepdf wraps the chunk in
`/FlateDecode`. Adobe's own .ai files don't filter the AIPrivateData streams
at all, so `read_raw_bytes()` works on Illustrator-saved files and fails on
pikepdf-resaved ones.

**Fix:** read with `read_bytes()` (filter-aware), so the same module handles
both Illustrator-saved and pikepdf-saved files. Round-trips are now stable:
the synthetic test fixture stays at 290 bytes through repeated apply-saas
runs.

This was the only concrete blocker hit during the port. ~5 minutes to
diagnose, 1 line of code to fix.

### 2. CMYK / Gray strokes silently fall through to default

`apply.py` only matches `RG` (RGB stroke-color setters in PDF content
streams); CMYK strokes (`K`) and gray strokes (`G`) are skipped. We mirror
that here: only `XA`'s last 3 RGB floats are read. CMYK-only files would
need a separate code path — not in scope for this port.

### 3. Files with no `/PieceInfo`

A plain `.pdf` (or an `.ai` saved without the round-trip option) won't have
`/PieceInfo /Illustrator /Private`. The module raises `ValueError` early
with a clear message; the CLI surfaces this to the user. The right call
in that case is to fall back to `arch-lw apply` (the existing PDF-stream
rewriter).

### 4. Width-token formatting

AI native uses bare integers (`5 w`) for whole-number widths and
decimals (`0.25 w`) otherwise. Python's `f"{w:g}"` formats `1.0` as `"1"`
correctly, but `f"{int(w):g}"` would lose precision for something like
`0.25`. We pick the right form via `if w == int(w): str(int(w)) else f"{w:g}"`
in `_format_width`. Tested at boundaries (`1.0`, `5.0`, `0.25`, `0.13`).

### 5. A stroke-width op with no preceding `XA`

If the payload places a `<w> w` before any `XA` (e.g. a default in a
prologue), `_color_at(offset)` returns `None`. We rewrite to `default_width`
in that case. This is consistent with `apply.py`'s behavior (no `current_rgb`
yet → use `default_width`), and the test
`test_rewrite_no_xa_uses_default` covers it.

## Limitations / known gaps

| # | Limitation | Impact | Possible follow-up |
|---|------------|--------|--------------------|
| 1 | RGB-only mapping | CMYK / Gray strokes skipped | Add a CMYK→tier path if a user file actually contains CMYK strokes (none observed in Rhino exports). |
| 2 | No layer-aware classification | Width is per-color, not per-layer | The semantic classifier in `layer_classify.py` works on layer names; a future enhancement could parse `(LayerName) Ln` markers and bucket strokes per layer. Out of scope here. |
| 3 | `default_width` always overrides | A stroke whose color isn't in the mapping always gets rewritten | `apply.py` has the same behavior. Could be a flag (`--leave-unmatched`). |
| 4 | No validation that the modified file still parses as `.ai` | The function relies on the spike's empirical proof that Illustrator round-trips this format | The `04_roundtrip_modify.py` and `08_modify_stroke_width.py` spikes have already validated the format end-to-end through Illustrator. |
| 5 | One page only | The current implementation reads `pdf.pages[0]` | Rhino exports are always single-page; multi-page would need a loop. |
| 6 | No `--keep-pieceinfo` flag | Always preserves PieceInfo (the entire point of this path) | If a user wants the strip-and-rewrite-PDF-stream behavior, they should use `arch-lw apply`. |

## Verification

End-to-end smoke test against a synthetic fixture (no real user files
touched):

```
$ python /tmp/build_synthetic_ai.py        # builds 1.2 KB .ai with 2 strokes
$ arch-lw apply-saas /tmp/synthetic_test.ai --auto --preset section \
      -o /tmp/synthetic_test_OUT.ai
# 2 colors mapped using auto:section
--- 1.0 pt ---
  RGB(  0,  0,  0)        1 strokes
--- 0.08 pt ---
  RGB(255,  0,  0)        1 strokes

rewrote 2 stroke-width ops across 2 stroke-color sets
payload: 292 → 290 bytes (1 → 1 chunks)
   0.08 pt  →        1 ops
    1.0 pt  →        1 ops

wrote /tmp/synthetic_test_OUT.ai  (1,238 bytes)
```

Decompressed payload before/after, side-by-side:

| Layer / token | Before | After |
|---------------|--------|-------|
| `(SyntheticLayerA) Ln` | preserved | preserved |
| red XA `0 0 0 0 1 0 0` | preserved | preserved |
| width op (bare form) | `0.25 w` | `0.08 w` |
| `(SyntheticLayerB) Ln` | preserved | preserved |
| black XA `0 0 0 1 0 0 0` | preserved | preserved |
| width op (setup form) | `1 J 1 j 0.5 w 4 M []0 d` | `1 J 1 j 1 w 4 M []0 d` |

Idempotency: running `apply-saas` twice on the output produced the same
payload size (290 → 290 bytes), and `pikepdf.open` survived the
double-round-trip without error.

Test coverage:
- 26 existing tests (`tests/test_basic.py`) — unchanged, all pass
- 9 new tests (`tests/test_apply_saas.py`) — round-trip, rewrite, parity

## Next steps (out of scope for this port)

These are mentioned in `saas-architecture.md` as the v0.5 roadmap; not in
scope for the current port:

1. **Layer-aware width assignment** — read `(<LayerName>) Ln` markers,
   apply `layer_classify.classify_layer(name).weight_pt` per layer block
   instead of (or in parallel with) per-color.
2. **Poché injection** — write polygonized cut-layer fills as new closed
   `pathItem` blocks inside a layer's `BeginLayer .. LB` envelope. The
   syntax pattern is the same one this module already manipulates.
3. **Validate against ≥3 real user files** — the only Rhino-export AI24
   file in hand is the user's ARCH 202B section drawing, which we are
   under instruction not to use for testing during this port.

## Time spent

Roughly 60 minutes of agent work, well under the 90-minute budget. Most
of that was reading the spike scripts and existing modules to map regex
patterns + framing constants to a generalized API. The single bug
(pikepdf auto-Flate vs. spike's `read_raw_bytes`) cost ~5 minutes.
