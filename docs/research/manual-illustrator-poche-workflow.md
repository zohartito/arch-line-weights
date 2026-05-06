# Manual Illustrator Poche Workflow

Research date: 2026-05-05

Scope: manual cleanup workflow for a Rhino/Make2D section axon in Adobe
Illustrator, and how that workflow should map back into `arch-line-weights`.
This is a workflow spec, not a tutorial for one drawing.

## Sources

- Adobe Illustrator layers, lock/hide, search/filter, and layer selection:
  https://helpx.adobe.com/uk/illustrator/desktop/manage-layers/create-and-organize-layers/layers-panel-overview.html,
  https://helpx.adobe.com/illustrator/using/locking-hiding-deleting-objects.html,
  https://helpx.adobe.com/illustrator/desktop/manage-layers/create-and-organize-layers/find-and-filter-layers.html
- Adobe object selection by layer/similar appearance:
  https://helpx.adobe.com/illustrator/desktop/manage-objects/select-objects/select-objects.html,
  https://helpx.adobe.com/illustrator/desktop/manage-objects/select-objects/select-objects-by-characteristics.html
- Adobe Join, Shape Builder, and Live Paint cleanup tools:
  https://helpx.adobe.com/illustrator/using/tool-techniques/join-tool.html,
  https://helpx.adobe.com/illustrator/using/tool-techniques/shape-builder-tool.html,
  https://helpx.adobe.com/in/illustrator/desktop/paint-and-fill/learn-painting-basics/about-live-paint.html,
  https://helpx.adobe.com/illustrator/desktop/paint-and-fill/learn-painting-basics/find-and-close-gaps-in-live-paint-groups.html,
  https://helpx.adobe.com/illustrator/desktop/paint-and-fill/learn-painting-basics/expand-and-release-live-paint-groups.html
- Adobe print/proof checks:
  https://helpx.adobe.com/illustrator/using/overprinting.html,
  https://helpx.adobe.com/id_id/illustrator/using/printing-color-separations.html
- Parent-conversation Rhino/AI context:
  https://howtorhino.com/rhino-grasshopper-tutorials/rhino-to-illustrator-section/,
  https://developer.rhino3d.com/api/rhinocommon/rhino.rhinodoc/export,
  https://developer.rhino3d.com/guides/rhinocommon/code-driven-file-io/,
  https://helpx.adobe.com/illustrator/using/pdf-options.html,
  https://ai-scripting.docsforadobe.dev/jsobjref/PDFSaveOptions/,
  https://www.datalogics.com/adobe-illustrator-and-pdf-compatibility

## Manual Goal

The manual goal is not "make every closed shape black." It is to make the
section plane read clearly:

```text
true cut solid mass > cut/profile lines > visible object edges > surface tone
> context/reference lines
```

In practice, the architect preserves the Rhino/Make2D layer structure, repairs
only the incomplete cut geometry, creates black filled faces for true solid
matter, and keeps non-solid cut elements as strong strokes rather than fills.

## 1. Preserve The Original Drawing

Manual workflow:

- Save a copy before cleanup.
- Keep original Rhino/Make2D layers intact.
- Create working layers above the original, typically:
  - `ARCH_LW_POCHE`
  - `ARCH_LW_CUT_LINES`
  - `ARCH_LW_REPAIR_GUIDES`
  - optional `ARCH_LW_REVIEW`
- Lock untouched context layers while repairing one subset.
- Use layer search/filter and layer selection instead of hand-selecting random
  objects across the whole drawing.

Reasoning:

Large Make2D files are too dense for safe global editing. Illustrator's layer
panel and object selection tools are the reliable manual control surface:
select by layer, same stroke/fill, or nested layer when possible. The original
drawing stays recoverable and the cleanup layers remain auditable.

Program rule:

Never mutate source layers destructively. Add generated overlays and diagnostics
as named layers. Preserve enough provenance to say which source layers produced
each poche face or cut stroke.

## 2. Classify Before Filling

