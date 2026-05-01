# SaaS stack — recommended choices for Phase D MVP

> Research transcript, 2026-04-30. Time-boxed ~60 min of agent work.
> Inputs: `docs/ROADMAP.md` Phase D2-D6, `docs/research/saas-architecture.md`,
> `pyproject.toml`. Constraints: solo founder, 10–100 paid users at v1
> scaling to 1000–5000 at v2, <$100/mo at v1, privacy-conscious users
> (architects with confidential drawings), Python-first (existing codebase
> is pikepdf + zstd + shapely), 10–60 s processing per file, 10–50 MB
> uploads.

## TL;DR — recommended stack

| Layer | Pick | Boring alternative | Cost @ 100 users |
|---|---|---|---|
| Backend framework | **FastAPI** | Django REST | $0 (libs) |
| Hosting/compute | **Fly.io Machines** (1 web + autoscaled workers) | Hetzner CX22 + Coolify | ~$25 |
| Database | **Neon** (serverless Postgres) | Managed Postgres on Fly | $0 (free tier) |
| Object storage | **Tigris** (EUR multi-region, on Fly) | Cloudflare R2 | ~$2 |
| Frontend | **SvelteKit** + Tailwind + shadcn-svelte | Astro + HTMX | $0 |
| Job queue | **Custom Redis + RQ on Fly** (in same project) | Synchronous + nginx upload buffering | ~$3 |
| Auth | **Roll-your-own magic links** (Resend + Postgres) | Stytch (free <10k MAUs) | $0 |
| Email | **Resend** | Postmark | $0 (free tier) |
| Error tracking | **GlitchTip self-hosted on Fly** | Sentry free tier | ~$3 |
| Analytics | **Plausible Cloud (EU)** | None | $9 |
| Payments | **Stripe + Stripe Tax** (per Phase D5) | — | 2.9% + 30¢ per txn |
| Domain | **Cloudflare Registrar** | Porkbun | ~$1/mo amortized |
| **Total infrastructure @ 100 users** | | | **~$45/mo** |

## Decision matrices

### 1. Backend framework

| Option | Pros | Cons | Lock-in |
|---|---|---|---|
| **FastAPI** | Massive ecosystem, OpenAPI docs free, Pydantic v2, used at OpenAI/Anthropic, async-first, 4.5M daily downloads | Pydantic v2 serialization slower than msgspec | Low — request handlers map cleanly to ASGI; portable |
| Litestar | 2x faster (msgspec serialization), 40-120% production gains | Smaller ecosystem; fewer Stack Overflow answers when stuck | Low — also ASGI |
| Django REST | Battle-tested, admin panel free, ORM included | Heavyweight for an upload-process-download API; sync-first | Medium — Django ORM patterns are sticky |
| Flask | Minimal, familiar | Sync-by-default, manual OpenAPI, no Pydantic | Low |

**Pick FastAPI.** Compute is dominated by zstd/pikepdf (NOT serialization), so Litestar's perf edge doesn't matter for this workload. FastAPI's ecosystem and the fact it's the obvious 2026 default makes hiring/AI-pairing easier. Boring alternative is Django REST if you later want the admin panel free.

### 2. Hosting / compute

The compute profile (10–60 s, ~110 MB peak RAM, CPU-bound zstd) rules out:
- **Vercel Python serverless**: 60 s hard timeout on Pro, no persistent storage, 50 MB upload limit by default. Marginal fit.
- **AWS Lambda**: 15 min timeout works, but cold starts on a 110 MB payload + pikepdf wheel are painful, and Lambda + API Gateway + S3 wiring is a lot of YAML for a solo founder.

| Option | Pros | Cons | Cost @100 / 1000 / 5000 |
|---|---|---|---|
| **Fly.io Machines** | Pay-per-second, machines auto-stop, EU regions for privacy, native Docker, good Python support, Tigris storage 1-click, persistent volumes if needed | Volume snapshots became billable Jan 2026; some debugging requires `fly ssh`; ops slightly more hands-on than Render | ~$15 / ~$80 / ~$300 |
| Render | Flat pricing, predictable bills, dead-simple Git deploy, managed Postgres | $7/mo per always-on web service; no per-second billing for workers; Background Workers cost more | ~$30 / ~$200 / ~$800 |
| Railway | Fastest code-to-URL, $5 hobby plan | Usage-based pricing can spike; weaker EU presence | ~$25 / ~$180 / ~$700 |
| Hetzner VPS + Coolify | Cheapest at any scale (~€5/mo CX22), EU-based (privacy win), full control | Solo-founder ops burden; security: 11 critical CVEs in Coolify Jan 2026, must keep updated; no autoscaling out of the box | ~$8 / ~$25 / ~$80 |

