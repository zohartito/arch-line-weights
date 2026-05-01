# v0.5 Code Quality Review — arch-line-weights

Diff: b721e96 → HEAD, 4250 lines, 12 files. Time-boxed 30-min review focused
on hacky patterns that meaningfully hurt readability/maintainability. Not
fixing — flagging only.

## Top 5 highest-impact issues

1. **Hatch recipe MultiPolygon dispatch is copy-pasted 19 times**
   (`src/arch_line_weights/hatch.py`). Every `hatch_*` function opens with
   the same 3-line `if isinstance(polygon, MultiPolygon): return
   functools.reduce(operator.iadd, (hatch_X(p, scale, **kw) for p in
   polygon.geoms), [])`. The pre-v0.5 file already had ~14 of these; v0.5
   added 5 more. This is the single biggest invitation-to-bug pattern in the
   codebase: a new recipe author can forget the boilerplate (and there's no
   abstract base / decorator to enforce it) or get the recursive name wrong.
   Fix: a `@multipolygon_dispatch` decorator (or just call the per-polygon
   helper inside one shared `hatch_polygon()` driver, since `MaterialRecipe`
   already exists). Each recipe shrinks to one substantive line.

2. **`--source` flag duplicated across 5 click commands with copy-paste echo
   blocks** (`src/arch_line_weights/cli.py`). The decorator block and the
   "if AUTO: echo detected ... else echo forced ..." block appear in
   `inspect`, `apply`, `apply_jsx_cmd`, `apply_saas_cmd`, `poche_cmd`, and
   `explain_layer` in five subtly different shapes (different label
   strings, some omit the `_resolve_source` call, `apply_jsx_cmd` doesn't
   actually pass it through to the JSX classifier). Worth extracting a
   shared `@source_option` decorator + a `_log_resolved_source(rep, source)`
   helper. Today, fixing the wording or detection flow means editing 5
   places and risking drift; the JSX path's `source` is already silently
   dead-wired.

3. **`bridge.infer_bridges_best` swallows all strategy exceptions
   silently** (`src/arch_line_weights/bridge.py:486-534`). Each of the four
   strategy attempts is wrapped in `try: ... except Exception: pass`. A
   genuine bug in the backtracking search or DBSCAN code becomes a quiet
   "no candidate produced" with no log. Worse, the third block sets
   `collapsed = list(segments)` in the except branch and then the fourth
   block's `if collapsed and collapsed != list(segments)` becomes the only
   signal of failure. Replace with explicit logging + reraising on
   programmer-error exceptions; only suppress shapely/numpy domain errors.

4. **Misleading docstring: "adaptive ε DBSCAN" is only adaptive at the
   layer level, then fixed within a layer** (`bridge.py:_adaptive_eps`,
   `_dbscan`). The module docstring (line 38-41) and prose throughout
   sells "adaptive ε derived from the local nearest-neighbour distance" —
   but `_adaptive_eps` returns a single scalar (median NN × 1.5, capped),
   and `_dbscan` then uses that scalar uniformly across all points. It's
   layer-adaptive, not point-adaptive — the latter is what "local" implies.
   Rename to `_layer_eps` / drop the word "local" from the docstring, or
   make it actually point-local.

5. **`Source` enum leaks across the API boundary even though consumers
   shouldn't care which library matched** (`layer_classify.py`,
   `cli.py`). Every CLI command takes `--source`, `TierAssignment` carries
   `source: Source`, `explain_source_match` re-runs classification just to
   re-derive the source label. But the only consumer that needs to know
   the source is the tooling that emits ExtendScript (`as_jsx_function`).
   Everyone else only reads `weight_pt` / `tier`. The enum-and-confidence
   plumbing in `TierAssignment` propagates noise into every test. Better:
   `classify_layer(name)` does its own internal dispatch (try Rhino, then
   AutoCAD, pick higher-confidence result), `--source` becomes an opt-in
   forcing knob, and `TierAssignment.source` becomes an internal-only
   diagnostic.

## The one issue most worth fixing now

**Issue #1 (the MultiPolygon boilerplate)** has the highest leverage:
~10 minutes of decorator work eliminates ~60 lines of duplicated code,
prevents future bugs in new recipes, and is mechanically safe (recipes are
already covered by tests in `test_hatch_v05.py`). Issue #2 (CLI
`--source` plumbing) is bigger but riskier and should wait for a real
need.

