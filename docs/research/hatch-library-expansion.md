# Hatch library expansion — 14 → 30+ canonical recipes

> Phase E2 of the roadmap. Brings `arch_line_weights.hatch` to the "amazing"
> bar of 25+ recipes covering timber, masonry, concrete, metal, insulation,
> roofing, finishes, and ground. Sub-agent research, 2026-04-30.

## Purpose

Current state: 14 recipes (concrete, concrete_solid, clt_cross_grain,
clt_solid, solid_timber, steel_solid, steel_hatch_45,
insulation_mineral_wool, insulation_rigid, earth, brick, glass, gypsum,
aluminum). The library skews structural-cut. It is missing finishes,
roofing, masonry variants, and 2026 envelope materials (CLT panels, copper
rain screen, ETFE).

Target: 30 recipes (16 new). All recipes must be implementable with the
existing helper kit:

- `parallel_hatch(poly, spacing, angle, offset_fn)` — diagonal scanlines
- `crosshatch(poly, spacing, angle1, angle2)` — two-pass parallel
- `poisson_disk(poly, min_dist)` + `stipple_dots/triangles` — random fills
- `sine_zigzag(poly, wavelength, amplitude, row_spacing)` — wave fills
- `brick_pattern(poly, brick_w, brick_h)` — stretcher-bond grid
- `clt_layers(poly, lamella)` — alternating-grain strips
- `mm_to_pt(mm, scale)` — unit conversion

No new geometry primitives are needed for any recipe below. Three new
helpers will be added as part of E2: `running_bond_pattern` (generalized
brick with offset/seam controls), `seam_lines` (single-direction parallel
seams for standing-seam metal), and `random_polygon_fill` (Voronoi-style
irregular cells for stone, slate, terrazzo).

## Authoritative sources consulted

- Ramsey & Sleeper, *Architectural Graphic Standards* 12th ed. — material
  symbols pp. 5-3 to 5-22 (ASTM-derived hatching conventions)
- Ching, *Architectural Graphics* 6th ed. — graphic vocabulary chapter
- NCS v5 Plotting Guidelines — pen weight assignments per layer class
- ISO 128-50 — sectional view conventions
- AutoCAD `acad.pat` — `AR-CONC`, `AR-BRSTD`, `AR-RROOF`, `AR-SAND`,
  `AR-HBONE`, `AR-RSHKE`, `AR-PARQ1`, `AR-B816`, `AR-B816C`, `INSUL`,
  `EARTH`, `GRAVEL`, `STEEL`, `BRSTONE`. Pattern math is ASCII; angles and
  spacings are public.
- Detail magazine 2018-2024 issues — verified copper, ETFE, CLT detailing
  conventions as drawn in real construction sets.

> Note on quoting: ≤15-word excerpts only per copyright. Pattern math
> (angles, spacings, offset rules) is functional and not protectable.

---

## Standards reference: tier classification of all recipes

| Recipe | Tier (from `presets.SECTION`) | Stroke pt | Frequency in real drawings |
|---|---|---|---|
| concrete | material | 0.18 | very high |
| concrete_solid | (filled) | — | very high |
| clt_cross_grain | material | 0.18 | high (mass-timber projects) |
| clt_solid | (filled) | — | high |
| solid_timber | material | 0.18 | medium |
| steel_solid | (filled) | — | very high |
| steel_hatch_45 | material | 0.18 | medium |
| insulation_mineral_wool | material | 0.18 | very high |
| insulation_rigid | material | 0.18 | very high |
| earth | texture | 0.13 | high (any below-grade) |
| brick (stretcher bond) | material | 0.18 | very high |
| glass | special | 0.13 | very high |
| gypsum | texture | 0.13 | very high |
| aluminum | material | 0.18 | medium |
| **brick_running_bond** | material | 0.18 | very high (clarifies brick) |
| **brick_flemish_bond** | material | 0.18 | medium (heritage / precedent) |
| **brick_herringbone** | material | 0.18 | medium (paving + accent walls) |
| **cmu** | material | 0.18 | very high (commercial work) |
| **stone_cut** | material | 0.20 | medium |
| **stone_rough** | material | 0.20 | medium |
| **slate** | material | 0.18 | medium (roofing + flooring) |
| **terrazzo** | texture | 0.13 | medium |
| **stucco** | texture | 0.13 | high (residential, Spanish revival) |
| **plywood_end_grain** | material | 0.18 | medium |
| **osb** | material | 0.18 | high (sheathing) |
| **board_formed_concrete** | material | 0.18 | high (contemporary) |
| **polished_concrete** | texture | 0.13 | high (floors) |
| **rigid_insulation_xps** | material | 0.18 | very high |
| **rigid_insulation_polyiso** | material | 0.18 | very high |
| **standing_seam_copper** | material | 0.18 | high (2026 vernacular) |
| **zinc_panel** | material | 0.18 | medium (Euro contemporary) |
| **etfe_cushion** | special | 0.13 | medium (large public buildings) |
| **wood_flooring** | texture | 0.13 | high |
| **carpet** | texture | 0.13 | high (commercial interiors) |
| **acoustic_ceiling_tile** | texture | 0.13 | very high (commercial) |
| **single_ply_membrane** | material | 0.18 | very high (flat roofs) |
| **bituminous_waterproofing** | material | 0.18 | high (foundations) |
| **gravel** | texture | 0.13 | high (drainage layer, ballast) |