Manual workflow:

For each suspicious dark/cut area, decide which bucket it belongs to before
using any fill tool:

| Bucket | Manual treatment | Examples |
| --- | --- | --- |
| True cut mass | Filled black poche, no decorative outline dependency | concrete walls, foundations, CLT slabs/roof plates, solid structural walls |
| Cut/profile line | Heavy solid stroke, usually black; no area fill | panel edges, SHS/HSS section edges, window/frame edges, thin cut returns |
| Context/object edge | Medium/light stroke | visible facade lines, slab edges beyond cut, background structure |
| Surface/texture | Very light stroke or hatch tone | rainscreen perforations, panel seams, material grain |
| Void/glass/air | No black fill | openings, rooms, glazing, cavities |

Reasoning:

The biggest failure mode in the iso axon is treating every clipping-plane or
dark source layer as poche. A curtain-wall return, rainscreen, window frame, or
connector can be cut by the section plane and still not be solid black mass.

Program rule:

Separate `poche_eligible` from `cut_line_style`. A layer can be a strong cut
line while explicitly not being a poche candidate.

## 3. Isolate A Local Component

Manual workflow:

- Hide or lock unrelated systems.
- Work on one architectural component at a time: one foundation wall, one slab
  strip, one roof plate, one retaining wall, one facade bay.
- Bring in only the helper geometry needed for that component: clipping
  intersections, visible edges, tangent curves, and nearby returns.
- Avoid one giant Live Paint group for the whole drawing.

Reasoning:

Illustrator's Live Paint can fill faces even when the boundaries are made from
separate paths, but Adobe notes that gap detection can slow down on large,
complex Live Paint groups. Manual success comes from reducing the problem to a
small, architecturally coherent subset.

Program rule:

Build component-local topology groups. Do not run expensive bridge/closure/fill
logic across an entire layer when that layer contains many unrelated facade,
screen, connector, or texture fragments.

## 4. Repair Broken Make2D Boundaries

Manual workflow, from conservative to stronger:

1. Use Join or Object > Path > Join for obvious open endpoints on the same
   boundary.
2. Use the Join tool to connect near paths or trim small overlaps.
3. Draw a short repair segment on `ARCH_LW_REPAIR_GUIDES` when the Make2D
   boundary is missing one edge.
4. Use Shape Builder on selected component geometry when the desired face is
   visually clear.
5. Use Live Paint only on the isolated subset, enable gap preview, close small
   gaps, fill the intended face, then expand to ordinary paths.

Reject these manual repairs:

- Long bridges across unrelated geometry.
- Convex-hull or bounding-box faces that merely surround a component.
- Triangle/curved-cap blobs where a fourth boundary is missing.
- Helper-only faces that do not share a meaningful cut boundary.
- Fills that cover openings, cavities, glazing, or facade screens.

Reasoning:

The manual editor uses architectural judgment while closing gaps: the inferred
edge must be local, short, and explainable as missing Make2D output. A face that
looks mathematically closed but architecturally wrong is rejected.

Program rule:

Completion candidates need morphology gates: shared cut-edge length, expected
material/component thickness, aspect/short-side checks, compactness checks, and
negative tests for square blobs, triangular caps, and facade returns.

## 5. Create The Poche Overlay

Manual workflow:

- Put black fill shapes on `ARCH_LW_POCHE`.
- Use no stroke on the fill faces unless the face itself needs a generated cut
  outline.
- Keep cut/profile strokes visible above the fill layer, or duplicate key cut
  edges to `ARCH_LW_CUT_LINES`.
- Set generated fills behind annotation and fine linework that must remain
  readable.
- Remove or fix any white stripes, dashed cut fills, or partial black squares.

Reasoning:

Poche is a figure-ground layer. It should not erase the drawing's cut edges or
produce broken/dashed fills. If a floor plate is solid cut mass, it should read
as a continuous solid face; if it is only a thin cut edge, it should read as a
continuous strong stroke.

Program rule:

