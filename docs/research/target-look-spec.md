# The Target Look — Studio Corpus Spec + Translation Recipe

*Synthesis of a reference corpus of ~400 student drawings from an accredited M.Arch program (405 PDFs across 8 studios), plus the defect analysis of the current real-drawing run. Purpose: define what "good" looks like across the whole corpus, name the real stylistic forks so they become presets rather than a single dogma, give the exact `arch-lw` recipe that hits the look today, and hand issue #83 the concrete engine gaps.*

---

## 1. The Target Look

Eight studios, four different house styles, but the strong boards converge on one grammar. Where a board is weak it is almost always because it broke one of these rules; where it is strong it obeyed all of them.

### 1.1 Value is the medium — neutral ground, weight does the talking
Every top-ranked drawing that reads at a glance sits on **white or near-white paper** and lets a weight/value ramp carry the read. The colored-field and negative boards can be beautiful but consistently lose figure-ground (see §1.7 and every studio's anti-patterns). The cleanest statement of this is the Studio A conclusion: *a neutral ground plus a genuine 3:2:1 weight step (cut : profile : texture) separates the strong boards from the weak far more than color or rendering does.*

### 1.2 The weight ramp — cut > profile/structure > texture > annotation
A consistent 3–4 tier ladder governs the best sheets. Measured ratios from the corpus:

| Tier | What it is | Weight |
|---|---|---|
| 1 — heaviest | Section-cut profile + cut-mass poché; the continuous ground datum | 1.0 pt |
| 2 — medium | Elevational/"beyond" edges, structural members, stairs, furniture-in-plan | ~0.5 pt |
| 3 — hairline | All surface texture (floor grids, coursing, tile joints, soil stipple), keynote leaders, dashed setback/hidden lines | ~0.25 pt |
| 4 — lightest | Dimension strings, extension lines, level datums (often tinted so they never read as building line) | thinnest |

Observed ratios: **2.5–3×** from surface coursing up to the cut line in wall sections (Studio B, Ref B-1), rising to **5–10×** when black is spent only on a sectional-axo cut (Studio C, Ref C-1), and a dramatic **6–8×** when a single system is isolated in solid black (Studio B, Ref B-2).

### 1.3 The cut owns the darkest value — and nothing else may reach it
The single most repeated rule in the corpus. Black (or the most-saturated fill) is **reserved for what the section plane slices**; everything not cut steps down hard. Structure-seen-but-not-cut drops to grey/thin line; organizing geometry stays one hairline; subordinate info goes dashed. The reference set states the ladder most cleanly: **black = cut, grey = solid-but-uncut, hairline = organizing line, dashed = subordinate, tone = material** — figure-ground reads before a single label is examined.

Anchor exemplars, one per drawing type:

- **Section (the aspiration target):** Studio B, Ref B-3 — cut glulam solid ochre with wood-grain through it, cut CLT same, earth dot-stipple under one heavy grade line; everything beyond the cut recedes to thin grey wood-grain. Section depth from **value**, no cast shadow.
- **Cut-vs-beyond-vs-texture, cleanest 4-tier:** Studio D, Ref D-1 — reserved-black cut profile + solid-salmon cut structure/foundation, thin black diagrid "beyond," soil stipple as demoted texture, chartreuse figures as pure outline.
- **Plan hierarchy with restraint:** Studio A, Ref A-1 — perimeter footprint heaviest, interior cut walls a clear step lighter, furniture quiet, cut legible with **zero solid black** (outline-poché + faint stud hatch inside wall thickness).
- **Plan poché / figure-ground textbook:** the reference set — a published reference plan (I.M. Pei, Suzhou Museum), p56, and Schodek, *Structures*, p500 — cut walls/slabs solid black, everything else a lighter tone.
- **Detail-grade construction (the 1:5/1:10 ceiling):** Studio A, Ref A-2 — material-coded poché (concrete red w/ aggregate speckle, batt-insulation blue scallop squiggle, metal deck red corrugated, steel embeds white w/ hex bolt-holes); and Studio E, Ref E-1 (portfolio, p11) — ortho section + iso cutaway both keyed 0–22 to a real **CSI/MasterFormat keynote legend**.
- **Masonry/concrete section vocabulary:** Studio B, Ref B-1 — brick coursing, 45° grout hatch, concrete cross-hatch with aggregate, rebar as dashed centerline with tie wedges, all carried by hatch against one strong cut line, no black.
- **Building section on white with datum craft:** Studio A, Ref A-3 — doubled outline-poché cut, continuous ground line at +0'-0" as the single heaviest stroke, half-black target markers stepping +15/+30/+40/+53.
- **Elevation ranking (profile > structure > datum > dimension):** Studio F, Ref F-1 (p1) — building-profile edge 2–3× the diagrid mullions, circle-tick datum markers, dimension strings dropped to true hairline.

### 1.4 Material by hatch at constant weight — not by weight
The corpus's genuine, transferable strength. Material identity is carried by **hatch pattern/density while line weight stays fixed**. The tidiest "lookup table" to emulate is Studio C, Ref C-2: four copper panels differentiated purely by hatch — blank outline = smooth, parallel ridge = corrugated, dense ellipse rows = corrugated-perforated, dot-grid = flat-perforated. Reinforce with the geological-strata library in Studio E, Ref E-2 (sand stipple → wavy mudstone → diagonal shale) and the differentiated wall-section hatches in Studio A, Ref A-4 (aggregate stipple / insulation cross-hatch / gravel dot / coursed earth in one cut).

### 1.5 Annotation lives on the lightest layer
Dimension lines, leaders and level datums are the thinnest strokes on every strong sheet, frequently **tinted** (magenta in Studio B, violet in Studio G, red dashed leaders in Studio F/Studio A) so they never read as building line. Detail call-outs are standardized: circular blow-up bubbles or numbered bubble tags on thin dashed leaders ending in small dots, small sans-serif labels. Best annotation-discipline reference for leader weight: Studio D, Ref D-2 (true-hairline leaders that never compete with geometry).

### 1.6 Scale figures and "beyond" geometry stay subordinate
Figures are **flat single-color silhouettes, outline-only, no internal detail** (magenta/grey in Studio B, chartreuse in Studio D, solid terracotta in Studio C) — a deliberate demonstration that *color is not hierarchy, weight and fill are.* Glazing is a single hairline (optionally a faint wash). Plans get a **light-grey massing ghost** behind them for figure-ground (Studio A, Ref A-1). Chroma is rationed — often to exactly one accent used only on the figure.

### 1.7 The universal failure mode
Every studio's anti-pattern section names the same thing: **weight-flatness** — a uniform Make2D hairline where cut floor plates read at the same weight as the elevation behind them, so nothing anchors the eye. The canonical "improve-this" input is Studio E, Ref E-3 (portfolio, p6, "CARAPACE"): a clean whole-building cut drawn at one flat weight with zero poché — *the exact drawing this tool exists to correct.* Secondary failures: saturated grounds that crush value contrast, hue-as-hierarchy (collapses in greyscale), and cast-shadow blobs faking depth instead of earning it through cut poché + receding line.

---

## 2. Where the Studios Disagree — Forks to Ship as Presets

These are real, defensible stylistic choices, not right-vs-wrong. The tool should expose them as selectable presets rather than hard-coding one.

**Fork A — How to fill the cut (poché style).** Five live conventions in the corpus:
1. **Full solid-black poché** — the reference set (published Suzhou plan / Schodek section); Studio C sectional-axo. Maximum figure-ground, greyscale-safe.
2. **Color-coded solid poché** — Studio B ochre timber / Studio D salmon timber / Studio A red concrete. Reads material-by-material, still punches greyscale.
3. **Hatched poché** — Studio B 45° masonry / concrete cross-hatch; Studio D teal crosshatch; Studio H. No black; cut carried by hatch density against a heavier cut line.
4. **Outline-poché (white-filled)** — Studio A plans (Ref A-1), sections (Ref A-3). Cut = doubled heavier profile + faint stud hatch; deliberately no fill.
5. **Translucent-grey poché** — Studio D, Ref D-3 concrete-as-ghost, so rebar stays visible.

**Fork B — Black budget.** *Reserve black strictly for the cut* (Studio C, the reference set) **vs** *never use black at all* — carry the cut with saturation/tone (Studio F, Studio G, Studio E). The second only works on a controlled ground; recommend it as an opt-in "no-black / tonal-cut" preset.

**Fork C — Ground polarity.** White/neutral ground (Studio A, Studio D best sheets) **vs** saturated color field or negative (Studio B, Ref B-4 white-on-slate, Studio G flooded fields, Studio C red). Ref B-4 proves the cut-heavy/content-hairline logic **survives value inversion**, so the tool's hierarchy is polarity-independent — offer a "negative/dark-ground" preset that keeps the same ramp with reversed value.

**Fork D — Isolation vs even ramp.** *Blacken exactly ONE system to establish figure* (Studio B steel frame, 6–8×) **vs** a smooth multi-tier ramp where no single system dominates. Ship both as "isolate-system" and "balanced-ramp."

**Fork E — Material-system color coding.** Two-color system coding (Studio A, Ref A-5 orange-timber / blue-steel; hardware flat neutral grey against colored timber) **vs** monochrome material-by-hatch. Offer a "system-color" toggle.

**Fork F — Datum device.** Heavy continuous ground line at +0'-0" with half-black target level markers (Studio A, Ref A-3) **vs** a flat color-tint wash splitting the sheet at grade (Studio D, Ref D-3 blue = below-grade). Both are legitimate "where is grade" conventions.

---

## 3. Translation Recipe — Raw Rhino Export → Target Look, Today

### 3.1 The one correct pipeline choice
Three pipelines exist; only one hits the look cleanly on a Rhino-native `.ai`:

- **`apply-saas --auto` (color-luminance ladder)** — *do not use for these files.* It sorts distinct colors darkest→lightest and buckets the darkest into the cut role. On the real run this promoted projected connector plates colored `RGB(40,40,40)` to full 1.0 pt cut weight (defect **D4**), even though their layer names say "0.25 pt connectors." A hand-edited color `--mapping.json` **cannot** fix this either, because the connectors share the darkest color bucket with genuine dark strokes.
- **`apply-saas --architectural` (layer-first)** — **use this.** It installs a `layer_weight_resolver` that resolves weight **by layer name first**, falling back to color only for unknown layers. Connectors/cleat-plates resolve to 0.25 pt by layer; `ClippingPlaneIntersections` cut layers resolve to 1.0 pt — decoupled from the shared `RGB(40,40,40)`. `arch-lw explain-layer` already returns the correct weights per layer, so the knowledge is there; only the color path collapses it.
- **`arch-lw poche` (osascript/polygonize_dump path)** — **avoid.** It calls the unbounded `_visible_structural_completion_candidates` (poche.py:398), which has no upper area cap and no cut-bounds containment check, so it solid-filled two projected `TEC_FOUNDATION` strips far to the right of the cut plane (defect **D1**: area 22515 and 7145 at x up to 1146, where the real cut maxes at x≈500). `apply-saas --poche` instead runs `make2d complete_structural_cut_polygons`, whose `TEC_FOUNDATION` area cap of 2500 rejects those strips by construction.

### 3.2 The defect-fix rerun (one headless pass, no Illustrator needed)
From `<scratch>/real-hero/`, using `<repo>/.venv/bin/arch-lw`:

**Step 1 — `overrides.json`** (fixes D3, the slender CLT wall that fragmented into ~17 disconnected chains reading as white dashes; bbox collapses it to one continuous band — verified n=1, area 8931):
```json
{
  "axon precedent 1::Visible::ClippingPlaneIntersections::20_CLT_THICK_REMAP_49FT_BACKUP_WALL_V68": { "strategy": "bbox" }
}
```

**Step 2 — one pass on the RAW native export:**
```
arch-lw apply-saas "section-raw.ai" \
  --architectural \
  --poche \
  --poche-overrides overrides.json \
  --bridge-strategy best \
  -o "section-v4 POCHE.ai"
```

Why this clears all four defects in one pass:
- **D4** — `--architectural` resolves connectors/cleat-plates to 0.25 pt by layer, cut layers to 1.0 pt, independent of `RGB(40,40,40)`.
- **D1** — `apply-saas` never calls the unbounded visible-completion path; the capped `complete_structural_cut_polygons` (`TEC_FOUNDATION` cap 2500) rejects the 22515/7145 projected strips.
- **D3** — the bbox override collapses the wall to one continuous band matching the clean left reference.
- **D2** — the capped completion + no visible-loop path removes the stray beam-end/wall-fragment squares near the right cut edge; any residual tiny square lands on the isolated poché overlay and is deletable in one click.

Optional ISO-128 print weights: add `--for-print --scale 1/4`.
QA: render `section-v4 POCHE.ai` vs `section-raw HIERARCHY-saas.ai`, diff for new-black blobs — expect **no** blob at pxfrac x>0.63 y>0.83 (D1 gone) and a **single continuous** band at pxfrac x≈0.57 (D3 fixed).

### 3.3 Illustrator finishing moves (the preserved layers allow all of these)
Editability is confirmed: the native Illustrator payload is intact (63 OCG layers, all 62 original Rhino layers untouched), and **poché is written as a single overlay layer, `ARCH_LW_POCHE_FILL`, not injected into source cut layers.** Consequences:

1. **Every original stroke and its weight is re-tunable per layer** — nudge tier 2 (structure) or tier 3 (texture) up/down without re-running the engine, to dial the 3:2:1 ramp of §1.2 by eye.
2. **All poché is isolated on one layer** — recolor it wholesale to switch Fork-A preset (black → ochre/salmon/red), lower its value so it never out-values the profile bounding it, hide it, or delete it.
3. **Stray fills (any residual D1/D2 blob) are removed by hand on that one layer** — select `ARCH_LW_POCHE_FILL`, delete the offending polygon; no source geometry is touched.
4. **Add the corpus finishing vocabulary the engine doesn't place:** tint the annotation/dimension layer (magenta/violet per §1.5), drop a light-grey massing ghost behind plans (§1.6), set the ground datum as the single heaviest stroke and add half-black level target markers (§1.3, Fork F), and flatten scale figures to one accent silhouette.

---

## 4. Engine Gaps → Issue #83

### 4.1 Concrete fixes from the defect analysis (the current run's four)
Each is a real code gap that the recipe above only *routes around*; the engine should be made safe by construction.

- **D1 — unbounded visible-structural completion.** `poche.py:_visible_structural_completion_candidates` (398–467) has **no upper area cap and no cut-bounds containment check**, so a giant projected foundation strip is promoted to poché. **Fix:** before accepting (poche.py:452), add (a) an upper area cap mirroring `make2d_completion._completion_area_limit` (`TEC_FOUNDATION`=2500, make2d_completion.py:190–202) and (b) a centroid-inside-cut-bounds gate (`bounds_gate.covers(poly.centroid)`, make2d_completion.py:446) computed from the sibling `ClippingPlaneIntersections` cut lines — so a projected strip whose centroid falls outside the cut envelope is rejected. This makes the osascript path as safe as `apply-saas`.

- **D2 — stray self-closing projected loops.** `_structural_open_loop_candidates` (poche.py:587–637) closes every disconnected chain individually, and `_timber_beam_candidate_is_plausible` (make2d_completion.py:280–308) accepts 80–450-area cells with weak anchoring, so tiny projected beam-end/wall fragments close into standalone black squares. **Fix:** raise the cut-anchor requirement in the small-cell branch (make2d_completion.py:292–299) to `shared >= max(required*2, 40)` **and** require the chain's two endpoints to lie on real `ClippingPlaneIntersections` cut lines; equivalently reject any per-chain closure whose closing segment (poche.py:610–612) is not coincident with a cut edge.

- **D3 — fragment-gap bridging limited to foundation/concrete.** `_structural_fragment_gap_bridges` (poche.py:651) is applied only where `_uses_jsx_structural_helpers` is true (poche.py:276–278 = only `TEC_CONCRETE_BASE`/`TEC_FOUNDATION`), so slender CLT/backup-wall cut layers fragment into white-dashed bands. **Fix:** gate the bridge call in `_try_structural_open_loop` (poche.py:1016–1018) on a broader predicate that also matches `CLT_THICK`/`BACKUP_WALL`, or auto-default **slender high-aspect single-axis cut layers** (width ≤ ~10 pt, aspect > 20) to a bbox/concave-hull closure — removing the need for a per-file override.

- **D4 — color ladder promotes projected fixtures to cut weight.** `classify.py` `auto_by_luminance` (34) / `auto_by_role_ladder` (105) bucket the darkest color into the cut role, so projected `::Visible::Curves::` connectors sharing `RGB(40,40,40)` become 1.0 pt cut strokes. **Fix:** exclude `::Visible::Curves::` and `::Visible::Tangents::` layers from eligibility for the darkest "cut" bucket (only `ClippingPlaneIntersections` layers may receive cut weight by color). Simpler policy fix: **make `apply-saas` default to `--architectural` (layer-first) weight resolution for Rhino-sourced native `.ai`,** falling back to color only for unknown layers — this alone retires the `--auto` foot-gun for this whole file class.

### 4.2 Beyond the defects — target-look features the engine doesn't yet cover
These are gaps between what §1–§2 prize and what the pipeline currently produces (the recipe fixes them only as manual Illustrator moves). Candidate roadmap items for #83:

- **Material-hatch library / lookup table.** The corpus's single biggest strength (§1.4) — concrete-aggregate, insulation-scallop/cross-hatch, gravel-dot, brick coursing, wood-grain, geological strata, perforated-panel dot-grids — is applied by hand today. A **material→hatch lookup keyed off layer name** (the Studio C, Ref C-2 swatch column is a ready-made schema) would let the tool poché *material-by-material* instead of one flat fill.
- **Preset system for the §2 forks.** Poché style (full-black / color-coded / hatched / outline / translucent), black-budget, ground polarity, isolate-vs-ramp, system-color, datum device — all currently require re-runs or manual edits. Encode them as named presets.
- **Tonal recede for "beyond" geometry.** The best sections push un-cut structure to thin grey (§1.3); the engine sets weights but does not (per the analysis) auto-demote *value/opacity* of beyond-cut layers.
- **Datum + level-marker automation** (§1.3/Fork F) and **annotation-layer tinting/demotion** (§1.5) are pure Illustrator finishing today; both are deterministic from layer names and could be engine-placed.

*(4.2 items are inferred from the corpus spec, not from a reproduced defect — flag for triage before committing them to #83, unlike the D1–D4 fixes which are verified against the current run.)*
