# Postmortem — every poché attempt and what we learned

> Living document. Each entry: what we tried, what worked, what failed,
> what to keep doing or stop doing. The point is to make sure no future
> contributor (including future-us) repeats any of these.

## Context

Project: `arch-line-weights` — apply architectural line-weight hierarchy +
poché to color-coded vector drawings (typically Rhino-exported `.ai`).
Reference test file: USC ARCH 202B section drawing, 24 MB, 340,323 strokes,
62 OCG layers, 21 of which are `Visible::ClippingPlaneIntersections::*` (the
section cuts that should become poché).

## Attempt 1 (v0.1) — pikepdf rewrite + strip PieceInfo

**What:** Rewrite the PDF content stream to inject `<width> w` before every
stroke operator, color-keyed by the most recent `RG`. Strip `/PieceInfo` so
Illustrator parses the modified stream instead of its private cache.

**Result:** Strokes worked perfectly. Speed was great (110 s on 340 K
strokes). Shipped as v0.1.

**Failure:** Stripping PieceInfo **flattened all 62 Rhino layers into a
single Illustrator layer**. The user opened it, said "you turned it into one
layer," and we rolled back the default.

**Root cause:** `.ai` files are dual-encoded: `/PieceInfo /Illustrator
/Private` holds the canonical layer/group structure; the PDF content stream
is a rendering fallback. Strip PieceInfo → Illustrator falls back to the PDF
parser, which collapses OCGs to the default Layer 1 unless you open via
`File > Open` with `pDFPreserveLayers` enabled (no equivalent for
double-clicking the file).

**Lesson kept:** Layer fidelity > raw speed for any tool whose users will
iterate on the output. Default to layer-preserving even if slower.

**Lesson kept:** "Open in Illustrator and look at the Layers panel" is a
required acceptance test — not just "fills look right in preview."

## Attempt 2 (v0.2) — Illustrator JSX with `maximumUndoDepth=1`

**What:** Hand a JSX to Illustrator that walks each leaf layer, derives a
weight from the new semantic layer-name classifier (`layer_classify.py`),
and applies it to every `pathItem` in that layer. Outline view + cap undo
depth at 1 to keep ExtendScript linear-time.

**Result:** Worked. 11 minutes for 340 K strokes, all 62 layers preserved,
0 errors. Shipped as v0.2.

**Lesson kept:** ExtendScript per-item iteration is **linear with
`maximumUndoDepth=1`, exponential without**. The first naive try (no undo
cap) showed exponential degradation — first 10 K paths in 79 s, second in
132 s, third in 280 s. ETA was 2+ hours and rising.

**Lesson kept:** Layer-name semantic classification beats color
classification for any Rhino export. `Visible::ClippingPlaneIntersections::*`
is **always** the cut tier regardless of trailing material code.

## Attempt 3 (v0.3 try 1) — JSX `app.executeMenuCommand("join")` to chain endpoints + fill

**What:** For each cut layer, select all paths, repeatedly call
`app.executeMenuCommand("join")` to chain coincident endpoints, then fill
the resulting closed paths black.

**Result:** Catastrophic. Each layer's 100s of paths joined into ONE giant
self-intersecting tangled polygon, which then filled along its zigzag stroke
order. The user's screenshot showed black bars criss-crossing the courtyard.

**Failure:** Illustrator's Join is not topology-aware. Given N paths whose
endpoints are all near-coincident in pairs, Join chains them in **arbitrary
order**, not by the actual graph structure. So 100 segments that should form
10 separate closed polygons collapse into 1 self-intersecting blob.

**Lesson kept:** Naive endpoint-chaining (Illustrator's Join, simple
linemerge without graph structure) is a trap. Use shapely's
`linemerge + polygonize` which **preserves topology** — it identifies
*separate* connected components and only chains within each.

**Kept in repo:** `scripts/poche/apply_join_NAIVE.jsx` as a warning marker.

## Attempt 4 (v0.3 try 2) — pikepdf-only OCG-aware stream rewrite

**What:** Walk the PDF content stream, track current OCG via `BDC/EMC` +
`/Properties` lookup, collect line segments per OCG, run shapely linemerge +
polygonize per OCG, append filled polygons to the content stream, save.

**Result:** Buggy. My MC# matcher used `"/MC28"` in one place and `"MC28"`
(no slash) in the other — collected 0 segments for every layer.