**Pick Fly.io Machines.** Two reasons: (1) auto-stop billing matches the bursty workload — a worker only runs 10–60 s per upload and stops; users at 100/mo means only ~10–60 min/day of compute; (2) EU regions (`fra`, `ams`) are one-flag away, important for privacy-conscious architects. **Boring alt: Hetzner + Coolify** if you want predictable cost ceilings — but accept the security update churn and the lack of multi-region.

### 3. Database

| Option | Pros | Cons | Cost @100 / 1000 / 5000 |
|---|---|---|---|
| **Neon** | Serverless, scales-to-zero, branchable (great for staging), 100 CU-h free tier (October 2025 doubled), $0.35/GB-mo storage (down from $1.75), Databricks-backed | EU regions exist but newer; cold-start latency on first query after idle (300-500 ms) | $0 / ~$25 / ~$80 |
| Supabase | Postgres + auth + storage + realtime in one, generous free tier (500 MB DB, 1 GB storage, 50k MAU) | Lock-in via auth + storage if you use them; coupling to Supabase client; pricing jumps to $25/mo for paid | $0 / ~$25 / ~$100 |
| PlanetScale (MySQL) | Branching, scales hard | MySQL not Postgres (we'd lose array types, JSONB, range types); no longer free tier for hobby | ~$39 / ~$100 / ~$500 |
| SQLite + Litestream | $0 ops, file-based, replicates to S3 | Single-writer; can't horizontally scale; backup-restore not as instant as Postgres point-in-time | $0 / $0 / brittle |
| RDS Postgres | AWS gold standard | $15+/mo minimum, no scale-to-zero, Console UX, ops-heavy | ~$15 / ~$60 / ~$200 |

**Pick Neon.** Free tier covers v1; scale-to-zero matches our bursty workload; branching is genuinely useful for staging. Boring alt: Supabase Postgres (skip their auth/storage products to avoid lock-in).

### 4. Object storage

User drawings are confidential. We store them encrypted, retain 7 days (free) or until user deletes (paid). Per drawing ~30 MB; 100 users × 4 drawings/mo × 30 MB = 12 GB stored, ~30 GB egress.

| Option | Pros | Cons | Cost @100 / 1000 / 5000 |
|---|---|---|---|
| **Tigris** | Native on Fly.io (one-click), $0 egress, EU multi-region buckets at $0.025/GB-mo, encryption at rest by default, S3 API compatible, SOC 2 Type II | Newer (2024 GA), smaller ecosystem | ~$1 / ~$10 / ~$50 |
| Cloudflare R2 | $0 egress, $0.015/GB storage, S3 API, mature | EU bucket option exists but jurisdiction = Cloudflare US; some architects may object | ~$1 / ~$8 / ~$40 |
| Backblaze B2 | $6/TB ($0.006/GB), free egress via Cloudflare Bandwidth Alliance | US-based; egress only free if proxied through Cloudflare | ~$1 / ~$6 / ~$30 |
| AWS S3 | Universal | Egress fees ($0.09/GB) destroy the budget at any scale; complex IAM | ~$5 / ~$50 / ~$300 |

**Pick Tigris.** Co-located with Fly compute (zero internal latency, zero egress), EU multi-region for privacy, free 5 GB tier. Boring alt: Cloudflare R2 if Tigris ever flakes.

### 5. Frontend

The UI needs: marketing landing page, pricing page, sign-in (magic link), upload form, job-progress UI, downloads page, billing portal (Stripe-hosted), settings. A handful of authenticated pages — not a SPA-shaped app.

| Option | Pros | Cons | Lock-in |
|---|---|---|---|
| **SvelteKit** | 50% less JS than Next, half interactivity delay on auth dashboards, SSR + islands as needed, Svelte 5 runes ergonomic, shadcn-svelte mature in 2026 | Smaller ecosystem than React; fewer hireable devs | Low — components are mostly HTML/CSS |
| Next.js | Biggest ecosystem, infinite tutorials, Vercel-optimized | Vercel-pricing pressure; React-heavy bundle; over-engineered for our needs | Medium |
| Astro + islands | Static-first is wickedly fast for marketing pages | Friction for the dashboard half (auth/upload/progress) — fights `client:load` everywhere | Low |
| HTMX + Jinja (no JS framework) | Zero build step, ship from FastAPI directly, smallest payload, perfect for upload-process-download | Real-time progress (job updates) needs SSE; ecosystem of pre-built components is thin; fewer architects-as-users will tolerate the lo-fi feel | None |

**Pick SvelteKit.** The dashboard side (upload, progress, downloads, settings) needs interactivity that islands fight; the marketing side benefits from SvelteKit's SSR. Roadmap D3 already specified this. Boring alt: **HTMX + Jinja** if you want to ship 2 weeks earlier — the upload-process-download flow is genuinely well-suited to it. Architects-as-users won't notice if the UI is server-rendered, as long as it's clean.

### 6. Job queue

10–60 s processing is too long to block an HTTP request, but short enough that we don't need durable workflows. Three meaningful tiers:

| Option | Pros | Cons | Cost @100 / 1000 / 5000 |
|---|---|---|---|
| **Redis + RQ in same Fly project** | Owns the data; native Python; auto-stops when idle on Fly Machines; $0 lock-in | Solo founder owns Redis ops; no fancy step functions | ~$3 / ~$8 / ~$30 |
| Inngest | Beautiful step functions, retries, observability | Python SDK less mature than TypeScript; $75/mo starting tier; data flows through their cloud (privacy review needed) | $0 / $75 / $200+ |
| Trigger.dev | Step functions, $10/mo, 50k task runs free | Python only via build extensions (script execution, not native SDK) — would shoehorn pikepdf | $0 / $10–50 / $100+ |
| Cloudflare Queues | Cheap | TypeScript Worker primary; Python on CF Workers via Pyodide is constrained (no pikepdf) | N/A |
| Synchronous (no queue) | Zero infrastructure | A 60-s blocked HTTP request fails on most proxies (60 s default timeout); user can't navigate during processing | $0 |

**Pick Redis + RQ.** Both run in the same Fly project; the worker machine auto-stops when the queue is empty. Privacy bonus: drawings never leave our infrastructure, which a third-party orchestrator like Inngest can't claim. Boring alt: synchronous with a generous proxy timeout (e.g., set Fly's HTTP service timeout to 90s) and progress polling — only viable if jobs stay reliably <60 s.