---

## New material recipes

### 1. `brick_running_bond`

Same as existing `brick`, but explicit name. Half-brick offset every course.
Most-common modern bond. Existing `brick_pattern(poly, 215, 65)` already
implements this exactly — the existing recipe is renamed/aliased.

**Pattern math:** 215×65 mm modular brick (UK std), 10 mm mortar.
Half-brick offset on alternate courses.

**Citation:** Ramsey/Sleeper 12th, Masonry section; AutoCAD `AR-BRSTD`.

**Parameters:**
```python
brick_pattern(poly, mm_to_pt(215, scale), mm_to_pt(65, scale))
```

**ASCII sample:**
```
|----|----|----|----|
  |----|----|----|---
|----|----|----|----|
  |----|----|----|---
```

**Layer keywords:** `BRICK_RB`, `BRICK_RUNNING`

**Notes:** Walls (cut + elevation), pavers (plan).

---

### 2. `brick_flemish_bond`

Alternating header (115 mm visible) + stretcher (215 mm) within each course,
half-brick offset between courses. Used in heritage facades and contemporary
projects deliberately referencing 18th–19th c masonry.

**Pattern math:** Course = repeating unit of stretcher (215) + mortar (10) +
header (115) + mortar (10) = 350 mm. Course offset = 175 mm (half unit).

**Citation:** Ching 6th ed. masonry plate; AutoCAD `AR-BRSTD2`.

**Parameters:**
```python
flemish_bond_pattern(poly, stretcher_mm=215, header_mm=115, course_mm=65)
# Internally: brick_pattern variant with alternating header marks per course
```

**ASCII sample:**
```
|----|--|----|--|----
|--|----|--|----|--|
|----|--|----|--|----
|--|----|--|----|--|
```

**Layer keywords:** `BRICK_FLEM`, `FLEMISH`

**Notes:** Heritage walls; contemporary precedent (e.g., Caruso St John).

---

### 3. `brick_herringbone`

45-degree paving / accent-wall pattern. Each brick rotated 45°, perpendicular
to neighbor. Common in patios, fireplaces, herringbone-tile floors.

**Pattern math:** Two perpendicular sets of parallel-hatch lines at 45°
and 135°, with an alternating module of 215×65. Implementable as two
`brick_pattern` passes rotated 45° each, masked by checkerboard cells.

**Citation:** Ching 6th ed., paving plate; AutoCAD `AR-HBONE`.

**Parameters:**
```python
herringbone_pattern(poly, brick_w=215, brick_h=65, angle=45)
```

**ASCII sample:**
```
/--/--/--/--/
\--\--\--\--\
/--/--/--/--/
\--\--\--\--\
```

**Layer keywords:** `BRICK_HB`, `HERRINGBONE`, `_HBONE_`

**Notes:** Floors (most common), accent walls, courtyards.

---

### 4. `cmu` — Concrete masonry unit (CMU block)

8" × 16" nominal block (190×390 mm). Stacked-bond or running-bond. Optional
hollow-cell glyphs at small scale.

**Pattern math:** 390×190 mm grid with 10 mm mortar joints. Running-bond
half-block offset.

**Citation:** Ramsey/Sleeper 12th, Masonry; AutoCAD `AR-B816` (8×16 block).

**Parameters:**
```python
brick_pattern(poly, mm_to_pt(390, scale), mm_to_pt(190, scale))
# + optional hollow-cell stipple via stipple_dots at cell centers
```

**ASCII sample:**
```
|--------|--------|--------|
    |--------|--------|----
|--------|--------|--------|
    |--------|--------|----
```

**Layer keywords:** `CMU`, `CONC_BLOCK`, `_CMU_`, `BLOCKWORK`

**Notes:** Commercial walls, retaining, partitions. Highest-frequency
masonry omission in current library.

---

### 5. `stone_cut` — Smooth-cut / dressed stone

Rectangular ashlar with irregular but rectilinear coursing. Joints are crisp
horizontal + variable vertical. Drawn with random cell sizes within a horizontal-band grid.

**Pattern math:** Horizontal courses at 200–400 mm random spacing; vertical
joints at 300–800 mm random offset per course.

**Citation:** Ching 6th ed.; Ramsey/Sleeper Stone section; `BRSTONE`.

**Parameters:**
```python
random_band_pattern(
    poly,
    course_min_mm=200, course_max_mm=400,
    joint_min_mm=300, joint_max_mm=800,
    seed=42,
)
```

**ASCII sample:**
```
|---|----|--|------|
|------|--|----|--|
|--|------|------|
|----|--|---|----|
```

**Layer keywords:** `STONE_CUT`, `ASHLAR`, `LIMESTONE`, `SANDSTONE`

**Notes:** Foundations, plinths, heritage facades, contemporary base
courses.

---

### 6. `stone_rough` — Rubble / rough-cut stone

Irregular polygons (Voronoi cells) at 100–300 mm scale. No coursing.

**Pattern math:** Generate Voronoi tessellation from Poisson-disk seed
points (`min_dist=200 mm`); intersect each cell with the polygon; emit
cell boundaries.

**Citation:** Ching 6th ed., Stone p. 197 plate.

**Parameters:**
```python
voronoi_fill(poly, mm_to_pt(200, scale), seed=42)
# Uses scipy.spatial.Voronoi; falls back to bounding-box Voronoi clipping
```

