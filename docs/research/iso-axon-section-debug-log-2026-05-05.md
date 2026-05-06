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

## v0.6.12/v0.6.13 Make2D Completion Follow-Up

The next debugging pass tested the user's proposed architecture:

```text
architectural components -> complete broken Make2D geometry -> hierarchy/poché
```

That is the right model. The old pipeline treated poché as a layer-local
polygonization problem. The real failure is broader: Rhino Make2D can split one
architectural component across `ClippingPlaneIntersections`,
`Visible::Tangents`, and `Visible::Curves`, and both line hierarchy and poché
need the same repaired component understanding.

What changed:

- Added `src/arch_line_weights/make2d_completion.py` as the first reusable
  completion stage. It attaches architectural assignments, layer roles,
  component keys, and accepted/rejected completion candidates to parsed paths.
- Wired structural completion into `poche_saas` as bounded evidence, not as a
  blanket visible-layer fill.
- Added the rule learned from the false blobs:
  helper/visible completion candidates must share meaningful boundary with the
  real target `ClippingPlaneIntersections` layer before automatic fill.
- Added a second guard for concrete/foundation: helper geometry cannot wildly
  expand an already valid cut-only face.
- Added opt-in `ARCH_LW_POCHE_OVERLAY=1`, which creates a top-stack
  `ARCH_LW_POCHE` layer so later visible curves cannot draw over black fills.

Real outputs:

```text
v0612-bounds-candidates.ai
  better coverage, but still false helper-only blobs

v0614-no-concrete-blob.ai
  lower-left concrete-base helper expansion removed
  still missing some true slab/roof/foundation mass

v0615-overlay.ai
  same guarded geometry, plus a top ARCH_LW_POCHE layer
  confirms that remaining gaps are mostly missing component completion,
  not just layer draw order

v0616-current-best.ai
  same overlay/guarded poché, with quieter secondary steel and connector
  hierarchy after reducing section-screen secondary steel to 0.25 pt and
  connector hardware to 0.18 pt
```

Rule learned:

- The program should not "learn" implicitly from failures. Every bad run must
  become a documented failure case, a geometric rule, and a regression test.
  This pass added tests for helper-only rejection, anchored completion,
  concrete over-expansion, completion env disable, and overlay injection.

Still not solved:

- Some real cut faces appear to have zero clipping-plane boundary support.
  Those may be legitimate missing Make2D components, but accepting all of them
  creates false blobs. The next stage needs a component graph/review report
  that can say "these five candidates look like missing cut mass; these three
  are probably facade/return artifacts" with reasons.

Current best immediate output:

```text
/Users/zohartito/SynologyDrive/USC/Spring 2026/ARCH 202B/
iso axon section  [Converted] HIERARCHY-saas-ARCHITECTURAL-v0616-current-best.ai
```

It is safer than `v0612-bounds-candidates.ai`, but still not the final bar for
automatic poché on this drawing.

## v0.6.14/v0.6.15 Research-To-Rules Pass

The next pass paused more real-file trial output and converted the manual
workflow, book-derived rulebooks, and agent findings into code rules/tests.

Agent findings that became implementation:

- Sagan: the hard area caps were rejecting real roof/slab/foundation completion
  candidates. Result: large candidates can pass only when they are strongly
  anchored and material-strip-like.
- James: cut-line styling is separate from black poché. Result:
  architectural mode now has weight, stroke-color, and solid-dash resolvers.
- Erdos: the first foundation/roof gate was too permissive and tests did not
  cover RGB stroke rewrite or fill safety. Result: RGB `XA` and CMYK `K` stroke
  overrides are tested, lowercase fill operators stay untouched, and compact
  foundation/triangular roof failures are regression tests.
- Dewey: semantic-first hierarchy policy. Result: blacklist-before-whitelist
  classification, so glazing, membranes, connectors, and cladding/rainscreen
  layers cannot become black poché just because they also contain structural
  tokens.
- Raman: remaining v0618 failures point to open-loop cleanup and beam completion,
  not just completion caps. Result: post-clean open-loop filters reject tiny
  backup-wall fragments and large irregular roof surfaces; `TEC_TIMBER_BEAMS`
  completion is allowed only for small cut-anchored rectangles.
- Dirac/Locke: layer-scoped payload rewrites must anchor to real
  `%AI5_BeginLayer` envelopes. Result: stray `Ln` text outside a layer no longer
  steals architectural overrides.
- Lorentz: manual Illustrator workflow now lives in
  `docs/research/manual-illustrator-poche-workflow.md`.

Manual workflow rules now treated as program rules:

- Preserve original Make2D layers; generated poché/cut strokes must be auditable.
- Classify before filling: true cut mass, strong cut line, context edge,
  surface/texture, void/glass/air.
- Isolate one architectural component at a time. Whole-layer filling is unsafe.
- If a beam/slab/wall/roof/foundation is truly cut, incomplete Make2D output is
  not an excuse to leave it blank. The program must complete it correctly or
  report an explicit candidate/reason.
- Strong non-poché cut elements still need solid cut strokes.
- Every failure should become a rule, test, and issue note.

New regression coverage:

