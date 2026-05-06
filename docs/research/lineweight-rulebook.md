# Lineweight Rulebook - Section Axon Structure Hierarchy

Date: 2026-05-05

Scope: semantic line-weight hierarchy for architectural section axons in the
`--architectural` mode planned for issue #16. This rulebook is derived from
the local reference-book SQLite index, the current classifier in
`src/arch_line_weights/layer_classify.py`, and the real iso axon debug log.
Page references below use the `page_number` stored in
`data/reference_books/reference_pages.sqlite`; no source PDFs, extracted full
text, or copied diagrams are reproduced here.

## Sources Searched

- Ching, `Architectural Graphics`: indexed pp. 28, 62, 80, 94-97, 157-160,
  165, 171-172. Used for the graphic hierarchy of cut/profile/edge/material
  linework, section contrast, surface texture, and reference/background
  handling.
- Ching, `Building Construction Illustrated`: indexed pp. 88, 97-100, 131-132,
  143, 149-151, 155, 168, 192, 207-208, 211-212, 236, 252-255, 259-264,
  271, 314, 320-321, 325-328, 331. Used for CLT, foundations, concrete,
  roofs, steel connections, curtain walls, cladding, rainscreens, glazing,
  and membranes.
- Ching, `Building Structures Illustrated`: indexed pp. 33, 47, 96, 120,
  136, 139-140, 142, 144, 173, 178-179, 189-194, 199, 220, 222-223. Used for
  load path, structural continuity, wood/timber systems, steel/concrete
  frames, curtain-wall relationships, facade screens, and roof structure.
- Repo sources: `src/arch_line_weights/layer_classify.py`,
  `src/arch_line_weights/presets.py`, `src/arch_line_weights/hatch.py`,
  `tests/test_layer_classify.py`, `docs/research/iso-axon-section-debug-log-2026-05-05.md`.

## Governing Rule

For a section axon, hierarchy should read in this order:

```text
true cut solid mass > primary structural profile > secondary framing >
frames/object edges > connectors/detail hardware > enclosure/cladding >
material hatches/textures/reference lines
```

The current classifier already carries most of this ladder, but
`--architectural` needs a material-aware overlay. In particular, the generic
Rhino rule `CLIPPINGPLANEINTERSECTIONS => cut` is too broad. It should remain
the last structural fallback, not the first rule. Screens, copper returns,
window frames, glass, membranes, datums, and connectors can live on
`ClippingPlaneIntersections` layers without deserving black cut poche.

Graphic basis: Ching's graphics chapters treat the section cut as the
heaviest, most continuous profile, then step down through visible edges,
surface material, texture, and distant/reference information
(`Architectural Graphics`, indexed pp. 28, 62, 80, 94-97). Section tone and
poche are used to separate cut solids from what is seen beyond the cut plane
(`Architectural Graphics`, indexed pp. 171-172). Hatches and texture build
tone through density and spacing, so they should remain lighter than object
edges (`Architectural Graphics`, indexed pp. 157-160, 165).

## Tier Rules

| Semantic role | Section screen weight | Poche eligibility | Meaning in a section axon | Page support |
|---|---:|---|---|---|
| `cut` | `1.0 pt` | Yes, structural whitelist only | Material physically sliced by the section plane: foundation, concrete, CLT slab/wall/roof, true cut timber or steel solids | AG pp. 28, 80, 172; BCI pp. 97-100, 155, 207-208, 211-212, 236; BSI pp. 33, 173, 179, 199 |
| `structure_primary` / `profile` | `0.5 pt` | No, unless also a structural cut layer | Major load-bearing profiles seen in elevation behind the cut: CLT walls, timber beams/columns, concrete wall/slab profiles, main roof/foundation profiles | BCI pp. 155, 207, 212, 236; BSI pp. 136, 173, 179, 199 |
| `structure_secondary` | `0.25 pt` target | No by default | Steel SHS/RHS/CHS/UC/UB members and secondary framing legible behind the cut, but quieter than the cut mass and primary profile | BCI pp. 131-132, 192, 194; BSI pp. 120, 222-223 |
| `frames` / `edges_secondary` | `0.3 pt` | No by default | Window frames, sash, mullions, stair risers, door/window object edges | BCI pp. 320-321, 325-326 |
| `connectors` | `0.18 pt` | No by default | Brackets, cleats, plates, clips, straps, bolts, welded/bolted connection hardware | BCI pp. 88, 131-132, 150-151, 168, 206, 234; BSI pp. 139, 178, 189, 223 |
| `glazing` / `special` | `0.25 pt` or lighter | Never in section axon default | Transparent glass and insulated glazing. Keep legible but visually light and separate from structural mass | BCI pp. 314, 320-321, 325-328, 331; BSI pp. 194 |
| `cladding` / `hidden` | `0.18 pt` | Never in section axon default | Facade screens, copper panels, rainscreen layers, curtain-wall infill, surface panels, punch returns | BCI pp. 263-264, 271, 325-326, 331; BSI pp. 190, 192-194 |
| `material_minor` / `insulation` / `reference` | `0.13 pt` | Never | Membranes, EPDM, sealants, insulation, hatches, datum/grid/reference lines | AG pp. 157-160, 165; BCI pp. 252-255, 259-260 |
| `texture` | `0.08 pt` where available | Never | Dense hatch lines, perforation texture, panel grain, background surface texture | AG pp. 97, 157-160, 165 |

