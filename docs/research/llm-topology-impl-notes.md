# LLM topology-inference rung — implementation notes

> Implementation companion to
> `docs/research/stubborn-layers-deep-dive.md` §5 (the algorithm
> proposal) and `docs/research/ai-augmented-mode.md` §4–6 (the
> Anthropic-integration recommendation, prompt template, and
> privacy stance).
>
> Closes GitHub Issue #6. Implements rescue rung 5 in
> `src/arch_line_weights/poche.py`'s `polygonize_layer` ladder.
> Default OFF — opt-in via `ARCH_LW_LLM_FALLBACK=1` or the new
> `--llm-fallback` CLI flag.

## Where it sits

The polygonize rescue ladder, in order of attempt:

| # | Strategy | Source module | Rung confidence |
|---|---|---|---|
| 1 | `linemerge_bare` | `poche._polys_at_tolerance(tol=0)` | 1.0 |
| 2 | `linemerge_snap` | `poche._polys_at_tolerance(tol>0)` | 0.7–0.95 |
| 3 | `auto_bridge` | `bridge.infer_bridges` / `infer_bridges_best` | 0.25–1.0 |
| 4 | `alpha_shape` | `alpha_shape.alpha_shape_all_regions` | 0.55 |
| **5** | **`llm_topology`** | **`llm_topology.infer_closing_plan`** | **0.65** |
| 6 | `concave_hull` | `shapely.concave_hull` | 0.55 |
| 7 | `bbox` | `shapely.box(*bounds)` | 0.30 |

Rung 5 sits between alpha_shape and concave_hull because:

- Alpha_shape is cheap, deterministic, and frequently solves
  `26_CLT_GAP_ROOF_CAP` on its own. Don't pay for an LLM call when
  the geometric rung already wins.
- Concave_hull is lossy and confidence-floored at 0.55. The LLM
  rung's output is *augmented* line geometry fed back into
  `linemerge`+`polygonize`, so its output is genuinely closed
  polygons (confidence 0.65) — strictly better than the lumpy
  envelope from `concave_hull`.

## What gets sent to the LLM

The privacy allow-list is enforced in
`llm_topology._build_user_message`. Only these fields reach the API:

- The **leaf** layer name (everything left of `::` is stripped).
- The bounding box of the endpoint cloud.
- The endpoint count.
- The indexed list of `(x, y)` coordinates (capped at
  `MAX_ENDPOINTS = 200` — covers every stubborn layer in our reference
  drawing comfortably while keeping per-call token cost predictable).

It does **not** send: filenames, file paths, project codes, customer
emails / studio names, PieceInfo metadata, project XMP, or the
hierarchical `::`-joined layer prefix. The unit test
`test_user_message_only_contains_leaf_layer_name` enforces this.

## Prompt template

The system prompt (`SYSTEM_PROMPT` in `llm_topology.py`) is:

1. A short job description ("propose a closure plan").
2. Domain hints for the three stubborn layers identified in
   `stubborn-layers-deep-dive.md`:
   - `WINDOW_FRAMES` → many small frame rectangles
   - `CLT_GAP_ROOF_CAP` → two separate caps with a gap
   - `CU_CORR` → corrugated copper, single undulating profile
