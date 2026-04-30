# Show HN draft

> Drafts from the marketing sub-agent (2026-04-30). Edit before posting.
> Verify all install commands match the actual PyPI/GitHub state at post time.

## Title

`Show HN: arch-line-weights – Apply architectural line hierarchy to Rhino PDF exports`

## Body

Rhino exports vector PDFs/AIs with uniformly thin lines. Architects then spend
30+ minutes per sheet in Illustrator manually thickening cut lines, lightening
hidden geometry, and filling poché — every time the model changes.

arch-line-weights does this in one command. It rewrites the PDF content stream
directly (via pikepdf) for color-classify mode, OR drives Illustrator via JSX
for layer-preserving mode. Layer-name semantic classification backed by ISO 128,
Ramsey/Sleeper, and Ching gives sensible defaults; ISO-128 standards-aligned
weights via `--scale 1/4 --for-print`.

The interesting bit: detecting closed regions for poché fills. Illustrator's
"Join" command isn't topology-aware — it joins by endpoint proximity, not
graph connectivity, so it silently drops or mis-stitches segments. I ended up
using shapely's `linemerge + polygonize` with a layered fallback (snap, then
concave_hull, then bbox, with confidence scoring per fill). Every failed
approach is documented in a public POSTMORTEM.md so others don't repeat them.

Install (pre-PyPI): `pipx install git+https://github.com/zohartito/arch-line-weights`

MIT, 23 tests, Python 3.11+. Stack: pikepdf, pymupdf, shapely, click, Pillow.

https://github.com/zohartito/arch-line-weights

Feedback welcome — especially from anyone who's wrestled with PDF content
stream operators or Make2D output.
