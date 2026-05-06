# Iso Axon Section Debug Log

Date: 2026-05-05

Source file:

```text
/Users/zohartito/SynologyDrive/USC/Spring 2026/ARCH 202B/iso axon section  [Converted].ai
```

## User-Visible Symptoms

- `apply-saas --auto --preset section --poche --bridge-strategy=best` appeared
  to hang for 20+ minutes at 100% CPU.
- CLI printed `0 colors mapped using auto:section`.
- Output showed incorrect black poché:
  - facade-return blobs
  - missing first-floor/floor-plate poché
  - foundation/concrete not consistently shaded
  - left concrete/CLT wall missing or partial
  - roof cut partially filled
  - steel connectors too heavy in the hierarchy

## Confirmed Root Causes

### Runtime

The slow layer was:

```text
15_CU_PUNCH_RETURNS_SOUTH_BAY_ALIGNED_V44
```

It only had 36 segments, but it triggered a combinatorial backtracking trap in
`infer_bridges_best`. Segment count alone was not a reliable predictor.

### Wrong Poché Blobs

The biggest false fills came from low-confidence rescue geometry:

```text
15_CU_PUNCH_RETURNS...   alpha_shape   conf=0.55
26_CLT_GAP_ROOF_CAP...   bbox          conf=0.30
```

These should be diagnostics, not default black fills.

### Empty Auto Mapping

The public PDF stream had zero strokes, and the native Illustrator payload used
CMYK `K` operators rather than RGB `XA`. The original classifier was blind to
that file.

### Missing Legitimate Poché

After blocking low-confidence fills, the remaining problem became clearer:
several structural cut layers are open or partial loops. Examples:

```text
TEC_CONCRETE_BASE      base=1 polygon, open-loop closure finds another concrete wall polygon
TEC_ROOF_CLT           base=1 polygon, open-loop closure finds additional roof polygons
26_CLT_GAP_ROOF_CAP    3 segments, no valid closed loop by default
TEC_CLT_SLABS          many open endpoints; some slab regions are partial
03b_CLT_BACKUP_WALL    many open endpoints; wall poché is incomplete
```

This requires structural open-loop closure, not global `bbox`.

## Patch Landed

- `bridge-best` now has a per-layer wall-clock budget.
- `bridge-best` logs the slow layer name.
- Large endpoint layers can fall back to greedy per-layer.
- Low-confidence fallback poché is not injected by default.
- `inspect` falls back to the AI private payload.
- `apply-saas` supports both RGB `XA` and CMYK `K`.
- Empty `--auto` mapping is a hard error.

## Real Patched Run

Output:

```text
iso axon section  [Converted] HIERARCHY-saas-PATCHED.ai
```

Run summary:

```text
35 colors mapped
63 stroke-width ops rewritten
212 poché polygons injected
15/15 injected cut layers
15_CU_PUNCH_RETURNS skipped as alpha_shape conf=0.55
26_CLT_GAP_ROOF_CAP skipped as bbox conf=0.30
```

This removed the major facade-return blob but did not fully solve architectural
poché coverage.

## Next Fix

Add an `--architectural` mode:

```bash
arch-lw apply-saas drawing.ai --auto --preset section --poche --architectural
```

Behavior:

1. Layer semantics first, color second.
2. Poché whitelist for true structural cut material:
   - foundation
   - concrete
   - CLT slabs
   - roof CLT
   - CLT backup/thick walls
   - true timber/steel cut solids
3. Poché blacklist:
   - copper/cladding/screens/perforated
   - punch returns
   - glass/window/frame
   - EPDM/membranes/datum/reference
   - connectors/brackets/cleats/clips
4. Structural open-loop closure:
   - only for whitelisted structural layers
   - close open chains with plausible missing edges
   - reject tiny/snake/facade shapes
   - report every inferred closure
5. Semantic hierarchy:
   - cut structural layers: heaviest
   - primary profiles: heavy
   - SHS/RHS steel framing: secondary
   - steel connectors/brackets/cleats: connector tier
   - cladding/screens: light material/surface tier
   - glass: special/light

## Do Not Repeat

- Do not turn low-confidence `bbox` back on globally.
- Do not poché every `ClippingPlaneIntersections` layer.
- Do not rely on color luminance for Rhino drawings when layer names are rich.
- Do not use PDF preview as final proof of native-payload output.

## Architectural Mode Run

Output:

```text
/Users/zohartito/SynologyDrive/USC/Spring 2026/ARCH 202B/iso axon section  [Converted] HIERARCHY-saas-ARCHITECTURAL.ai
```

Command:

```bash
ARCH_LW_BRIDGE_BEST_LAYER_BUDGET_SEC=5 \
PYTHONPATH=src pyenv exec python -m arch_line_weights.cli apply-saas \
  "iso axon section  [Converted].ai" \
  -o "iso axon section  [Converted] HIERARCHY-saas-ARCHITECTURAL.ai" \
  --auto --architectural --preset section --poche --bridge-strategy=best --no-progress
```

Run summary:

```text
35 colors mapped
63 stroke-width ops rewritten
62 architectural layer overrides
49 poché polygons injected across 7/7 structural cut layers
```

Injected structural layers:

```text
TEC_CLT_SLABS                            linemerge_bare       9 polygons
20_CLT_THICK_REMAP_49FT_BACKUP_WALL_V68  linemerge_bare      10 polygons
TEC_FOUNDATION                           structural_open_loop  2 polygons
TEC_CONCRETE_BASE                        structural_open_loop  2 polygons
TEC_ROOF_CLT                             structural_open_loop  3 polygons
03b_CLT_BACKUP_WALL_5in                  structural_open_loop  4 polygons
TEC_TIMBER_BEAMS                         structural_open_loop 19 polygons
```