```text
tests/test_apply_saas.py
  layer intervals use %AI5_BeginLayer envelopes
  RGB XA and CMYK K stroke recolor work
  lowercase fill operators stay untouched
  strong cut dashes can be normalized to solid

tests/test_architectural_mode.py
  blacklist wins over structural-looking cut tokens
  generic clipping-plane layers become cut lines, not fills
  tiny backup-wall fragments are rejected
  large irregular roof open-loop surfaces are rejected
  legitimate tall backup-wall strips and roof strips are preserved

tests/test_apply_saas_poche.py
  large anchored roof/foundation strips can pass when plausible
  compact foundation blobs and triangular roof surfaces are rejected
  small timber beam cut rectangles can be completed
  large timber beam blobs are rejected
```

Focused verification:

```text
PYTHONPATH=src pyenv exec python -m pytest \
  tests/test_apply_saas.py \
  tests/test_architectural_mode.py \
  tests/test_apply_saas_poche.py -q

89 passed
```

Important unresolved point:

- The right retaining wall/foundation candidate currently has zero cut anchor in
  the source-derived probe. The consensus is not "leave it blank"; it is "do not
  auto-fill helper-only geometry as black mass until a component-graph or review
  rule can prove it is the cut concrete/foundation." That belongs in Issue #21
  as the next component-completion problem.

## v0619/v0620 Report + Hierarchy Pass

The next pass incorporated the subagent findings into a safer review workflow.

James found that poché eligibility was mostly safe, but the cut-stroke style
resolver still promoted too many non-solid cut layers to `0.5 pt`. That made
connectors, SHS/HSS, cladding returns, and generic clipping-plane fragments
compete with true structural cut mass.

Rule added:

- True structural cut mass keeps `1.0 pt` black solid strokes and poché.
- Primary visible structure keeps `0.5 pt`.
- Secondary steel cut strokes resolve to `0.25 pt`.
- Frames/mullions resolve to `0.3 pt`.
- Connectors and cladding/screen cut returns resolve to `0.18 pt`.
- Generic clipping-plane cut lines resolve to `0.3 pt` and should be reviewed.

Real output:

```text
iso axon section  [Converted] HIERARCHY-saas-ARCHITECTURAL-v0619-report-hierarchy.ai
iso-axon-v0619-report.json
```

The run stayed fast and injected the same safe poché set:

```text
48 polygons across 7/7 injectable cut layers
8 cut layers considered
6 inferred layers
1 clean filled layer
1 low-confidence diagnostic-only layer
```

The stroke distribution moved in the intended direction:

```text
0.5 pt strokes: 27 -> 15
0.18/0.25/0.3 pt subordinate strokes increased
```

The new JSON report names the remaining risky candidates instead of hiding
them:

- `26_CLT_GAP_ROOF_CAP_REMAP_49FT_V68` remains `bbox`, `conf=0.30`,
  diagnostic-only.
- `TEC_ROOF_CLT` has two rejected large helper candidates, one `37,317.5`
  area and one `11,081.2` area. Both have meaningful cut sharing but fail the
  current large-strip plausibility rules.
- `TEC_FOUNDATION` has rejected helper candidates with `shared=0.0` or outside
  the target cut bounds, matching the unresolved right foundation/wall problem.
- `TEC_TIMBER_BEAMS` still has a rejected `1,732.0` area candidate; likely next
  rule is beam-cell decomposition rather than allowing one large timber blob.

As a controlled experiment, `ARCH_LW_POCHE_ALLOW_LOW_CONFIDENCE=1` produced:

```text
iso axon section  [Converted] HIERARCHY-saas-ARCHITECTURAL-v0620-lowconf-roofcap.ai
iso-axon-v0620-lowconf-report.json
```

It injected one additional roof-cap bbox, but Illustrator review showed a
large black roof/rainscreen blob. That confirms the default low-confidence
refusal is correct. `v0620` is evidence, not a print candidate.

Current print-leaning candidate:

```text
iso axon section  [Converted] HIERARCHY-saas-ARCHITECTURAL-v0619-report-hierarchy.ai
```

It is not perfect poché, but it is safer than the low-confidence variant. The
next true geometry fix should be component-graph completion and beam-cell
decomposition, not global loosening of confidence gates.

## v0621/v0622 Deadline Pass

The latest safe run produced:

```text
iso axon section  [Converted] HIERARCHY-saas-ARCHITECTURAL-v0621-deadline-safe.ai
iso-axon-v0621-deadline-safe-report.json
```

Then a narrow timber-beam cell preservation patch was tested. It changes
`make2d_completion._candidate_polygons()` so `TEC_TIMBER_BEAMS` can evaluate
raw polygonized cells before adjacent cells are unioned into one larger blob.
The focused regression proves repeated small beam cells can pass while the
large timber blob remains rejected.

Real output:

```text
iso axon section  [Converted] HIERARCHY-saas-ARCHITECTURAL-v0622-beam-cells.ai
iso-axon-v0622-beam-cells-report.json
```

Result on the iso axon:

```text
48 polygons across 7/7 injectable cut layers
TEC_TIMBER_BEAMS remains 18 polygons
the remaining 1,525.9 area timber candidate is still rejected as not a small
cut rectangle
```

Conclusion:

- The timber-cell patch is safe and useful for future repeated beam-end cases.
- It does not solve this exact iso axon. The remaining true misses require
  component-graph completion, especially for right foundation/wall and roof/slab
  strip evidence.
- For the 2026-05-06 9:30 a.m. deadline, the practical path is to use v0622 as
  the automatic base and add a small `ARCH_LW_POCHE_CLEANUP` layer in
  Illustrator for the few true cut faces the engine still cannot prove.
