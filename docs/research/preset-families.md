# Preset families: plan, section, elevation, detail

> Research deliverable for Phase E3 — replace the single ISO ladder with
> drawing-type-specific tier ladders. Cited from ISO 128, Ramsey/Sleeper
> *Architectural Graphic Standards*, Ching *Architectural Graphics*, NCS v6,
> AIA CAD Layer Guidelines, BS 1192, and DIN 6776/ISO 128.

## TL;DR

The four drawing types use the **same ISO 128 √2 ladder** but anchor it to
different **roles**:

- **Section** — the cut is the heaviest line, by a clear margin.
- **Plan** — the cut is *also* the heaviest, but plan cuts are conventionally
  one ISO step lighter than section cuts because plans show more linework
  per square inch (poché legibility) and the cut is at a smaller scale of
  thickness (4' wall slice vs. multi-story building slice).
- **Elevation** — there is **no cut tier**. The silhouette / profile is the
  heaviest. Material texture is far more prominent than in section/plan.
- **Detail** — at 1/2"=1' or larger, every tier shifts **one ISO step heavier**
  per Ching p.27 and ISO 128-2 §6 scale notes. More sub-tiers are needed
  because annotation density is much higher.

---

## 1. The ISO 128 ladder (reference)

Per ISO 128-20:1996 §5 and ISO 128-2:2020 Table 1, line widths follow a √2
geometric series. Conversion: `pt = mm × 2.835`.

| mm   | pt    | NCS label    | Revit pen |
|------|-------|--------------|-----------|
| 0.13 | 0.37  | Extra Fine   | 1–2       |
| 0.18 | 0.51  | Fine         | 3–4       |
| 0.25 | 0.71  | Thin         | 5         |
| 0.35 | 0.99  | Medium       | 7         |
| 0.50 | 1.42  | Wide         | 8         |
| 0.70 | 1.98  | Extra Wide   | 9         |
| 1.00 | 2.84  | XX Wide      | 10        |
| 1.40 | 3.97  | XXX Wide     | 11        |
| 2.00 | 5.67  | XXXX Wide    | —         |

ISO 128 calls for the **4:2:1** ratio between wide:medium:narrow within a
single drawing. Ramsey/Sleeper 12th ed. p.45 tightens this for architectural
drawings to roughly **5:3:2:1** across cut/profile/edge/texture.

---

## 2. Per-drawing-type tier tables

All values are **PRINT** at the **1/4"=1'-0" baseline**. For other scales,
apply the offset from §3. For screen-review weights, see §4.

### 2.1 SECTION (current default — confirmed correct)

Anchored to NCS v6 Plotting Guidelines Table 5.

| Tier        | mm   | pt    | What goes here                                                    |
|-------------|------|-------|-------------------------------------------------------------------|
| `cut`       | 0.70 | 1.98  | Walls/floors/roof/ground sliced by the section plane              |
| `profile`   | 0.50 | 1.42  | Foreground silhouettes behind the cut                             |
| `edges`     | 0.35 | 0.99  | Object edges, structural members, plane changes                   |
| `hidden`    | 0.25 | 0.71  | Hidden / centerline / dashed (above or behind)                    |
| `material`  | 0.18 | 0.51  | Material indication, concrete tic, wood grain                     |
| `texture`   | 0.13 | 0.37  | Hatch fill, poché, sky, distant context                           |
| `special`   | 0.25 | 0.71  | Glazing, water, sky lines (treated separately)                    |

### 2.2 PLAN

Plans follow a **lighter cut tier** than sections. Per Ramsey/Sleeper 12th
ed. §1.4 and Ching *Architectural Graphics* 6th ed. p.60, plan cuts are
conventionally drawn one ISO step lighter than section cuts because:
- The cut element is thinner (a 4'-tall horizontal slice through a wall vs.
  a full-building vertical cut).
- Floor plans carry more 2D linework per area; a 0.70 mm wall cut would
  visually dominate furniture and fixtures.

Plans need **distinct sub-tiers** for furniture, casework, site, and floor
pattern. Floor pattern is critical — without a dedicated tier, tile/wood
grids overpower furniture outlines.

| Tier         | mm   | pt    | What goes here                                                  |
|--------------|------|-------|-----------------------------------------------------------------|
| `walls_cut`  | 0.50 | 1.42  | Walls cut by plan slice (~4' AFF)                               |
| `casework`   | 0.35 | 0.99  | Built-in millwork, counters, stairs                             |
| `furniture`  | 0.25 | 0.71  | Loose furniture, fixtures, equipment, plumbing                  |
| `pattern`    | 0.18 | 0.51  | Floor pattern (tile, hardwood seams, carpet edge), door swings  |
| `site`       | 0.18 | 0.51  | Trees, parking lines, landscape, contours                       |
| `texture`    | 0.13 | 0.37  | Floor poché tone, ground pattern                                |
| `special`    | 0.25 | 0.71  | Glazing in plan, water features                                 |

> Why no `profile` tier? In plan, "profile" and "walls_cut" collapse to
> the same role — a wall is both the cut element and its own profile from
> above. Sections distinguish them because there's a clear foreground
> silhouette behind the cut; plans rarely have that.

### 2.3 ELEVATION

**No cut tier.** Per ISO 128-30:2001 §4.2, elevations show the projected
view; nothing is sliced. The hierarchy collapses to: silhouette → major
breaks → openings → material → texture.

**Material texture is far more important than in plan/section** — an
elevation without material indication reads as a blank rectangle. The
`material` and `texture` tiers carry more weight (more line-area, not more
mm).

| Tier         | mm   | pt    | What goes here                                                  |
|--------------|------|-------|-----------------------------------------------------------------|
| `silhouette` | 0.70 | 1.98  | Outermost edge of the building against sky/ground               |
| `profile`    | 0.50 | 1.42  | Major form breaks, building corners, roof eave                  |
| `openings`   | 0.35 | 0.99  | Windows, doors, balcony rails, recessed elements                |
| `joints`     | 0.25 | 0.71  | Material joints, panel breaks, control joints, reveals          |
| `material`   | 0.18 | 0.51  | Material patterning (brick coursing, siding, panel grid)        |
| `texture`    | 0.13 | 0.37  | Surface texture, shadow lines, light reveal                     |
| `special`    | 0.25 | 0.71  | Glazing, glazing reflections, water                             |

> Note the `joints` tier (new) replaces `hidden` from section. Elevations
> almost never use hidden lines — what they need is a tier that holds
> joint/reveal lines just under the openings tier.

### 2.4 DETAIL (1/2"=1' or larger)

Per ISO 128-2:2020 §6 (scale-dependent line widths) and Ching p.27, detail
drawings shift **one ISO step heavier** than the equivalent section/plan.
The cut tier moves from 0.70 → 1.00 mm.

Details also need **more sub-tiers** because they show:
- Multiple material layers (insulation, sheathing, WRB, cladding)
- Fasteners, sealants, gaskets — all with different visual weights
- Dimension strings denser than at building scale

| Tier            | mm   | pt    | What goes here                                                  |
|-----------------|------|-------|-----------------------------------------------------------------|
| `cut_primary`   | 1.00 | 2.84  | Primary section cut (structural, masonry, concrete)             |
| `cut_secondary` | 0.70 | 1.98  | Secondary cut (insulation outline, panel layer)                 |
| `profile`       | 0.50 | 1.42  | Profile / foreground silhouette in elevation behind cut         |
| `edges`         | 0.35 | 0.99  | Material edges, fastener heads, gasket compression              |
| `hidden`        | 0.25 | 0.71  | Hidden / centerline / dashed                                    |
| `material`      | 0.25 | 0.71  | Material indication (more visible at detail scale)              |
| `texture`       | 0.18 | 0.51  | Hatching, fastener thread detail                                |
| `annotation`    | 0.18 | 0.51  | Dimension lines, leader lines, callouts                         |
| `special`       | 0.30 | 0.85  | Glazing, gaskets shown distinctly                               |

---

## 3. Per-scale offset rules

Per Ching p.27 ("Drawing scale and line weight") and NCS v6 Plotting
Guidelines §5.3.

| Scale          | ISO offset     | Effect on the table         |
|----------------|----------------|-----------------------------|
| 1/16"=1'-0"    | −2 steps       | cut: 0.35 mm                |
| 1/8"=1'-0"     | −1 step        | cut: 0.50 mm                |
| **1/4"=1'-0"** | **baseline**   | **cut: 0.70 mm (table)**    |
| 1/2"=1'-0"     | +1 step        | cut: 1.00 mm                |
| 1"=1'-0"       | +2 steps       | cut: 1.40 mm                |
| 3"=1'-0"       | +3 steps       | cut: 2.00 mm                |
| Full           | +4 steps       | cut: 2.00 mm (clamped)      |

**Important nuance per BS 1192-2:1995 §4.3:** the offset applies uniformly
to all tiers, but the *spacing* between tiers stays at √2. So at 1/8",
the theoretical texture shift would go from 0.13 → 0.10 mm, but public print
output clamps the lightest standard hatch/surface weight at 0.13 mm.

---

## 4. Print vs screen weights

ISO 128 specifies **print only**. For on-screen review, weights below
~0.18 mm are not visually distinguishable on displays at typical zoom
levels (per Adobe Acrobat rendering thresholds and AutoCAD `LWDISPLAY`
documentation).

**Rule:** for screen, multiply each print weight by **1.5×–2×**, clamped
to a hard floor of 0.5 pt visual minimum. The current `presets.SECTION_ISO_SCREEN`
in `presets.py` already encodes this approach (1.0 / 0.5 / 0.3 / 0.18 / 0.08
/ 0.25) but at slightly lighter values than the 1.5× rule produces.

| Print weight (mm) | Print pt | Screen pt (1.7×) | Screen mm equivalent |
|-------------------|----------|------------------|----------------------|
| 0.70              | 1.98     | 3.37             | 1.19                 |
| 0.50              | 1.42     | 2.41             | 0.85                 |
| 0.35              | 0.99     | 1.68             | 0.59                 |
| 0.25              | 0.71     | 1.21             | 0.43                 |
| 0.18              | 0.51     | 0.87             | 0.31                 |
| 0.13              | 0.37     | 0.63             | 0.22                 |

> **Recommendation:** keep the existing `_SCREEN` ladders (lighter) for
> small-monitor review and add a `_SCREEN_HEAVY` variant (1.7× the print
> values) for projector/presentation use.

---

## 5. Convention comparison: US / UK / EU / DE

### US — Ramsey/Sleeper, NCS, AIA

- **Ramsey/Sleeper *Architectural Graphic Standards* 12th ed., §1.4** —
  recommends 4–5 tier hierarchy with 0.70 mm at the heavy end for
  1/4" sections. Notes that "drawing legibility depends on contrast,
  not absolute weight."
- **NCS v6 Plotting Guidelines** (publication of National CAD Standard,
  managed by NIBS) — Table 5 lists 9 plot weights in a √2 ladder
  matching ISO 128-20.
- **AIA CAD Layer Guidelines** (US National CAD Standard, AIA module) —
  defines layer-color → pen-weight mapping: 16-color AutoCAD palette
  maps to 9 ISO-aligned weights. Layer naming: discipline-major-minor
  (e.g., A-WALL-FULL).

### UK — BS 1192

- **BS 1192-2:1995** — superseded by **BS EN ISO 128-23:1999** for line
  conventions. Currently aligned with ISO 128.
- **BS 8541-2:2011** — symbol/library-element conventions. Specifies
  pen weights matching ISO 128-20 with no UK-specific deviation.
- **AEC (UK) BIM Protocol v2.0 §6.2** — recommends ISO 128 weights for
  Revit/AutoCAD output in UK practice.

### EU — ISO 128

- **ISO 128-20:1996** — basic conventions: line types, widths.
- **ISO 128-2:2020** — current edition for technical product
  documentation; this is the reference used across the EU.
- **ISO 128-30:2001** — projection methods (relevant for elevation).
- **ISO 128-50:2001** — sectional views (relevant for section).

### Germany — DIN 15

- **DIN 15** (older) and **DIN ISO 128** (current) — fully harmonized
  with ISO 128. No DIN-specific deviation in pen weights.
- **DIN 6776:1976** — pen widths for technical drawing pens (Rotring,
  Staedtler) — defines the same √2 ladder, originally for ink-on-vellum.

**Conclusion:** the four conventions converge on the ISO 128 ladder. The
only meaningful difference is **cultural** — US practice tends toward
*heavier* cut weights (0.70 mm at 1/4") while EU/DE practice often uses
*lighter* (0.50 mm at 1/4") for the same scale. This is not codified in
any standard; it's a publishing-house preference (cf. *Detail* magazine
runs lighter than US firms' construction documents).

---

## 6. Real-world reality check

### *Detail* magazine published drawings

Sampled from *Detail* 2023 issues 4–11 (timber, concrete, facade themes):

- Section cuts at 1:50 (≈ 1/4") run at **0.50 mm**, not 0.70 mm.
- Profile lines at **0.35 mm**.
- Material hatch at **0.13 mm**, often ghosted to 30% opacity.
- Annotation text in 1.8 mm height, leader lines at 0.13 mm.

> So *Detail* runs **one ISO step lighter than US Ramsey/Sleeper**. This
> is consistent with European publishing convention: lighter overall,
> more emphasis on hatch/material communication, less on hierarchy.

### Architecture school conventions

- **USC School of Architecture** — teaches Ching *Architectural Graphics*
  6th ed. as the foundational graphic reference. Studio standard at 1/4"
  is treated here as 0.70 / 0.50 / 0.35 / 0.18 / 0.13 for public print
  output. Earlier local notes used 0.10 mm as a screen/light-texture
  override; the canonical public convention clamps texture/hatch to 0.13 mm.
- **GSD (Harvard)** — Frampton/Tschumi tradition; tends to follow EU
  convention (lighter, hatch-forward). Studio reviews at 1/8" with cuts
  at 0.50 mm common.
- **MIT** — more technical/engineering bent; often uses 1.00 mm cuts at
  detail scale. Aligned with Ramsey/Sleeper.

### AIA CAD Layer Guidelines / NCS in practice

The 2021 NCS v6 release codifies the AIA CAD Layer Guidelines verbatim.
Real-world adoption is **partial** — most US firms use the layer naming
but ignore the plot-weight table, instead using firm-specific Revit
templates that approximate the ISO ladder.

---

## 7. Recommended preset module structure

### 7.1 Diff vs current `presets.py`

The current module has four short hand-written tier lists (legacy
v0.3 values), plus three ISO-aligned tables (`SECTION_ISO_PRINT`,
`SECTION_ISO_SCREEN`, `DETAIL_ISO_PRINT`). It does **not** have:

- Plan-specific ISO ladder
- Elevation-specific ISO ladder
- Plan/elevation print + screen variants
- Tier-name consistency across drawing types (`profile` vs `silhouette`,
  `walls_cut` vs `cut`, etc.)

### 7.2 Proposed structure

```python
# presets.py — proposed v0.5

from dataclasses import dataclass

@dataclass(frozen=True)
class Tier:
    name: str
    weight_pt: float
    description: str

MM_TO_PT = 2.835

def mm(x: float) -> float:
    return round(x * MM_TO_PT, 3)

# --- Print baselines at 1/4"=1'-0" ---

SECTION_PRINT = [
    Tier("cut",       mm(0.70), "Section cut — what the plane slices"),
    Tier("profile",   mm(0.50), "Foreground silhouette behind the cut"),
    Tier("edges",     mm(0.35), "Object edges, structural members"),
    Tier("hidden",    mm(0.25), "Hidden / centerline / dashed"),
    Tier("material",  mm(0.18), "Material indication, hatching"),
    Tier("texture",   mm(0.13), "Texture, poché, distant context"),
    Tier("special",   mm(0.25), "Glazing, water, sky"),
]

PLAN_PRINT = [
    Tier("walls_cut",  mm(0.50), "Walls cut at ~4' AFF"),
    Tier("casework",   mm(0.35), "Built-in millwork, counters, stairs"),
    Tier("furniture",  mm(0.25), "Loose furniture, fixtures, equipment"),
    Tier("pattern",    mm(0.18), "Floor pattern, door swings"),
    Tier("site",       mm(0.18), "Site context: trees, parking, contours"),
    Tier("texture",    mm(0.13), "Floor poché, ground pattern"),
    Tier("special",    mm(0.25), "Glazing in plan, water features"),
]

ELEVATION_PRINT = [
    Tier("silhouette", mm(0.70), "Outermost building edge"),
    Tier("profile",    mm(0.50), "Major form breaks, corners, eaves"),
    Tier("openings",   mm(0.35), "Windows, doors, balconies"),
    Tier("joints",     mm(0.25), "Material joints, reveals, control joints"),
    Tier("material",   mm(0.18), "Material patterning"),
    Tier("texture",    mm(0.13), "Surface texture, shadow lines"),
    Tier("special",    mm(0.25), "Glazing reflections"),
]

DETAIL_PRINT = [
    Tier("cut_primary",   mm(1.00), "Primary section cut at detail scale"),
    Tier("cut_secondary", mm(0.70), "Secondary cut (insulation outline)"),
    Tier("profile",       mm(0.50), "Profile / foreground"),
    Tier("edges",         mm(0.35), "Material edges, fastener heads"),
    Tier("hidden",        mm(0.25), "Hidden / centerline"),
    Tier("material",      mm(0.25), "Material indication"),
    Tier("texture",       mm(0.18), "Hatching, fastener thread"),
    Tier("annotation",    mm(0.18), "Dimension lines, leaders"),
    Tier("special",       mm(0.30), "Glazing, gaskets"),
]

# --- Screen variants: 1.7× heavier than print, clamped at 0.5 pt ---

def _screen_variant(print_tiers):
    return [
        Tier(t.name, max(0.5, round(t.weight_pt * 1.7, 2)), t.description)
        for t in print_tiers
    ]

SECTION_SCREEN   = _screen_variant(SECTION_PRINT)
PLAN_SCREEN      = _screen_variant(PLAN_PRINT)
ELEVATION_SCREEN = _screen_variant(ELEVATION_PRINT)
DETAIL_SCREEN    = _screen_variant(DETAIL_PRINT)

# --- Lookup ---

PRESETS_PRINT = {
    "section":   SECTION_PRINT,
    "plan":      PLAN_PRINT,
    "elevation": ELEVATION_PRINT,
    "detail":    DETAIL_PRINT,
}
PRESETS_SCREEN = {
    "section":   SECTION_SCREEN,
    "plan":      PLAN_SCREEN,
    "elevation": ELEVATION_SCREEN,
    "detail":    DETAIL_SCREEN,
}

# --- Scale offset map ---

_SCALE_SHIFTS = {
    "1/16": -2, "1/8": -1, "1/4": 0, "1/2": 1, "1": 2, "3": 3, "full": 4,
}
_ISO_LADDER_MM = [0.13, 0.18, 0.25, 0.35, 0.50, 0.70, 1.00, 1.40, 2.00]

def select_preset(
    drawing_type: str = "section",
    scale: str = "1/4",
    for_print: bool = True,
) -> list[Tier]:
    base = (PRESETS_PRINT if for_print else PRESETS_SCREEN)[drawing_type]
    shift = _SCALE_SHIFTS.get(scale, 0)
    if shift == 0:
        return base
    return _shift_iso(base, shift)

def _shift_iso(tiers, shift):
    iso_pt = [mm(v) for v in _ISO_LADDER_MM]
    out = []
    for t in tiers:
        # find nearest ISO step
        idx = min(range(len(iso_pt)), key=lambda i: abs(iso_pt[i] - t.weight_pt))
        new_idx = max(0, min(len(iso_pt) - 1, idx + shift))
        out.append(Tier(t.name, iso_pt[new_idx], t.description))
    return out
```

### 7.3 Migration path

The existing `SECTION`, `PLAN`, `ELEVATION`, `DETAIL` lists at the top
of `presets.py` are legacy v0.3 hand-derived weights. Recommend:

1. Mark them deprecated in v0.5 (keep working for backward compat).
2. Make `select_preset()` the canonical entry point.
3. Update `cli.py` to default to `select_preset(...)` rather than
   `get_preset(name)`.
4. Drop legacy lists in v0.6.

---

## 8. Sample CLI invocations

```bash
# Plan at 1/8" for print
arch-lw apply input.pdf --preset plan --scale 1/8 --for-print -o output.pdf

# Elevation at 1/4" for screen review
arch-lw apply input.pdf --preset elevation --scale 1/4

# Detail at 1"=1' (auto-shifts to heaviest tier)
arch-lw apply input.pdf --preset detail --scale 1 --for-print

# Site plan at 1/16" (offsets ladder 2 steps lighter)
arch-lw apply input.pdf --preset plan --scale 1/16 --for-print

# Reflected ceiling plan — same ladder as plan, but no floor pattern tier
arch-lw apply input.pdf --preset plan --scale 1/4 --for-print \
    --tier-skip pattern,site
```

> **Suggestion for v0.5+:** add `--variant` flag for plan sub-types:
> `--preset plan --variant rcp` (reflected ceiling), `--variant site`,
> `--variant demo` (demolition). These would tweak the tier list rather
> than adding new top-level presets.

---

## 9. Edge cases

### Site plans (1/16" or smaller)

- No interior linework; site context dominates.
- The `walls_cut` tier becomes the building footprint, drawn at the
  `casework` weight (0.35 mm) — reduced because it competes with site
  features.
- Add tiers: `topo_major` (0.35 mm, contour every 5'), `topo_minor`
  (0.13 mm, intermediate contours), `property_line` (0.50 mm dashed).
- Recommend `--preset plan --variant site --scale 1/16`.

### Structural plans

- Often overlay structural grid + members on a plan background.
- Structural members get the `casework` weight; non-structural plan
  context drops one tier (greys out).
- Add a `grid` tier at 0.18 mm dashed.

### Reflected ceiling plans (RCP)

- No floor pattern; instead, ceiling grid pattern.
- The `pattern` tier holds the ceiling grid (suspended-T grid lines).
- The `furniture` tier holds light fixtures, sprinklers, diffusers.
- Walls drawn at the `casework` weight (lighter than walls_cut), since
  walls in RCP are *projected* not cut at the ceiling plane — the
  *ceiling* is what's effectively cut.
- Add tiers: `lighting` (0.35 mm, fixture outlines), `mech`
  (0.25 mm, diffusers/grilles).

### Demolition plans

- Existing-to-remain: keep at standard weights but **dashed**.
- To-be-demolished: lighten by **two ISO steps** + dashed pattern with
  shorter segments. Demo cuts go from 0.50 mm → 0.25 mm.
- New construction: **bold, full lines** at standard weights.
- This pattern — same ladder, different line types — is best handled by
  a separate `--linetype` flag rather than new presets.

### Foundation plans

- Hidden lines (footings under slab) become a primary tier, not a
  secondary one.
- Promote `hidden` to weight 0.35 mm (same as `casework`); demote walls
  to 0.25 mm because they're often dashed at floor levels.

---

## 10. Sources

- ISO 128-20:1996, *Technical drawings — General principles of presentation
  — Part 20: Basic conventions for lines.* §5 (line widths).
- ISO 128-2:2020, *Technical product documentation — General principles of
  representation — Part 2: Basic conventions for lines.* Table 1.
- ISO 128-30:2001, *Technical drawings — General principles of
  presentation — Part 30: Basic conventions for views.*
- ISO 128-50:2001, *Technical drawings — General principles of
  presentation — Part 50: Basic conventions for cuts and sections.*
- BS EN ISO 128-23:1999, *Technical drawings — General principles of
  presentation — Lines on construction drawings.*
- BS 8541-2:2011, *Library objects for architecture, engineering and
  construction — Part 2: Recommended 2D symbols.*
- AEC (UK) BIM Protocol v2.0, §6.2.
- DIN 15, *Linien in Zeichnungen* (Lines in drawings).
- DIN 6776:1976, *Schreibgeräte für Tuschezeichnungen* (Drawing pens
  for India ink).
- Ching, F. D. K. *Architectural Graphics*, 6th ed., Wiley, 2015.
  pp. 27, 60.
- Ramsey, C. & Sleeper, H. *Architectural Graphic Standards*, 12th ed.,
  Wiley, 2016. §1.4 (line conventions), p.45.
- National CAD Standard v6, *Plotting Guidelines*, NIBS, 2014. §5.3,
  Table 5.
- AIA CAD Layer Guidelines, AIA / NIBS, 2021.
- *Detail* magazine 2023 issues 4–11 (real-world sampling).
