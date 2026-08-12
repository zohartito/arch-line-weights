# Visual Judgment Rubric — Architectural Line-Weight Hierarchy + Poché

This is the committed, anonymized judgment standard for `arch-lw` output. It is
distilled from a reference corpus of ~400 student architecture drawings and the
defect analysis of real Rhino-export runs. The deterministic `scripts/visual_judge.py`
enforces the measurable parts (§ *Scored axes* below); the opt-in vision judge
`scripts/visual_judge_llm.py` reads this whole file to judge the perceptual parts.

The strong drawings in the corpus converge on one grammar. Where a board is weak it
is almost always because it broke one of these rules.

---

## 1. The weight ramp — cut > profile/structure > texture > annotation

A consistent 3–4 tier ladder governs a good sheet. Target ratios:

| Tier | What it is | Relative weight |
|---|---|---|
| 1 — heaviest | Section-cut profile + cut-mass poché; the continuous ground datum | 1.0 |
| 2 — medium | Elevational / "beyond" edges, structural members, stairs, furniture-in-plan | ~0.5 |
| 3 — hairline | Surface texture (floor grids, coursing, tile joints, soil stipple), keynote leaders, dashed hidden/setback lines | ~0.25 |
| 4 — lightest | Dimension strings, extension lines, level datums (often tinted so they never read as building line) | thinnest |

The genuine step is roughly **3 : 2 : 1** (cut : profile : texture). A neutral ground
plus a real 3:2:1 step separates strong boards from weak ones far more than color or
rendering does. Observed cut:texture ratios run **2.5–3×** in wall sections, rising to
**5–10×** when black is reserved for a single sectional cut.

**Rule:** cut : texture ratio should be **≥ 3 : 1**. Below that the sheet slides toward
weight-flatness (§4).

## 2. The cut owns the darkest value — and nothing else may reach it

The single most repeated rule in the corpus. Black (or the most-saturated fill) is
**reserved for what the section plane slices**; everything not cut steps down hard:

- **black** = cut
- **grey** = solid-but-uncut (structure seen but not sliced)
- **hairline** = organizing / layout line
- **dashed** = subordinate (hidden, setback)
- **tone / hatch** = material

Figure-ground should read *before a single label is examined*. Section depth comes from
**value**, not from cast shadow. Projected fixtures, connectors, and "beyond" geometry
must **not** reach cut weight or cut value — if a projected fixture renders as dark as
the cut, that is a defect ("why are these squares so thick").

## 3. Material by hatch at constant weight — not by weight

Material identity is carried by **hatch pattern / density while line weight stays fixed**:
aggregate stipple, insulation scallop or cross-hatch, gravel dot, brick coursing, wood
grain, geological strata, perforated-panel dot-grids. Two panels of different material
should differ by *hatch*, not by stroke weight.

## 4. Annotation and scale figures stay subordinate

- Dimension lines, leaders, and level datums are the **thinnest** strokes, frequently
  **tinted** so they never read as building line.
- Scale figures are **flat single-color silhouettes, outline-only, no internal detail** —
  a demonstration that color is not hierarchy; weight and fill are. Chroma is rationed,
  often to a single accent used only on the figure.
- Glazing is a single hairline (optionally a faint wash).

---

## Named failure modes (what "doesn't read good" means)

- **Weight-flatness** — the universal failure. A uniform hairline where cut floor plates
  read at the same weight as the elevation behind them, so nothing anchors the eye. A clean
  whole-building cut drawn at one flat weight with zero poché is *the exact drawing this tool
  exists to correct*.
- **False poché** — solid black boxes that are **not** the cut: a projected member or a
  fragment closed into a filled polygon and left floating in whitespace, outside the cut
  envelope. Black must mean "sliced here", nowhere else.
- **Fragmented cut band** — a slender cut wall that breaks into disconnected chains and
  reads as **white dashes** instead of one continuous solid band. The cut is the continuous
  ground datum; it must not stutter.
- **Fixtures reaching cut value** — projected connectors / fixtures promoted to cut weight
  or cut darkness, competing with the true cut for the eye.
- **Hue-as-hierarchy** — using color instead of weight/value to rank; it collapses in
  greyscale.
- **Cast-shadow blobs** faking depth instead of earning it through cut poché + receding line.

---

## Scored axes (deterministic — `scripts/visual_judge.py`)

Each maps a rubric rule to a machine-checkable metric with a fixed threshold:

| Axis | Rubric rule | Metric | Verdict = review when |
|---|---|---|---|
| `false_poche` | §2 (cut owns black), "false poché" | fraction of solid-fill mass floating in whitespace | `> 0.05` |
| `band_continuity` | §1 continuous datum, "fragmented cut band" | worst along-axis gap fraction of a heavy band | `> 0.20` |
| `hierarchy_spread` | §1 the weight ramp | cut : texture stroke-weight ratio | `< 3.0` |
| `fixture_weight` | §2, "fixtures reaching cut value" | mean darkness of projected-fixture regions (needs report) | `> 0.55` |

Any axis over threshold → overall verdict `review`, with a rubric-cited reason. The
vision judge adds the perceptual rules (§2 gestalt, §3 material-by-hatch, tonal recede of
"beyond" geometry) that pixels alone cannot gate.

---

## Stylistic forks (legitimate choices — do NOT penalize)

These are real house-style choices, not right-vs-wrong; the judge must not fail a drawing
merely for picking one:

- **Poché fill style:** full solid-black · color-coded solid · hatched · outline (white-filled)
  · translucent-grey.
- **Black budget:** reserve black strictly for the cut · never use black, carry the cut with
  saturation/tone (only on a controlled ground).
- **Ground polarity:** white/neutral ground · saturated or negative dark ground (the same ramp,
  reversed value).
- **Isolation vs even ramp:** blacken exactly one system to establish figure · a smooth
  multi-tier ramp where no single system dominates.
- **Material-system color coding** vs monochrome material-by-hatch.
- **Datum device:** heavy continuous ground line with half-black level markers · a flat
  color-tint wash splitting the sheet at grade.