### 7. Auth

| Option | Pros | Cons | Lock-in |
|---|---|---|---|
| **Roll-your-own magic links** | Phase D6 already specified magic-link-only; ~80 lines of FastAPI; controls email content; no third party gets user list | Have to handle rate limiting, token expiration, replay protection ourselves; small attack surface but still ours | None |
| Stytch | Generous free tier (10k MAUs free), passwordless primitives, EU residency option | $0.01/MAU after 10k = $50/mo at 5000 active; vendor reads our user list | Medium |
| Clerk | Best DX in React; February 2026 pricing restructure ($25/mo Pro start) | React-skewed; UI components SvelteKit-unfriendly; sends user data through Clerk Cloud | High |
| Supabase Auth | Free with Supabase | Lock-in tightens if Postgres also there | High if combined |
| WorkOS AuthKit | Free <1M MAUs, includes social/MFA/passkeys | Designed for B2B SSO; SSO connections billed per-customer at $125/mo (only matters at studio tier) | Medium |

**Pick roll-your-own magic links.** The existing roadmap (D6) called this out; total code is ~80 lines; saves $0 today and ~$50–100/mo at 5000 users; privacy-conscious architects don't want their email going to Clerk/Stytch. Boring alt: **Stytch** if writing the magic-link code feels too risky — free tier covers all of v1.

### 8. Email

We need transactional only (magic links, billing receipts, drawing-ready notifications). No newsletters in v1.

| Option | Pros | Cons | Cost @100 / 1000 / 5000 |
|---|---|---|---|
| **Resend** | 3000/mo free, $20–35/mo Pro, beautiful API, React Email templates, EU region | Newer (founded 2023); ~3 yr track record | $0 / $20 / $35 |
| Postmark | Best deliverability for transactional, mature | $15/mo + $1.80/1k after 10k; 100/mo dev tier only | $15 / $15 / ~$40 |
| Loops | Best for lifecycle marketing | $49/mo for 5k subscribers; we don't need marketing automation | N/A |
| ConvertKit | Newsletter-focused | Wrong shape | N/A |
| AWS SES | Cheapest ($0.10/1k) | Deliverability worse OOB; reputation management overhead | ~$0 / ~$0 / ~$5 |

