# Poche Rulebook

Research date: 2026-05-05

This rulebook derives implementation rules from the local reference index, a
transient OCR pass over the image-only Visual Dictionary PDF, and the existing
project notes. It intentionally stores no source PDF text or diagrams.

Source shorthand:

- BCI: Ching, Building Construction Illustrated, local page index.
- VDA: Ching, A Visual Dictionary of Architecture, transient OCR page checks.
- PC: docs/research/poche-conventions.md.
- ISO: docs/research/iso-axon-section-debug-log-2026-05-05.md.

## Core Rule

Poche means the solid matter physically cut by the plan or section plane. It is
not a general darkness, shadow, material color, facade tone, or surface finish.
VDA defines poche around cut walls, columns, and other solids; VDA defines
section as a scaled view through an intersecting cut plane (VDA pp.77, 79).

Use structural semantics first, graphic color second. BCI separates the
structural system, which carries loads to ground, from enclosure and service
systems, which layer weather, light, air, heat, and access functions around that
structure (BCI p.55). In ambiguous drawings, poche only the structural cut mass.

## What Should Be Poche

- Structural walls, columns, beams, slabs, and load-bearing walls when the cut
  plane passes through their solid section (VDA pp.77, 79; BCI pp.55, 73).
- Foundations, footings, grade beams, foundation walls, mats, pile caps, and
  concrete ground slabs when they are cut as load-bearing substructure
  (BCI pp.96-102).
- Concrete structural members, including cast-in-place, precast, reinforced
  concrete walls, slabs, beams, columns, and structural tees (BCI pp.106,
  119-120, 127, 167).
- Structural masonry and CMU when acting as wall mass, bearing wall, pier,
  bond beam, lintel, or filled reinforced unit. Treat cavity walls by poching
  only the solid wythes crossed by the cut, not the air cavity (BCI pp.170-173,
  177, 180, 183).
- Mass timber and structural wood members, including CLT walls/slabs/roof
  plates, glulam, LVL, heavy timber beams/columns, structural decking, and true
  cut timber framing (BCI pp.147, 149, 154, 204, 208; VDA pp.303-306).
- Structural steel profiles when the plane cuts the member body: W shapes,
  HSS/SHS/RHS, channels, tubes, columns, beams, and primary frame members
  (BCI pp.130-132, 193-195; VDA pp.185-186).
- Ground or earth only when the drawing convention intentionally treats the
  section cut through ground as a cut mass; otherwise show it as earth hatch or
  context (BCI p.484; PC).

## What Should Never Be Black Poche

- Voids, rooms, cavities, air spaces, shafts, openings, glazing gaps, and
  unfilled space. A void can be outlined or shaded as space, but it is not solid
  cut matter (VDA pp.77, 79; BCI pp.170-173, 263).
- Curtain walls, rainscreens, cladding, siding, shingles, screens, louvers,
  perforated panels, copper returns, and facade-return layers unless the layer is
  explicitly a structural cut substrate. BCI treats curtain walls and veneers as
  supported enclosure or facing systems, not primary load path (BCI pp.264,
  267-269, 274-275, 330-331).
- Veneer brick, stone facing, GFRC panels, EIFS finish coats, plaster/stucco
  skins, trim, casing, ornament, and finish surfaces. Use material texture or
  line hierarchy instead (BCI pp.267-270, 276-278, 372-373; VDA pp.197-205).
- Glass, glazing, window sash, mullions, storefronts, channel glass, safety
  glazing, sealant, gaskets, and backer rods. Show glass as transparent/light,
  with edge lines or a glass hatch only (BCI pp.307, 314, 319-323, 330; VDA
  pp.121-122).
- Membranes, waterproofing, vapor retarders, air barriers, flashing, EPDM,
  roofing underlayment, drip edges, and sealants. These are thin layers; black
  poche would overstate their mass (BCI pp.211-212, 242, 252-256, 260, 263).