Implementation note: the section preset currently maps `structure_secondary`
to `edges` in `tier_weights_for_preset("section")`, which would make secondary
steel too loud for this section axon. For issue #16, keep a distinct
`structure_secondary` weight in
architectural mode so steel framing can sit between primary profiles and
window/object edges.

## Material-Specific Rules

### CLT

CLT is structural when it is a wall, floor, slab, or roof panel. BCI describes
CLT as engineered mass timber panels for floors, load-bearing walls, and roofs
(indexed pp. 155, 207-208, 236). Therefore:

- `TEC_CLT_SLABS`, `TEC_ROOF_CLT`, `03b_CLT_BACKUP_WALL`,
  `_CLT_THICK_`, and `_CLT_GAP_ROOF_` on a true cut layer are `cut`,
  eligible for solid poche and structural open-loop closure.
- The same CLT terms on ordinary visible/elevation curves are
  `structure_primary`.
- CLT rain-screen layers, furring, membranes, and exterior protection layers
  are enclosure/material layers, not CLT structure.

### Concrete And Foundations

Foundations and concrete bearing elements are the most important poche
targets. BCI treats footings and foundation walls as support and anchorage for
the superstructure (indexed pp. 97-100), and BSI emphasizes vertical load
continuity to the foundation (indexed pp. 33, 173, 179). Therefore:

- `TEC_FOUNDATION`, `TEC_CONCRETE_BASE`, `FOUNDATION`, `FOOTING`,
  `CONCRETE_*_WALL`, and structural `SLAB` terms on true cut layers are
  `cut`, eligible for solid poche and open-loop closure.
- Concrete slabs/walls seen behind the section cut are `structure_primary`.
- Concrete texture, board-form marks, control joints, and surface hatching
  stay in `material_minor` or `texture`.

### Roofs

The roof has both structure and weathering layers. BCI and BSI separate roof
structure from membranes, insulation, and flashing (BCI indexed pp. 211-212,
252-255, 259-260; BSI indexed p. 199). Therefore:

- `TEC_ROOF_CLT`, `ROOF_CLT`, `ROOF_STRUCT`, and structural concrete/steel/
  timber roof deck terms are `cut` if sliced and `structure_primary` or
  `structure_secondary` if seen beyond the cut.
- `26_CLT_GAP_ROOF_CAP` is a structural CLT roof cap, not a generic facade
  cap. It should be eligible for structural open-loop closure, but never via
  global `bbox`; inferred closures must be reported.
- `EPDM`, `TPO_MEMBRANE`, `_MEM_`, `_WP_`, `SEALANT`, `FLASHING`, and roof
  insulation are `material_minor` and are not poche targets.

### Steel Framing

Steel beams, columns, and moment/braced frames are primary structural systems
in the building, but in this iso section they should not overpower the cut
CLT/concrete mass unless they are themselves cut. BCI and BSI describe steel
frames, beam-column action, and connection rigidity as structural load-path
systems (BCI indexed pp. 131-132, 192, 194; BSI indexed pp. 120, 222-223).

- `SHS`, `RHS`, `CHS`, `UC`, `UB`, `HSS`, and `_STL_` visible framing terms
  map to `structure_secondary` at about `0.25 pt` in section-axon screen output.