Reported but not injected:

```text
26_CLT_GAP_ROOF_CAP_REMAP_49FT_V68       bbox conf=0.30
```

Visual check in Illustrator:

- The large false facade-return/blob fill is gone.
- Connectors and facade/screen layers no longer receive cut-weight treatment
  just because their source colors are dark.
- More legitimate structural poché is present than the previous patched run.
- The output is improved but not yet perfect: some areas still read like heavy
  cut bands rather than fully filled cut solids because the Rhino/AI source
  provides partial cut-edge geometry instead of complete cut-face boundaries.

Next engineering follow-up:

- Add a per-layer review report with inferred closure edges and skipped
  structural candidates.
- For deadline work, expose a controlled manual override/closure layer for
  the remaining areas that only the designer can disambiguate quickly.

## v0.6.11 Poché Failure Note

Current user-visible symptoms:

- The first-floor slab is still missing from the black poché field.
- Roof and wall cut areas are not fully black, so the section reads as bands
  and fragments rather than continuous cut mass.
- White stripes remain inside areas that should read as solid structural cut.
- Some beam-cap regions collapse into three-point or curved black blobs instead
  of clean rectangular/plate-like cut fills.

Diagnosis so far:

- Some structural helper geometry is present, but it is not in the same geometry
  bucket the poché extractor currently trusts. The useful boundary evidence can
  live in `Visible::Curves` and `Visible::Tangents`, while the poché path has
  only been considering `ClippingPlaneIntersections`.
- That mismatch explains why the lineweight hierarchy can see structural cut
  intent while the fill generator still misses slabs, roof plates, walls, and
  beam caps.
- The layer-name parser has also shown that it can swallow stray bytes. That can
  corrupt the semantic signal needed to decide whether a layer is structural
  cut material, facade/connector/detail linework, or diagnostic geometry.

Intended v0.6.11 fix:

- Let structural poché eligibility use the same normalized semantic evidence as
  architectural lineweight classification, including validated helper geometry
  from `Visible::Curves` and `Visible::Tangents` when it belongs to a structural
  cut layer.
- Harden layer-name parsing so stray bytes cannot silently erase or distort
  structural tokens.
- Keep the architectural rule explicit: cut stroke hierarchy is separate from
  poché fill eligibility. A line can deserve a heavy cut stroke without being
  eligible for black fill, and a structural cut fill must still pass material,
  layer, and topology checks before injection.
- Preserve the earlier guardrails: no global low-confidence bbox or alpha-shape
  fallback for facade returns, connectors, cladding, membranes, glass, or other
  nonstructural layers.

Actual v0.6.11 patch:

- `poche_saas` now enumerates all layer paths in architectural mode, keeps the
  poché target list restricted to structural `ClippingPlaneIntersections`, and
  passes same-leaf `Visible::Curves` / `Visible::Tangents` paths as helper
  geometry only.
- `poche` now has a parallel-edge structural recovery path for cut faces made
  of opposite edges with missing end caps. It clips inferred fills to the actual
  overlap span and requires helper-derived candidates to share meaningful
  boundary with the real cut lines.
- Layer enumeration now starts from `%AI5_BeginLayer` envelopes, which prevents
  stray setup text from being decoded as a layer name.

Real run:

```text
arch-lw apply-saas "iso axon section  [Converted].ai" \
  -o "iso axon section  [Converted] HIERARCHY-saas-ARCHITECTURAL-v0611.ai" \
  --auto --architectural --preset section --poche --bridge-strategy=best
```

Result:

```text
35 colors mapped
63 stroke-width ops rewritten
62 architectural layer overrides
poché: injected 51 polygons across 8/8 cut layers (+9,311 bytes)
  20_CLT_THICK_REMAP_49FT_BACKUP_WALL_V68  linemerge_bare       10
  TEC_FOUNDATION                           structural_open_loop   2
  TEC_CONCRETE_BASE                        structural_open_loop   2
  TEC_ROOF_CLT                             structural_open_loop   2
  03b_CLT_BACKUP_WALL_5in                  structural_open_loop   7
  TEC_CLT_SLABS                            structural_open_loop   6
  TEC_TIMBER_BEAMS                         structural_open_loop  20
  26_CLT_GAP_ROOF_CAP_REMAP_49FT_V68       structural_open_loop   2
```

Computer Use visual check:

- Better: no global low-confidence bbox blob; all 8 structural cut target
  layers inject; runtime no longer stalls; layer names are clean.
- Still not good enough to call solved: much of the drawing still reads as
  heavy cut outline/bands rather than continuous cut mass. Some true cut faces
  appear to live only in visible structural layers, not in clipping-plane
  layers.
- A prototype that filled visible structural candidates (`03bc_CLT_BACKUP_COURT`,
  `26_CLT_GAP_ROOF_CAP_REMAP_49FT_V68`, `TEC_FOUNDATION`) recovered more mass
  but created obvious black false blobs. That path should stay behind an
  explicit/manual review workflow, not become the default.

Next step:

- Build a per-layer review/report mode before attempting broader visible-layer
  poché: show structural helper candidates, inferred closure edges, skipped
  visible structural solids, and confidence/reason so Zohar can approve the
  ambiguous faces quickly.
- For immediate deadline use, run `--architectural` for hierarchy and
  high-confidence poché, then manually fill the remaining ambiguous wall/roof/
  foundation faces or add a controlled `__POCHE_CLOSE__`/manual mask workflow.