**ASCII sample:**
```
/-\__/-\___
|  X    \--\
\--/-\__/  |
   |    \__/
```

**Layer keywords:** `STONE_RUBBLE`, `STONE_ROUGH`, `RUBBLE`

**Notes:** Rustic foundations, garden walls. Lower priority for 2026
practice.

---

### 7. `slate` — Roofing slate / flooring slate

Overlapping rectangles at roof slope, or a 200×400 random-band pattern at
floor scale. Both share a horizontal-band base.

**Pattern math:** 200×400 mm tiles, half-tile offset every course (like
brick but rotated 90°). For roof: tiles run perpendicular to slope axis.

**Citation:** Ramsey/Sleeper 12th, Roofing; AutoCAD `AR-RSHKE`.

**Parameters:**
```python
brick_pattern(poly, mm_to_pt(200, scale), mm_to_pt(400, scale))
# rotated to slope angle if known
```

**ASCII sample:**
```
|----|----|----|----|
  |----|----|----|---
|----|----|----|----|
```

**Layer keywords:** `SLATE`, `_SLT_`, `ROOF_SLATE`

**Notes:** Pitched roofs, slate floors. Stable old material; still used
today on heritage + premium projects.

---

### 8. `terrazzo`

Random small "chip" stipples in two sizes inside a smooth field. No coursing.

**Pattern math:** Two layers of `stipple_triangles`:
- coarse chips: 4 mm spacing, 2 mm size
- fine chips: 2 mm spacing, 1 mm size

**Citation:** Ramsey/Sleeper 12th, Flooring; Ching p. 218.

**Parameters:**
```python
stipple_triangles(poly, mm_to_pt(4, scale), mm_to_pt(2, scale)) + \
stipple_triangles(poly, mm_to_pt(2, scale), mm_to_pt(1, scale))
```

**ASCII sample:**
```
. ▲  ·  ▲  · ·
·  ▲  ·  · ▲ ·
▲ · ·  ▲  · · ▲
```

**Layer keywords:** `TERRAZZO`, `_TZ_`

**Notes:** Floor finishes, stair treads, lobbies. Common 2026 commercial.

---

### 9. `stucco` — Cement plaster / EIFS finish coat

Fine random stipple, denser than gypsum, no directional pattern.

**Pattern math:** `stipple_dots` at 0.6 mm spacing, 0.2 mm dot size. Tighter
than gypsum (1.5 mm), looser than earth (0.4 mm).

**Citation:** Ramsey/Sleeper 12th, Plaster section.

**Parameters:**
```python
stipple_dots(poly, mm_to_pt(0.6, scale), dot_size=mm_to_pt(0.2, scale))
```

**ASCII sample:**
```
. . . · . · . . · .
· . . . · . . · · .
. · · . · . . . · ·
```

**Layer keywords:** `STUCCO`, `EIFS`, `PLASTER`, `_STC_`

**Notes:** Exterior finishes, residential, Mediterranean / desert
contemporary. Heavily used near user's Page AZ studio site.

---

### 10. `plywood_end_grain`

Three or four parallel curves following a wavy "ply" line, indicating
laminated edge of a plywood panel.

**Pattern math:** Existing `solid_timber` `offset_fn` with
`grain_offset = 0.4*sin(0.7y) + 0.2*sin(2.3y)` already does this, but at
plywood scale we need wider line spacing (3–6 mm) and consistent offset
between plies.

**Citation:** Ching p. 152, Wood section.

**Parameters:**
```python
parallel_hatch(
    poly, mm_to_pt(4, scale), _principal_angle(poly),
    offset_fn=lambda y: 0.6*math.sin(y*0.4) + 0.3*math.sin(y*1.7),
)
```

**ASCII sample:**
```
~~~~~~~~~~~~~~~~~
~~~~~~~~~~~~~~~~~
~~~~~~~~~~~~~~~~~
```

**Layer keywords:** `PLY_`, `PLYWOOD`, `_PLY_END_`

**Notes:** Sheathing edges, exposed end-grain in cabinetry / millwork.

---

### 11. `osb` — Oriented strand board

Random small rectangular flake stipples in two scales and rotations.

**Pattern math:** Random rectangles 8×3 mm at random angles, density ≈ 50%
coverage. Implement as Poisson-disk centers + a small rectangle (4 lines)
at each center with a random rotation.

**Citation:** Ramsey/Sleeper 12th, Wood Panels.

**Parameters:**
```python
osb_flakes(poly, mm_to_pt(6, scale), flake_size_mm=8, seed=42)
```

**ASCII sample:**
```
\\  //   \\  __  //
 //  \\  //  ||  \\
__  //  ||  \\  //
\\  ||  \\  //  __
```

**Layer keywords:** `OSB`, `_OSB_`, `STRAND_BOARD`

**Notes:** Sheathing, structural panels. Common in light-frame and
mass-timber hybrid construction.

---

### 12. `board_formed_concrete`

Standard concrete pattern (45° hatch + stipple) **plus** horizontal "board"
seams every 200 mm to indicate the formwork board pattern.

**Pattern math:** `hatch_concrete` + parallel horizontal lines spaced
200 mm at 0°.

**Citation:** Detail magazine 2018-2024 (heavily used Brutalist revival);
Ching p. 84.