- A steel member on a true cut layer may be `cut` only when it is a structural
  member, not a connector, clip, or facade support bracket.
- If the layer name is ambiguous between steel frame and hardware, prefer the
  lighter hardware rule and report it.

### Connectors, Brackets, Cleats, Clips

Connections transfer force, but graphically they are detail hardware. BCI and
BSI show many connectors as mediating parts: hangers, angles, straps, plates,
bolts, anchorages, and slotted adjustment hardware (BCI indexed pp. 88,
131-132, 150-151, 168, 206, 234; BSI indexed pp. 139, 178, 189, 223).

- `TEC_STEEL_CONNECTOR`, `L-BRACKET`, `CLEAT_PLATE`, `BRACKET`, `CLIP`,
  `FASTENER`, `BOLT`, `SCREW`, `STRAP`, `ANCHOR`, and similar terms map to
  `connectors` at `0.18 pt` in section-axon screen output.
- They are not default poche targets, even when dark in the source file.
- In detail drawings they may become heavier, but section axons should keep
  them precise and subordinate.

### Facade Screens And Copper Panels

Curtain walls, rainscreens, panels, and copper screens belong to enclosure
and surface systems. BCI describes curtain walls as non-load-bearing exterior
walls carried by the structural frame and metal cladding as panels supported
by girts; BSI separates curtain-wall enclosure from the primary frame
(BCI indexed pp. 263-264, 271, 325-326, 331; BSI indexed pp. 190, 192-194).

- `CU_CORR`, `CU_FLAT`, `CU_PUNCH`, `CU_PUNCH_RETURNS`, `PERF_SCREEN`,
  `SCREEN`, `RAINSCREEN`, `CLADDING`, `FACADE`, `PANEL`, and `SPANDREL`
  map to `cladding` at `0.18 pt`, with perforation/punch textures allowed
  to fall to `texture`.
- They are never default poche targets in a section axon. The debug log's
  `15_CU_PUNCH_RETURNS_SOUTH_BAY_ALIGNED_V44` false blob is the reference
  failure mode.
- `11_CU_CORR_SOLID_OPAQUE` should be treated as copper/cladding unless a
  user override explicitly declares it structural.

### Windows And Glass

Glazing systems require frames/mullions that support glass while allowing
movement; curtain-wall glazing is non-load-bearing enclosure in the normal
case (BCI indexed pp. 314, 320-321, 325-328, 331; BSI indexed p. 194).

- `WINDOW_GLASS`, `WINDOW_IGU_GLASS`, `GLASS`, `IGU`, and `GLAZING` map to
  `glazing`/`special`; never poche.
- `WINDOW_FRAME`, `WINDOW_ALUM_FRAME`, `MULLION`, `SASH`, `JAMB`, `HEAD`,
  and `SILL` map to `frames`/`edges_secondary`.
- `23_WINDOW_FRAMES_REMAP` is explicitly a no-poche layer in architectural
  mode. The older topology research treated it as a geometry challenge, but
  the section-axon hierarchy rule says window frames should stay outlined.

### Hatches, Textures, And Reference Lines

Hatches and surface textures create tone through stroke density, not line
weight. Ching's graphics chapters place texture and reference information
below object edges in the visual hierarchy (indexed pp. 97, 157-160, 165).

- `FLOOR_DATUMS`, `_DATUM`, `_GRID`, `_REF`, and guide/reference layers map
  to `reference` at `0.13 pt`.
- `INSULATION`, `_INS_`, `_MW_`, `_RW_`, `_XPS_`, `_PIR_`, membrane, sealant,
  and hatch-only layers map to `material_minor` or `insulation` at `0.13 pt`.
- Dense material texture should use the `texture` tier where the output path
  supports it, around `0.08 pt` for section screen output.

## Implementation Hooks For Issue #16

### 1. Add an architectural semantic overlay

Create an architectural layer interpretation step that returns both stroke
tier and poche eligibility:

```python
@dataclass(frozen=True)
class ArchitecturalAssignment:
    tier: str
    weight_pt: float
    semantic: str
    poche: bool
    open_loop_closure: bool
    confidence: float
    why: str
```

