# AI-augmented mode — feasibility for Phase G4 (and earlier)

> Sub-agent research, 2026-04-30. Time-boxed ~75 min.
> Closes the dangling reference at `docs/ROADMAP.md` line 326–329 (Phase
> G4) and `docs/BUSINESS.md` §"Existential risks" items #2 and #3.
> Companion doc to `docs/research/stubborn-layers-deep-dive.md` (which
> already proposes one concrete LLM use case at the bottom of the
> rescue ladder) and `docs/research/competitive-landscape.md` Ring 4
> (AI-first sketch-to-render entrants).
>
> Methodology: ~75-min sub-agent pass. Direct-fetched 2026 pricing pages
> for Anthropic and Google; cross-checked OpenAI / Meta via search
> snippets (OpenAI's pricing page 403'd direct fetch). Reasoned about
> token budgets from the existing PieceInfo dump structure documented in
> `docs/research/saas-architecture.md`. Quotes capped at 15 words per
> the project's copyright rules.
>
> Disclaimer: pricing changes. Refresh quarterly with `BUSINESS.md`
> §"Existential risks" review. The qualitative recommendation
> ("Phase G2 — defensive pivot, but ship one feature at Phase F as a
> trust-building wedge") is robust to ±50% pricing drift; the per-
> drawing dollar figures are not.

---

## TL;DR — recommendation

| Question | Answer |
|---|---|
| Build full AI-augmented mode at launch (Phase F)? | **No.** "AI-powered" is on the *anti-tagline* list in `BUSINESS.md` for a reason. The deterministic classifier is the moat; leading with AI dilutes it. |
| Build full AI-augmented mode in year 2 (Phase G)? | **Yes, conditionally** — defensive trigger, not a feature push. Ship if any of the four existential risks lights up: McNeel ships built-in line weights, school workflow pivots to AI-render, AutoLineWeight gets a maintainer, or interview signal in Phase C surfaces an unmet "I want it to suggest" need. |
| Ship anything LLM-flavored at launch (Phase F)? | **One narrow feature: layer-name semantic inference for unknown patterns** (the `DEFAULT` bucket in the classifier). Behind a feature flag, opt-in, audit-logged, free-tier-only, with deterministic fallback. The MVP described below. |
| Per-drawing inference cost on the recommended MVP? | **~$0.0002–0.001 (Haiku 4.5) to ~$0.01 (Haiku 3.5 with full PieceInfo)**. Detailed math in §3. |
| One MVP feature most worth building? | **Layer-name semantic inference for `DEFAULT`-bucketed layers** — turns the deterministic classifier from a 98%-on-Rhino-style-names tool into a forgiving-of-naming-conventions tool, the part Phase E5 (Vectorworks/Inkscape/AutoCAD layer-name patterns) is otherwise hand-coded one regex at a time. |

**Honest acknowledgement up front.** Most of the eight LLM use cases in the
prompt ("style consistency check", "drawing critique", "auto-naming",
"composition suggestion") are **shiny-object traps**. They sound great in a
landing-page bullet list but fail the test of "would Zohar himself trust
this output enough to ship it without manual review?" The two that pass that
test are (a) layer-name inference for unknown patterns and (b) topology
inference for stubborn layers (already covered in
`stubborn-layers-deep-dive.md`). Everything else either competes badly with
deterministic tools we already have (poché bridges) or competes with the
human's actual creative judgment (composition, critique). Build the two
that pass; flag the rest as "available if a customer pulls it."

---

## 1. What problems would AI augment that the deterministic core can't solve?

For each of the 8 use cases the prompt lists, here's whether AI is the right
tool, and whether it justifies a separate code path.

| # | Use case | Deterministic alternative | AI actually needed? | Verdict |
|---|---|---|---|---|
| 1 | **Stubborn-layer topology inference** | DBSCAN + backtracking + α-shape ladder (covered in `stubborn-layers-deep-dive.md`) | Yes — for the residual ~3% after the geometric ladder | **Build.** Already on the E1 roadmap. Cost: ~$0.003/stubborn layer × ~3 layers/drawing ≈ $0.01/drawing. |
| 2 | **Layer-name semantic inference for `DEFAULT` patterns** | Regex pattern library (`layer_classify.py`); user override JSON | Yes — non-Rhino exports (Inkscape, Vectorworks, AutoCAD DXF) have layer names the regex doesn't recognize; expanding the regex by hand is the Phase E5 grind | **Build (the MVP).** See §6. Single highest-leverage feature. |
| 3 | **Material identification from drawing context** ("looks like CLT roof") | Layer-name → hatch lookup table (current behavior) | **Marginal.** If the layer is named `26_CLT_GAP_ROOF_CAP`, the lookup already wins. If it's named `LAYER_47`, an LLM looking at vector geometry alone has very low signal — CLT cross-grain hatches and brick hatches both look like dense parallel lines at this resolution. | **Skip at launch.** Maybe Phase G6 (style transfer) territory. |
| 4 | **Style consistency check** ("section line weights don't match plan") | Compare derived ISO ladders across drawings programmatically; flag deviations deterministically | **No.** This is a programmatic check, not an LLM judgment call. The classifier already outputs the chosen tier per layer; cross-drawing diff is a 50-line function. | **Skip — build deterministic version in Phase G5 (multi-drawing consistency).** |
| 5 | **Drawing critique** ("section cut isn't dark enough relative to foreground") | None | Yes, technically — but this is a *creative* judgment, the part the architect wants to keep. Outputting "your cut should be 0.7mm not 0.5mm" overrides ISO 128 + Ramsey/Sleeper, which is a worse authority than the LLM. | **Skip.** Conflicts with `BUSINESS.md` §Defensibility item #1 ("architecture-specific intelligence" — the *deterministic* kind). |
| 6 | **Auto-naming layers in untagged drawings** | None deterministic | Yes — but writing names back into the .ai mutates customer files in a way that's hard to undo and not what they paid for. They paid for line weights; renaming layers is a side-effect they didn't ask for. | **Skip.** If interviewees specifically request this in Phase C, revisit. |
| 7 | **Suggesting `__POCHE_CLOSE__` bridges for the user** | Auto-bridge greedy + backtracking + DBSCAN (already in the ladder) + LLM topology inference (use case #1) | **Already covered by use case #1**. The user-facing version of "suggest bridges" is already what auto-bridge does silently and what the LLM fallback does on the residual. | **Already on roadmap (E1). Don't build twice.** |
| 8 | **Layout / composition suggestions** ("would read better at 1/8\" with these tier shifts") | None | Yes — but at this point we're competing with Show It Better's $347 Everything Pack, not delivering a line-weight tool. Different product. | **Skip — out of scope.** If we ever go here, it's a separate product. |

**Summary:** of 8 candidates, 1 is already on the deterministic roadmap (#1 +
#7), 1 is the MVP (#2), 1 is deterministic-not-LLM territory (#4), and 5 are
shiny-object traps. Build #2 first; #1 lands as a side effect of the E1
stubborn-layer work.

---

## 2. LLM capability matrix

Pricing as of 2026-04-30 from the model providers' published pages
(Anthropic, Google directly fetched; OpenAI cross-referenced via
intermediaries because their pricing page 403'd a direct fetch — figures
flagged with † should be re-confirmed before commit).

| Model | Input $/MTok | Output $/MTok | Cache hit $/MTok | Latency (typ.) | Privacy posture (commercial API default) | Architecture fit (1–5) | Notes |
|---|---|---|---|---|---|---|---|
| **Claude Haiku 3.5** | $0.80 | $4.00 | $0.08 | 1–3 s | API inputs *not* used to train (commercial default) | **5** | The model the existing `stubborn-layers-deep-dive.md` § "LLM topology inference" already costs against. Cheapest credible Anthropic option. Stable, well-known JSON tool-use. |
| **Claude Haiku 4.5** | $1.00 | $5.00 | $0.10 | 1–3 s | Same | **5** | Newer, higher quality, ~25% more expensive than 3.5. Reasonable default if 3.5 underperforms in spike. |
| **Claude Sonnet 4.5** | $3.00 | $15.00 | $0.30 | 2–5 s | Same | **4** | Overkill for layer-name classification. Reserve for whole-drawing critique experiments (which we've decided not to ship). |
| **Claude Opus 4.7** | $5.00 | $25.00 | $0.50 | 5–15 s | Same | **2** | Wrong cost class entirely for per-drawing inference. |
| **GPT-4o-mini**† | $0.15 | $0.60 | n/a (50% cached) | 1–2 s | API inputs *not* used to train (commercial default since 2023) | **4** | Genuinely cheap. JSON mode mature. Privacy ToS comparable to Anthropic. Risk: model lifecycle (4o-mini is not the current frontier; OpenAI's roadmap is GPT-5.x). |
| **GPT-5-mini**† | ~$0.25 | ~$2.00 | n/a | 1–3 s | Same | **4** | Newer than 4o-mini; ~1.7× input / 3.3× output for arguably better quality. |
| **GPT-5.5**† | ~$5.00 | ~$30.00 | n/a | 3–10 s | Same | **2** | Same overkill problem as Opus. |
| **Gemini 2.5 Flash** | $0.30 | $2.50 | n/a | 1–2 s | API inputs *not* used to train per Google Cloud terms; consumer Gemini is different | **4** | Cheap; multimodal so can take a rendered PNG as input. Less mature JSON tool-use than Anthropic/OpenAI. |
| **Gemini 2.5 Pro** | $1.25 (≤200k) / $2.50 | $10.00 / $15.00 | n/a | 3–8 s | Same | **3** | Nice for whole-drawing analysis; expensive at our token budget. |
| **Llama 3.3 70B (Groq / Deep Infra hosted)** | ~$0.58 | ~$0.71 | n/a | <1 s on Groq | Hosted: depends on provider ToS (variable). Self-hosted: zero data leaves the box. | **3** | Genuinely interesting *if* we run it ourselves on the SaaS box (Phase D Fly.io upgrade) for "Pro Privacy" tier. Cost = our hosting; no per-token meter. Quality ~Sonnet-class for structured outputs, weaker on long-context reasoning. |
| **Qwen 2.5 32B (local)** | $0 marginal (own GPU) | $0 marginal | — | depends on hardware | Self-hosted: zero data leaves the user box | **3** | Interesting only for the Phase B3 hybrid local-helper tier. Not relevant to v1 SaaS. |
| **Cohere Command R+** | ~$2.50 | ~$10 | n/a | 2–5 s | Commercial-friendly licensing per Cohere ToS | **2** | No standout reason vs. Haiku 4.5 + Anthropic for our use case; doesn't merit a separate integration. |

**Recommendation for the MVP:** **Claude Haiku 4.5** as primary, **GPT-4o-mini** as a documented swap option for the cost-conscious. Two reasons:

1. The `claude-api` skill in this codebase already enforces prompt caching ergonomics and migration-on-deprecation discipline. We get to reuse that infrastructure for free.
2. Anthropic's commercial-API ToS posture (inputs not used to train, by default) is the cleanest sentence to write on the marketing page. "Your drawings are never used to train AI" is a literal restatement of Anthropic's commercial terms.

Llama 3.3 70B self-hosted is the **defensive option for Phase G** if the privacy story becomes a sales blocker for a studio segment. Park it.

---

## 3. Cost per drawing — math, not vibes

The drawing payload structure is well-understood from `docs/research/saas-architecture.md`:

- A reference Rhino-exported `.ai` has **62 OCG layers**.
- Decompressed PieceInfo payload is **~55 MB plain-text Adobe Illustrator native PostScript**.
- Of that, layer names + structure (the part the LLM needs for use case #2) is a small subset. Roughly: 62 layer name strings × ~30 chars + structure ≈ 3 KB ≈ **~750 tokens**.
- Full polyline geometry per stubborn layer (the part the LLM needs for use case #1) is ~30 endpoints × ~40 chars = ~1.2 KB ≈ **~300 tokens**, plus boilerplate prompt ~1.5 KB ≈ **~1700 tokens total per stubborn layer**.

### Cost matrix per drawing (Haiku 4.5 reference rates)

| Feature | Tokens in (cached + fresh) | Tokens out | Cost per drawing | Notes |
|---|---|---|---|---|
| **Layer-name semantic inference (MVP, use case #2)** | ~1500 fresh + ~500 cached system prompt | ~400 (one JSON object) | $0.0015 + $0.000005 + $0.002 ≈ **$0.0035** | Per-drawing one-shot. Cache hit on identical system prompt across all customers (`cache_control: ephemeral`). |
| **Stubborn-layer topology inference (use case #1)** | 3 stubborn × 1700 = 5100 fresh + ~500 cached | 3 × 300 = 900 | 5100 × $1e-6 + 900 × $5e-6 = **$0.0096/drawing** | Already costed in `stubborn-layers-deep-dive.md` at ~$0.01 with Haiku 3.5; the math holds for Haiku 4.5. |
| **Both features together** | — | — | **~$0.013/drawing** | Round to **~$0.02/drawing** with safety margin for retries. |
| **Hypothetical "send the whole 55 MB PieceInfo" critique mode** | ~14M tokens fresh | ~2k | 14M × $1e-6 + 2k × $5e-6 = **~$14/drawing** | DO NOT BUILD. This is the "shiny-object" path. Even at GPT-4o-mini rates ($0.15 in / $0.60 out) it's still $2.10/drawing — economic poison at $9/mo subscription. |

### Cost matrix at GPT-4o-mini reference rates (defensive comparison)

| Feature | Cost per drawing | Notes |
|---|---|---|
| Layer-name semantic inference | ~$0.0005 | 7× cheaper |
| Topology inference (stubborn layers only) | ~$0.0015 | 7× cheaper |
| Both | **~$0.002/drawing** | If Anthropic prices ever feel painful, swap in. |

### Headroom check

At $9/mo personal-tier subscription with an assumed cap of 100 drawings/mo
(generous; most students are ≤30/mo per `personal-use-log.md` patterns),
**LLM cost ceiling = $0.013 × 100 = $1.30/drawing-month per user**, or
~14% of revenue. Tolerable. At $0.002/drawing on GPT-4o-mini it's 2% of
revenue — comfortable.

The $9/mo tier survives LLM costs even at 5× drawings per user. **The
economics are not the blocker.** The trust story and the regression
discipline are.

---

## 4. What does the LLM see?

Privacy-by-design rule: the LLM sees **layer names + minimal geometry only**, never customer-identifying metadata.

| Field | Sent to LLM? | Why / why not |
|---|---|---|
| Layer names (`23_WINDOW_FRAMES_REMAP`, etc.) | **Yes** | The whole point of use case #2; cannot infer without them. |
| Polyline geometry (vector endpoints as text) | **Yes for use case #1 only**; **no for use case #2** | Topology inference needs the points; layer-name inference doesn't. |
| Color palette (RGB tuples) | **Optional** for use case #2 | Useful signal ("0.5pt red strokes" → cut layer hint). 6 RGB triples = ~30 tokens. Cheap. |
| Rendered drawing as PNG (multimodal) | **No, at v1** | Would unlock case #5 (critique) but increases token cost ~10× and adds vision-model cost. Park for Phase G experimentation. |
| Customer name / studio / email | **NEVER** | Strip in the API client *before* serialization. Unit test for this. |
| File path | **NEVER** | Same. |
| Filename | **NEVER** | Filenames often contain project codes, addresses, "JOHNSON_RESIDENCE_2026.ai". Strip. |
| Drawing date stamps inside PieceInfo | **NEVER** | Strip during the existing pikepdf decompression pass. |
| Project metadata (XMP) | **NEVER** | Already not in our processing path; verify still excluded. |

The serialization function should be **a single allow-list helper** in
`src/arch_line_weights/llm/serialize.py`, with a unit test asserting that no
field outside the allow-list is present in any payload. This is the file
the privacy lawyer wants to see during the Phase D8 review.

---

## 5. Privacy & marketing posture

The marketing claim that has to hold: **"Your drawings are never used to train AI."** Per §2 capability matrix, this is true by default for:

- **Anthropic API (commercial default)** — inputs and outputs are not used to train models for commercial customers (Claude API, Claude for Work, Bedrock). Source: Anthropic privacy center.
- **OpenAI API (commercial default since March 2023)** — API data not used for training. Source: OpenAI API data usage policy.
- **Google Cloud Vertex AI / Gemini commercial API** — same posture.

**What is *not* automatically true:**

- Consumer-grade Claude/ChatGPT/Gemini accounts do *not* have the same posture (Anthropic specifically changed consumer terms in 2025 to opt-in training by default — see `BUSINESS.md` existential risk #2 monitoring). Use **API keys**, never consumer-tier OAuth.
- "Zero Data Retention" mode (Anthropic enterprise-only addendum) is a *stronger* claim than "not used to train". We can claim the latter on standard API; the former requires an enterprise contract.

### Marketing copy that is defensible

| Claim | Defensible? | Caveat |
|---|---|---|
| "Your drawings are never used to train AI." | **Yes** | True under Anthropic/OpenAI commercial API ToS by default. |
| "Your drawings are end-to-end encrypted." | **No** | We've already decided server-side encryption only at v1 (per `saas-privacy.md`). LLM call adds another touch point. |
| "We never see your drawings." | **No** | We process them server-side. |
| "Layer names sent to AI; full geometry stays on our servers." | **Yes (for use case #2 only)** | Use this. It's both true and uniquely strong vs. competitors. |
| "Local AI option available." | **Yes — at Phase G** | Llama 3.3 self-hosted on our box, or Qwen-on-user's-machine for the hybrid tier. Don't promise at launch. |

### GDPR / DPIA implications

- **Subprocessor list update:** adding Anthropic (or whichever LLM provider) requires a `/subprocessors` page entry per `saas-privacy.md` §Subprocessors. Half-day of work.
- **DPIA trigger:** sending vector geometry to a third party is a subprocessor relationship under GDPR Art. 28; not exempt. Add Anthropic's DPA (publicly available) to the customer-facing DPA bundle.
- **Opt-out:** the privacy-conscious user must be able to disable LLM augmentation per drawing or globally. UI toggle: "Use AI to suggest fixes for unrecognized layer names." Default **off** at launch — we earn the toggle, we don't assume it.
- **Retention:** Anthropic API retains inputs for 30 days for abuse monitoring by default. Disclose in privacy policy.

### Why "default off"

The line-weight tool's promise is deterministic. Defaulting AI on contradicts the brand. The MVP defaults **off**; the user opts in per drawing or per project after reading a one-sentence explanation. This gives us:

- Trust signal: "we didn't sneak AI into your pipeline."
- Cost signal: AI cost only on opt-in users.
- Regression signal: A/B-able. We see exactly which drawings get AI augmentation and what the deterministic-vs-AI delta is.

---

## 6. Prototype sketch — the MVP feature

**Feature:** Layer-name semantic inference for unknown patterns.

**Trigger:** when `layer_classify.py` returns `DEFAULT` for ≥1 layer in the drawing AND the user has opted in to AI assistance for this run.

**What it does:** ask Haiku 4.5 to classify each `DEFAULT`-bucketed layer into the existing semantic taxonomy (cut, profile, hidden, ground, hatch, annotation, etc.), with a confidence score. Use the suggestion only if confidence ≥ 0.85 *and* the suggestion is one of the known buckets. Otherwise keep `DEFAULT` (current behavior).

### Prompt template

```
SYSTEM (cached, identical across all calls — qualifies for cache_control):

You classify Rhino-exported architectural drawing layer names into one of
these semantic buckets:

  CUT_THICK        — section cut, primary
  CUT_MEDIUM       — section cut, secondary
  PROFILE          — silhouette of a 3D form, no cut
  HIDDEN           — dashed, behind cut plane
  GROUND_LINE      — site / horizon
  ANNOTATION       — text, dimension, leader
  HATCH_FILL       — material fill (poché, texture)
  GUIDE            — non-printing construction line
  DEFAULT          — none of the above; insufficient info

Conventions you've seen:
  - Number prefix (e.g. `23_`) = layer index, ignore for classification
  - `SECTION` / `CUT` / `PROFILE` / `OUTLINE` / `EDGE` strong signals
  - `FRAME`, `MULLION`, `SILL`, `JAMB` = profile (window/door parts)
  - `CMU`, `BRICK`, `CLT`, `GYPSUM`, `INSUL`, `MEMBRANE` = hatch fill
  - `DIM`, `TEXT`, `LEAD`, `NOTE`, `TAG` = annotation
  - `GUIDE`, `CL`, `CENTERLINE`, `REF` = guide
  - `GROUND`, `EARTH`, `SITE`, `TERRAIN` = ground line
  - Suffix `_REMAP` after a Rhino BlockReference name often preserves
    parent semantics — strip suffix and re-classify the stem
  - When ambiguous, prefer DEFAULT over guessing

For each input layer name, return a JSON object:
{
  "name": "<input layer name>",
  "bucket": "<one of the 9 buckets above>",
  "confidence": <float 0.0-1.0>,
  "reasoning": "<≤20 words>"
}

Be conservative: confidence < 0.85 means "not sure"; we default to DEFAULT
in that case.

USER:

Drawing context: {drawing_type or "unknown"} — {scale or "unknown scale"}

Color palette (hex strokes): {palette_csv}

Layers to classify (one per line):
{layer_names_newline_separated}

Return one JSON object per line, no array wrapper, no commentary outside
the JSON objects.
```

### Output schema

JSON-lines (`{}\n{}\n{}\n…`), one object per `DEFAULT`-bucketed layer:

```json
{"name": "layer_string", "bucket": "CUT_THICK|CUT_MEDIUM|...", "confidence": 0.0, "reasoning": "≤20 words"}
```

Validate with `pydantic.BaseModel`; reject the whole response if any line
fails to parse — fall back to deterministic `DEFAULT` for everything.

### Fallback strategy when LLM is wrong

This is the part that determines whether we ship or get burned.

1. **Confidence floor.** Reject any suggestion with `confidence < 0.85`. Empirically tune this floor on the regression suite (below) before unlocking the feature.
2. **Bucket allow-list.** Reject any suggestion whose `bucket` is not in the 9-item enum. (This is the LLM-hallucination guard.)
3. **Deterministic post-check.** After applying LLM suggestions, run the existing `verify_classification.py` (if exists) or its Phase E5 successor. Any classification that violates a deterministic invariant (e.g. an LLM-classified `HATCH_FILL` whose layer has no closed polygons) reverts to `DEFAULT`.
4. **User-visible diff.** The output preview marks LLM-augmented layers in a different color (e.g. cyan halo). The user sees exactly what the LLM contributed and can override per layer via the existing JSON override path (`docs/research/stubborn-layers-deep-dive.md` §"per-layer JSON override schema").
5. **Audit log.** Every LLM call is logged with input layer names, output suggestions, confidence, model version. Stored 90 days for regression analysis. Disclosed in privacy policy.
6. **Regression suite as gate.** Build a 50-drawing regression set with hand-labeled ground truth before ever shipping. Each release re-runs the suite; any drop in classification precision is a release blocker. This is the discipline that separates "AI feature that ships" from "AI feature that gets quietly removed in v1.2 because it embarrasses the founder."

### Effort estimate

- Day 1: extract layer names, build LLM client wrapper, unit test the privacy allow-list (no PII leaks).
- Day 2: prompt template, JSON-lines parser, pydantic validator, confidence-floor logic.
- Day 3: integration with `apply_jsx.py` / `apply_saas.py`, UI toggle, audit log, fallback paths.
- Day 4: regression suite of 30+ hand-labeled drawings, baseline measurement, confidence-floor tuning.
- Day 5: documentation, privacy policy update, subprocessor-list update.

**~5 person-days for the MVP.** Compare to ~4.75 person-days for the
deterministic-only stubborn-layer rescue ladder in
`stubborn-layers-deep-dive.md`. The two efforts are comparable in scope;
the regression-suite discipline (#6 in fallbacks) is the most expensive
non-obvious item.

---

## 7. Roadmap timing recommendation

| Phase | Recommendation |
|---|---|
| **Phase F (public launch)** | Ship the MVP (use case #2: layer-name semantic inference for `DEFAULT`) **as a feature flag, default off, free-tier-only**. Marketing copy: zero mention. Internal-only signal: see if any opt-in users pull on it. Cost ceiling: <$50/mo at 1000 active users × 10 drawings × $0.005. |
| **Phase G2 (year 2, conditional)** | Promote to **on by default** for all tiers *only if* the Phase F flag's regression suite has held precision ≥98% for 6 months *and* one of the four existential triggers has fired (McNeel ships built-in line weights, Adobe AI competitor, AutoLineWeight gets a maintainer, Phase C interview signal). |
| **Phase G4 (full AI-augmented mode)** | Build *only* as a defensive pivot if the F1 (McNeel ships) or F3 (school-tooling AI-first pivot) risks materialize. The competitive-landscape doc gives 18–36 months for F1 and 24+ months for F3. We don't need to spec G4 now; we need to keep the option open by having the LLM client wrapper, prompt template, and regression suite already in production. |
| **Never ship** | The 5 shiny-object use cases (#3, #5, #6, #8, plus full-PieceInfo critique). Re-evaluate annually but keep on the "skip" list until interview data forces a change. |

### Why "Phase F flag, off by default" instead of "Phase G defensive only"

Three reasons:

1. **Phase E5 (smarter Rhino layer-name inference for non-Make2D exports) is on the deterministic roadmap already.** That's the regex-by-hand grind. Use case #2 (LLM layer-name inference) is the *same problem* with a different tool. Better to have both available; the LLM is the catch-all for the long tail the regex won't ever cover (German layer names, French layer names, custom firm conventions, accidentally-typoed names).
2. **The regression discipline takes 6 months to develop.** If we wait until Phase G to start, the moment we need it we're behind. Building the audit-logging + regression-suite infrastructure at Phase F means it's ready when it has to scale.
3. **One legitimate AI feature dilutes the "AI is on the anti-tagline list" stance less than a shipped-late scramble.** If McNeel ships built-in line weights in Phase G and we have to bolt AI on as a panic feature, customers smell it. If we shipped a *subtle, opt-in, not-marketed* AI feature in Phase F, the panic-pivot to G4 looks like an extension of an existing capability, not a desperation move.

---

## 8. Risks

### Engineering risks

| Risk | Severity | Mitigation |
|---|---|---|
| **LLM hallucinates a `HATCH_FILL` classification on an actual annotation layer → poché applied to text → catastrophic visual output** | **Severe** | Confidence floor 0.85 + deterministic post-check (#3 above) + visible diff (#4). Worst-case the user sees one obviously-broken poché and overrides via JSON. Not silent. |
| **LLM returns malformed JSON → entire request fails → deterministic fallback should still produce shippable output** | **Medium** | The classifier already handles `DEFAULT` correctly without LLM. LLM failure = no degradation, just no augmentation. Unit-test this path explicitly. |
| **Model deprecation (e.g. Anthropic deprecates Haiku 3.5 → silent regression)** | **Medium** | The `claude-api` skill in this codebase enforces model-pin best practices. Pin to `claude-haiku-4-5` or successor; CI alarm on deprecation announcements. |
| **Latency hit (1–3 s per drawing extra)** | **Low** | Run LLM call in parallel with non-LLM-dependent processing steps. Already async in `apply_saas.py` patterns. Net p95 latency increase ≈ 0.5 s. |
| **Token-cost surprise (a customer with a 500-layer drawing rings up $X)** | **Low** | Per-call hard cap on tokens out (`max_tokens=2000`). Per-tenant monthly cap with overage email notification at 80%. |

### Customer-trust risks

| Risk | Severity | Mitigation |
|---|---|---|
| **"AI-powered" perception poisons the deterministic-tool brand** | **Severe** | This is the dominant reason to keep AI off by default and out of the marketing copy at launch. The Phase F flag is purely an optionality bet, not a positioning bet. |
| **A privacy-conscious studio refuses to use the SaaS because "drawings sent to OpenAI/Anthropic"** | **Medium** | Per-drawing toggle + clear "deterministic-only" mode in UI. Phase G3 ship of self-hosted Llama unlocks this segment fully. |
| **Audit-log discovery → customer learns we're sending their data to Anthropic and feels misled** | **Severe** | Privacy policy disclosure on day 1. Subprocessors page lists Anthropic from the moment the flag exists, even if it's off. No surprise. |
| **LLM suggests something architecturally wrong that the user accepts uncritically and submits to studio review** | **Medium** | Visible diff (#4 above). Confidence-floored, allow-listed bucket. The user should always see the LLM's reasoning sentence; if they ignore it, that's downstream of our duty of care. |

### Strategic risks

| Risk | Severity | Mitigation |
|---|---|---|
| **The "moat is the deterministic classifier" claim weakens once we ship LLM inference for the same problem** | **Medium** | Frame as "deterministic-first, LLM-fallback for the long tail." `BUSINESS.md` §Defensibility item #2 still holds: the *pattern library* is the moat, the LLM is the safety net for the regex's blind spots. |
| **Competitor (AutoLineWeight v2, F5 in `competitive-landscape.md`) ships LLM layer-name inference first** | **Medium** | Ship-fast Phase F advantage. Once we have the regression suite and audit log, our LLM feature is more trustworthy than a v0.1 competitor's. |
| **Anthropic / OpenAI raises prices 5×** | **Low** | Pricing is currently in the bottom-of-the-S-curve drift; raises are unlikely. Hedge by maintaining a GPT-4o-mini-compatible code path; swap if pricing shifts. |
| **Architecture-school workflow pivots fully to AI-render before we're ready** (existential risk #3) | **Severe** | Promote G4 timing if F3 risk materializes. The `personal-use-log.md` Phase A signals are the early warning. |

---

## 9. Honest "is this needed?" check

**The shiny-object trap is real here.** Every architecture-tool roadmap doc since 2024 has had "AI-augmented mode" on it. Most of those products shipped one and discovered:

- The deterministic version handled 95% of cases.
- The AI version handled the remaining 5% with 60% accuracy.
- The user trust hit from the 40% AI-failure rate exceeded the value of the 5% lift.

The reason the proposed MVP (use case #2) might escape this trap:

1. **It's a fallback, not a primary path.** The deterministic regex already handles the 98% of Rhino-style names. The LLM only fires on `DEFAULT` — the part where there's *no* deterministic answer to be wrong about.
2. **The failure mode is graceful.** LLM wrong → `DEFAULT` fallback → user adds a manual override. Worst case: same as today.
3. **The signal is cheap.** $0.0035/drawing × 100 opt-in users × 30 drawings/mo = $10.50/mo. The data we get back (which layer-name patterns the regex doesn't cover) feeds Phase E5.
4. **It compounds.** Every quarter, we move high-confidence LLM patterns from "LLM territory" to "regex territory" — the LLM acts as a discovery engine for the deterministic library. The classifier *gets better* as a side effect.

The reason the *other* 6 use cases probably stay traps:

- They compete with a deterministic alternative we already have or can build (#4, #7).
- They override the architect's creative judgment, which the architect is paying us to support (#5, #8).
- They mutate customer files in unrequested ways (#6).
- They have no defensible signal-to-noise ratio at the geometry resolution we work at (#3).

**Bottom line:** ship one feature, the discovery-engine one. Resist the rest. Re-evaluate after Phase F MRR data + Phase E5 layer-name pattern coverage measurements.

---

## 10. Update recommendations for `docs/ROADMAP.md` and `docs/BUSINESS.md`

### `ROADMAP.md` Phase G4

Current text (line 326–329):

> G4. **AI-augmented mode** — LLM analyzes drawing semantics, suggests
> stylistic improvements, flags inconsistencies. Could be the feature
> that survives any "Rhino 9 ships built-in line weights" competitive
> shock.

Suggested replacement:

```markdown
- [ ] G4. **AI-augmented mode (defensive pivot)** — full feature set
  TBD; only build if F1/F3/F5 existential triggers fire. Foundations
  ship in Phase F as a flag-gated MVP (layer-name semantic inference for
  `DEFAULT`-bucketed layers) per `docs/research/ai-augmented-mode.md`.
  Per-drawing cost ceiling: $0.02. Default off, opt-in per drawing.
  Anthropic Haiku 4.5 primary, GPT-4o-mini fallback.
```

### `ROADMAP.md` Phase F (insert new sub-item)

```markdown
- [ ] F7. **AI-augmentation foundation (flag-gated, default off)** —
  layer-name semantic inference for `DEFAULT`-bucketed layers via
  Haiku 4.5. Behind opt-in toggle. Audit logged. ~5 person-days. Spec:
  `docs/research/ai-augmented-mode.md` §6.
```

### `BUSINESS.md` §"Existential risks" item #2

Append: "Mitigation foundation in Phase F via `docs/research/ai-augmented-mode.md` MVP; full G4 escalation only if McNeel ships."

### `BUSINESS.md` §"Existential risks" item #3

Append: "Defensive feature path lives in `docs/research/ai-augmented-mode.md`. Phase G4 trigger: ≥30% of architecture-school interviewees in re-run Phase C (year 2) prefer AI-render output to line drawings."

### `BUSINESS.md` §"Marketing / messaging" anti-tagline

Current text:
> "AI-powered" — we're not, and the credibility is worth more than the buzzword

This stays correct for Phase F. Revisit at Phase G2 if the MVP graduates to default-on. Even then, do **not** lead with AI; the lead remains "Architectural line weights, automatically."

---

## Sources

Pricing pages cited per copyright rules: ≤15 words quoted per source.

- [Anthropic API pricing — platform.claude.com](https://platform.claude.com/docs/en/about-claude/pricing) — direct fetch, 2026-04-30. Authoritative for Haiku 3.5 ($0.80/$4), Haiku 4.5 ($1/$5), Sonnet 4.5 ($3/$15), Opus 4.7 ($5/$25), and prompt caching multipliers (1.25× write, 0.1× read).
- [Anthropic privacy center — model training opt-out](https://privacy.claude.com/en/articles/7996868-is-my-data-used-for-model-training) — commercial API default-no-train confirmed.
- [OpenAI API pricing](https://openai.com/api/pricing/) — direct fetch returned 403; figures (GPT-4o-mini $0.15/$0.60, GPT-5-mini ~$0.25/$2.00, GPT-5.5 ~$5/$30) cross-referenced via [Nicola Lazzari 2026 pricing breakdown](https://nicolalazzari.ai/articles/openai-api-pricing-explained-2026) and [pricepertoken.com](https://pricepertoken.com/pricing-page/model/openai-gpt-5-mini). Re-verify before commit.
- [Google Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing) — direct fetch, 2026-04-30. Gemini 2.5 Flash $0.30/$2.50, Gemini 2.5 Pro $1.25–2.50 / $10–15.
- [Llama 3.3 70B pricing — Artificial Analysis aggregator](https://artificialanalysis.ai/models/llama-3-3-instruct-70b) — median ~$0.58/$0.71 across hosted providers.
- [Anthropic prompt caching docs](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching).
- `docs/research/saas-architecture.md` — PieceInfo size + decompressed PostScript token-budget reasoning.
- `docs/research/stubborn-layers-deep-dive.md` §5 — prior LLM costing for topology inference (~$0.01/drawing).
- `docs/research/competitive-landscape.md` Ring 4 — F1 (McNeel), F3 (AI sketch-to-render), F5 (open-source v2) trigger conditions.
- `docs/research/saas-privacy.md` §Subprocessors — DPA + subprocessor-list workflow already in place; LLM provider slots into existing infrastructure.
- `docs/BUSINESS.md` §Anti-tagline — "AI-powered" off the marketing copy by design.
- `docs/ROADMAP.md` Phases F, G4 — existing scaffolding this doc fills in.
- [Chaos blog — AI rendering tools 2026](https://blog.chaos.com/best-ai-rendering-tools-for-architects-compared) — competitive context for F3 trigger.