**Pick Resend.** 3000/mo free covers v1 magic links. Boring alt: **Postmark** for max deliverability if Resend has a regression — Postmark has 10+ year track record.

### 9. Error tracking

| Option | Pros | Cons | Cost @100 / 1000 / 5000 |
|---|---|---|---|
| **GlitchTip self-hosted on Fly** | Sentry SDK-compatible (zero-cost migration later), 4 containers vs Sentry's 40+, GlitchTip 6 (Feb 2026) improved stack traces, our data in our infra | We run it; needs Postgres + Redis (already have both) | ~$3 / ~$3 / ~$5 |
| Sentry Cloud free | Best UX, generous free tier (5k events/mo) | Privacy: errors may contain user data → leaks to Sentry; $26/mo Team plan | $0 / $26 / $80 |
| GlitchTip Cloud | Same as self-hosted but managed | $15/mo starting | $15 / $15 / $40 |
| Honeybadger | Per-project pricing ($49/mo for 15 projects); error volume doesn't matter | More expensive than self-hosted GlitchTip | $49 / $49 / $99 |

**Pick GlitchTip self-hosted.** Privacy alignment + Sentry SDK-compatible (we can migrate to Sentry Cloud anytime). Boring alt: Sentry free tier — switch when (if) we exceed 5k events/mo.

### 10. Analytics

| Option | Pros | Cons | Cost @100 / 1000 / 5000 |
|---|---|---|---|
| **Plausible Cloud (EU)** | EU-hosted, GDPR-native, no cookie banner needed, simple, ~1 KB script | $9/mo for 10k pageviews; $14/mo Growth tier | $9 / $14 / $19 |
| Fathom | Privacy-first, $15/mo for 100k pageviews | More expensive at low volume than Plausible | $15 / $15 / $19 |
| PostHog Cloud | 1M events free, session replays, A/B tests, feature flags | Heavier script; broader product but we don't need most of it; data → PostHog Cloud (US) | $0 / $0 / $0 |
| None | $0; honors privacy fully | No conversion-funnel insight | $0 |

**Pick Plausible (EU region).** Architects-as-users care about privacy and lack-of-banner is a UX win. Boring alt: **PostHog free tier** if we want session replays for support; mind the data-residency tradeoff. Cheapest alt: **None** — server logs + Stripe dashboards cover most signals at v1.

## Recommended stack — combined

```
[browser: SvelteKit + Tailwind + shadcn-svelte, served via Fly]
        |
        v  HTTPS, magic-link cookie session
[FastAPI (uvicorn) on Fly Machine, region=fra, EU residency]
        |
        +-- Postgres @ Neon (EU region, scale-to-zero)
        |
        +-- Redis @ Fly upstream + RQ workers (auto-stop)
        |     |
        |     v  pikepdf + zstd + shapely (existing arch_line_weights)
        |     v  fetch input from Tigris, write output to Tigris
        |
        +-- Tigris (EU multi-region, encrypted at rest, 7 day retention)
        |
        +-- Stripe Checkout + Stripe Tax (webhook → Postgres)
        |
        +-- Resend (magic links, drawing-ready emails)
        |
        +-- Plausible (script tag on marketing pages only, not on dashboard)
        |
        +-- GlitchTip (sidecar Fly Machine, Sentry SDK in FastAPI)
```

## Cost projection — itemized monthly bill

### At 100 paid users ($9/mo personal × 80 + $19/mo pro × 15 + $49/mo studio × 5 = $1,200 MRR target)

| Line item | Monthly |
|---|---|
| Fly.io web (1× shared-cpu-2x, 1 GB, always-on, fra) | $14 |
| Fly.io worker (autoscaled, ~10 s × 400 jobs/mo = 1.1 hr) | $1 |
| Fly.io Redis (256 MB, fra) | $3 |
| Fly.io GlitchTip sidecar | $3 |
| Neon Postgres (free tier — 100 CU-h covers it) | $0 |
| Tigris (12 GB stored × $0.025) | $1 |
| Resend (free 3k/mo email) | $0 |
| Plausible 10k Starter | $9 |
| Stripe (2.9% + 30¢ × 100 txns ≈ $65 fees) | excluded; cost of revenue |
| Cloudflare Registrar (~$10/yr) | $1 |
| Domain renewals + minor ($10/yr × 2) | $2 |
| **Total infrastructure** | **~$34/mo** |
| % of $1,200 MRR | 2.8% |