This can wrap `classify_layer()` rather than replace it. The wrapper should
run before color luminance and should be the default inside
`apply-saas --architectural --auto --preset section --poche`.

### 2. Use precedence before generic cut

Recommended rule order:

1. Reference/annotation/datums.
2. Glass and windows.
3. Membranes/insulation/sealants.
4. Connectors/brackets/cleats/clips/fasteners.
5. Copper/cladding/screens/facade infill/punch returns.
6. Structural cut whitelist.
7. Structural visible profiles.
8. Secondary steel framing.
9. Generic `ClippingPlaneIntersections` fallback as low-confidence cut
   requiring review.

This order fixes the current problem where any clipped screen, frame, or
connector becomes `1.0 pt` and may receive black fill.

### 3. Concrete mapping table

| Real layer or pattern | Architectural semantic | Tier | Weight | Poche | Closure |
|---|---|---|---:|---|---|
| `axon::Visible::ClippingPlaneIntersections::TEC_FOUNDATION` | concrete foundation cut | `cut` | `1.0` | yes | yes |
| `axon::Visible::ClippingPlaneIntersections::TEC_CONCRETE_BASE` | concrete base cut | `cut` | `1.0` | yes | yes |
| `axon::Visible::ClippingPlaneIntersections::TEC_CLT_SLABS` | CLT floor/slab cut | `cut` | `1.0` | yes | yes |
| `axon::Visible::ClippingPlaneIntersections::TEC_ROOF_CLT` | CLT roof cut | `cut` | `1.0` | yes | yes |
| `axon::Visible::ClippingPlaneIntersections::26_CLT_GAP_ROOF_CAP` | separated CLT roof caps | `cut` | `1.0` | yes | yes, reported |
| `axon::Visible::ClippingPlaneIntersections::03b_CLT_BACKUP_WALL` | CLT backup wall cut | `cut` | `1.0` | yes | yes |
| `axon::Visible::Curves::TEC_TIMBER_COLUMNS` | primary timber profile | `structure_primary` | `0.5` | no | no |
| `axon::Visible::Curves::TEC_TIMBER_BEAMS` | primary timber profile | `structure_primary` | `0.5` | no | no |
| `axon::Visible::Curves::05_RHS_STL_FRAME` | secondary steel frame | `structure_secondary` | `0.25` | no | no |
| `axon::Visible::Curves::06_SHS_STL_FRAME` | secondary steel frame | `structure_secondary` | `0.25` | no | no |
| `axon::Visible::Curves::TEC_STEEL_CONNECTOR_L-BRACKET` | connector hardware | `connectors` | `0.18` | no | no |
| `axon::Visible::Curves::CLEAT_PLATE` | connector hardware | `connectors` | `0.18` | no | no |
| `axon::Visible::ClippingPlaneIntersections::15_CU_PUNCH_RETURNS_SOUTH_BAY_ALIGNED_V44` | copper punch return | `cladding` | `0.18` | no | no |
| `axon::Visible::Curves::14_CU_CORR_PERF_SCREEN` | perforated copper screen | `cladding` or `texture` | `0.18`/`0.08` | no | no |
| `axon::Visible::ClippingPlaneIntersections::11_CU_CORR_SOLID_OPAQUE` | copper cladding panel | `cladding` | `0.18` | no | no |
| `axon::Visible::Curves::C03_CU_CORR_PANELS` | copper panel surface | `cladding` | `0.18` | no | no |
| `axon::Visible::Curves::03c_WINDOW_IGU_GLASS` | insulated glazing | `glazing` | `0.25` | no | no |
| `axon::Visible::ClippingPlaneIntersections::23_WINDOW_FRAMES_REMAP` | window frame outlines | `frames` | `0.3` | no | no |
| `axon::Visible::Curves::WINDOW_ALUM_FRAME` | window frame | `frames` | `0.3` | no | no |
| `axon::Visible::Curves::WP_MEMBRANE_ROOF_EPDM` | roof membrane | `material_minor` | `0.13` | no | no |
| `axon::Visible::Curves::INSULATION_MW` | insulation hatch | `insulation` | `0.13` | no | no |
| `axon::Visible::Curves::FLOOR_DATUMS` | reference/datum | `reference` | `0.13` | no | no |

### 4. Poche whitelist and blacklist

Whitelist for `--architectural --poche`:

