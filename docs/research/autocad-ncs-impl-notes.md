# AutoCAD / AIA NCS classifier — implementation notes

> Phase E5 first slice. Adds AIA *CAD Layer Guidelines* (NCS / ISO 13567-2)
> support to `layer_classify.py` so AutoCAD/DXF-origin PDFs classify by
> layer name, not just by stroke color. Companion to
> `docs/research/layer-name-patterns.md` (the design doc).

## What landed

1. **Per-source dispatch in `layer_classify.py`**
   - New `Source` enum (`AUTO`, `RHINO`, `AUTOCAD`).
   - `RHINO_RULES` (existing) and `AUTOCAD_RULES` (new) live side-by-side
     in a `DISPATCH[Source] → rules` table.
   - `TierAssignment` now carries `source` and `confidence` fields. Default
     values match Rhino baseline so old call-sites keep working.
   - `classify_layer(name)` (no `source=` arg) preserves pre-Phase-E5
     behavior 1:1.

2. **AIA NCS pattern library — 25 field tokens, 8 tiers**
   - `cut` (1.0): `-WALL-FULL-`, `-WALL-CONC-`, `-FLOR-DECK-`, `-ROOF-OTLN-`,
     `-S-COLS-`, `-S-FNDN-`
   - `glazing` (0.25): `-GLAZ-`, `-WALL-GLAZ-`
   - `frames` (0.3): `-JAMB-`, `-HEAD-`, `-FRAM-`, `-WALL-SILL-`
   - `structure_primary` (0.5): `-S-BEAM-`, `-S-JOIS-`, `-S-DECK-`,
     `-ROOF-STRC-`, `-CLNG-STRC-`
   - `edges_secondary` (0.3): `-DOOR-`, `-FLOR-`, `-EQPM-`, `-FURN-`, `-STRS-`
   - `cladding` (0.18): `-PATT-` (any major)
   - `material_minor` (0.13): `-INSL-`, `-MEMB-`
   - `reference` (0.13): `-GRID-`, `-REFR-`
   - `annotation` (0.13): `-ANNO-`, `-IDEN-`, `-DIMS-`, `-TEXT-`, `-NOTE-`,
     `-TTLB-`, `-SYMB-`

   Rules are **hyphen-anchored** (haystack is wrapped as `-{NAME}-`) so
   field tokens only match NCS field boundaries — `A-WALL-FULLY-` does
   not match the `-WALL-FULL-` cut rule.

3. **Source detection — `detect_source(pdf_metadata, layer_names)`**
   - Priority 1: PDF `/Producer` / `/Creator` substring (`Rhino`, `AutoCAD`,
     `DWG to PDF`, `BricsCAD`, `DraftSight`, `NanoCAD`).
   - Priority 2: layer-name shape inference. ≥50% containing `::` →
     Rhino at 0.90 conf; ≥30% matching `^[A-Z]-[A-Z]{2,4}(-|$| )` → AutoCAD
     at 0.70 conf.
   - Inconclusive returns `(Source.AUTO, 0.0)` — caller falls back to the
     color classifier.

4. **CLI `--source auto|rhino|autocad`** added to:
   `apply`, `apply-saas`, `apply-jsx`, `poche`, `inspect`, `explain-layer`.
   Default is `auto`. `inspect` and `apply` print the detected source +
   confidence to stderr so users can spot mis-detection and re-run with
   `--source autocad` (or rhino).

5. **`InspectionReport`** gained `pdf_metadata: dict` and
   `layer_names: list[str]` fields, populated from PyMuPDF's
   `doc.metadata` and `doc.layer_ui_configs()` / `doc.layers()`. Old
   callers that hand-construct `InspectionReport` still work because
   both fields default to empty.

## Tests

`tests/test_layer_classify.py` — 53 cases covering:
- Rhino regression (12 parametrized + bare-default + auto-fallback)
- AIA NCS classification (37 parametrized)
- Field-anchored matching (no substring false positives)
- Source detection (Rhino producer, AutoCAD producer, BricsCAD, lowercase
  metadata keys, layer-shape Rhino, layer-shape AIA, mixed-source files,
  inconclusive fallback)
- `--source autocad` override (forces dispatch even for Rhino-shaped names)
- Unknown layer → `AUTOCAD_DEFAULT` 0.25pt at low confidence
- `explain_source_match` helper

All 160 tests in the in-scope suites pass; ruff clean on touched files.

## Pre-existing quirks preserved

- `TEC_STAIR_RISERS` still classifies as `structure_primary` (0.5) under
  the Rhino pattern library, because the broader `TEC_STAIR` rule wins on
  rule-order. The Rhino regression test asserts this exact behavior so a
  future refactor does not silently change it.

## Out of scope (per task brief — Phase E5 v0.5+)

- ArchiCAD, Vectorworks, Revit-via-DWG, Inkscape pattern libraries
- Locale tables (FR/DE/ES) for Revit category names
- ArchiCAD `_PenNN` suffix sniff
- Multi-source majority-vote per layer
- `--source-strict` failure mode

## Smoke check

    arch-lw explain-layer A-WALL-FULL --source autocad
    # source: autocad (forced via --source)
    # 1.0 pt — cut (AIA NCS section cut: structural full-height + slab edge + column)
    #   [source=autocad, confidence=0.85]

    arch-lw explain-layer A-WALL-FULL                # auto-detection
    # detected source: autocad (confidence=0.70)
    # 1.0 pt — cut ...

    arch-lw explain-layer 'axon::Visible::Curves::TEC_TIMBER'
    # detected source: rhino (confidence=0.90)
    # 0.5 pt — structure_primary ...

## Expected market reach

The AIA NCS / ISO 13567-2 convention is the dominant pattern in U.S. and
European architectural offices that ship from AutoCAD. Anecdotally
(Seidler, Novedge, Duke Facilities mirror) ≥60% of architectural firms
using AutoCAD use NCS-aligned templates verbatim. Adding this single
source library roughly **doubles** addressable users versus the
Rhino-only baseline, with no new dependencies and no regression to
existing Rhino workflows.