**Failure:** Format mismatch in dict keys. Trivial bug, hours to find
because PDF content-stream debugging is hard.

**Lesson kept:** When walking PDF marked content, normalize names exactly
once. `pikepdf.Name` objects can stringify with or without leading `/`
depending on context.

**Lesson kept:** When an extraction returns 0 results across the board,
**dump the actual operator format first** before debugging the geometry.

## Attempt 5 (v0.3 try 3) — JSX dump anchors + Python shapely + JSX apply

**What:** Two-stage pipeline:
1. JSX A walks every cut layer and dumps `pathItem.pathPoints[i].anchor` to
   `/tmp/cut_geometry.json` (skips PDF stream entirely)
2. Python loads the JSON, runs `shapely.ops.linemerge + polygonize` per
   layer (with snap+linemerge fallback ladder)
3. Python builds JSX B with the resulting polygon coordinates baked in as a
   JS object literal (no I/O at runtime)
4. JSX B opens the file in Illustrator, creates new closed `pathItem`s in
   each layer with `filled = true; fillColor = black`, saves

**Result:** Mostly works.

| Outcome | Layers | Why |
|---|---|---|
| Clean polygons | 13 / 21 | Bare linemerge produced N separate closed loops |
| Concave-hull fallback | 7 / 21 | linemerge gave 0 polys → fell back, produces 1 lumpy polygon instead of N |
| Failed | 1 / 21 | `23_WINDOW_FRAMES` — too few points |

**Sub-failures along the way:**
- v3 added `snap()` pre-pass that **over-merged** the dense cladding layers.
  TEC_STAIRS went from 29 polys (no snap) to 0 (snap at 0.5pt) → fell back
  to bad concave_hull. Reverted snap → use bare linemerge first.
- After `saveAs`, Illustrator's in-memory copy of the *source* doc still
  contains all the JSX-added pathItems. If the user clicks back to that tab
  thinking it's the clean source, they see "weird extra lines." Reproduced
  by the user. Force-close and reopen from disk to recover.

**Lessons kept:**
- Two-stage pipeline (Illustrator dump → Python compute → Illustrator
  apply) is the working pattern. Easier to debug than PDF content stream
  hacking.
- For per-layer geometry processing, **try a sweep of strategies and pick
  the one that maximizes polygon count**, not the first that gives any
  polygons. Some layers want 0.01pt tolerance, some want 2pt.
- After `saveAs` with new pathItems added, the source doc is dirty. Either
  close-without-saving programmatically before next iteration, or instruct
  the user to manually close and reopen.

## Attempt 6 (planned, v0.4) — Disconnected-loop rescue

**What:** Per the disconnected-loops sub-agent report, layered fallback with
confidence scoring:
1. bare linemerge → conf 1.00
2. snap+linemerge at 0.5/1/2/5 pt → conf 0.85–0.7 (whichever maxes polys)
3. user-marked `__POCHE_CLOSE__` layer (Rhino-side fix) → conf 0.95
4. concave_hull(densified) → conf 0.55
5. axis-aligned bbox → conf 0.30

Plus emit per-fill metadata so the UI can flag low-confidence with warnings.

**Status:** Roadmapped. Not yet implemented.

## Attempt 7 (2026-04-30) — Open-source publish, then yank

**What:** Published v1.0.0 to PyPI under MIT license via OIDC Trusted
Publishing. Build verified; clean-venv install confirmed; CLI returned
"arch-lw, version 1.0.0".

**Result:** Working publish. Anyone could `pip install arch-line-weights`
for ~15 minutes.

**Failure:** I had committed to MIT before deciding the business model.
The user wanted to monetize. MIT distribution is irrevocable for
distributed copies. We yanked v1.0.0 (hides from `pip install`,
preserves project name, still legally MIT for anyone who downloaded it).
Removed the Trusted Publisher to cut the OIDC pipeline. Disabled the
release workflow. Made the repo private.

**Side effects:**
- GitHub Pages site went 404 (private repos need GH Pro for Pages)
- Marketing drafts in `docs/announce/` are now stale (they pitch open-source)
- v1.0.0 still installable via explicit `pip install arch-line-weights==1.0.0`
  (yank semantics, not deletion)

**Lesson kept:** **Pick the license BEFORE you publish to a public
registry.** Once a version is on PyPI under any license, that exact
version's license is fixed in perpetuity. Future versions can be any
license, but the MIT cat is partially out of the bag for v1.0.0.

