# r/Python "Showcase Saturday" post draft

> Drafts from the marketing sub-agent (2026-04-30). Edit before posting.

## Title

`[Showcase] arch-line-weights — rewriting PDF content streams with pikepdf + shapely to fix architectural drawings`

## Body

Hi r/Python. Sharing a niche-but-fun project: a CLI that post-processes
Rhino-exported PDFs/AIs to apply line-weight hierarchy and fill closed
regions (poché) for architectural drawings.

**Stack:**
- `pikepdf` — direct PDF content stream rewriting (the `w`, `RG`, `S`, `f` operators)
- `pymupdf` — page geometry inspection and rendering for diff previews
- `shapely` — the interesting part: detecting closed polygons from a soup of line segments
- `click` — CLI
- `Pillow` — raster previews

**Build:** hatchling + hatch-vcs for version-from-tags. 23 tests (pytest), MIT.

**The technically interesting bit:** Illustrator's "Join" command is not
topology-aware — it joins by endpoint proximity. For poché fills you need
actual closed regions from a graph of segments that may be split, overlapping,
or have rounding-error gaps. I ended up with `shapely.ops.linemerge` →
`polygonize`, with a layered fallback: bare linemerge, then snap-and-merge at
increasing tolerances, then concave_hull, finally bounding-box. Each layer
catches what the previous missed, with a confidence score per fill.

I documented every approach that didn't work (and why) in
[docs/POSTMORTEM.md](https://github.com/zohartito/arch-line-weights/blob/main/docs/POSTMORTEM.md)
— including a naive `executeMenuCommand("join")` attempt that produced
beautifully wrong tangled polygons. Hopefully useful if anyone else hits the
closed-region detection problem.

Install (pre-PyPI): `pipx install git+https://github.com/zohartito/arch-line-weights`
Repo: https://github.com/zohartito/arch-line-weights

Happy to dig into any of the implementation choices.