3. The strict JSON output schema (enforced by the
   `submit_closure_plan` tool's `input_schema`):

   ```json
   {
     "closures": [[start_idx, end_idx], ...],
     "confidence": 0.0,
     "rationale": "<= 30 words"
   }
   ```

4. Conservative-bias instructions ("confidence < 0.6 means 'not
   sure'; prefer empty closures and low confidence over a
   confident-but-wrong plan").

The prompt is wrapped in a `cache_control: {type: "ephemeral"}` block
so Anthropic prompt-caching kicks in: the first call writes the
~600-token system prefix to cache (1.25× input price), every
subsequent call reads it back at ~10% input price.

## Strict-JSON via `tool_use`

We force structured output through Anthropic's tool-use mechanism
rather than free-text JSON. The `submit_closure_plan` tool defines an
`input_schema` that the API enforces server-side, then we set
`tool_choice = {"type": "tool", "name": "submit_closure_plan"}` so
the model *must* return a tool-call, not free text.

This is more robust than:

- **Plain text + `json.loads`** — drifts on quote escaping, trailing
  commas, model thinking out loud.
- **`output_config.format`** — works on Opus 4.7 / Sonnet 4.6 but the
  spec calls for Haiku 3.5 / 4.5 to keep cost down (~$0.003 / call),
  and `tool_use` is the most portable strict-JSON path across the
  Haiku family.

A second-pass schema check in `_validate_plan_schema` enforces the
constraints JSON Schema can't express — index bounds (`end_idx <
n_anchors`) and self-loop rejection (`start_idx == end_idx`).

## Retry behavior

**By design, no in-rung retries.** Every call to the rescue ladder is
already gated behind a four-rung geometric pipeline that filters out
~95% of cases. When the LLM fails (network blip, malformed plan,
hallucinated indices), the right move is to skip to the next rung
(concave_hull, then bbox) — not to burn another $0.003 retrying.

The Anthropic SDK already retries 429 and 5xx errors automatically
(`max_retries=2` by default), so transient failures are absorbed
upstream. Anything that bubbles out is real (auth error, malformed
schema, timeout) and not worth re-issuing.

## Cost reasoning

From `docs/research/stubborn-layers-deep-dive.md` §5 / `ai-augmented-
mode.md` §3, validated with current Anthropic pricing
(2026-04-30 snapshot):

| Model | Input $/MTok | Output $/MTok | Cache hit $/MTok | Per-call cost |
|---|---|---|---|---|
| Claude Haiku 3.5 (default) | $0.80 | $4.00 | $0.08 | ~$0.003 |
| Claude Haiku 4.5 | $1.00 | $5.00 | $0.10 | ~$0.004 |
| Claude Sonnet 4.6 | $3.00 | $15.00 | $0.30 | ~$0.012 (overkill) |
| Claude Opus 4.7 | $5.00 | $25.00 | $0.50 | ~$0.020 (don't) |

Assumptions: ~2,000 input tokens (system + user) on the first call,
~500 cache-read tokens on subsequent calls within a 5-min cache
window, ~300 output tokens (closure plan with rationale).

A typical drawing has ~3 stubborn layers that exhaust the geometric
ladder → ~$0.01 / drawing of LLM cost. At a $9/mo personal-tier
subscription with 30 drawings/mo, this is ~3% of revenue — well below
any concerning fraction. See `ai-augmented-mode.md` §3 for the full
headroom analysis.

DEBUG mode (`ARCH_LW_DEBUG=1`) prints the actual cost of every call
to stderr in the form
`[arch-lw llm] model=claude-haiku-3-5 in=1234 out=156 cache_read=512
cache_write=0 cost=$0.000312`.

## Error handling philosophy

`infer_closing_plan` **never raises** on its public surface. It returns
`None` on every failure mode:

- Gate is closed (`ARCH_LW_LLM_FALLBACK != "1"`)
- `anthropic` package not installed
- `ANTHROPIC_API_KEY` not set
- Empty anchor list
- `client.messages.create` raised
- Response had no parseable `tool_use` block
- Plan failed schema validation (bad confidence, OOB indices, etc.)

The polygonize ladder's `try / except / pass` wrapping turns any
unexpected exception into "skip to the next rung". The unit tests
`test_infer_network_error_returns_none`,
`test_infer_invalid_response_returns_none`, and
`test_sdk_missing_returns_none` enforce these contracts.

## Toggling the rung

| Way | Effect |
|---|---|
| `ARCH_LW_LLM_FALLBACK=1` env var | Gate ON for the duration of the process |
| `arch-lw apply-saas --llm-fallback` | Sets the env var for the CLI run |
| `arch-lw poche --llm-fallback` | Same, on the standalone poche command |
| `ANTHROPIC_API_KEY=...` env var | Required when the gate is on |
| `ARCH_LW_LLM_MODEL=claude-haiku-4-5` | Override default `claude-haiku-3-5` |
| `ARCH_LW_DEBUG=1` env var | Print per-call cost to stderr |

The CLI flag is the recommended path; setting the env var directly
is for batch / cron contexts.

## Optional dependency

The `anthropic` SDK is in `[project.optional-dependencies]` as
`llm = ["anthropic>=0.40"]`. Install with:

```sh
pip install -e .[llm]
```

When the SDK is missing AND the gate is on, the rung returns `None`
with a one-line stderr warning in DEBUG mode (silent otherwise) — see
`test_sdk_missing_returns_none`.

## Expected behavior on the three stubborn cut layers

Per the analysis in `stubborn-layers-deep-dive.md` §5:

| Layer | Expected outcome with the LLM rung enabled |
|---|---|
| `23_WINDOW_FRAMES_REMAP` | **Likely fixes.** The LLM sees `WINDOW_FRAMES` and a list of stub endpoints, infers each stub should close into a small frame rectangle. A small-LLM strength. |
| `26_CLT_GAP_ROOF_CAP` | **Already fixed by alpha_shape (rung 4) in v0.5.2.** The LLM rung is a backstop if alpha_shape fails on a future variant. |
| `11_CU_CORR_SOLID_OPAQUE` | **Likely fixes.** "CORR" (corrugated) plus a long zigzag of endpoints → infers single-polygon topology with bridges along the bottom edge connecting alternating corrugation troughs. Backtracking bridger may also fix this; whichever wins first stops the ladder. |

## Open questions / future work

1. **Empirical confidence floor.** The hard-coded confidence floor in
   `_validate_plan_schema` is permissive — any plan with
   `confidence ∈ [0, 1]` passes. We may want to refuse plans below
   ~0.6 once we have regression data on real Haiku outputs.
2. **Multimodal input.** Could send a rendered PNG of the layer to a
   vision-capable model (Sonnet 4.6, Gemini 2.5 Flash) instead of /
   in addition to the endpoint list. Would unlock Use Case #5 in
   `ai-augmented-mode.md`. Park for Phase G.
3. **Regression suite.** `ai-augmented-mode.md` §6 calls for a
   30-prompt regression suite with golden polygon counts before
   shipping default-on. Not built yet — the v0.5.2 rung is opt-in
   only, so quality gates can develop alongside it.
4. **Migrate to Opus 4.7 / Haiku 4.5 default.** Haiku 3.5 is older;
   when an Opus 4.7-tier Haiku ships and pricing settles, re-run
   the cost analysis and bump `DEFAULT_MODEL`.

## Cross-references

- Algorithm proposal: `docs/research/stubborn-layers-deep-dive.md` §5
- Anthropic integration recommendation:
  `docs/research/ai-augmented-mode.md` §4–6
- Privacy stance: `docs/research/saas-privacy.md` §Subprocessors
- Roadmap context: `docs/ROADMAP.md` Phase F7 / G4
- POSTMORTEM Attempt 5: the three stubborn cut layers context