```text
TEC_FOUNDATION
TEC_CONCRETE_BASE
FOUNDATION
FOOTING
CONCRETE
TEC_CLT_SLABS
TEC_ROOF_CLT
CLT_BACKUP
CLT_THICK
CLT_GAP_ROOF
TEC_TIMBER
TIMBER_BEAM
TIMBER_COLUMN
true cut STEEL/SHS/RHS/CHS/UC/UB/HSS members only when not connector hardware
```

Blacklist for `--architectural --poche`:

```text
CU_CORR
CU_FLAT
CU_PUNCH
PUNCH_RETURNS
PERF_SCREEN
SCREEN
CLADDING
RAINSCREEN
FACADE
FACADE_PANEL
COPPER_PANEL
METAL_PANEL
SPANDREL
WINDOW
GLASS
IGU
GLAZING
WINDOW_FRAME
ALUM_FRAME
FRAMES_REMAP
MULLION
EPDM
MEMBRANE
SEALANT
FLASHING
INSULATION
DATUM
GRID
REF
CONNECTOR
BRACKET
CLEAT
CLIP
FASTENER
BOLT
SCREW
STRAP
ANCHOR
```

If a name hits both lists, blacklist wins unless the user supplies an explicit
override. This is the safe behavior for deadline drawings.

### 5. Tests To Add

Add tests in a new `tests/test_architectural_mode.py` or extend
`tests/test_layer_classify.py` once the architectural wrapper exists:

```python
@pytest.mark.parametrize(
    "layer,tier,weight,poche,closure",
    [
        ("axon::Visible::ClippingPlaneIntersections::TEC_CONCRETE_BASE", "cut", 1.0, True, True),
        ("axon::Visible::ClippingPlaneIntersections::TEC_ROOF_CLT", "cut", 1.0, True, True),
        ("axon::Visible::ClippingPlaneIntersections::26_CLT_GAP_ROOF_CAP", "cut", 1.0, True, True),
        ("axon::Visible::ClippingPlaneIntersections::03b_CLT_BACKUP_WALL", "cut", 1.0, True, True),
        ("axon::Visible::ClippingPlaneIntersections::15_CU_PUNCH_RETURNS_SOUTH_BAY_ALIGNED_V44", "cladding", 0.18, False, False),
        ("axon::Visible::ClippingPlaneIntersections::11_CU_CORR_SOLID_OPAQUE", "cladding", 0.18, False, False),
        ("axon::Visible::ClippingPlaneIntersections::23_WINDOW_FRAMES_REMAP", "frames", 0.3, False, False),
        ("axon::Visible::Curves::TEC_STEEL_CONNECTOR_L-BRACKET", "connectors", 0.18, False, False),
        ("axon::Visible::Curves::05_RHS_STL_FRAME", "structure_secondary", 0.25, False, False),
        ("axon::Visible::Curves::WP_MEMBRANE_ROOF_EPDM", "material_minor", 0.13, False, False),
        ("axon::Visible::Curves::FLOOR_DATUMS", "reference", 0.13, False, False),
    ],
)
def test_architectural_section_axon_semantics(layer, tier, weight, poche, closure):
    a = classify_architectural_layer(layer, preset="section")
    assert a.tier == tier
    assert a.weight_pt == weight
    assert a.poche is poche
    assert a.open_loop_closure is closure
```

Also add a regression that dark source colors cannot override semantics:

```python
def test_architectural_semantics_beat_luminance_for_connectors():
    a = classify_architectural_layer(
        "axon::Visible::Curves::TEC_STEEL_CONNECTOR_L-BRACKET",
        source_color_rgb=(0, 0, 0),
        preset="section",
    )
    assert a.tier == "connectors"
    assert a.weight_pt == 0.18
```

## Acceptance Criteria

- Structural CLT/concrete/foundation/roof cut layers become heaviest and are
  eligible for structural closure.
- Copper returns, perforated screens, cladding, windows, glass, membranes,
  reference lines, and connectors do not become black poche merely because
  Rhino put them under `ClippingPlaneIntersections`.
- Steel framing is legible as secondary structure, not mistaken for cut mass
  or connector hardware.
- The output report lists every skipped clipped layer, every inferred closure,
  and every low-confidence generic cut fallback.
- Color luminance is used only after semantic confidence is low.