- Insulation as solid black. Batt, loose fill, rigid foam, spray foam, and
  insulated cavities should get their own hatch or remain light, depending on
  scale (BCI pp.278-284, 484).
- Fasteners and connectors: bolts, nails, clips, cleats, brackets, angles, tab
  plates, gussets, anchors, unistrut, weld plates, straps, and fishplates. These
  can receive a connector lineweight but should not become the dominant cut
  figure (BCI pp.194, 206, 260; VDA pp.91-94, 151-152).
- Datum, guide, annotation, dimension, reference, centerline, hidden, phantom,
  furniture, entourage, and PDF clipping artifacts (VDA pp.77, 79-80; ISO).
- Low-confidence rescue geometry such as global bounding boxes or alpha-shape
  facade blobs. These are diagnostics unless a structural rule validates them
  (ISO).

## Material And Assembly Cues

At small section scale, structural poche can be solid black or near-black. At
detail scale, prefer material hatches so assemblies remain legible (PC; BCI
p.484).

| Cut material or assembly | Default treatment | Notes |
| --- | --- | --- |
| Concrete, CMU, grout-filled masonry | Solid black at small scale; concrete or masonry hatch at detail scale | Use only for the solid cut part, not cavities or drainage layers (BCI pp.96-102, 170-173, 484). |
| Structural brick or stone masonry | Solid/hatch for load-bearing wythes; bond/stone hatch at detail | Veneer or facing stays light (BCI pp.176-183, 189-190, 267-270, 484). |
| CLT, glulam, LVL, heavy timber | Solid at small scale; grain or lamella hatch at detail | CLT slabs/roof plates count as structural cut mass when named as such (BCI pp.147-154, 204, 208; PC). |
| Structural steel | Filled cut profile for primary members | Downgrade plates, clips, cleats, and bolts to connector hierarchy (BCI pp.130-132, 193-195; VDA pp.91-94). |
| Ground/earth | Earth hatch, stipple, or dark cut field by drawing convention | Do not confuse earth hatch with foundation concrete poche (BCI pp.22, 484; PC). |
| Insulation | Batt wave, rigid hatch, or light material fill | Never solid black by default (BCI pp.278-284, 484). |
| Glass/glazing | Thin edge lines, light diagonal/glass hatch, or transparent tint | Never black poche (BCI pp.307, 314, 319-323, 330; VDA pp.121-122). |
| Membrane/flashing/air barrier | Thin line or membrane symbol | Never area poche unless it is part of a deliberately exaggerated detail symbol (BCI pp.252-256, 263). |

## Conservative Open-Loop Policy

Open-loop closure is allowed only for whitelisted structural layers and only
after blacklist checks. The goal is to recover missing cut mass, not to invent a
general silhouette.

Closure may proceed when all are true:

- The layer name or nearby metadata identifies structural cut material.
- Endpoints belong to the same material layer or an explicit structural pair.
- The missing edge is short, local, and plausible relative to the drawn member
  thickness or median segment length.
- The inferred polygon is simple, compact, above the minimum plot-area
  threshold, and does not self-intersect.
- The closure does not cross a known void, glazing layer, cavity, membrane,
  cladding layer, annotation layer, or different material boundary.
- The algorithm records the inferred edge, confidence, area, and reason.

Reject closure when any are true:

- The result requires a global bounding box, alpha shape, convex hull, or long
  diagonal bridge across unrelated geometry.
- The candidate is a long skinny snake, facade-return strip, perforated screen,
  cladding fold, or layer with mostly open decorative/profile linework.
- The only evidence is dark color or a `ClippingPlaneIntersections` style name.
- Confidence is below the injection threshold. Keep it in diagnostics.

Suggested confidence bands:

- `1.00`: native closed polygon on a whitelisted structural layer.
- `0.80-0.95`: local structural closure with short inferred edge and clean
  topology.
