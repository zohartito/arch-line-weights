# Layer-name patterns: extending the classifier beyond Rhino/Make2D

> Sub-agent research, 2026-04-30. Phase E5 of the roadmap. Doubles addressable
> market for `arch-line-weights` by teaching `layer_classify.py` to recognize
> layer-name conventions from non-Rhino vector sources.
>
> The existing classifier (`src/arch_line_weights/layer_classify.py`) only
> understands Rhino's Make2D + Clipping Plane convention:
>
>     <view>::Visible|Hidden::Curves|ClippingPlaneIntersections::<material>
>
> Anything else falls through to `DEFAULT = 0.25 pt`. This document specifies
> the additional pattern libraries needed to handle Inkscape, Vectorworks,
> AutoCAD/DXF (AIA NCS), ArchiCAD, and Revit-via-AutoCAD layered PDFs.

---

## 1. Per-source pattern library

Each table below is the full set of patterns and the tier each should map to.
Patterns are written here in regex form for clarity; the implementation uses
substring matching (with optional regex fallback) for ExtendScript
portability — see Section 4.

### 1.1 AutoCAD / DXF — AIA CAD Layer Guidelines (NCS / ISO 13567-2)

The AIA *CAD Layer Guidelines* (incorporated into the U.S. National CAD
Standard, NCS) is the canonical 4-field layer name:

    <discipline>-<MAJOR>-<MINOR1>-[MINOR2]-[STATUS]
    e.g. A-WALL-FULL-N      A-GLAZ-SILL      S-COLS-FULL