## Per-file findings

### `src/arch_line_weights/hatch.py`

- **L374-545: 19 near-identical recipe functions, each with the same
  6-line MultiPolygon dispatch**. Top issue. The functions that *don't*
  follow the pattern (`hatch_concrete_solid`, `hatch_clt_solid`,
  `hatch_steel_solid` — all `*a, **kw): return []`) make the pattern even
  more conspicuous.
- **L478, L594: `# v0.5 expansion`** comments narrate the change, not the
  code. Once shipped these become noise.
- **L1029-1035, L1052+: `LAYER_TO_MATERIAL` substring list bloated to 67+
  entries with comment-bracketed regions**. The comments-as-section-headers
  are fine but consider a structured map (`{material: [substrings]}`)
  inverted at module load — current ordering bugs (e.g. requiring `CMU`
  before `CONCRETE`) are an artifact of the linear scan and the
  `test_cmu_specificity_order` / `test_standing_seam_specificity_order`
  tests exist purely to lock in an ordering that the data structure
  doesn't enforce.
- **L1107: trailing-space hack** `"PIR ", "insulation_polyiso"` — comment
  flags it correctly ("trailing space avoids matching e.g. PIRELLI") but
  this is the kind of stringly-typed disambiguation that hyphen-anchored
  matching (already in `layer_classify.py` for AutoCAD) would solve
  cleanly.

### `src/arch_line_weights/cli.py`

- **L25-44: `_resolve_source` helper exists but isn't used uniformly**.
  `apply_jsx_cmd` (L267-269) skips it and just echoes the raw flag;
  `poche_cmd` (L564-565) does the same. The helper is half-applied.