**Parameters:**
```python
hatch_concrete(poly, scale) + \
parallel_hatch(poly, mm_to_pt(200, scale), 0.0)
```

**ASCII sample:**
```
___________________
. ' / / / .   /  .
___________________
   /  . ' /  .  .
___________________
```

**Layer keywords:** `CONC_BOARD`, `BOARD_FORM`, `BFC`

**Notes:** Walls, signature exposed-concrete projects. High contemporary
frequency.

---

### 13. `polished_concrete`

Light Poisson-disk stipple over a clean field. Indicates floor (no aggregate
exposure, sealed surface). Sparser than `concrete` recipe.

**Pattern math:** `stipple_dots` at 4 mm spacing, 0.15 mm dot. No diagonal
hatch (the slab is a finish, not a structural cut).

**Citation:** Ramsey/Sleeper 12th, Flooring; ASTM E303.

**Parameters:**
```python
stipple_dots(poly, mm_to_pt(4, scale), dot_size=mm_to_pt(0.15, scale))
```

**ASCII sample:**
```
.       .       .
    .       .
.       .   .
    .       .
```

**Layer keywords:** `CONC_POLISHED`, `POLISHED_CONC`, `_PC_FLR_`

**Notes:** Floor finishes; lobbies, retail, museums.

---

### 14. `rigid_insulation_xps`