**Lesson kept:** Yank is a one-way door for `pip install` discovery
but not for legal rights. Treat "what license is on the wheel I'm
about to upload" as the gate, not "what license is in my README right
now."

**Lesson kept:** Going private and enabling docs auto-deploy on the
same day is a foot-gun. Pages 404'd within 5 minutes of the visibility
flip. Always check what depends on the visibility before changing it.

## Attempt 8 (2026-04-30) — pikepdf-only .ai modification (the SaaS unlock)

**What:** Investigate whether pikepdf alone can modify a Rhino-exported
`.ai` file's `/PieceInfo /Illustrator /Private` payload such that
Illustrator opens the result with all 62 OCG layers intact and the
modifications applied. This was the make-or-break question for the SaaS
pivot.

**Result:** **Worked, end-to-end.** Eight spike scripts in
`scripts/spike/saas-feasibility/` demonstrate inspect / decompress /
round-trip / stroke-color modify / stroke-width modify, all verified in
Illustrator.

**Discovery:** The 305 `/AIPrivateData` streams concatenate into a
20-byte ASCII prefix `%AI24_ZStandard_Data` + Zstandard-compressed
payload. Decompressed: ~55 MB of plain-text Adobe Illustrator native
PostScript — the same publicly-documented AI3-AI8 syntax we'd been
writing JSX against for months, just zstd-wrapped + chunked across PDF
streams.

**Verified operations:**
- Round-trip null edit → byte-perfect, OCG count 62→62
- Stroke color: `(1 0 1) XA` → 172 paths now magenta
- Stroke width: `1 w` → `5 w` → 172 paths now 5pt

**Implications for the project:**
- **The "no Illustrator on Linux server" blocker is gone.** We can run
  the entire pipeline server-side in pure Python.
- The existing JSX-based `apply_jsx.py` and `poche.py` can be ported to
  operate directly on the decompressed AI native PostScript instead of
  via Illustrator's scripting bridge. Estimated 1-2 days.
- The hybrid local-helper path (Attempt-3-style) is no longer needed as
  primary architecture; reserved for "Pro Privacy" upsells.

**Lesson kept:** The format we'd been treating as proprietary all along
**was actually a documented PostScript dialect wrapped in modern
compression**. Future-us: when a format looks closed, check if it's
just an old format wearing modern packaging before assuming it's
proprietary.

**Lesson kept:** A 60-minute time-boxed feasibility spike resolved a
question that v0.1 (Attempt 1, "strip PieceInfo") tried to dodge by
flattening layers. Spikes > workarounds.

**Kept in repo:** Eight scripts in `scripts/spike/saas-feasibility/`
demonstrating the operations. These become the foundation of the v0.7
prototype that ports the apply / poché pipelines to pure Python.

## Cross-cutting lessons (the durable ones)

1. **Layer fidelity is non-negotiable.** Any change that destroys it must
   be explicit opt-in, not the default.
2. **Sub-agents in parallel** are how to move fast on unknowns. Eight
   sub-agent reports across this 30-hour session each gave us in 2 minutes
   what would have taken hours of solo research.
3. **Two-stage pipelines** (Illustrator dump → Python compute → Illustrator
   apply) are easier to debug than monolithic pikepdf or monolithic JSX.
4. **Topology-aware geometry libraries** (shapely) > naive endpoint chaining
   (Illustrator Join) every time.
5. **Best-effort sweep over strategies + confidence scoring** > picking one
   tolerance and hoping. Different layers need different tolerances within
   the same file.
6. **Document failed approaches in the repo**, not just successful ones.
   This file is the contract.
7. **The user's verification ritual matters.** "Does it look right in
   Illustrator's Preview view at the layers panel?" is the ground truth, not
   "does the JSON say success."
8. **Save the source separately from the modification.** Use `saveAs` to a
   new file every time. Never modify the user's source in place.
9. **`maximumUndoDepth=1` + Outline view** turns ExtendScript from
   exponential-time to linear-time on bulk edits.
10. **Standards-compliant defaults trump aesthetics.** The current 0.1–1.0pt
    range was chosen for screen review; for plotted print at 1/4"=1' the
    section cut should be 0.7mm = 1.98pt per ISO 128. v0.4 will add scale-
    aware presets (see `docs/research/standards.md`).