- **L78, L176-180, L376-380, L656-666: `--source` echo block repeated 5
  times** with subtle wording differences ("layer-source", "layer-name
  source", "detected source"). Issue #2.
- **L920-922: dead-import comment** `Re-export so the unused
  classify_layer import stays referenced and downstream callers can still
  from arch_line_weights.cli import classify_layer.` This is a smell
  (a CLI module shouldn't be a re-export point). If callers really need
  `classify_layer`, they should import it from `layer_classify` directly.

### `src/arch_line_weights/layer_classify.py`

- **`Source` exposed in public API** (issue #5). `TierAssignment` carries
  `source: Source` and `confidence: float` for every match, but the only
  external consumer that uses these is the CLI's diagnostic logging —
  `apply_to_file` / `apply_to_file_saas` / `apply_via_jsx` ignore them.
- **L130, L328, L365: comments say "preserves pre-Phase-E5 behavior"** —
  narrating-the-change comments. Drop after release.
- **L1551: `f"-{upper}-" if source == Source.AUTOCAD else upper`** —
  inline ternary that mixes hyphen-padding with case conversion. Extract
  a `_normalize(name, source)` helper; today the same ternary recurs in
  `as_jsx_function` (L1581: `if source == Source.AUTOCAD: lines.append(...)`).
- **L1620-1663: `detect_source` mixes producer matching (substring), then
  falls through to layer-shape inference (regex), then returns
  `Source.AUTO`** — three-level conditional with magic thresholds (`>=
  0.5`, `>= 0.3`, `>= 0.9`, `>= 0.85`, `>= 0.7`). The thresholds are not
  named constants; they're inline literals across the function and tests.
- **L1666-1677: `explain_source_match` re-runs `classify_layer` just to
  print the match** — fine for a CLI helper, but `TierAssignment.source`
  is already on the result; the function could take a `TierAssignment`
  directly.

### `src/arch_line_weights/bridge.py`

- **`infer_bridges_best` swallows exceptions silently** (issue #3,
  L486-534). Each strategy block is `try ... except Exception: pass`.
- **Misleading "adaptive ε" docstring** (issue #4). The string "adaptive ε
  derived from the local nearest-neighbour distance" is in the module
  docstring (L38-40) and `_adaptive_eps` (L257-262) — but ε is fixed once
  per layer.
- **L139-181: `_backtrack_search` uses a 3-element list-as-mutable-state
  for `best_score`** — `best_score: list[int] = [_polygon_count(segments),
  0]`. Functions that need to mutate state from a closure usually use
  `nonlocal` or a small dataclass. The list-of-2-ints idiom is a Python
  trick that's harder to read than `best_score = [...]` and never
  appended to — a `[score, n_bridges]` slot.
- **L508-515: `dbscan_collapse` confidence formula is hand-rolled and
  doesn't match the helper `_confidence`** that the other strategies use.
  Three slightly different confidence formulas in the same selector.

### `src/arch_line_weights/poche_saas.py`

- Module docstring is a mini-spec (L1-43). High signal for understanding
  the file. Keep.
- **L286-334: `compute_polygons_for_layers` has its own override-
  resolution loop** that's a copy-paste of `poche.polygonize_dump`'s
  override loop. The pattern-matching glob (`pattern.endswith("*") and
  layer_name.endswith(pattern[:-1].split("::")[-1])`) is duplicated.
  Extract to `poche._resolve_override(layer_name, overrides)`.
- **L431-498: `apply_saas_with_poche` is a near-clone of
  `apply_saas.apply_to_file`** with a poché step inserted. The pikepdf
  `with` block, `_read_payload`/`_write_payload` calls, and result wiring
  are duplicated. A `apply_to_file_saas(..., extra_payload_passes=[...])`
  hook would unify them.
- **L535-603 + tests: `write_synthetic_test_ai` lives in production code
  but only tests use it.** Move to `tests/conftest.py` or
  `tests/_fixtures.py`.

### `src/arch_line_weights/presets.py`

- **L9-11: docstring narrates the change** ("v0.5 (2026-04-30): the
  legacy four hand-tuned lists are retained..."). After release this is
  archaeology.
- **L83-110: comment block of standards rationale** is good (citations are
  load-bearing) — keep.
- **L121-122: redundant module-level constant**: `_ISO_LADDER_PT = [mm(x)
  for x in _ISO_LADDER_MM]`. The pre-v0.5 code recomputed it inside
  `select_preset`; the v0.5 refactor lifted it to module level — good. But
  `_ISO_LADDER_MM` is then never referenced again. Inline it into the
  list comp and drop one symbol.
- **L499-526: `_SCALE_SHIFTS` has 18 keys for 8 distinct values** because
  every scale string is spelled 3 ways (`"1/4"`, `"1/4\"=1'"`, `"1/4=1'"`).
  Normalize at the call site: strip `"=1'"` and `'"'` chars, then look up
  in a 6-key table.

### `src/arch_line_weights/inspect.py`

- **L1173-1186: `_extract_pdf_metadata` returns both lowercase and
  capitalized variants of every key** so downstream code doesn't have to
  pick a canonical form. This is the wrong fix — `detect_source` already
  has its own `or` chain at L1639-1640. Pick one canonical form and
  enforce it.
- **L1189-1222: `_extract_layer_names` tries two PyMuPDF APIs with
  bare-except blocks** — fine pattern but the "merge" (`if n and n not in
  seen`) implies the two APIs can return overlapping data; in practice
  they're mutually exclusive across PyMuPDF versions. Could be an
  `if-else`, not `if + if`.

### `tests/test_*.py`

- Tests are well-structured and document intent clearly. Two minor things:
  - `test_apply_saas_with_poche_end_to_end_on_synthetic_fixture` depends
    on `write_synthetic_test_ai` from production code (see
    `poche_saas.py` finding above).
  - `test_cmu_specificity_order` / `test_standing_seam_specificity_order`
    test the *ordering* of `LAYER_TO_MATERIAL` rather than its
    *behavior* — they pin in place a bug the data structure doesn't
    prevent.

## Minor / not worth fixing

- `poche_saas.py:603 _ = contextlib.nullcontext` to suppress unused-import
  warning — odd but harmless.
- `cli.py:_resolve_source` returns `(Source, float)` where the float is
  always `0.0` or `1.0` for the forced/fallback branches and a real
  number only for genuine detection — that asymmetry is fine for a
  one-shot CLI output but would matter if it ever became a library.
- Unicode markers `✓ ~ ✗` in CLI output (`cli.py:836`) work on macOS but
  could trip Windows terminals — not a v0.5 regression but a latent issue.
