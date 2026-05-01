# Demo gallery — rendering limitation

The `scripts/demo_gallery.py` generator produces before/after PNGs by
invoking PyMuPDF on each `.ai` file. PyMuPDF is fast, headless, and ships in
the project's existing dependency tree — but it has one important
limitation that affects what the demo PNGs show.

## What `apply-saas` actually modifies

`apply-saas` rewrites the AI-native payload at:

```
/Trailer
  /Root
    /Pages
      /Kids[0]
        /PieceInfo
          /Illustrator
            /Private
              /AIPrivateData1 .. /AIPrivateDataN  (zstd-compressed, prefixed)
```

Adobe Illustrator stores its **authoritative** drawing data inside
`/PieceInfo /Illustrator /Private`. When Illustrator opens an `.ai` file,
it prefers this payload over the legacy PDF content stream. The headless
SaaS path (`apply_saas.apply_to_file`) edits this payload in place — that
is what makes line-weight changes visible inside Illustrator and what
allows OCG layers to be preserved.

## What PyMuPDF renders

PyMuPDF (and any other "PDF-only" renderer — Ghostscript, Preview, Chrome's
PDF viewer) does not understand Illustrator's `/PieceInfo` payload. They
render the **legacy PDF content stream** that Illustrator embeds as a
viewer fallback for non-AI consumers.

The legacy stream is **never modified** by `apply-saas`. So when the demo
gallery renders before+after PNGs through PyMuPDF, both halves walk the
same untouched PDF stream and look identical.

## Why this is a feature, not a bug

`apply-saas`'s entire reason for existing is to be the **headless-server**
path that does not require Illustrator. If we re-rendered the PDF stream
to match the new line weights, we would either:

1. Have to ship a PDF rasterizer that is aware of Illustrator's stroke
   width metadata (none exists), or
2. Strip `/PieceInfo` and rewrite the PDF stream — exactly what
   `apply` (the non-saas path) does, and the reason that path **flattens
   layers** when opened in Illustrator.

The PieceInfo-preserving design is a deliberate trade. Visual proof that
line-weights actually changed requires:

* Adobe Illustrator (renders from the modified PieceInfo payload), or
* A round-trip via `arch-lw apply-jsx` (which uses Illustrator to bake the
  changes back into the PDF stream too — slower but visually verifiable in
  any PDF viewer).

## What the gallery PNGs are still good for

* **File-opens-cleanly check.** PyMuPDF refuses to render a corrupted PDF
  trailer; if the demo PNG renders, the output file is at least
  structurally sound.
* **Portfolio context.** The original drawing is shown next to the
  modified file, which is useful as a "here is the kind of input
  arch-line-weights handles" artefact.
* **Layout sanity.** Page dimensions and content placement are visible,
  which catches catastrophic failures (truncation, missing pages).

## What the gallery PNGs are *not* good for

* Line-weight verification — both halves are identical at the pixel level.
* Poché verification — the injected polygons live inside the PieceInfo
  payload only; PyMuPDF never sees them.

## Recommended companion artefacts

When producing portfolio assets:

1. Generate the demo gallery for context (this script).
2. Open both files in Illustrator. Take a screen capture. Drop it next to
   the gallery PNG.
3. Optionally run `arch-lw apply-jsx` to produce a `_HIERARCHY.ai` whose
   PDF stream **also** reflects the changes, then re-render through
   PyMuPDF for a verifiable headless before/after.

The header strip on each demo PNG includes a numeric summary (layer
count, cut-layer count, poché success rate, runtime) that is real even
when the visual halves are not — those numbers come from the same
`InspectionReport` and `apply-saas` diagnostics the CLI prints.

## Related files

* `scripts/demo_gallery.py` — generator
* `scripts/benchmark.py` — timing companion (does not have this limitation
  because it reports numbers, not pixels)
* `src/arch_line_weights/preview.py` — preview helpers used by both
* `src/arch_line_weights/apply_saas.py` — what the gallery is trying to
  visualise