Per the [NCS layer name format spec](https://www.nationalcadstandard.org/ncs5/pdfs/ncs5_clg_lnf.pdf),
discipline is one of `A` (architectural), `S` (structural), `C` (civil),
`M` (mechanical), `E` (electrical), `P` (plumbing), `T` (telecom), `X` (other).
Major Group is a 4-char abbreviation; Minor Groups are optional 4-char
sub-codes.

| Tier | Pattern (uppercase, hyphen-anchored) | Examples | Notes |
|---|---|---|---|
| `cut` (1.0) | `S-COLS`, `S-FNDN`, `A-WALL-FULL`, `A-WALL-CONC`, `A-FLOR-DECK`, `A-ROOF-OTLN` | `A-WALL-FULL-N`, `S-COLS-PIER` | Section-cut profile in NCS = full-height structural walls + columns + slab edges. NCS doesn't have an explicit "cut" tier; we infer from FULL + structural disciplines. |
| `glazing` (0.25) | `A-GLAZ`, `A-WALL-GLAZ`, `A-GLAZ-SILL`, `A-GLAZ-IDEN` | `A-GLAZ`, `A-GLAZ-FULL` | Per [Seidler](https://seidlerstudio.com/lesson/autocad-standard-layer-names-floor-plans/), `GLAZ-Full` = full-height glazed wall. |
| `frames` (0.3) | `A-WALL-JAMB`, `A-WALL-HEAD`, `A-DOOR-FRAM`, `A-WALL-SILL` | `A-WALL-JAMB` | Door + window jambs/heads — per AIA `JAMB`/`HEAD` minor group. |
| `structure_primary` (0.5) | `S-BEAM`, `S-JOIS`, `S-DECK`, `A-ROOF-STRC`, `A-CLNG-STRC` | `S-BEAM-MAIN`, `S-JOIS` | Structural beams + joists + roof structure. |
| `edges_secondary` (0.3) | `A-DOOR`, `A-DOOR-IDEN`, `A-FLOR`, `A-FLOR-OTLN`, `A-FLOR-STRS`, `A-EQPM`, `A-FURN` | `A-DOOR`, `A-FLOR-STRS` | Door leaves, stairs, equipment outlines, furniture. |
| `cladding` (0.18) | `A-WALL-PATT`, `A-FLOR-PATT`, `A-ROOF-PATT`, `A-CLNG-PATT` | `A-WALL-PATT` | NCS minor group `PATT` = wall insulation/hatching/fill — material-pattern hatch. |
| `material_minor` (0.13) | `A-WALL-INSL`, `A-ROOF-INSL`, `A-WALL-MEMB` | `A-WALL-INSL` | Insulation hatches. |
| `reference` (0.13) | `S-GRID`, `A-GRID`, `A-DETL-REFR`, `A-ANNO-REFR` | `S-GRID` | Construction grid + datum reference. |
| `annotation` (0.13) | `*-ANNO`, `*-ANNO-DIMS`, `*-ANNO-TEXT`, `*-ANNO-NOTE`, `*-ANNO-IDEN`, `*-ANNO-TTLB` | `A-ANNO-DIMS`, `A-DOOR-IDEN` | All `ANNO` major group + `IDEN` minor group (door tags, window tags). |
| `default` (0.25) | (anything starting with a discipline designator that didn't match above) | `A-ANNO-SYMB` | Falls back to default. |

Sources:
- [NCS v5 Layer Name Format](https://www.nationalcadstandard.org/ncs5/pdfs/ncs5_clg_lnf.pdf)
- [AIA CAD Layer Guidelines (Duke Facilities mirror)](https://facilities.duke.edu/sites/default/files/AIA%20CAD%20Layer%20Guidelines.pdf)
- [Seidler Studio — Floor Plans](https://seidlerstudio.com/lesson/autocad-standard-layer-names-floor-plans/)
- [Novedge — AutoCAD Layer Naming](https://novedge.com/blogs/design-news/autocad-tip-autocad-layer-naming-convention)

### 1.2 ArchiCAD

[ArchiCAD international templates](https://community.graphisoft.com/t5/Project-data-BIM/ARCHICAD-23-LAYER-NAMING-CONVENTIONS-USA-Template/td-p/259137)
have evolved from descriptive (`Walls Exterior`) to NCS-aligned (`A-Wall-Exterior`).
Two flavors coexist:

| Tier | Pattern (case-insensitive) | Examples | Notes |
|---|---|---|---|
| `cut` (1.0) | `A-Wall`, `Walls`, `Wall-Ext`, `Wall-Int`, `Slab`, `Floor-Slab`, `Slabs`, `Foundation`, `S-Slab`, `S-Foundation` | `A-Wall-Ext`, `Walls Exterior`, `Slab` | ArchiCAD's `Wall`/`Slab` tools auto-create these layers. Both NCS-style and legacy descriptive names. |
| `glazing` (0.25) | `Window`, `A-Glaz`, `Curtain-Wall`, `Curtain Wall`, `Glazing` | `Curtain-Wall` | Per [Graphisoft Pen Set docs](https://helpcenter.graphisoft.com/user-guide/76266/), the "Architectural" pen set has a dedicated "Openings" group. |
| `frames` (0.3) | `Door`, `A-Door`, `Window-Frame`, `Door-Frame` | `A-Door` | |
| `structure_primary` (0.5) | `S-Beam`, `Beams`, `S-Column`, `Columns`, `Roof`, `A-Roof` | `Beams`, `Roof` | ArchiCAD's `Beam`/`Column`/`Roof` tools. |
| `edges_secondary` (0.3) | `Stair`, `A-Strs`, `Furniture`, `Object`, `A-Furn`, `Equipment` | `Furniture`, `Stair` | ArchiCAD `Object`/`Stair` tools. |
| `cladding` (0.18) | `Zone`, `Mesh`, `Hatch`, `Cover-Fill`, `Cladding`, `Skin` | `Cladding` | |
| `material_minor` (0.13) | `Fill`, `Mesh-Fill`, `Insulation` | `Insulation` | |
| `annotation` (0.13) | `Dimension`, `Text`, `Label`, `A-Anno`, `Marker`, `Section-Marker`, `Drawing-Title` | `Dimension` | ArchiCAD's `Marker`/`Dimension` tools. |

Pen-set hint: ArchiCAD assigns specific pen indexes to element functions (e.g.
slab cut line = pen 29). When DXF/DWG export uses the
`<ArchiCADLayer>_<Prefix>Pen No.<Postfix>` pattern, layer names embed pen
numbers — we can extract `_Pen29` etc. as a strong "cut" signal even for
non-NCS layer names.

### 1.3 Vectorworks

Vectorworks separates **design layers** (Z-stacked, like floors) from
**classes** (object kind, NCS-style, semantic). Per
[Vectorworks help](https://app-help.vectorworks.net/2026/eng/VW2026_Guide/Structure/Creating_classes.htm),
classes follow `Discipline-Object-Modifier-Modifier`, e.g. `Arch-Wall-Ext`,
`Elec-Lite-Ceiling`. PDF export emits class names as OCG layers; design layer
names sometimes prefix.

| Tier | Pattern | Examples | Notes |
|---|---|---|---|
| `cut` (1.0) | `Arch-Wall`, `Wall-Ext`, `Wall-Int`, `Wall-Comp`, `Style-Wall`, `Slab-Style`, `Arch-Floor-Main`, `Arch-Roof-Main` | `Arch-Wall-Ext`, `Style-Wall-Wood Stud-GWB Each Side` | Vectorworks `Wall Style` classes + auto-classed components. |
| `glazing` (0.25) | `Glaz`, `Window-Glass`, `Curtain Wall-Glazing`, `Style-Glaz` | `Window-Glass` | |
| `frames` (0.3) | `Window`, `Door`, `Window-Frame`, `Style-Window`, `Style-Door` | `Style-Window-Frame` | |
| `structure_primary` (0.5) | `Struct-Beam`, `Struct-Column`, `Struct-Joist`, `S-Cols`, `Arch-Roof-Main` | `Struct-Beam-Steel` | |
| `edges_secondary` (0.3) | `Arch-Stair`, `Furn`, `Equip`, `Arch-Door` | `Arch-Stair-Run` | |
| `cladding` (0.18) | `Hatch`, `Component-Wall`, `Wall-Component`, `Style-Wall-Cladding`, `Skin` | `Style-Wall-Cladding` | |
| `material_minor` (0.13) | `Insulation`, `Wall-Component-Insul` | | |
| `reference` (0.13) | `Grid-Line`, `Site-Datum`, `Building-Line`, `Centerline` | `Grid-Line` | Vectorworks `Grid` tool. |
| `annotation` (0.13) | `Dim`, `Text`, `Notes`, `Tag`, `Annotation`, `Marker`, `Title-Block` | `Annotation-Dim` | |

Sources:
- [Vectorworks Classes (2026)](https://app-help.vectorworks.net/2026/eng/VW2026_Guide/Structure/Creating_classes.htm)
- [Vectorworks Layer/Class/Viewport Standards](https://app-help.vectorworks.net/2026/eng/VW2026_Guide/Structure/Layer_class_and_viewport_standards.htm)
- [Vectorworks Auto-Created Classes](https://app-help.vectorworks.net/2016/eng/VW2016_Guide/Structure/Automatically_Created_Classes.htm)

### 1.4 Revit (via DWG → PDF)

Per [Engipedia](https://www.engipedia.com/how-to-create-pdf-with-layers-from-revit/),
**Revit's native PDF export does not produce layered PDFs**. The only path to
OCG layers is:

    Revit view → Export DWG → AutoCAD plot to PDF (with "Include layer info")

So Revit-origin PDFs use AutoCAD layer names, which by default are derived
from Revit **categories** (not subcategories) via the export Layer Key:

| Tier | Pattern | Source | Notes |
|---|---|---|---|
| `cut` (1.0) | `Walls`, `A-WALL`, `Floors`, `A-FLOR`, `Roofs`, `A-ROOF`, `Structural Columns`, `S-COLS`, `Structural Foundations`, `S-FNDN`, `Structural Framing`, `S-BEAM` | Revit category names (English locale) + AIA mapping | Revit's standard exportlayers.txt maps category → AIA pattern. |
| `glazing` (0.25) | `Curtain Panels`, `Curtain Wall Mullions`, `Windows`, `A-GLAZ` | | |
| `frames` (0.3) | `Doors`, `A-DOOR` | | |
| `edges_secondary` (0.3) | `Stairs`, `A-FLOR-STRS`, `Furniture`, `A-FURN`, `Casework`, `A-EQPM`, `Specialty Equipment`, `Generic Models` | | |
| `cladding` (0.18) | (subcategory `<Stuff>-Surface Pattern`, `_PATT`) | Revit subcategories — only present if the user splits them | |
| `annotation` (0.13) | `Dimensions`, `Text Notes`, `Title Blocks`, `Detail Items`, `Section Lines`, `Reference Planes`, `A-ANNO`, `Tags` | | |
| `reference` (0.13) | `Grids`, `Levels`, `Reference Planes`, `S-GRID` | | |

Caveat: Revit category names are **localized**. A French Revit will export
`Murs` not `Walls`, German `Wände`, etc. The pattern library should include
the top-3 locales (EN, DE, ES) at minimum.

Source: [Revit PDF export limitations (Engipedia)](https://www.engipedia.com/how-to-create-pdf-with-layers-from-revit/),
[Modelical Revit PDF Export](https://www.modelical.com/en/gdocs/export-to-pdf/)

### 1.5 Inkscape

Per [Inkscape DocumentLayers wiki](https://wiki.inkscape.org/wiki/DocumentLayers)
and [SVG layer convention discussion](https://bylr.info/articles/2023/03/17/layer-names/),
Inkscape stores layer names in `inkscape:label` on `<g inkscape:groupmode="layer">`.
**There is no architectural standard for Inkscape layer names** — users invent
their own conventions.

Empirically, plotter / pen-art / hand-drafting workflows use:

| Tier | Pattern | Examples | Notes |
|---|---|---|---|
| `cut` (1.0) | `cut`, `section`, `profile-heavy`, `0.7mm`, `1.0mm`, `pen-1`, `heavy` | `Layer 1 - Cut`, `0.7mm` | Many users name layers by **pen weight**, e.g. `0.7mm` directly. |
| `profile` (0.5) | `profile`, `outline`, `silhouette`, `0.5mm`, `pen-2`, `medium` | `0.5mm` | |
| `edges_secondary` (0.3) | `edges`, `details`, `0.35mm`, `0.3mm`, `pen-3`, `light` | `0.35mm` | |
| `cladding` (0.18) | `hatch`, `pattern`, `material`, `0.18mm`, `pen-4` | `0.18mm` | |
| `material_minor` (0.13) | `0.13mm`, `0.1mm`, `pen-5`, `fine`, `extrafine` | `0.13mm` | |
| `annotation` (0.13) | `text`, `dim`, `label`, `notes`, `annotation` | `text` | |

Strategy: Inkscape gets the **lowest source confidence**. Layer-name
inference only works ~30% of the time; fall back to color classifier.

### 1.6 DraftSight / BricsCAD / NanoCAD

These are AutoCAD-clone CAD apps. Their layer naming is **identical to
AutoCAD** (they're DWG-native and read AIA NCS templates verbatim). No
separate pattern library needed — reuse §1.1.

---

## 2. Source-detection heuristics

Order: cheapest signal first; first match wins.

### 2.1 PDF Producer / Creator metadata

PDF dictionary `/Producer` and `/Creator` strings, in priority order:

| Substring (case-insensitive) | Source | Confidence |
|---|---|---|
| `Rhino`, `Rhinoceros`, `McNeel`, `Make2D` | Rhino | 0.95 |
| `Adobe Illustrator`, `Illustrator CS` | Illustrator (post-process) | 0.50 — could be re-exported from anything |
| `Inkscape` | Inkscape | 0.90 |
| `Vectorworks`, `Nemetschek Vectorworks` | Vectorworks | 0.95 |
| `AutoCAD`, `DWG to PDF`, `Autodesk DWG` | AutoCAD/DXF (AIA NCS most likely) | 0.85 |
| `ArchiCAD`, `GRAPHISOFT`, `Archicad` | ArchiCAD | 0.95 |
| `Revit`, `Autodesk Revit` | Revit (native, unlayered) | 0.95 — but no OCG layers anyway |
| `BricsCAD`, `DraftSight`, `NanoCAD` | AutoCAD-clone (AIA NCS) | 0.85 |
| `pdfTeX`, `LibreOffice`, `Cairo` | unknown / generic | 0.10 |

`/Producer` reflects **last app to write the PDF**, not the origin. A Rhino
PDF re-saved through Illustrator will have `Producer=Adobe Illustrator`. So
also check `/Creator` (closer to origin) and look for app-specific `XMP`
metadata (`xmpMM:DerivedFrom`, `pdf:Producer` history).

### 2.2 Layer-name shape inference

If metadata is ambiguous, sniff the layer-name population:

| Heuristic | Implies | Confidence |
|---|---|---|
| ≥ 50% of layer names contain `::` | Rhino Make2D | 0.90 |
| ≥ 30% match `^[A-Z]-[A-Z]{4}-` regex (NCS shape) | AutoCAD / Revit-DWG / Vectorworks-NCS / ArchiCAD-NCS | 0.70 |
| ≥ 30% start with `Arch-`, `Struct-`, `Elec-` (case-sensitive) | Vectorworks (its native order is title-case) | 0.65 |
| Layer names contain `_PenNN` suffix | ArchiCAD with DXF pen-prefix translator | 0.85 |
| Layer names match `^\d+\.\d+mm$` or `pen-\d+` | Inkscape pen-art workflow | 0.80 |
| Layer names are short English-only words (`Walls`, `Doors`, `Floors`, `Roofs`) | Revit-via-DWG default Layer Key | 0.75 |
| All layers have `inkscape:label` SVG attribute (only valid for SVG inputs) | Inkscape | 1.00 |

If sources tie within 0.05 confidence, **defer to color classifier** rather
than guess.

### 2.3 Font-choice signal (low priority)

Fonts embedded in the PDF can hint at origin:

- `RhSS`, `Rhino Sans` → Rhino
- `RomanS`, `simplex.shx`, `Arial Narrow` → AutoCAD
- `CityBlueprint`, `CountryBlueprint` → AutoCAD shape fonts
- `Helvetica` only → Vectorworks default
- `Arial` + `ArialMT` → Revit default

This is too noisy to drive detection on its own; use only as a tiebreaker.

### 2.4 `--source` CLI override

Always-trust user. Add to `apply` and `apply-saas`:

```
--source [auto|rhino|autocad|vectorworks|archicad|revit|inkscape|color-only]
```

Default `auto`. `color-only` skips layer-name classifier entirely (current
behavior pre-Phase-E5). Each named source forces that pattern library and
skips detection.

---

## 3. Confidence scoring

Each tier assignment now carries a `confidence` ∈ [0, 1]. The classifier
returns the highest-confidence match across all enabled sources; if the top
two scores are within 0.10 of each other and below 0.6, fall back to color
classifier.

Per-source baseline confidence:

| Source | Baseline confidence (matched) | Reason |
|---|---|---|
| Rhino Make2D + Clipping Plane | 0.95 | Hierarchy is unambiguous, material codes are project-private (TEC_*, _CU_*). |
| AutoCAD/DXF AIA NCS | 0.85 | Convention is documented and stable; firm-specific deviations exist. |
| ArchiCAD | 0.70 | Two coexisting conventions (legacy + NCS); pen-set hint helps. |
| Vectorworks | 0.70 | Class names are user-edited heavily. |
| Revit-via-DWG | 0.65 | Localization + Revit Layer Key user overrides. |
| Inkscape | 0.45 | No standard at all. |
| (no match) | 0.0 | Fall through to color classifier. |

Per-pattern confidence multipliers:
- Multi-token match (e.g. `S-COLS-PIER` matches `S-COLS` AND `S-`) → ×1.0
- Prefix-only match (`S-` alone) → ×0.5
- Substring match in middle of name → ×0.7
- Match against most-specific pattern (longer string) → wins over shorter

---

## 4. Classifier extension diff (pseudo-code)

```python
# src/arch_line_weights/layer_classify.py

from dataclasses import dataclass
from enum import Enum

class Source(str, Enum):
    RHINO = "rhino"
    AUTOCAD = "autocad"      # AIA NCS / ISO 13567-2
    ARCHICAD = "archicad"
    VECTORWORKS = "vectorworks"
    REVIT = "revit"          # via DWG -> PDF
    INKSCAPE = "inkscape"
    COLOR_ONLY = "color-only"
    AUTO = "auto"

@dataclass(frozen=True)
class TierAssignment:
    weight_pt: float
    tier: str
    why: str
    source: Source = Source.RHINO
    confidence: float = 1.0   # NEW

# Move existing RULES into a per-source dispatcher:
RHINO_RULES = [...]              # current RULES list
AUTOCAD_RULES = [...]            # §1.1 table above, in regex form
ARCHICAD_RULES = [...]           # §1.2
VECTORWORKS_RULES = [...]        # §1.3
REVIT_RULES = [...]              # §1.4 (currently EN-only; locales TODO)
INKSCAPE_RULES = [...]           # §1.5

DISPATCH = {
    Source.RHINO: RHINO_RULES,
    Source.AUTOCAD: AUTOCAD_RULES,
    Source.ARCHICAD: ARCHICAD_RULES,
    Source.VECTORWORKS: VECTORWORKS_RULES,
    Source.REVIT: REVIT_RULES,
    Source.INKSCAPE: INKSCAPE_RULES,
}

SOURCE_BASELINE_CONFIDENCE = {
    Source.RHINO: 0.95,
    Source.AUTOCAD: 0.85,
    Source.ARCHICAD: 0.70,
    Source.VECTORWORKS: 0.70,
    Source.REVIT: 0.65,
    Source.INKSCAPE: 0.45,
}

def detect_source(pdf_metadata: dict, layer_names: list[str]) -> tuple[Source, float]:
    """Return (best-guess source, confidence). See §2."""
    # 1. Producer/Creator
    producer = (pdf_metadata.get("/Producer") or "").lower()
    creator  = (pdf_metadata.get("/Creator")  or "").lower()
    for needle, src, conf in [
        ("rhino", Source.RHINO, 0.95),
        ("inkscape", Source.INKSCAPE, 0.90),
        ("vectorworks", Source.VECTORWORKS, 0.95),
        ("archicad", Source.ARCHICAD, 0.95),
        ("graphisoft", Source.ARCHICAD, 0.95),
        ("autocad", Source.AUTOCAD, 0.85),
        ("dwg to pdf", Source.AUTOCAD, 0.85),
        ("bricscad", Source.AUTOCAD, 0.85),
        ("draftsight", Source.AUTOCAD, 0.85),
    ]:
        if needle in producer or needle in creator:
            return src, conf

    # 2. Layer-name shape (see §2.2)
    n = max(1, len(layer_names))
    rhino_hits = sum(1 for x in layer_names if "::" in x)
    if rhino_hits / n >= 0.5:
        return Source.RHINO, 0.90
    ncs_hits = sum(1 for x in layer_names if re.match(r"^[A-Z]-[A-Z]{4}-", x))
    if ncs_hits / n >= 0.3:
        return Source.AUTOCAD, 0.70
    vw_hits = sum(1 for x in layer_names if re.match(r"^(Arch|Struct|Elec|Plumb)-", x))
    if vw_hits / n >= 0.3:
        return Source.VECTORWORKS, 0.65
    pen_hits = sum(1 for x in layer_names if re.search(r"_Pen\d+", x))
    if pen_hits / n >= 0.2:
        return Source.ARCHICAD, 0.85
    inkscape_hits = sum(1 for x in layer_names if re.match(r"^\d+(\.\d+)?mm$", x))
    if inkscape_hits / n >= 0.3:
        return Source.INKSCAPE, 0.80

    return Source.AUTO, 0.0  # caller will fall back to color classifier

def classify_layer(name: str, source: Source = Source.RHINO) -> TierAssignment:
    rules = DISPATCH[source]
    upper = name.upper()
    for patterns, assignment in rules:
        if isinstance(patterns, str):
            if patterns in upper:
                return assignment
        else:
            for p in patterns:
                if p in upper:
                    return assignment
    return DEFAULT_FOR(source)
```

CLI side:

```python
# src/arch_line_weights/cli.py — add to apply + apply-saas:
@click.option(
    "--source",
    type=click.Choice([s.value for s in Source]),
    default="auto",
    show_default=True,
    help="Force a layer-name convention (auto detects from PDF metadata + layer-name shape).",
)
```

`apply.py` flow:
1. `report = inspect_file(...)` (already collects layer names)
2. `source, conf = detect_source(report.pdf_metadata, report.layer_names)` if `--source auto`
3. If `conf < 0.6` and source is `AUTO`: warn and fall back to color classifier
4. Otherwise: `mapping = {layer: classify_layer(layer, source).weight_pt for layer in report.layer_names}`

JSX export: `as_jsx_function()` needs a `source` arg too. For now, ship a
single combined JSX that pattern-matches all sources — Illustrator users
typically don't know the origin and the combined JSX is only ~200 lines.

---

## 5. Test cases (synthetic layer names per source)

### 5.1 AutoCAD / DXF / Revit-DWG

| Layer name | Expected tier | Notes |
|---|---|---|
| `A-WALL-FULL` | `cut` (1.0) | NCS structural full-height wall |
| `A-WALL-PATT` | `cladding` (0.18) | NCS pattern hatch |
| `A-WALL-JAMB` | `frames` (0.3) | NCS door/window jamb |
| `A-WALL-INSL` | `material_minor` (0.13) | NCS insulation |
| `A-DOOR` | `edges_secondary` (0.3) | bare A-DOOR |
| `A-DOOR-IDEN` | `annotation` (0.13) | door tag |
| `A-GLAZ-FULL` | `glazing` (0.25) | curtain wall |
| `A-GLAZ-SILL` | `glazing` (0.25) | sill — still glass tier |
| `A-FLOR-OTLN` | `edges_secondary` (0.3) | floor outline |
| `A-FLOR-STRS` | `edges_secondary` (0.3) | stairs |
| `A-ROOF-PATT` | `cladding` (0.18) | roof pattern |
| `A-ANNO-DIMS` | `annotation` (0.13) | dimensions |
| `A-ANNO-TTLB` | `annotation` (0.13) | title block |
| `S-COLS` | `cut` (1.0) | structural columns (cut in plan) |
| `S-BEAM-MAIN` | `structure_primary` (0.5) | beam |
| `S-GRID` | `reference` (0.13) | grid line |
| `M-DUCT` | `default` (0.25) | not in arch tier — defaults |

### 5.2 ArchiCAD

| Layer name | Expected tier | Notes |
|---|---|---|
| `A-Wall-Ext` | `cut` (1.0) | NCS-style |
| `Walls Exterior` | `cut` (1.0) | Legacy descriptive |
| `Slab` | `cut` (1.0) | |
| `Foundation` | `cut` (1.0) | |
| `Curtain-Wall` | `glazing` (0.25) | |
| `Door` | `frames` (0.3) | |
| `Beams` | `structure_primary` (0.5) | |
| `Roof` | `structure_primary` (0.5) | |
| `Stair` | `edges_secondary` (0.3) | |
| `Cladding` | `cladding` (0.18) | |
| `Insulation` | `material_minor` (0.13) | |
| `Marker` | `annotation` (0.13) | |
| `WALL_Pen29` | `cut` (1.0) | pen-29 = slab cut, hint match |

### 5.3 Vectorworks

| Layer name | Expected tier | Notes |
|---|---|---|
| `Arch-Wall-Ext` | `cut` (1.0) | NCS-style class |
| `Style-Wall-Wood Stud-GWB Each Side` | `cut` (1.0) | auto-generated wall-style class |
| `Window-Glass` | `glazing` (0.25) | |
| `Style-Window-Frame` | `frames` (0.3) | |
| `Struct-Beam-Steel` | `structure_primary` (0.5) | |
| `Arch-Stair-Run` | `edges_secondary` (0.3) | |
| `Style-Wall-Cladding` | `cladding` (0.18) | |
| `Grid-Line` | `reference` (0.13) | |
| `Annotation-Dim` | `annotation` (0.13) | |

### 5.4 Revit (via DWG)

| Layer name | Expected tier | Notes |
|---|---|---|
| `Walls` | `cut` (1.0) | |
| `Floors` | `cut` (1.0) | |
| `Roofs` | `cut` (1.0) | |
| `Structural Columns` | `cut` (1.0) | |
| `Structural Foundations` | `cut` (1.0) | |
| `Structural Framing` | `structure_primary` (0.5) | |
| `Curtain Panels` | `glazing` (0.25) | |
| `Curtain Wall Mullions` | `frames` (0.3) | |
| `Doors` | `frames` (0.3) | |
| `Windows` | `glazing` (0.25) | |
| `Stairs` | `edges_secondary` (0.3) | |
| `Furniture` | `edges_secondary` (0.3) | |
| `Generic Models` | `edges_secondary` (0.3) | catch-all |
| `Grids` | `reference` (0.13) | |
| `Levels` | `reference` (0.13) | |
| `Reference Planes` | `reference` (0.13) | |
| `Dimensions` | `annotation` (0.13) | |
| `Title Blocks` | `annotation` (0.13) | |
| `Murs` | `cut` (1.0) | French — locale TODO |
| `Wände` | `cut` (1.0) | German — locale TODO |

### 5.5 Inkscape

| Layer name | Expected tier | Notes |
|---|---|---|
| `0.7mm` | `cut` (1.0) | direct mm → tier mapping |
| `0.5mm` | `profile` (0.5) | |
| `0.35mm` | `edges_secondary` (0.3) | |
| `0.18mm` | `cladding` (0.18) | |
| `0.13mm` | `material_minor` (0.13) | |
| `Layer 1 - Cut` | `cut` (1.0) | |
| `Hatch` | `cladding` (0.18) | |
| `text` | `annotation` (0.13) | |
| `Layer 1` | `default` (0.25) | bare numeric layer |
| `My Stuff` | `default` (0.25) | unknown user name |

### 5.6 Detection regression tests

| Input | Expected `(source, conf)` |
|---|---|
| Producer=`Rhinoceros 8`, layers all `::`-joined | (`rhino`, 0.95) |
| Producer=`AutoCAD 2025 (DWG to PDF)`, layers `A-WALL-FULL`, `A-DOOR`, ... | (`autocad`, 0.85) |
| Producer=`Adobe Illustrator 2024`, layers all `::`-joined | (`rhino`, 0.90) — metadata ambiguous, layer shape wins |
| Producer=`Inkscape 1.3`, layers `0.5mm`, `0.35mm`, ... | (`inkscape`, 0.90) |
| Producer=`Cairo`, layers `Walls`, `Doors`, `Floors` | (`revit`, 0.75) — shape inference |
| Producer=`Cairo`, layers `Layer 1`, `Layer 2` | (`auto`, 0.0) → fall back to color classifier |

---

## 6. Implementation plan (person-days)

| # | Task | Days |
|---|---|---|
| 1 | Add `Source` enum + `confidence` to `TierAssignment`; refactor `RULES` to `DISPATCH[source]`; reroute existing rules to `Source.RHINO`. | 0.5 |
| 2 | Encode AutoCAD/AIA NCS rules (§1.1) + tests in `tests/test_layer_classify_autocad.py` (~25 cases from §5.1). | 1.0 |
| 3 | Encode Revit-via-DWG rules (§1.4) + EN/DE/ES/FR locale aliases; tests (~20 cases). | 0.75 |
| 4 | Encode ArchiCAD rules (§1.2) including `_PenNN` suffix sniff; tests. | 0.5 |
| 5 | Encode Vectorworks rules (§1.3); tests. | 0.5 |
| 6 | Encode Inkscape rules (§1.5) including `\d+(\.\d+)?mm` extractor; tests. | 0.5 |
| 7 | Implement `detect_source(pdf_metadata, layer_names)` (§2.1, §2.2); detection regression tests (§5.6). | 0.75 |
| 8 | Wire `inspect_file` to expose `pdf_metadata` + `layer_names` to detector (touch `inspect.py`). | 0.5 |
| 9 | Add `--source` CLI option to `apply` + `apply-saas`. | 0.25 |
| 10 | Update `as_jsx_function()` to emit per-source dispatcher (single combined JSX, ~200 lines). | 0.5 |
| 11 | Confidence-based fallback: when detection conf < 0.6, log warning and use color classifier. | 0.25 |
| 12 | End-to-end tests with sample PDFs from each source (need to source a Revit-DWG-PDF + ArchiCAD PDF + Vectorworks PDF + Inkscape SVG-as-PDF). | 1.0 |
| 13 | Docs: extend `docs/research/standards.md` with this file as companion; add `--source` to README. | 0.25 |
| **Total** | | **7.25 days** |

Stretch (optional):
- Locale tables for Revit (FR/DE/ES/IT) — +0.5 day
- Pen-set extraction from ArchiCAD `_PenNN` suffix → cross-reference with NCS-aligned pen-table to recover tiers when layer names are otherwise meaningless — +1.0 day
- Firm-specific override file (`~/.arch-lw/firm-patterns.yml`) — +0.5 day

---

## 7. Failure-mode analysis

### 7.1 Wrong source detected

If we lock onto the wrong source library, every layer in the file gets
classified by patterns that don't apply. Likely outcomes:

| Wrong detection | Most-common failure |
|---|---|
| Rhino patterns applied to AutoCAD PDF | Most layers fall to `DEFAULT 0.25` because the `::` hierarchy is missing. **No catastrophic error**, just no signal — equivalent to color-only mode. |
| AutoCAD patterns applied to Rhino PDF | `::` text contains `_TEC_` etc. that may accidentally match `S-COLS` or `A-WALL` — but since those are hyphen-delimited NCS strings and Rhino layers have no hyphens, false-positive rate is low (<5%). |
| AutoCAD patterns applied to Vectorworks PDF | Vectorworks NCS-style `Arch-Wall-Ext` would match `A-WALL`-rooted patterns if we lowercase aggressively. **Acceptable**: Vectorworks NCS classes ARE close enough to AIA that the same weights apply. |
| Revit-EN patterns applied to Revit-FR PDF | All categories miss; falls to `DEFAULT`. Mitigation: ship locale tables. |
| Inkscape patterns applied to anything else | Inkscape patterns are very loose (`pen-1`, `0.5mm`); false-positive rate against AIA names is near-zero. Safe default-of-last-resort. |

### 7.2 Mitigations (in priority order)

1. **Always log the detected source + confidence to stderr**, so the user
   sees `# detected source: vectorworks (conf=0.70)` and can override.
2. **`--source` CLI override** documented in the failure message: "if this
   looks wrong, re-run with `--source autocad`".
3. **Fall-back to color classifier** when confidence < 0.6 — never apply a
   low-confidence pattern library and pretend it's right.
4. **Multi-source matching**: when source is `auto` and confidence is
   moderate (0.6 ≤ conf < 0.8), evaluate all source libraries and
   majority-vote per layer. Ship as a v0.5 stretch goal.
5. **Whitelist mode for high-stakes use**: `--source-strict` errors out if
   detection confidence < 0.8 instead of falling back. For users who want
   guaranteed-pattern behavior in CI.

### 7.3 What never breaks

The pre-Phase-E5 color classifier (`classify.py`) is unchanged. Worst case
under any failure scenario, the user gets the existing v0.3 output. Phase E5
is **strictly additive** — no existing pipeline is replaced.

---

## 8. Sources

Primary:
- [NCS v5 Layer Name Format](https://www.nationalcadstandard.org/ncs5/pdfs/ncs5_clg_lnf.pdf)
- [AIA CAD Layer Guidelines (Duke Facilities)](https://facilities.duke.edu/sites/default/files/AIA%20CAD%20Layer%20Guidelines.pdf)
- [NCS v6 CLG](https://www.nationalcadstandard.org/ncs6/pdfs/ncs6_clg_lnf.pdf)
- [BS EN ISO 13567-2:2017 (NBS index)](https://www.thenbs.com/PublicationIndex/documents/details?Pub=BSI&DocID=320665)
- [Vectorworks 2026 — Creating Classes](https://app-help.vectorworks.net/2026/eng/VW2026_Guide/Structure/Creating_classes.htm)
- [Vectorworks — Layer/Class/Viewport Standards](https://app-help.vectorworks.net/2026/eng/VW2026_Guide/Structure/Layer_class_and_viewport_standards.htm)
- [Vectorworks 2016 — Auto-Created Classes](https://app-help.vectorworks.net/2016/eng/VW2016_Guide/Structure/Automatically_Created_Classes.htm)
- [ArchiCAD Pen Sets (Graphisoft Help Center)](https://helpcenter.graphisoft.com/user-guide/76266/)
- [ArchiCAD Layer Theory Part 5 (Graphisoft)](https://www.graphisoft.com/us/archicad-layer-theory-part-5-attribute-names-and-the-tyranny-of-alphabetical-order)
- [ArchiCAD 23 Layer Naming Conventions (USA template thread)](https://community.graphisoft.com/t5/Project-data-BIM/ARCHICAD-23-LAYER-NAMING-CONVENTIONS-USA-Template/td-p/259137)
- [Revit PDF export — Engipedia](https://www.engipedia.com/how-to-create-pdf-with-layers-from-revit/)
- [Revit Export to PDF — Modelical](https://www.modelical.com/en/gdocs/export-to-pdf/)
- [Inkscape DocumentLayers wiki](https://wiki.inkscape.org/wiki/DocumentLayers)
- [vpype layer-name discussion (bylr.info)](https://bylr.info/articles/2023/03/17/layer-names/)

Secondary / examples:
- [Seidler Studio — AutoCAD Standard Layer Names: Floor Plans](https://seidlerstudio.com/lesson/autocad-standard-layer-names-floor-plans/)
- [Novedge — AutoCAD Layer Naming Convention](https://novedge.com/blogs/design-news/autocad-tip-autocad-layer-naming-convention)
- [BIMUK Layer Standard (BS 1192 summary)](https://bimuk.co.uk/standards/layer-standard/)
- [Designing Buildings — BS 1192](https://www.designingbuildings.co.uk/wiki/BS_1192)
- [Wikipedia — ISO 13567](https://en.wikipedia.org/wiki/ISO_13567)