### At 1000 paid users (assumes same mix → $12k MRR)

| Line item | Monthly |
|---|---|
| Fly.io web (2× shared-cpu-2x, 2 GB, always-on, multi-region) | $35 |
| Fly.io workers (autoscaled, ~11 hr/mo) | $9 |
| Fly.io Redis (1 GB) | $13 |
| Fly.io GlitchTip sidecar | $5 |
| Neon Postgres Launch tier | $25 |
| Tigris (120 GB) | $3 |
| Resend Pro (50k/mo) | $20 |
| Plausible 100k Growth | $14 |
| Stripe Tax | included |
| **Total infrastructure** | **~$124/mo** |
| % of $12k MRR | 1.0% |

### At 5000 paid users (assumes same mix → $60k MRR)

| Line item | Monthly |
|---|---|
| Fly.io web (3× shared-cpu-4x, 4 GB, multi-region) | $130 |
| Fly.io workers (autoscaled, ~55 hr/mo) | $40 |
| Fly.io Redis (4 GB) | $40 |
| Fly.io GlitchTip sidecar | $15 |
| Neon Postgres Scale tier | $80 |
| Tigris (600 GB) | $15 |
| Resend Pro 100k tier | $35 |
| Plausible 1M | $69 |
| **Total infrastructure** | **~$424/mo** |
| % of $60k MRR | 0.7% |

All three milestones stay under the budget targets ($100 / $500 / scales linearly).

## Lock-in / migration analysis

| Choice | Lock-in level | Migration cost if forced |
|---|---|---|
| FastAPI | Very low — ASGI is portable to Litestar / Starlette / any ASGI host | 1–2 weeks |
| SvelteKit | Low — components are HTML/CSS, only adapter changes per host | 2 weeks if rewriting to Next |
| Fly.io | Medium — Machines API is custom, but Dockerfiles are portable | 1 week to Hetzner/Render (rebuild deploy pipeline) |
| Neon Postgres | **Very low** — it's just Postgres; `pg_dump` to anywhere | 1 day |
| Tigris | Low — S3 API; swap endpoint URL | 1 day |
| Stripe | Medium — webhook handlers + customer IDs sticky, but API is well-documented | 1–2 weeks to switch to Lemon Squeezy / Paddle |
| Roll-your-own auth | None | Already ours |
| Resend | Low — SMTP fallback works for magic links | 1 day |
| GlitchTip | None — Sentry SDK-compatible | 1 hour |
| Plausible | None — replace JS snippet | 1 hour |
| Redis + RQ | Low — Redis is everywhere | 1 day |

**Highest-stickiness choice in this stack: Fly.io.** Mitigation: keep Dockerfiles + a `fly.toml` checked into git; the same images deploy to Render/Railway/Hetzner with minor changes. **Stripe is the second-stickiest**; Phase D5 already accepted that.

## "Boring choice" alternative stack

If the recommended stack feels too new (Tigris is 2024 GA, Neon is post-Databricks-acquisition, GlitchTip is community-driven), here is the "every choice has 5+ years of stability" alt:

| Layer | Boring choice | Why |
|---|---|---|
| Backend | FastAPI | Same — no boring alt needed |
| Hosting | **Hetzner CX22 + Coolify** | €5/mo VPS, EU, predictable. Accept ops burden. |
| DB | **Managed Postgres on the same Hetzner box** | Or Supabase Postgres (skip the auth product). |
| Storage | **Cloudflare R2** | 4+ years GA, $0 egress, $0.015/GB |
| Frontend | **HTMX + Jinja** served from FastAPI | Zero build step, ships in days |
| Queue | **RQ + Redis on same Hetzner** | One box, one Redis |
| Auth | **Stytch free tier** | Battle-tested |
| Email | **Postmark** | 10+ year track record, best deliverability |
| Errors | **Sentry Cloud free tier** | Most-used in industry |
| Analytics | **Plausible Cloud** (same) | Already boring at 6 yr old |

Boring stack v1 cost @100 users: ~$25/mo (just the Hetzner box + Plausible + Stytch free + Postmark $15). Beats the recommended stack on cost; loses on auto-scaling and EU multi-region.

## Starter template — fork-and-go scaffolding

Top candidates (all evaluated April 2026):

