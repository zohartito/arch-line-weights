# Bridge-Best Performance Fix

Date: 2026-05-05

## Summary

The 43 MB `iso axon section  [Converted].ai` failure was two separate bugs
showing up at once:

1. `bridge_strategy=best` could spend unbounded time in the depth-first
   backtracking rung on one small but pathological layer:
   `15_CU_PUNCH_RETURNS_SOUTH_BAY_ALIGNED_V44`.
2. The native-payload output drew low-confidence fallback geometry as solid black fills.
   On this file, that meant an `alpha_shape` fallback on facade returns and a
   `bbox` fallback on a roof-cap layer were injected as if they were real cut
   poche.

There was also a classifier bug behind the suspicious CLI line:

```text
# 0 colors mapped using auto:section
```

The converted AI file had zero usable strokes in the public PDF content stream,
and its native Illustrator payload used CMYK `K` stroke operators instead of the
RGB `XA` operator that `apply-saas` originally parsed. Auto-classification was
blind, and width rewriting defaulted instead of applying a real hierarchy.

## Repro Findings

On the real source file:

```text
public inspect stroked: 0
public inspect colors: 0
native payload XA events: 0
native payload K events: 63
cut layers: 18
```

The slow layer was not the largest layer. A timed per-layer run showed:

```text
TIMEOUT>15s 36 15_CU_PUNCH_RETURNS_SOUTH_BAY_ALIGNED_V44
```

The dense cladding/screen cut layers were not the hang:

```text
14_CU_CORR_PERF_SCREEN: 704 segments, ~0.36s
13_CU_FLAT_PERF_TRANSLUCENT: 280 segments, ~0.05s
11_CU_CORR_SOLID_OPAQUE: 277 segments, ~0.07s
```

With a 1 second bridge budget after the fix, the former slow layer exits in
about 1.7 seconds, logs its full name, and produces only a low-confidence
diagnostic fallback:

```text
strategy=backtrack timed out after 1.14s
layer='...15_CU_PUNCH_RETURNS_SOUTH_BAY_ALIGNED_V44'
result: alpha_shape, confidence=0.55, injected=false
```

For the full iso cut-layer set with a 1 second budget:

```text
elapsed: ~2.2s
cut layers: 18
injected layers: 15
injected polygons: 212
not injected: 15_CU_PUNCH_RETURNS... alpha_shape conf=0.55
not injected: 26_CLT_GAP_ROOF_CAP... bbox conf=0.30
```

## Changes

### Bridge guardrails

`infer_bridges_best` still remains the default, but now accepts:

- `time_budget_sec`
- `layer_name`

The backtracking explorer checks a monotonic deadline and raises
`BridgeSearchTimeout` cooperatively. The selector catches that timeout, logs the
layer and rung, then returns the best result collected so far instead of
continuing through the expensive ladder forever.

`polygonize_layer` wires the budget through with:

```text
ARCH_LW_BRIDGE_BEST_LAYER_BUDGET_SEC
```

Default: `60`.

It also adds an endpoint cap:

```text
ARCH_LW_BRIDGE_BEST_MAX_ENDPOINTS
```

Default: `1000`.

If a layer exceeds the endpoint cap, only that layer falls back to greedy. The
global default remains `best`.

### Conservative poche injection

`polygonize_layer` and `compute_polygons_for_layers` still report all fallback
results, but only inject trustworthy fills by default.

Default injection rule:

- inject `confidence >= 0.85`
- always inject explicit `user_override`
- do not inject `failed` or `skipped`

Emergency fallback geometry such as `alpha_shape`, `concave_hull`, `bbox`, and
LLM topology remains visible in the report but is not drawn as black poche by
default. This prevents facade returns or broad bounding boxes from becoming
visually convincing false poche.

Opt-in knobs:

```text
ARCH_LW_POCHE_MIN_INJECT_CONFIDENCE=0.85
ARCH_LW_POCHE_ALLOW_LOW_CONFIDENCE=1
```

### RGB and CMYK native color support

The native-payload parser now recognizes both:

- RGB `XA`
- CMYK `K`

CMYK is normalized into RGB tuples for the existing preset classifier. This
allows converted AI files to classify and rewrite line weights instead of
falling back to default widths.

`inspect_file()` also falls back to Illustrator private payload inspection when
the public PDF stream has no stroke colors.

### Empty auto mapping now fails loudly

If `--auto` finds zero stroke colors, the CLI now exits with a usage error
instead of printing `0 colors mapped` and continuing.

## Deadline-Safe Command

For the iso axon file and similar converted drawings, use a shorter per-layer
budget while the output is being tuned:

```bash
ARCH_LW_BRIDGE_BEST_LAYER_BUDGET_SEC=5 \
arch-lw apply-saas "/path/to/drawing.ai" \
  --auto --preset section --poche --bridge-strategy=best
```

If the drawing does not need poche:

```bash
arch-lw apply-saas "/path/to/drawing.ai" --auto --preset section
```

If a layer is missing legitimate cut fill after the conservative default, add a
specific per-layer override rather than allowing every low-confidence fallback
globally.