Generated poche fills and generated cut strokes are separate outputs. Strong cut
layers should have solid dash patterns normalized, and generated fills should
not depend on source stroke dashes.

## 6. Apply Line-Weight Hierarchy

Manual workflow:

- Heaviest: true section cut outlines and solid cut mass edges.
- Strong but not filled: cut thin elements such as panels, SHS/HSS, mullions,
  window/profile edges, and returns.
- Medium: primary visible structure behind the cut.
- Light: secondary steel, connectors, facade panels, frames, object edges.
- Lightest: texture, perforation, hatch, datum, and distant context.

Reasoning:

The hierarchy is visual, not just material based. Steel connections may be
structural, but if they are small detail hardware in the view, they should not
compete with the cut floor/wall/roof mass.

Program rule:

Line weights should consume the same component classification used by poche.
Layer names, RGB/CMYK source colors, cut context, and architectural semantics
must all feed a single style resolver.

## 7. Print-Test And Review

Manual workflow:

- Zoom out to the intended sheet scale.
- Print or export a PDF proof, then review at print size.
- Use Overprint Preview or separations checks when using black fills and colored
  strokes.
- Scan for:
  - false blobs
  - missing floor/roof/wall/foundation faces
  - white stripes inside black cut mass
  - dashed or partial cut edges
  - cut lines that disappear under the fill
  - background/detail lines that overpower the cut
- Mark corrections on `ARCH_LW_REVIEW`, then iterate on the affected component
  only.

Reasoning:

Poche is judged by print legibility. A generated result that looks plausible at
screen zoom can still fail at sheet scale if blobs, gaps, or over-heavy detail
lines disturb the section read.

Program rule:

Every run should produce a review report with accepted fills, rejected
candidates, inferred closures, layer style overrides, and warnings. Longer term,
it should produce visual QA snapshots or a review overlay.

## Mapping To Arch-Line-Weights Stages

| Manual step | Program stage | Required behavior |
| --- | --- | --- |
| Save copy and preserve layers | AI payload parse/write | Keep original layers, write new generated layers, preserve source provenance. |
| Select by layer/same appearance | Layer/color classifier | Support RGB and CMYK source colors, layer names, and Illustrator stroke operators. |
| Classify cut mass vs cut line vs context | Architectural semantic resolver | Return both `poche_eligible` and `cut_line_style`; blacklist non-solid systems from black fill. |
| Isolate one wall/slab/roof/foundation | Component grouping | Group clipping, visible, tangent, and helper paths by architectural component. |
| Join small gaps | Local endpoint bridging | Only bridge short, compatible endpoints within the same component and time budget. |
| Shape Builder/Live Paint on a subset | Component polygonization | Polygonize local subsets, not whole degenerate layers; use per-layer/component budgets. |
| Gap preview and close gaps | Make2D completion diagnostics | Log inferred edges, gaps, confidence, and rejected repairs. |
| Fill only true solid faces | Poche generation | Inject black fills only for structural cut mass above confidence threshold. |
| Heavy stroke for cut non-mass | Cut stroke generation | Normalize dashes to solid and set strong strokes for panels, SHS/HSS, frames, returns, and glazing edges without filling them. |
| Keep texture/context light | Hierarchy style resolver | Downweight hatches, perforations, screens, connectors, and distant/reference lines. |
| Print proof and mark errors | QA/report stage | Emit a human-readable report and optional review overlay for false blobs, missing fills, and incomplete cut outlines. |

## New Program Rules Learned

1. Poche and line weight cannot be two independent passes. Both need the same
   architectural component model.
2. Manual success depends on local isolation; the program should default to
   component-local repair instead of layer-global rescue.
3. A closed polygon is not enough evidence. The candidate must be architecturally
   plausible for the material and component.
4. Non-poche cut elements still need strong cut styling. This is why the program
   needs cut-line output in addition to black fill output.
5. Review artifacts are part of the product. The tool should tell the user what
   it filled, what it refused, and why.