1. **[FastSvelte](https://github.com/harunzafer/fastsvelte)** — explicit FastAPI + SvelteKit SaaS starter; includes session auth, Stripe webhooks, multi-tenancy, an AI demo app to gut. Closest fit. **Recommended fork target.**
2. **[Quartalis sveltekit-fastapi-starter](https://github.com/Quartalis/sveltekit-fastapi-starter)** — free tier, premium tier adds Stripe + admin dashboard + RBAC + email verify + password reset. Simpler scaffolding.
3. **[faulander/fastapi-sveltekit-template](https://github.com/faulander/fastapi-sveltekit-template)** — minimal, Tailwind-styled, email/password + token auth. Easier to gut down.
4. **[urjeetpatel/fastapi-sveltekit-starter](https://github.com/urjeetpatel/fastapi-sveltekit-starter)** — Async SQLAlchemy + Postgres + pytest scaffolding.
5. **[startino/saas-starter](https://github.com/startino/saas-starter)** — SvelteKit-only (no FastAPI), Supabase + Stripe + shadcn-svelte. Reference for SvelteKit-side patterns even if we don't use Supabase.

**Recommendation: fork FastSvelte.** Gut the AI demo, replace with our pikepdf upload-process-download flow. Strip multi-tenancy initially — re-add when studio tier ships in Phase F3.

## Risks / unknowns

1. **Tigris is the newest dependency.** Mitigation: it's S3-compatible; swapping to R2 takes ~1 day if Tigris flakes.
2. **Fly.io volume snapshots became billable Jan 2026.** Not a blocker — we don't need volumes for stateless workers; only the Redis machine wants persistence and snapshots are <$0.50/mo.
3. **Roll-your-own magic links carry implementation risk.** Mitigation: use a vetted JWT library, time-bounded tokens, single-use, rate-limit per email. ~80 lines, well-trodden pattern.
4. **Neon cold-start latency** on the free tier (300–500 ms after idle) may make the first request after a quiet period feel slow. Mitigation: keep a warm cron pinging it every 5 min, OR upgrade to Launch tier ($25/mo) at 1000 users.
5. **GlitchTip self-hosted** demands occasional Postgres schema migrations on upgrade. Mitigation: pin a version, upgrade quarterly during a maintenance window.

## See also

- [`docs/ROADMAP.md`](../ROADMAP.md) — Phase D2-D6 (web app MVP)
- [`docs/research/saas-architecture.md`](saas-architecture.md) — pikepdf + zstd compute model (the load this stack must support)
- [`docs/research/pricing-research.md`](pricing-research.md) — pricing tiers this stack must be sustainable under
- [`docs/research/binary-distribution.md`](binary-distribution.md) — alternative path if SaaS doesn't take

## Sources

- [Fly.io Pricing 2026](https://fly.io/pricing/) and [Cost Management](https://fly.io/docs/about/cost-management/)
- [Tigris pricing & multi-region buckets](https://www.tigrisdata.com/pricing/)
- [Neon pricing 2026](https://neon.com/pricing) — free tier doubled to 100 CU-h Oct 2025
- [Cloudflare R2 pricing](https://developers.cloudflare.com/r2/pricing/)
- [Resend pricing 2026](https://nuntly.com/resend-pricing)
- [Postmark pricing 2026](https://nuntly.com/versus/resend-vs-postmark)
- [Plausible Analytics 2026](https://glassanalytics.com/review/plausible-analytics)
- [PostHog vs Plausible vs Fathom 2026](https://devtoolpicks.com/blog/posthog-vs-plausible-vs-fathom-vs-mixpanel-2026)
- [Stytch / Clerk / WorkOS comparison 2026](https://www.kinde.com/comparisons/top-10-authentication-providers-for-b2b-software-2026/)
- [GlitchTip vs Sentry vs Honeybadger 2026](https://devtoolpicks.com/blog/sentry-vs-honeybadger-vs-glitchtip-indie-hackers-2026)
- [Litestar vs FastAPI 2026 benchmarks](https://byteiota.com/litestar-vs-fastapi-python-speed-test-2026-analysis/)
- [SvelteKit vs Astro vs HTMX 2026](https://www.gigson.co/blog/sveltekit-vs-next-js-vs-astro-which-framework-wins-in-2026)
- [Trigger.dev / Inngest pricing 2026](https://comparetiers.com/compare/inngest-vs-trigger-dev)
- [Hetzner + Coolify reality](https://ceaksan.com/en/hetzner-coolify-self-hosting-reality)
- [FastSvelte starter](https://fastsvelte.dev/)