- `0.60-0.79`: diagnostic only unless the user explicitly opts into review.
- `<0.60`: never inject by default. ISO alpha-shape `0.55` and bbox `0.30`
  examples belong here.

## Implementation Hooks

Normalize layer names to lowercase ASCII tokens before matching. Blacklist wins
over whitelist. Then run structural closure only on surviving candidates.

Whitelist tokens for solid cut candidates:

```text
foundation, footing, pilecap, pile_cap, gradebeam, grade_beam, mat, raft
concrete, conc, cip, cast_in_place, precast, cmu, masonry, block, grout
loadbearing, bearing, shearwall, shear_wall, core, wall, pier
slab, floorplate, floor_plate, deck, roof_clt, roof-clt, clt_roof
clt, mass_timber, glulam, lvl, timber, wood_beam, wood_column
steel_column, steel_beam, hss, shs, rhs, wide_flange, w_shape, tube
column, beam, girder, lintel, structural, cut
```

Blacklist tokens for non-poche or non-black candidates:

```text
glass, glazing, window, sash, mullion, storefront, curtain, curtainwall, curtain_wall
cladding, siding, shingle, rainscreen, screen, perforated, louver, facade
copper, cu, return, punch_return, punch, bay_return
veneer, facing, finish, plaster, stucco, eifs, trim, casing, ornament
membrane, epdm, waterproof, dampproof, vapor, air_barrier, flashing
sealant, gasket, backer, rod, drip, underlayment, roofing_membrane
insulation, batt, mineral_wool, rigid_foam, xps, pir, spray_foam
connector, bracket, clip, cleat, angle, bolt, screw, nail, anchor
plate, gusset, tab, strap, fishplate, unistrut, weld
datum, grid, guide, reference, annotation, dimension, text, hidden
phantom, furniture, entourage, hatch_only, clipping, bbox, alpha_shape
```

Classification order:

1. If blacklist matches a nonstructural role, mark `no_black_poche`.
2. If whitelist matches structural material and no blacklist role wins, mark
   `candidate_cut_solid`.
3. If candidate has valid closed topology, inject poche.
4. If candidate has incomplete topology, run conservative open-loop closure.
5. If closure fails, preserve original linework and emit a diagnostic.

## Iso Axon Section Tests

Add unit tests around the layer names from the 2026-05-05 debug log:

- `TEC_CONCRETE_BASE`: classified as structural concrete; closed or locally
  closed regions may receive poche.
- `TEC_ROOF_CLT`: classified as structural CLT roof; open-loop closure allowed
  only with local, logged inferred edges.
- `TEC_CLT_SLABS`: classified as structural CLT slabs; slab regions may be
  recovered, but cavities and gaps remain unfilled.
- `03b_CLT_BACKUP_WALL`: classified as structural backup wall if topology is
  plausible; incomplete loops are diagnostic until closure passes.
- `15_CU_PUNCH_RETURNS_SOUTH_BAY_ALIGNED_V44`: classified as copper/facade
  return; never inject black poche, including alpha-shape fallback.
- `26_CLT_GAP_ROOF_CAP`: do not inject a bbox fallback. It may receive poche
  only if a structural roof/CLT closure passes the local closure rules.
- Any layer containing `glass`, `glazing`, `window`, `mullion`, `curtain`,
  `membrane`, `epdm`, `insulation`, `connector`, `bracket`, `cleat`, or `clip`
  must not become black poche.

Regression checks for the architectural section mode on the private section regression drawing:

```bash
apply-saas --auto --preset section --poche --architectural
```

- Auto mapping must not silently produce zero mappings.
- No global bbox or alpha-shape fill is injected by default.
- Facade-return blobs are absent.
- Foundation/concrete, CLT slabs, roof CLT, and thick backup walls are present
  when topology validates them.
- Steel connectors are visible but lower in hierarchy than primary structural
  cuts.
- The report lists every inferred closure and every skipped low-confidence
  candidate.
