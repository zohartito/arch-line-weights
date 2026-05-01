# Sub-agent queue — next research tasks

> Prioritized list of what to delegate to research sub-agents next, in
> priority order. Each item: what to find out, why it matters, expected
> output format. Updated 2026-04-30 after the SaaS-first pivot.

## How to read this

- **Priority**: P0 = blocks current phase; P1 = blocks next phase; P2 =
  nice to have, not on critical path
- **Effort**: estimated sub-agent run time (minutes) — used to schedule
  parallel waves
- **Phase**: which roadmap phase the result feeds

When dispatching, prefer **batches of 3–5 in parallel** — they don't
share state, results consolidate cleanly into `docs/research/*.md` files.

## Status (2026-04-30, after Wave 1 + Wave 2)

| Wave | Status | Notes |
|---|---|---|
| Wave 1 (P0) | ✅ Complete | All 4 agents returned. SaaS feasibility resolved (B1 wins). |
| Wave 2 (P1, 4 agents) | ✅ Complete | Stripe vs LS, web stack, privacy, 3 stubborn layers all delivered. |
| Wave 3 (P1, 3 agents) | ✅ Complete | Hatch expansion, preset families, layer-name patterns delivered (run early in parallel with Wave 2). |
| Wave 4 (P2, partial) | ⚠️ Partial | Competitive landscape ✅ done. Marketing channels (#14), support tooling (#15), distribution-platform reanalysis (#13) still pending — see "Remaining" below. |
| Wave 5 (P2 long horizon) | ☐ Not yet run | AI-augmented mode (#16) — defer to post-launch. |
| **Engineering: B6 (apply.py port)** | ✅ Complete | `src/arch_line_weights/apply_saas.py` — 35/35 tests pass, CLI works on synthetic fixture. |
| **Engineering: B7 (poche.py port)** | ☐ Pending | Inject filled paths into AI native PostScript directly. Estimated 1–2 days. |
| **Engineering: B8 (end-to-end SaaS prototype)** | ☐ Pending | Wire B6+B7 into a single `arch-lw apply-saas --poche` command. |

### Remaining items in queue

- ☐ #13 — distribution-platform reanalysis at SaaS pricing (LS vs Stripe). **Partly addressed** by `saas-payments-comparison.md`; original Wave 2 prompt covered the same scope. Can mark closed.
- ☐ #14 — marketing channel research
- ☐ #15 — customer-support tooling
- ☐ #16 — AI-augmented mode feasibility (long horizon, defer to post-launch)

## P0 — gates Phase B (do this week)

### 1. Illustrator-less `.ai` output spike

- **Phase**: B1
- **Effort**: 60 minutes
- **Question**: Can pikepdf write a `.ai` file with `/PieceInfo
  /Illustrator /Private` such that Illustrator opens it with all OCG
  layers intact? Specifically, can we serialize the AI-private layer
  tree, or do we need to round-trip through a real Illustrator
  install at build time to get a "template" PieceInfo?
- **Why it matters**: This is the make-or-break for SaaS. If yes, the
  web app is buildable as pure Python. If no, we either ship PDF-only
  output (narrower audience) or hybrid local-helper (clunky UX).
- **Output format**: `docs/research/saas-architecture.md` —
  feasibility verdict + working pikepdf prototype if feasible +
  rejection rationale + alternatives if not.
- **Success criteria**: agent must produce **runnable code** that
  takes a 62-OCG-layer source and emits an `.ai` Illustrator opens
  with all layers visible in the Layers panel.

### 2. PDF-only output as the SaaS deliverable

- **Phase**: B2
- **Effort**: 30 minutes
- **Question**: If we ship a finished PDF (poché baked, weights baked,
  OCGs preserved) with no `.ai` round-trip, what's the audience cost?
  Specifically: how many architecture students / professionals iterate
  on the .ai *after* getting line weights right vs. just print-and-go?
- **Why it matters**: B2 is the simplest SaaS architecture if it's
  acceptable to users.
- **Output format**: `docs/research/pdf-only-acceptance.md` —
  segmented by user type, with quotes from forum threads /
  Reddit / Discord.

### 3. Hybrid local-helper architecture sketch

- **Phase**: B3
- **Effort**: 45 minutes
- **Question**: If the web app is just compute + paywall, and a tiny
  signed local binary drives the user's Illustrator, what's the UX
  flow? How do we authenticate the local helper to the web account?
  How does the user trigger a job, and how does data flow back?
- **Why it matters**: Privacy-friendliest path (drawings never leave
  user's machine). Worst UX path (two install steps).
- **Output format**: `docs/research/hybrid-local-helper.md` —
  architecture diagram, auth flow, comparison table vs. B1 / B2.

## P0 — gates Phase A (do alongside Phase A personal use)

### 4. Personal-use log template

- **Phase**: A5
- **Effort**: 15 minutes
- **Question**: What metrics should we track per drawing as Zohar
  uses the tool on his remaining ARCH 202B + ARCH 211 drawings?
- **Why it matters**: Phase A's data is the cheapest validation we'll
  ever get. Need a structured template so the data is comparable
  across drawings.
- **Output format**: `docs/research/personal-use-log.md` —
  template + first entry stub + analysis script that aggregates
  entries into roll-up metrics.

## P1 — gates Phase D (do after B decision)

### 5. Stripe vs Lemon Squeezy for monthly sub at $5–20/mo

- **Phase**: D5
- **Effort**: 30 minutes
- **Question**: At $9–19/mo monthly subscription, is Stripe + Stripe
  Tax cheaper net than Lemon Squeezy (5%+50¢)? At what volume does
  the trade flip? What's the operational burden of Stripe Tax vs.
  LS Merchant of Record?
- **Why it matters**: $9 transaction × 5%+50¢ = $0.95 fee = 10.5%
  effective rate. Stripe at 2.9%+30¢ + Stripe Tax 0.5% = $0.61 fee =
  6.8% effective rate. **At 100 customers, that's $40/mo difference.**
  Adds up.
- **Output format**: `docs/research/stripe-vs-lemonsqueezy-monthly.md`
  with break-even math, registration burden estimate, and recommendation.

### 6. Web app stack decision (FastAPI / Fly.io / SvelteKit)

- **Phase**: D2, D3
- **Effort**: 60 minutes
- **Question**: For a Python-heavy compute SaaS with file uploads and
  long-running jobs, what's the optimal stack in 2026?
  - Backend: FastAPI vs Litestar vs Django REST?
  - Hosting: Fly.io vs Render vs Railway vs Vercel (Python serverless)?
  - DB: Neon (Postgres) vs Supabase vs PlanetScale (MySQL)?
  - Storage: Cloudflare R2 vs S3 vs Backblaze B2?
  - Frontend: SvelteKit vs Next.js vs Astro+islands?
  - Queue: Inngest vs Trigger.dev vs custom RQ on Redis?
- **Why it matters**: Stack lock-in is real. Choosing wrong adds
  weeks to migration later.
- **Output format**: `docs/research/saas-stack.md` — decision matrix +
  recommended starter template + cost projection at 100 / 1k / 10k
  monthly users.

### 7. Privacy + security baseline for upload-process-download SaaS

- **Phase**: D8
- **Effort**: 45 minutes
- **Question**: What's the minimum-viable privacy posture for
  architects uploading drawings to our server? Specifically:
  - Encryption at rest (server-side or end-to-end?)
  - Retention policy (auto-delete after N days?)
  - Privacy Policy template (specific to upload-process-download)
  - GDPR / CCPA compliance baseline
  - SOC 2 readiness — when does it become a sales blocker for
    studios?
- **Why it matters**: Architects are paranoid about IP. Studios won't
  sign without a Privacy Policy + DPA. Get this right early or lose
  enterprise deals later.
- **Output format**: `docs/research/saas-privacy.md` — checklist +
  Privacy Policy template + DPA template + SOC 2 timeline.

## P1 — gates Phase E

### 8. Three stubborn cut layers — algorithmic deep dive

- **Phase**: E1
- **Effort**: 90 minutes
- **Question**: What approach actually solves these three layers
  on the reference drawing without `__POCHE_CLOSE__` user fix?
  - `23_WINDOW_FRAMES_REMAP` (too few points)
  - `26_CLT_GAP_ROOF_CAP` (disconnected segments, no nearest-pair under threshold)
  - `11_CU_CORR_SOLID_OPAQUE` (endpoint clusters fool bridger)
- **Approaches to evaluate**:
  - DBSCAN with adaptive ε on endpoint clusters
  - Spectral clustering on the polyline graph
  - Small LLM topology inference (architectural priors)
  - Rhino source `.3dm` query if user uploaded it
  - Voronoi-based gap detection
- **Why it matters**: 18/21 = 86%, 21/21 = 100%. The marginal 3 are the
  difference between "works for most layers" and "works for all
  layers" in the user's mental model.
- **Output format**: `docs/research/stubborn-layers-deep-dive.md` —
  approach comparison + working prototype for each + recommendation.

### 9. Material hatching library expansion to 25+ recipes

- **Phase**: E2
- **Effort**: 75 minutes
- **Question**: From Detail magazine, Ramsey/Sleeper, Ching, NCS, and
  archive.org architectural-drafting books, what's the canonical
  hatch pattern for: slate, terrazzo, OSB, polished concrete, perforated
  metal, pavers, mineral wool, glass block, stucco, board-formed
  concrete, ETFE, plywood end-grain, brick (running bond, common bond,
  Flemish bond, herringbone), CMU, structural clay tile, gypsum
  wallboard, acoustic ceiling tile, carpet, wood flooring (perpendicular
  vs parallel grain), ceramic tile, copper standing-seam, zinc?
- **Why it matters**: 14 → 25+ recipes is a measurable "amazing"
  upgrade and a concrete moat — competitors would have to research
  each pattern from scratch.
- **Output format**: `docs/research/hatch-library-expansion.md` — one
  entry per material with: pattern definition (math), citation,
  shapely-compatible parameter dict, sample image.

### 10. Plan / elevation / detail preset family

- **Phase**: E3
- **Effort**: 45 minutes
- **Question**: ISO 128 + Ramsey says detail = one step heavier than
  plan/section. What does that look like as a preset family in
  `presets.py`? What's the right tier-role mapping for each drawing
  type?
- **Why it matters**: Currently all preset families share the same
  ISO ladder, which is wrong for plotted print at non-section scales.
- **Output format**: `docs/research/preset-families.md` — preset
  table + Python preset module diff.

### 11. Smarter Rhino layer-name inference — non-Make2D sources

- **Phase**: E5
- **Effort**: 60 minutes
- **Question**: What layer-name conventions do Inkscape, Vectorworks,
  AutoCAD DXF, ArchiCAD, and Revit-exported PDFs use? Can we extend
  the classifier to handle them all with a unified pattern library?
- **Why it matters**: "We work with Rhino *and* Vectorworks" doubles
  the addressable market. The pattern library becomes the moat.
- **Output format**: `docs/research/layer-name-patterns.md` —
  per-source pattern library + classifier extension diff.

## P2 — fill in gaps from current docs

### 12. Competitive landscape (resolves dangling reference in BUSINESS.md)

- **Phase**: cross-cutting
- **Effort**: 60 minutes
- **Question**: Detailed competitive landscape for indie architecture
  drafting tools — Show It Better, Astute Graphics, VisualARQ, Lands
  Design, Veras, D5 Render, Enscape, plus AutoCAD CTB / Revit View
  Templates / ArchiCAD Pen Sets as inside-app alternatives. Per
  competitor: positioning, pricing, audience, distribution channel,
  what they do better, what they don't do, threat level.
- **Why it matters**: BUSINESS.md references `competitive-landscape.md`
  but the file doesn't exist. Fix the dangling reference and inform
  Phase F messaging.
- **Output format**: `docs/research/competitive-landscape.md` —
  competitor matrix + positioning canvas + threat assessment.

### 13. Distribution-platform reality check at SaaS pricing

- **Phase**: D
- **Effort**: 30 minutes
- **Question**: `docs/research/distribution-platforms.md` was written
  assuming one-time tiers ($29 / $79 / $249). At monthly subscription
  ($9–19/mo) the math changes. Re-run the comparison for
  subscription-first.
- **Output format**: append a "Subscription pricing reanalysis"
  section to the existing file.

### 14. Marketing channel research

- **Phase**: F
- **Effort**: 60 minutes
- **Question**: For an indie tool targeting architecture students +
  small studios, what are the proven distribution channels in 2026?
  Specifically: 30X40 Design Workshop YouTube, ArchDaily, Dezeen,
  Architizer, Reddit r/architecture, Show It Better newsletter,
  Discord servers (USC studio, GSAPP, etc.), Instagram, TikTok,
  university studio email lists, Food4Rhino (existing user base),
  Adobe Exchange (when UXP ships).
- **Why it matters**: Phase F's success depends on reaching the right
  channels at launch. Pre-research saves 6 weeks of trial.
- **Output format**: `docs/research/marketing-channels.md` —
  channel-by-channel cost / reach / fit / how-to-pitch.

### 15. Customer-support tooling for indie SaaS

- **Phase**: F6
- **Effort**: 30 minutes
- **Question**: At 10 / 100 / 1000 paying customers, what's the
  right inbox + docs + status-page stack? Plain vs Front vs HelpScout?
  Notion-published vs Mintlify vs ReadMe? Statuspage vs Better
  Stack vs Atlassian?
- **Output format**: `docs/research/support-stack.md` — recommendation
  per customer scale.

### 16. AI-augmented mode (G4) — feasibility and approach

- **Phase**: G4 (long horizon)
- **Effort**: 75 minutes
- **Question**: Can a small LLM (Claude Haiku, GPT-4o-mini, Gemini
  Flash, or local Llama) reliably analyze a section drawing and
  flag inconsistencies, suggest stylistic improvements, infer
  unlabeled layer semantics? Cost per drawing? Latency? Privacy
  implications (does the LLM see the drawing geometry, or just
  derived metadata)?
- **Why it matters**: G4 is the survival pivot if McNeel ships
  built-in line weights (existential risk #2 in BUSINESS.md).
  Pre-research keeps it from being a panic move.
- **Output format**: `docs/research/ai-augmented-mode.md` — LLM
  capability matrix + cost-per-drawing estimate + privacy posture +
  prototype sketch.

## Dispatch suggestions (waves)

### Wave 1 (this week, P0 only — 4 agents in parallel)

- Agent 1: Illustrator-less `.ai` output spike (#1)
- Agent 2: PDF-only acceptance research (#2)
- Agent 3: Hybrid local-helper architecture sketch (#3)
- Agent 4: Personal-use log template (#4)

After Wave 1 returns, **make the SaaS architecture decision** before
spawning Wave 2.

### Wave 2 (after architecture decision, P1 — 4 agents in parallel)

- Agent 5: Stripe vs Lemon Squeezy for monthly sub (#5)
- Agent 6: Web app stack decision (#6)
- Agent 7: Privacy + security baseline (#7)
- Agent 8: Three stubborn cut layers algorithmic deep dive (#8)

### Wave 3 (in parallel with web-app build, P1 — 3 agents)

- Agent 9: Material hatching library expansion (#9)
- Agent 10: Plan / elevation / detail preset family (#10)
- Agent 11: Smarter Rhino layer-name inference (#11)

### Wave 4 (P2 — opportunistic, 4 agents)

- Agent 12: Competitive landscape (#12)
- Agent 13: Distribution-platform reanalysis (#13)
- Agent 14: Marketing channel research (#14)
- Agent 15: Customer-support tooling (#15)

### Wave 5 (long horizon, P2 — 1 agent)

- Agent 16: AI-augmented mode feasibility (#16)

## Costs

Total estimated agent run time across all 16 tasks: **~13 hours of
parallelized agent compute**, spread across 5 dispatch waves over
~6 weeks. Each wave's outputs are used to make a decision before the
next wave; no agent does work that becomes obsolete.

If we run all of Wave 1 in parallel right now, results land in ~60
minutes. That's the path to the SaaS architecture decision.
