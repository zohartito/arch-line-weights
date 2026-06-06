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
- Accepted/rejected candidate reports must include the reason, provenance,
  bounds, area, confidence, and measured cut-anchor length.
- Concrete/foundation helper geometry cannot wildly expand an already valid
  cut-only face.
- Facade, glass, membrane, connector, and screen layers remain out of poché
  even when they can be polygonized.
- Covered structural cut-mass vocabulary includes CLT slabs, first-floor
  floor/slab plates, roof CLT, roof cut mass, foundation/concrete, backup walls,
  timber beam cells, and timber beam caps.

Line-weight implications:

- Cut mass and true profile edges should be decided from the component model,
  not only from color or isolated layer tokens.
- Connectors and secondary steel must stay subordinate even when dark source
  colors or nearby cut geometry make them visually tempting.
- Facade screens and panel texture should recede unless the user explicitly
  asks for an elevation/detail emphasis.

## Current Coverage

- Targeted synthetic regressions accept bounded, cut-anchored completion for
  first-floor plates, roof cut mass, concrete base, foundation strips, roof CLT,
  repeated timber beam cells, and timber beam caps.
- Helper-only closed shapes and large/compact false blobs are rejected and
  preserved in the candidate report with the rejection reason.
- Connector hardware, glazing, cladding, membranes, and secondary steel remain
  subordinate to structural cut mass; they can receive cut-line styling without
  becoming black poché.
- Private Illustrator visual QA is still required before using the private USC
  proof as launch evidence.

## Next Implementation Steps

1. Add `ArchitecturalComponent` grouping and component-level candidate scores.
2. Add more public synthetic fixtures that mimic the private section regression
   zones without exposing private geometry.
3. Extend visual QA snapshots once public-safe fixture views are available.

The books/reference library should feed this stage as executable rules and
tests, not as raw committed PDFs or live book-reading during each run.