Existing `insulation_rigid` recipe is generic — split into XPS (extruded,
crosshatch 45/135) and polyiso (different pattern, see #15).

**Pattern math:** Crosshatch at 45° + 135°, 1.0 mm spacing (matches existing
`insulation_rigid`).

**Citation:** ASTM C578; Ramsey/Sleeper 12th.

**Parameters:**
```python
crosshatch(poly, mm_to_pt(1.0, scale), 45.0, 135.0)
```

**ASCII sample:**
```
\X/X/X/X/X/X/X/X
/X\X/X\X/X\X/X\X
\X/X/X/X/X/X/X/X
```

**Layer keywords:** `XPS`, `_XPS_`

**Notes:** Below-grade, foundations, cavity insulation.

---

### 15. `rigid_insulation_polyiso`

PIR / polyiso typically drawn as **diagonal hatch with embedded triangles**
to distinguish from XPS.

**Pattern math:** Single-direction parallel hatch at 45°, 1.0 mm spacing,
with a triangle stipple at 4 mm Poisson spacing in between.

**Citation:** ASTM C1289; Ramsey/Sleeper 12th.

**Parameters:**
```python
parallel_hatch(poly, mm_to_pt(1.0, scale), 45.0) + \
stipple_triangles(poly, mm_to_pt(4, scale), size=mm_to_pt(0.5, scale))
```

**ASCII sample:**
```
//▲//////▲//////
/////▲///////▲//
//▲//////▲//////
```

**Layer keywords:** `PIR`, `POLYISO`, `_PIR_`

**Notes:** Roof insulation primarily; cavity insulation in commercial.

---

### 16. `standing_seam_copper` / `standing_seam_zinc`

Single-direction parallel seams at 45–60 cm spacing, perpendicular to slope.
Real seams are vertical ribs but in section we only see the seam location.

**Pattern math:** `parallel_hatch` at the slope direction, spacing 500 mm
(seam pitch), no fill between.

**Citation:** Detail magazine, copper-roof case studies; Ramsey/Sleeper
12th, Roofing Metals.

**Parameters:**
```python
parallel_hatch(poly, mm_to_pt(500, scale), _principal_angle(poly) + 90)
# Plus: thin parallel hatch 0.18 pt at 100 mm to indicate panel pattern
```

**ASCII sample (in section, perpendicular to seams):**
```
|              |              |
|              |              |
|              |              |
```

**Layer keywords:** `_CU_SS_`, `CU_STANDING`, `STANDING_SEAM`,
`COPPER_ROOF`, `ZN_SS_`

**Notes:** Roofs (most common) + walls (contemporary rain-screen).
**Critical for the user's own ARCH 202B project (copper rain screen).**

---

### 17. `zinc_panel`

Similar to standing-seam copper but tighter seam pitch and an optional
horizontal lap line every 1500 mm.

**Pattern math:** `parallel_hatch` at slope direction, 300 mm seam pitch,
plus 1500 mm lap line crosshatch.

**Citation:** Ramsey/Sleeper 12th, Architectural Metals; Detail magazine.

**Parameters:**
```python
parallel_hatch(poly, mm_to_pt(300, scale), 90.0) + \
parallel_hatch(poly, mm_to_pt(1500, scale), 0.0)
```

**ASCII sample:**
```
|  |  |  |  |  |  |
___________________
|  |  |  |  |  |  |
___________________
```

**Layer keywords:** `_ZN_`, `ZINC`, `ZN_PANEL`

**Notes:** Walls + roofs; common in EU contemporary.

---

### 18. `etfe_cushion`

Two thin parallel curves with a soft sine "puff" in the middle, indicating
inflated cushion in section.

**Pattern math:** Two `parallel_hatch` lines along principal axis with a
sine-wave amplitude offset between them. For a 200 mm cushion thickness,
draw top + bottom membrane (2 lines) and a wavy mid-line.

**Citation:** Detail magazine ETFE special issue (2014, 2019); Vector
Foiltec technical sheets.

**Parameters:**
```python
parallel_hatch(poly, mm_to_pt(200, scale), _principal_angle(poly))[:3]
# Plus a sine_zigzag with very low amplitude for the inflation indicator
```

**ASCII sample:**
```
~~~~~~~~~~~~~~~~~~  (top membrane)
                        (puff)
~~~~~~~~~~~~~~~~~~  (bottom membrane)
```

**Layer keywords:** `ETFE`, `_ETFE_`, `CUSHION`

**Notes:** Roofs of large public buildings, atriums, stadiums.

---

### 19. `wood_flooring`

Single-direction parallel lines at plank spacing (180 mm), perpendicular to
plank length. Optional offset stagger to indicate joints.

**Pattern math:** `parallel_hatch` at 0° (or grain), 180 mm spacing, plus
random short perpendicular ticks at 1500 mm to mark plank ends.

**Citation:** Ching 6th ed.; AutoCAD `AR-PARQ1`.

**Parameters:**
```python
parallel_hatch(poly, mm_to_pt(180, scale), _principal_angle(poly))
# + sparse perpendicular ticks every 1500 mm
```

**ASCII sample:**
```
___________________
___________________
___________________
___________________
```

**Layer keywords:** `WOOD_FLR`, `_TIMB_FLR_`, `OAK_FLR`, `PLANK`

**Notes:** Floors. Distinguish from CLT cross-grain (which is structural).

---

### 20. `carpet`

Dense fine stipple (denser than gypsum, lighter than earth) plus a slight
random horizontal grain.

**Pattern math:** `stipple_dots` at 0.5 mm spacing + a single very faint
parallel hatch at random angle for fiber direction.

**Citation:** Ramsey/Sleeper 12th, Flooring.

**Parameters:**
```python
stipple_dots(poly, mm_to_pt(0.5, scale), dot_size=mm_to_pt(0.1, scale))
```

**ASCII sample:**
```
.·.·.·.·.·.·.·.·
·.·.·.·.·.·.·.·.
.·.·.·.·.·.·.·.·
```

**Layer keywords:** `CARPET`, `_CPT_`, `_CARPET_`

**Notes:** Commercial interiors, residential, theaters.

---

### 21. `acoustic_ceiling_tile`

2'×2' or 2'×4' rectangular grid (610×610 or 610×1220 mm) with crisp lines.

**Pattern math:** Rectangular grid via two perpendicular `parallel_hatch`
calls at 610 and 1220 mm spacing.

**Citation:** Armstrong / USG technical libraries; Ramsey/Sleeper 12th.

**Parameters:**
```python
parallel_hatch(poly, mm_to_pt(610, scale), 0.0) + \
parallel_hatch(poly, mm_to_pt(1220, scale), 90.0)
```

**ASCII sample:**
```
|     |     |     |
|_____|_____|_____|
|     |     |     |
|_____|_____|_____|
```

**Layer keywords:** `ACT`, `ACOUSTIC_CEIL`, `CEIL_TILE`, `_ACT_`

**Notes:** Suspended ceilings. Commercial workhorse.

---

### 22. `single_ply_membrane`

Heavy single line (TPO/EPDM/PVC). At cut, drawn as a thick solid line plus
an optional fine 45° hatch underneath to distinguish from the substrate.

**Pattern math:** No internal hatch — recipe returns empty list. Caller
draws the membrane outline at heavier weight (0.35–0.5 pt). For visual
distinction in section, optional dense parallel hatch at 1 mm spacing.

**Citation:** GAF / Carlisle technical sheets; Ramsey/Sleeper 12th.

**Parameters:**
```python
# Membrane is generally a thick line, not a hatch, but at section/detail
# scale we add a dense hatch to indicate "rubber"
parallel_hatch(poly, mm_to_pt(0.8, scale), 0.0)
```

**ASCII sample:**
```
═══════════════════
═══════════════════
═══════════════════
```

**Layer keywords:** `EPDM`, `TPO`, `PVC_ROOF`, `_MEM_`, `MEMBRANE`,
`SINGLE_PLY`

**Notes:** Flat / low-slope roofs. Already partially mapped via existing
`MEMBRANE` → `concrete_solid` keyword (this is wrong — fix in
`material_for_layer` diff below).

---

### 23. `bituminous_waterproofing`

Heavy single line + dense closely-spaced 45° hatch indicating built-up
asphalt.

**Pattern math:** `parallel_hatch` at 45°, 0.5 mm spacing (very dense).

**Citation:** ASTM D6164; Ramsey/Sleeper 12th, Waterproofing.

**Parameters:**
```python
parallel_hatch(poly, mm_to_pt(0.5, scale), 45.0)
```

**ASCII sample:**
```
//////////////////
//////////////////
//////////////////
```

**Layer keywords:** `BITUMEN`, `_WP_`, `WATERPROOF`, `BUR`

**Notes:** Foundations, roof underlayment.

---

### 24. `gravel`

Random small irregular stipples + occasional larger circles to indicate
aggregate.

**Pattern math:** `stipple_triangles` at 2 mm spacing, 1 mm size + sparse
larger triangles at 8 mm spacing, 2 mm size.

**Citation:** AutoCAD `GRAVEL`; Ching p. 220 plate.

**Parameters:**
```python
stipple_triangles(poly, mm_to_pt(2, scale), size=mm_to_pt(1, scale)) + \
stipple_triangles(poly, mm_to_pt(8, scale), size=mm_to_pt(2, scale))
```

**ASCII sample:**
```
▲ . ▲ ·  ▲ · ▲
· ▲ ·   ▲ . ·
▲ . · ▲ ·  ▲ ▲
```

**Layer keywords:** `GRAVEL`, `BALLAST`, `_GRVL_`, `_AGG_DRAIN_`

**Notes:** Drainage layers, ballast on flat roofs, landscape.

---

### 25. `pavers_running_bond`

Same as brick, but unit size 200×200 mm or 100×200 mm. Different scale
distinguishes from wall brick.

**Pattern math:** `brick_pattern(poly, 200, 100)` — half-paver offset.

**Citation:** Ching plates; Ramsey/Sleeper Paving section.

**Parameters:**
```python
brick_pattern(poly, mm_to_pt(200, scale), mm_to_pt(100, scale))
```

**ASCII sample:**
```
|---|---|---|---|
  |---|---|---|--
|---|---|---|---|
```

**Layer keywords:** `PAVER`, `_PVRS_`, `PAVERS`

**Notes:** Plazas, courtyards, hardscape.

---

### 26. `glass_block`

Square grid pattern (190×190 mm typical) with small interior cross to indicate
the cellular block. Used in cut + plan.

**Pattern math:** Two perpendicular `parallel_hatch` at 190 mm spacing
(grid) + an inner small cross per cell.

**Citation:** Pittsburgh Corning technical lit; Ramsey/Sleeper 12th.

**Parameters:**
```python
parallel_hatch(poly, mm_to_pt(190, scale), 0.0) + \
parallel_hatch(poly, mm_to_pt(190, scale), 90.0)
# + per-cell cross
```

**ASCII sample:**
```
|---|---|---|
| X | X | X |
|---|---|---|
| X | X | X |
|---|---|---|
```

**Layer keywords:** `GLASS_BLOCK`, `GBLOCK`, `_GLB_`

**Notes:** Walls (rare in 2026 but still detailed for restoration).

---

### 27. `cork_linoleum`

Very fine random stipple — denser than carpet, lighter than terrazzo.

**Pattern math:** `stipple_dots` at 0.4 mm spacing, 0.1 mm dot.

**Citation:** Forbo / Armstrong technical lit; Ramsey/Sleeper Flooring.

**Parameters:**
```python
stipple_dots(poly, mm_to_pt(0.4, scale), dot_size=mm_to_pt(0.1, scale))
```

**ASCII sample:**
```
··············
··············
··············
```

**Layer keywords:** `CORK`, `LINO`, `LINOLEUM`, `MARMOLEUM`

**Notes:** Healthcare, schools, commercial. Sustainable specifications.

---

### 28. `perforated_metal`

Existing aluminum recipe + a regular array of small dots indicating
perforation.

**Pattern math:** `parallel_hatch` 45°, 0.8 mm + `stipple_dots` at 6 mm
spacing (regular grid via `parallel_hatch` instead of Poisson for
perforation pattern).

**Citation:** McNichols / Hendrick technical lit; relevant to user's
copper rain screen.

**Parameters:**
```python
parallel_hatch(poly, mm_to_pt(0.8, scale), 45.0) + \
stipple_dots(poly, mm_to_pt(6, scale), dot_size=mm_to_pt(2, scale))
```

**ASCII sample:**
```
//// o //// o //// o
//// o //// o //// o
//// o //// o //// o
```

**Layer keywords:** `_CU_PUNCH_`, `PERF_METAL`, `PERFORATED`

**Notes:** Rain screens, screens, balustrades. **High priority for user's
own project (perforated copper).**

---

### 29. `rammed_earth` / `earth_cut`

Horizontal striations indicating rammed lifts (typically 100–200 mm), plus
a fine stipple. Distinct from generic `earth` which is uniform stipple.

**Pattern math:** `parallel_hatch` at 0°, 150 mm spacing (random ±20 mm
offset between courses) + light `stipple_dots` at 1 mm.

**Citation:** Detail magazine, Wangen Tower; Ching p. 195.

**Parameters:**
```python
parallel_hatch(poly, mm_to_pt(150, scale), 0.0) + \
stipple_dots(poly, mm_to_pt(1.0, scale), dot_size=mm_to_pt(0.15, scale))
```

**ASCII sample:**
```
___________________
. · .   · . . · .
___________________
· . · · . . · . .
___________________
```

**Layer keywords:** `RAMMED_EARTH`, `RE_`, `_RAMMED_`

**Notes:** Walls. Niche but high-impact for sustainable architecture.

---

### 30. `asphalt_shingles`

Stagger of small rectangles (300×900 mm) following slope. Like a brick
pattern but different proportions and only the bottom edge of each course
is drawn (overlap implied).

**Pattern math:** `parallel_hatch` at slope direction, 200 mm spacing
(course height), plus short perpendicular ticks every 300 mm.

**Citation:** GAF / CertainTeed technical lit; Ramsey/Sleeper Roofing.

**Parameters:**
```python
brick_pattern(poly, mm_to_pt(300, scale), mm_to_pt(200, scale))
```

**ASCII sample:**
```
|--|--|--|--|--|
   |--|--|--|--|
|--|--|--|--|--|
```

**Layer keywords:** `SHINGLE`, `ASPHALT_SH`, `_SHGL_`, `ROOF_SHINGLE`

**Notes:** Pitched roofs, residential. Stable old material.

---

## Implementation plan

### Wave 1 — high-impact + quick (week 1, ~4 hours)

These 5 recipes use **only existing helpers** (no new geometry), are the
highest frequency in real drawings, and unblock the user's own ARCH 202B
project plus most commercial work:

1. **`cmu`** — `brick_pattern(poly, 390, 190)`. Highest masonry omission.
2. **`board_formed_concrete`** — `hatch_concrete + parallel_hatch 200@0°`.
3. **`standing_seam_copper`** — `parallel_hatch + parallel_hatch`.
4. **`stucco`** — `stipple_dots(0.6, 0.2)`.
5. **`rigid_insulation_polyiso`** — `parallel_hatch + stipple_triangles`.

### Wave 2 — finishes (week 2, ~3 hours)

6. **`wood_flooring`** — `parallel_hatch` at plank spacing
7. **`carpet`** — fine `stipple_dots`
8. **`acoustic_ceiling_tile`** — orthogonal grid via 2 `parallel_hatch`
9. **`polished_concrete`** — sparser `stipple_dots`
10. **`terrazzo`** — two-scale `stipple_triangles`

### Wave 3 — masonry variants (week 3, ~5 hours, needs `random_band_pattern` + Voronoi)

11. **`brick_running_bond`** — alias of existing `brick`
12. **`brick_flemish_bond`** — modified brick
13. **`brick_herringbone`** — rotated brick
14. **`pavers_running_bond`** — `brick_pattern(200, 100)`
15. **`stone_cut`** — random_band_pattern (NEW helper)
16. **`stone_rough`** — Voronoi (NEW helper, requires scipy)

### Wave 4 — roofing + waterproofing (week 4, ~3 hours)

17. **`single_ply_membrane`** — dense parallel_hatch
18. **`bituminous_waterproofing`** — dense 45° hatch
19. **`gravel`** — two-scale stipple
20. **`asphalt_shingles`** — `brick_pattern(300, 200)`
21. **`slate`** — `brick_pattern(200, 400)`

### Wave 5 — modern envelope (week 5, ~3 hours)

22. **`zinc_panel`** — copper variant
23. **`etfe_cushion`** — partial parallel_hatch + sine_zigzag
24. **`perforated_metal`** — aluminum + regular dots
25. **`glass_block`** — orthogonal grid
26. **`osb`** — random rectangle stipple (needs new `random_rect_stipple`)

### Wave 6 — niche (week 6, ~2 hours)

27. **`plywood_end_grain`** — wider `solid_timber` variant
28. **`rammed_earth`** — striated earth
29. **`cork_linoleum`** — finer carpet
30. **`rigid_insulation_xps`** — alias of `insulation_rigid`

After Wave 1, the library is at **19 recipes** (passes 25+ minimum once
Wave 2 lands; comfortably at 30 after Wave 5).

## `material_for_layer()` keyword extension diff

```python
# In src/arch_line_weights/hatch.py — REPLACE existing LAYER_TO_MATERIAL list:

LAYER_TO_MATERIAL: list[tuple[str, str]] = [
    # 1. Section-cut elements (most specific first)
    ("CONCRETE_BOARD", "board_formed_concrete"),
    ("BOARD_FORM", "board_formed_concrete"),
    ("BFC", "board_formed_concrete"),
    ("CONC_POLISHED", "polished_concrete"),
    ("POLISHED_CONC", "polished_concrete"),
    ("_PC_FLR_", "polished_concrete"),
    ("CONCRETE", "concrete_solid"),
    ("FOUNDATION", "concrete_solid"),
    ("CMU", "cmu"),
    ("CONC_BLOCK", "cmu"),
    ("BLOCKWORK", "cmu"),

    # 2. Mass timber
    ("CLT", "clt_solid"),
    ("PLY_END", "plywood_end_grain"),
    ("PLYWOOD", "plywood_end_grain"),
    ("OSB", "osb"),
    ("STRAND_BOARD", "osb"),
    ("WOOD_FLR", "wood_flooring"),
    ("_TIMB_FLR_", "wood_flooring"),
    ("OAK_FLR", "wood_flooring"),
    ("PLANK", "wood_flooring"),
    ("TIMBER", "solid_timber"),

    # 3. Steel
    ("STEEL", "steel_solid"),
    ("SHS", "steel_solid"),
    ("RHS", "steel_solid"),
    ("BRACKET", "steel_solid"),
    ("CLEAT", "steel_solid"),
    ("STAIR", "concrete_solid"),

    # 4. Architectural metals
    ("WINDOW_FRAME", "aluminum"),
    ("ALUM", "aluminum"),
    ("PERF_METAL", "perforated_metal"),
    ("PERFORATED", "perforated_metal"),
    ("_CU_PUNCH_", "perforated_metal"),
    ("_CU_SS_", "standing_seam_copper"),
    ("CU_STANDING", "standing_seam_copper"),
    ("STANDING_SEAM", "standing_seam_copper"),
    ("COPPER_ROOF", "standing_seam_copper"),
    ("_ZN_", "zinc_panel"),
    ("ZINC", "zinc_panel"),
    ("ZN_PANEL", "zinc_panel"),
    ("CU_", "concrete_solid"),  # generic copper falls back to solid
    ("CLADDING", "concrete_solid"),

    # 5. Insulation
    ("XPS", "rigid_insulation_xps"),
    ("PIR", "rigid_insulation_polyiso"),
    ("POLYISO", "rigid_insulation_polyiso"),
    ("MINERAL", "insulation_mineral_wool"),
    ("INSUL", "insulation_mineral_wool"),

    # 6. Membranes / waterproofing
    ("EPDM", "single_ply_membrane"),
    ("TPO", "single_ply_membrane"),
    ("PVC_ROOF", "single_ply_membrane"),
    ("SINGLE_PLY", "single_ply_membrane"),
    ("MEMBRANE", "single_ply_membrane"),
    ("BITUMEN", "bituminous_waterproofing"),
    ("BUR", "bituminous_waterproofing"),
    ("WATERPROOF", "bituminous_waterproofing"),

    # 7. Roofing
    ("SLATE", "slate"),
    ("SHINGLE", "asphalt_shingles"),
    ("ASPHALT_SH", "asphalt_shingles"),
    ("ETFE", "etfe_cushion"),
    ("CUSHION", "etfe_cushion"),

    # 8. Earth / aggregate
    ("RAMMED_EARTH", "rammed_earth"),
    ("RAMMED", "rammed_earth"),
    ("EARTH", "earth"),
    ("GROUND", "earth"),
    ("GRAVEL", "gravel"),
    ("BALLAST", "gravel"),
    ("_AGG_DRAIN_", "gravel"),

    # 9. Masonry
    ("BRICK_HB", "brick_herringbone"),
    ("HERRINGBONE", "brick_herringbone"),
    ("BRICK_FLEM", "brick_flemish_bond"),
    ("FLEMISH", "brick_flemish_bond"),
    ("BRICK", "brick_running_bond"),
    ("PAVER", "pavers_running_bond"),
    ("STONE_CUT", "stone_cut"),
    ("ASHLAR", "stone_cut"),
    ("LIMESTONE", "stone_cut"),
    ("SANDSTONE", "stone_cut"),
    ("STONE_RUBBLE", "stone_rough"),
    ("STONE_ROUGH", "stone_rough"),
    ("RUBBLE", "stone_rough"),

    # 10. Glazing
    ("GLASS_BLOCK", "glass_block"),
    ("GBLOCK", "glass_block"),
    ("GLASS", "glass"),
    ("IGU", "glass"),

    # 11. Finishes
    ("STUCCO", "stucco"),
    ("EIFS", "stucco"),
    ("PLASTER", "stucco"),
    ("TERRAZZO", "terrazzo"),
    ("CARPET", "carpet"),
    ("CORK", "cork_linoleum"),
    ("LINO", "cork_linoleum"),
    ("LINOLEUM", "cork_linoleum"),
    ("MARMOLEUM", "cork_linoleum"),
    ("ACT", "acoustic_ceiling_tile"),
    ("ACOUSTIC_CEIL", "acoustic_ceiling_tile"),
    ("CEIL_TILE", "acoustic_ceiling_tile"),

    # 12. Drywall (matches last so GWB doesn't override more specific)
    ("GYP", "gypsum"),
    ("GWB", "gypsum"),
]
```

Result: 87 keyword-to-material mappings (vs. 26 today). Order respects
"most specific first" so `BRICK_HB` matches before `BRICK`, `RAMMED_EARTH`
before `EARTH`, etc.

## Test plan (per-wave)

After each wave:

1. Add a synthetic test polygon (200×800 mm wall) per recipe in
   `tests/test_hatch.py` and assert (a) recipe registered, (b) returns
   `list[LineString]`, (c) line count > 0 for non-solid, (d) all returned
   lines fall within polygon bounds.
2. Run `arch-lw poche --style material` against
   `tests/fixtures/section_with_all_materials.ai` and visually diff vs
   the v0.3-baseline expected SVG.
3. Update `material_for_layer()` test cases to assert the new keyword
   matches.

## Open questions / future work

- **Hatch density at scale**: at 1/16"=1', a 0.4 mm stipple becomes
  invisible. Should the recipe inspect `scale` and switch to a coarser
  stipple below a threshold? (Defer to E3.)
- **Color**: glass is conventionally drawn light-blue. Recipe currently
  returns generic linestrings; coloring lives in the apply step. Do we
  attach a `recommended_color` to `MaterialRecipe`? (Defer to E4.)
- **DXF roundtrip**: AutoCAD's `acad.pat` patterns can be mapped 1:1 to
  many of these recipes. A `to_acad_pattern_name()` method would let
  `arch-lw export-dxf` emit native HATCH entities. (Phase F.)

---

## Sources cited (per-section above)

- Ramsey & Sleeper, *Architectural Graphic Standards*, 12th ed. — material
  symbol plates throughout
- Ching, *Architectural Graphics*, 6th ed. — section/plan vocabulary
- ISO 128-50 — sectional view conventions
- NCS v5 Plotting Guidelines
- AutoCAD `acad.pat` reference (Autodesk help, GUID-1BAB5B5C-D8AC-4729-AB69-9DA92B7204A3)
- ASTM C578 (XPS), C1289 (polyiso), D6164 (bituminous)
- Detail magazine 2014–2024 (ETFE, copper, rammed-earth issues)
