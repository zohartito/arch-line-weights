# Make2D Completion Architecture

Date: 2026-05-05

## Why This Exists

The `private section regression drawing.ai` failures showed that poché and line
weights cannot be solved as separate layer-local passes.

Rhino Make2D can split one architectural component across:

- `Visible::ClippingPlaneIntersections`
- `Visible::Tangents`
- `Visible::Curves`

If the program only trusts the clipping-plane layer, it misses slabs, roofs,
walls, foundations, and beam caps. If it fills visible structural layers
wholesale, it creates false black blobs. The missing stage is a shared
architectural component/topology model.

## Target Pipeline

```text
AI/Rhino payload
-> parse layers and paths
-> classify architectural semantics
-> group paths into components
-> complete broken Make2D topology
-> apply line-weight hierarchy
-> generate poché/material fills
-> produce visual QA + review report
```

## Data Model

The first code slice is `src/arch_line_weights/make2d_completion.py`.

It introduces:

- `DrawingLayer`: layer name, paths, architectural assignment, drawing role,
  and component key.
- `CompletionCandidate`: candidate geometry, source role, provenance,
  accepted/rejected state, reason, confidence, and cut-anchor length.

Next model to add:

- `ArchitecturalComponent`: one material/component key with cut, visible,
  tangent, hidden, and helper paths grouped together.
- `ComponentGraph`: adjacency/support relationships between slabs, walls,
  foundations, roof faces, beams, and facade systems.

## Rules Learned From The Iso Axon

Automatic fill rules:

- Same-component visible/tangent geometry may suggest a repair.
- Helper-only closed shapes are not automatic poché.
- For automatic black fill, helper-derived candidates must share meaningful
  boundary with the target clipping-plane layer.
- Concrete/foundation helper geometry cannot wildly expand an already valid
  cut-only face.
- Facade, glass, membrane, connector, and screen layers remain out of poché
  even when they can be polygonized.

Line-weight implications:

- Cut mass and true profile edges should be decided from the component model,
  not only from color or isolated layer tokens.
- Connectors and secondary steel must stay subordinate even when dark source
  colors or nearby cut geometry make them visually tempting.
- Facade screens and panel texture should recede unless the user explicitly
  asks for an elevation/detail emphasis.

## Current Outputs

- `private-regression-output.ai`: recovered more mass, but accepted helper-only
  false blobs.
- `private-regression-output.ai`: removed the lower-left concrete-base expansion
  and stayed conservative.
- `private-regression-output.ai`: adds a top `ARCH_LW_POCHE` layer; useful for draw-order
  review but does not solve missing component topology.

## Next Implementation Steps

1. Promote candidate reporting to a user-facing `diagnose-poche` or
   `--poche-report` output.
2. Add `ArchitecturalComponent` grouping and component-level candidate scores.
3. Add fixture tests for known zones in `private section regression drawing.ai`.
4. Let line-weight hierarchy consume the component graph, starting with
   connectors/secondary steel/facade screens.
5. Add visual QA screenshots for prior private run/prior private run/prior private run comparisons.

The books/reference library should feed this stage as executable rules and
tests, not as raw committed PDFs or live book-reading during each run.
