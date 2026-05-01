# Roadmap v3 — SaaS-first, post-pivot (2026-04-30)

> **Status:** v1.0.0 was published to PyPI under MIT for ~15 minutes,
> then yanked. Repo is private. Direction has shifted again — see "What
> changed since v2 of this doc" below. **Subscription web app, not
> one-time CLI binary**, is the v1 paid product.
>
> Supersedes v2 (which assumed CLI-binary + Lemon Squeezy as the launch
> motion). Don't act on v2 instructions; some are still useful, marked
> below.

## What "amazing" actually means (the bar)

The user's stated bar is "amazing and works flawlessly." Translated into
shippable terms, that's:

| Dimension | Bar |
|---|---|
| Cut-layer poché coverage on Rhino + Make2D + Clipping Plane outputs | ≥95% of layers polygonize cleanly without user intervention; the rest fall back gracefully with `__POCHE_CLOSE__` workflow |
| Layer-name semantic classification accuracy | ≥98% on Rhino-style layer names; clean failure mode for unknown patterns |
| Material hatching library | 25+ recipes covering: timber (lumber, glulam, CLT, plywood, OSB), masonry (brick, CMU, stone, terrazzo), concrete (cast, polished, precast), metal (steel, copper, aluminum, perforated), insulation (rigid, batt, mineral wool), roofing (membrane, slate, asphalt), other (gypsum, glass, plastic) |
| Preset coverage | Section, Plan, Elevation, Detail — each with their own ISO-aligned ladder per scale (1/16 → full size) |
| Output quality at print scale (1/4"=1', plotted on 24×36) | Indistinguishable from a human-drafted set graded against ISO 128 + Ramsey/Sleeper |
| Failure modes | Every fallback emits per-layer confidence; UI flags low-confidence work for user review |

**"Flawless" is not the bar.** Software with ≥95% on edge-case-heavy real
inputs *is* professional-grade. Holding for 100% means never shipping.

## Current state (2026-04-30)

### What we have

| Metric | Value |
|---|---|
| Total LOC (src + tests + docs) | ~4,100 |
| Source code (Python) | ~3,300 LOC across 11 modules |
| Tests passing | 26 / 26, ruff clean |
| Documented research transcripts | 10 in `docs/research/` |
| Material hatch recipes | 14 |
| Cut-layer coverage on reference drawing | 18 / 21 (86%) |
| Layer-fidelity preservation | 62 / 62 (100%) on the apply-jsx path |
| Preset families | 1 generic + per-scale offsets (sections only) |
| Rhino integrations | 3 scaffolds (GhPython component, Eto toolbar, pre-export tagger) |
| Visual preview | PyMuPDF default + Ghostscript fallback |
| MkDocs site | Built, but offline (private repo on GH free plan = no Pages) |

### What works (kept, will not regress)

1. **PDF stream rewrite for stroke widths** — `arch_line_weights.apply`
   path injects `<width> w` before stroke ops, color-keyed by recent RG.
   Fast (110 s on 340 K strokes). Use case: when layer fidelity is
   expendable.
2. **Layer-preserving JSX apply** — `apply_jsx.py` walks each leaf
   layer in Illustrator, classifies semantically, sets stroke weight per
   `pathItem`. 11 minutes for 340 K strokes, 0 layer loss. **The default
   path.**
3. **Two-stage poché pipeline** — JSX dump anchors → Python shapely
   linemerge+polygonize+fallback ladder → JSX apply with baked
   coordinates. 86% layer success on reference drawing.
4. **Auto-bridge inference** — `bridge.py` greedy nearest-endpoint
   pairing with STRtree. Rescues 4 additional layers (14 → 18 / 21).
5. **Material hatch engine** — 14 recipes (parallel, crosshatch,
   poisson-disk, sine-zigzag, brick stretcher-bond, CLT cross-grain).
   Bridson sampling capped to avoid pathological inputs.
6. **ISO 128 standards-aligned tier presets** — `--scale` and
   `--for-print` flags do the right thing for plotted output.
7. **Side-by-side / diff preview** — `preview.py` produces before-after
   PNGs at any DPI. PyMuPDF default; Ghostscript fallback for sub-0.25pt
   stroke fidelity.
8. **`maximumUndoDepth=1` ExtendScript pattern** — turns exponential
   bulk-edit time into linear time. Restored at end-of-script.
9. **POSTMORTEM-driven engineering** — every failed approach documented
   in `docs/POSTMORTEM.md`. 7 attempts logged. Future-us doesn't repeat
   them.

### What does NOT yet work (known limitations)

1. **3 stubborn cut layers** on the reference drawing —
   - `23_WINDOW_FRAMES_REMAP` — too few points; concave_hull degenerate
   - `26_CLT_GAP_ROOF_CAP` — disconnected segments, no nearest-pair under threshold
   - `11_CU_CORR_SOLID_OPAQUE` — endpoint clusters fool the bridger
2. **Plan / elevation / detail presets** — currently share the section
   ISO ladder. Should differ per drawing type.
3. **Non-Make2D vector sources** — Inkscape, Vectorworks, AutoCAD DXF —
   classifier doesn't recognize their layer-name conventions.
4. **Batch mode** — no "drag a folder" UX. One drawing per CLI invoke.
5. **Material library** — 14 recipes; the "amazing" bar wants 25+.
6. **No headless / no-Illustrator mode** — apply step requires
   Illustrator on the user's machine. **This is the fundamental blocker
   for SaaS web app.** See Phase B below.
7. **No license-key infrastructure** — placeholder only.
8. **No update server** — no auto-update for a future binary path.

### What we tried that did NOT work (reference: `docs/POSTMORTEM.md`)

- Strip `/PieceInfo` to force PDF parsing → flattens 62 layers to 1
- Naive Illustrator `app.executeMenuCommand("join")` → topology-blind,
  produces tangled self-intersecting blob
- pikepdf-only OCG-aware stream rewrite → format-mismatch bug, no segments
  collected, hours of debugging
- `snap()` pre-pass at 0.5pt → over-merges dense cladding layers
- `concave_hull` as a default → lossy lumpy polygons; only acceptable as
  flagged fallback
- MIT-licensing v1.0.0 before deciding the business model →
  irrevocable for that snapshot, had to yank
- Going private + auto-deploying docs → Pages 404 same day (free plan
  doesn't serve private-repo Pages)

## What changed since v2 of this doc

| | v2 (2026-04-30 morning) | v3 (this doc) |
|---|---|---|
| Public posture | Private until commercial decision | Private until product is "amazing" |
| Primary product | CLI binary, signed, distributed via Lemon Squeezy | **SaaS web app, monthly subscription** |
| Distribution | Phase D = binary launch | **Phase D = web app MVP**; binary launch deferred or skipped |
| Pricing model | One-time tiers ($29 / $79 / $249/yr) | **Monthly sub + annual sub for studios** |
| Critical-path engineering | Polish + signing infra | **Headless, Illustrator-less .ai output** (or graceful PDF-only fallback) |
| Launch trigger | First Phase C interviews → first sale | **Personal validation (Phase A) + feasibility gate (Phase B) + private beta (Phase E)**; public launch later |

The v2 phase-letters (A–G) are kept for continuity, but Phase B and D
now mean different things. The work in `docs/research/binary-distribution.md`
is **not wasted** — keep it for an eventual paid-CLI complementary
distribution channel after the web app proves out (likely Phase G2).

## Phases A–G (v3)

### Phase A — Personal use 🚧 (now → end of semester)

**Goal: prove the tool works on real drawings beyond the reference one,
generate portfolio assets, build organic demand signals.**

- [ ] A1. Use `arch-lw apply-jsx --poche` on every remaining ARCH 202B +
  ARCH 211 drawing this term
- [ ] A2. Build a portfolio with HIERARCHY.ai + POCHE.ai + diff
  preview outputs
- [ ] A3. Show classmates the result without explaining the tool — gauge
  organic "what'd you use?" reactions. **Target: 5+ unprompted asks**
- [ ] A4. Track and fix per-drawing manual interventions; that's the
  "remaining work" Phase E targets
- [ ] A5. Document each new drawing's outcome in
  `docs/research/personal-use-log.md` (new) — layer count, success
  rate, manual fixes, user-facing time saved
- [ ] A6. Capture 3+ before/after pairs at print resolution as future
  marketing assets

**Decision gate:** is the tool good enough that *Zohar* prefers it to
manual work? If no, fix the tool. If yes → advance to Phase B.

### Phase B — SaaS feasibility ✅ RESOLVED 2026-04-30

**Goal: answer the make-or-break question. Can we produce
shippable-quality output without Illustrator on the user's machine?**

**ANSWER: YES.** Wave 1 sub-agent spike proved pure-pikepdf modification
of `/PieceInfo /Illustrator /Private` works end-to-end on the reference
drawing.

Key findings (full report: [`docs/research/saas-architecture.md`](research/saas-architecture.md)):

- The 305 `/AIPrivateData` streams concatenate into a 20-byte ASCII
  prefix `%AI24_ZStandard_Data` + Zstandard-compressed payload.
- Decompressed payload is ~55 MB of **plain-text Adobe Illustrator native
  PostScript** — same publicly-documented AI3-AI8 syntax, just zstd-wrapped.
- Round-trip null edit: byte-perfect, OCG count 62→62, opens cleanly.
- Stroke color modification: `(1 0 1) XA` → magenta — Illustrator confirmed.
- **Stroke width modification (the project's actual use case)**: `1 w → 5 w`
  in the cut layer — Illustrator confirmed all 172 paths now `width=5`.
- 8 working spike scripts in `scripts/spike/saas-feasibility/`.

**What's open vs closed:**

| Operation | Status |
|---|---|
| Modify existing stroke widths in user-uploaded .ai | ✅ Works |
| Modify existing stroke colors | ✅ Works |
| Inject new filled paths (poché) into existing layer blocks | ✅ Path is clear (1-2 days port from `apply_jsx.py`) |
| Preserve all 62 OCG layers intact | ✅ Works |
| Synthesize a PieceInfo from scratch (greenfield SVG/DXF input) | ❌ Not proven, **not needed** — input is always Rhino-exported .ai |
| Rename layers in panel | ⚠️ Unknown 4th layer-name copy somewhere — **not blocking**, we never rename layers |

**Architectural implications:**

- **B1 (pure pikepdf .ai output) is the SaaS compute path.** No Illustrator
  on server required. Pure Python pipeline, scales horizontally.
- **B2 (PDF-only output) becomes a tier feature, not an architecture
  choice.** Cheap student tier can ship PDF; paid tiers ship editable .ai.
- **B3 (hybrid local-helper) is unnecessary as primary path.** Reserved
  for paranoid-privacy users who want drawings to never leave their
  machine — likely a "Pro Privacy" tier upcharge later, not v1.

**Phase B remaining work:**

- [ ] B6. **Port `apply.py` line-weight logic to operate on decompressed
  AI native PostScript** — regex-replace per-color stroke widths inside
  the AI24 zstd payload. Estimated 4-8 hours.
- [ ] B7. **Port poché pipeline (`poche.py`)** to inject filled `pathItem`
  blocks directly into cut-layer `BeginLayer..LB` envelopes via
  pikepdf+zstd. Estimated 1-2 days.
- [ ] B8. **End-to-end SaaS prototype**: input .ai → pure-Python pipeline →
  modified .ai output, no JSX, no Illustrator. Verify in Illustrator on
  user's machine.
- [ ] B9. **License swap** (deferred until product is ready to publish).
  When prototype works, replace LICENSE with PolyForm Free Trial 1.0.0
  + add commercial EULA. See `docs/research/licensing.md` for the 5-step
  checklist.

**Phase B exit criterion**: B6+B7 prototype produces a modified .ai
that's visually indistinguishable from the current JSX-driven output,
on the reference drawing. Once that's true, advance to Phase D.

### Phase C — Demand validation (parallel with B; 2 weeks)

**Goal: know if the market exists at the SaaS price points before
investing in web infrastructure.**

- [ ] C1. Interview 10 architecture students (script in
  `docs/research/customer-interviews.md`). **Demo with the SaaS frame:
  "you upload, we process, you download" — not "you install a CLI."**
- [ ] C2. Interview 5 sole-practitioner architects
- [ ] C3. Interview 3 small-studio principals (5–20 person offices)
- [ ] C4. Run Van Westendorp PSM on **monthly subscription** prices:
  candidate tiers $9/mo personal, $19/mo personal-pro, $49/mo studio
  (5 seats), $149/mo studio (20 seats). One-time alternative offered as
  comparison anchor.
- [ ] C5. **Decision gate:** if <30% commit at the proposed monthly
  price, reduce by one Fibonacci step ($9 → $5 → free w/ paid
  upgrades). If <30% even there, shelve to a portfolio piece.
- [ ] C6. Update `docs/BUSINESS.md` with concrete segment data, not
  gut numbers.

### Phase D — Web app MVP (month 2–4, after B + C decision gates pass)

**Goal: first private-beta paying customer using a web upload → process
→ download flow.**

- [ ] D1. Domain (`archlineweights.com` or `archlw.app` / `lineweights.app` —
  shorter alt). Use Cloudflare Registrar.
- [ ] D2. **Backend stack**: FastAPI (Python — already our language) on
  Fly.io (closest "deploy a binary, get a URL" experience to Render
  without per-instance pricing). PostgreSQL via Neon free tier
  (auto-scales, branchable). R2 / S3 for object storage. Stripe (not
  Lemon Squeezy yet — for monthly sub flexibility, see decision below).
- [ ] D3. **Frontend stack**: SvelteKit (lightweight, no React lock-in,
  pleasant DX) + TailwindCSS + shadcn-svelte. Mobile-responsive from
  day one.
- [ ] D4. **Compute model** based on Phase B decision —
  - If B1 (pikepdf-only output): pure Python compute, scales horizontally
  - If B2 (PDF-only): same, but more honest with users about what they get
  - If B3 (hybrid local helper): web is just a paywall + queue + license
    issuer; compute happens on user's machine
- [ ] D5. **Stripe vs Lemon Squeezy** — Stripe Tax handles MoR-equivalent
  globally; Stripe's subscription primitives are richer; lower fees at
  $5–20/mo prices matter (LS 5%+50¢ is brutal on a $9 transaction =
  16% effective fee). **Tentative: Stripe + Stripe Tax.** Re-confirm in
  Phase D research.
- [ ] D6. **Auth**: magic link only, no passwords (Resend or Postmark).
  No social login (privacy-conscious architects don't want Google
  knowing their tool stack).
- [ ] D7. **Payment & licensing flow**: Stripe Checkout → webhook →
  account auto-provisioned → first 30 days free → bills monthly.
- [ ] D8. **Privacy/security baseline** — drawings stored encrypted at
  rest, deleted 7 days after last access (free tier) or until user
  explicitly deletes (paid tier). Privacy Policy + Terms drafted by
  lawyer.
- [ ] D9. **Founder 100** private beta — first 100 invitees get $9/mo
  lifetime price (founders' rate). Source: Phase C interviewees + USC
  studio + 30X40 / Show It Better community partnerships.
- [ ] D10. First public sale 🎉 (still under "private launch" — no
  HN, no Twitter, just the Founders 100 community)

### Phase E — Solve unsolveds (months 4–6, parallel with D)

**Goal: tool stops requiring user-side workarounds.**

- [ ] E1. The 3 stubborn cut layers — proper algorithmic fix beyond
  `__POCHE_CLOSE__`. Approaches:
  - Better endpoint clustering (DBSCAN with adaptive ε)
  - Fallback that queries Rhino's source `.3dm` if available (huge — but
    requires user to upload the .3dm too)
  - Topology inference via small LLM (e.g. "given these 14 disconnected
    polylines and the layer name `WINDOW_FRAMES_REMAP`, infer the
    closing topology"). Cheap, uses architectural priors.
- [ ] E2. Material hatch library to 25+ recipes — slate, terrazzo, OSB,
  polished concrete, perforated metal, pavers, mineral wool variants,
  glass blocks, stucco, wood siding, board-formed concrete, ETFE, etc.
- [ ] E3. Plan / elevation / detail presets actually distinct from
  section. ISO 128 says detail = one ISO step heavier; we don't yet do
  that.
- [ ] E4. Batch mode — drag a folder of `.ai`s, process all in parallel.
  Critical for studio tier value prop.
- [ ] E5. Smarter Rhino layer-name inference — handle non-Make2D Rhino
  exports (Inkscape, Vectorworks, AutoCAD). Layer-name pattern library
  becomes the moat.

### Phase F — Public launch (month 6–8)

**Goal: move from "private beta" to "anyone can sign up."**

- [ ] F1. Public landing page launch. Tagline + before/after demo +
  pricing (monthly + annual + studio tiers). $9/$19/$49/$149/mo
  candidate ladder, finalized post-Phase C.
- [ ] F2. Public Twitter/X announcement, Hacker News (Show HN),
  ArchDaily / Dezeen / Architizer pitches.
- [ ] F3. Studio tier (5–20 seats) onboarding: invoicing, multi-seat
  billing, named-user license keys.
- [ ] F4. **Optional**: paid CLI binary at $149 one-time as a "Pro
  Desktop" tier for users who want offline use. Reuses `docs/research/binary-distribution.md`
  and `docs/research/distribution-platforms.md`. Lemon Squeezy.
- [ ] F5. Affiliate program — 30% rev share for arch YouTubers
  (30X40 Design Workshop, ArchDaily creators). Stripe handles the
  payouts.
- [ ] F6. Customer support — Plain or Front for inbox; Notion-published
  docs for self-serve.

### Phase G — Scale (year 2+)

**Goal: move from "indie tool" to "studio-standard."**

- [ ] G1. Studio enterprise plans — per-seat, SSO (SAML / Microsoft
  Entra), on-prem option for security-sensitive offices.
- [ ] G2. Rhino plugin distribution via Food4Rhino + GhPython component
  in McNeel marketplace.
- [ ] G3. Adobe Exchange listing if/when Adobe ships UXP for
  Illustrator publicly. Re-architect the JSX path as a UXP plugin if so.
- [ ] G4. **AI-augmented mode** — LLM analyzes drawing semantics,
  suggests stylistic improvements, flags inconsistencies. Could be the
  feature that survives any "Rhino 9 ships built-in line weights"
  competitive shock.
- [ ] G5. Multi-drawing consistency — apply same hierarchy across
  plan/section/elevation set. Studio tier killer feature.
- [ ] G6. Style transfer — "make this look like the Tatiana Bilbao
  funeral home section." Trained on labeled architectural-drawing
  corpus.
- [ ] G7. Live integration — Rhino plug-in that previews
  arch-line-weights output in real time as the user clips and views.
- [ ] G8. Mobile / iPad companion — review-only at first, then
  redline-and-publish.

## Decision gates (cumulative)

| Gate | Criterion | Outcome if pass | Outcome if fail |
|---|---|---|---|
| End of Phase A | Tool is good enough that Zohar prefers it to manual work | Advance to Phase B | Iterate on tool; do not advance |
| End of Phase B | Buildable Illustrator-less architecture exists | Advance to Phase D web app | Fall back to CLI binary v2 plan |
| End of Phase C | ≥30% interview commitment at proposed monthly tier | Advance to Phase D investment | Reprice or shelve |
| End of Phase D MVP | 10 paying private-beta customers, NPS ≥40 | Advance to Phase F | Iterate on product |
| 6 months post-launch | $1k+ MRR | Advance to Phase G | Narrow scope |
| 12 months post-launch | Revenue covers Zohar's hosting + signing certs + opportunity cost at $X/hr | Continue, hire | Wind down |

## What WILL break this roadmap

Documented for future-us so we recognize the moment:

1. **Adobe ships UXP for Illustrator publicly** → opens a much bigger
   market (Adobe Exchange listing) → accelerate Phase G3 to F2.
2. **Rhino 9 changes Make2D output format** → may need parser rewrites
   in `layer_classify.py` and `apply.py`.
3. **A competitor launches first** — Show It Better, Astute Graphics,
   or some YC company with venture money. Pivot to differentiation
   (the layer-name semantic classifier + POSTMORTEM-driven robustness)
   not feature parity.
4. **Architecture school tooling shifts to AI-first** (Hyperboloid,
   Sketch-to-3D, etc.) → may make line weights obsolete for new
   students. Pivot to G4 (AI-augmented mode), use existing classifier
   as training data.
5. **McNeel ships first-class layered .ai or PDF export** that survives
   the round-trip → primary problem disappears. Pivot to plan /
   elevation / detail consistency tooling (E3 + G5) as the new core
   value prop.
6. **Apple kills app-specific passwords / changes notarization in
   incompatible ways** → if we ever do Phase F4 (paid CLI), expect
   pain. Stay on web app primary.
7. **Stripe acquires another payments platform that affects the
   Lemon Squeezy migration path** → minor; we have multiple options.
8. **Illustrator-less .ai output is fundamentally infeasible** —
   PieceInfo format is more closed than expected. If Phase B B1 fails,
   we're forced to either ship PDF-only (B2 — narrows the audience) or
   hybrid local helper (B3 — clunky UX).

## Sub-agent queue — what to research next

See [`docs/research/subagent-queue.md`](research/subagent-queue.md)
for the prioritized list of next research tasks. Top of queue right
now: **the Illustrator-less `.ai` output spike (B1)** — it's the
single biggest unknown and gates the SaaS path.

## See also

- [`docs/POSTMORTEM.md`](POSTMORTEM.md) — every failed approach, never repeat
- [`docs/LESSONS_LEARNED.md`](LESSONS_LEARNED.md) — what works, kept short
- [`docs/BUSINESS.md`](BUSINESS.md) — pricing, target customers, learnings (private)
- [`docs/research/`](research/) — sub-agent research transcripts informing each phase
- [`NOTICE.md`](../NOTICE.md) — license history, v1.0.0 MIT snapshot disclosure
