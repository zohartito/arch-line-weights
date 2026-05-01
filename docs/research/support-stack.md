# Customer-support stack — recommended choices for Phase F6

> Research transcript, 2026-04-30. Time-boxed ~45 min of agent work.
> Inputs: `docs/ROADMAP.md` Phase F6, `docs/research/saas-stack.md`.
> Constraints: solo founder, 10 → 100 → 1000 paid users, low ops overhead,
> EU-leaning privacy posture (architects with confidential drawings).
> Companion to `saas-stack.md` (infrastructure side).

## TL;DR — recommended stack at each scale

| Category              | 10 customers           | 100 customers         | 1000 customers              |
|-----------------------|------------------------|-----------------------|-----------------------------|
| Inbox                 | **Gmail + labels**     | **HelpScout Standard**| **HelpScout Plus** (or Plain)|
| Self-serve docs       | **MkDocs Material**    | MkDocs Material       | MkDocs Material + Algolia DocSearch |
| Status page           | **Homepage notice**    | **Better Stack free** | **Instatus Pro** ($15/mo)   |
| Live chat             | **Skip**               | Skip                  | **Crisp Mini** (€45/mo) opt-in |
| Feedback widget       | **Skip**               | **Featurebase Free**  | **Featurebase Starter** ($29/mo) |
| Community             | **Skip**               | **GitHub Discussions**| GitHub Discussions or Discord |
| KB search             | **MkDocs built-in**    | MkDocs built-in       | **Algolia DocSearch** (free) |
| Onboarding            | **In-app checklist**   | In-app checklist      | In-app checklist (skip Userflow) |

## Per-category research

### 1. Inbox / shared mailbox

| Option | Cost (1 user) | Cost (3 users) | Pros | Cons | Solo-founder fit |
|---|---|---|---|---|---|
| **Gmail + labels** | $0 (personal) / $7 Workspace | $21 Workspace | Zero learning curve; you already know it; fine up to ~50 tickets/wk | No shared assignment; no SLA timer; no canned-reply UI; conflates personal mail | ★★★★★ (10 users) |
| **HelpScout Standard** | $25/user (annual) | $75 | Beautiful UI, mature (15 yr), Docs integrated free, 5-user free tier | Free tier is 5 users / 1 inbox; no per-conversation SLA on Standard | ★★★★ (100 users) |
| **HelpScout Plus** | $45/user | $135 | Adds AI summaries, multi-brand, advanced reporting | Pricier per seat than Plain at low volume | ★★★★ (1000 users) |
| **Plain** | $35/seat (Foundation) | $105 | B2B-aware (linear/slack/issue threading), AI agent included no per-resolution fee, viewer seats free | Younger tool (~3 yr), opinionated (better for product-engineering teams) | ★★★ (100 users), ★★★★ (1000 users for B2B/studio tier) |
| **Front** | $25 Starter / $65 Pro | $75 / $195 | Email-first UI, omnichannel | Starter = 1 channel, 10 seats max; AI is paid add-ons; pricier than HelpScout at parity | ★★★ |
| **Missive** | $14–18/user | $42–54 | Cheapest collab inbox; 5 channels; free for ≤3 users | Less polish than HelpScout; weaker reporting | ★★★★ |
| **Hey for Work** | $12/user (extra) + $10 first | $34/mo | Beautiful interface; clear mental model | No team-assignment workflow; no canned replies; basically Gmail-but-different | ★★ |
| **Self-hosted Mailpit + IMAP** | Hetzner box $5 | $5 | Cheapest, full control | Solo founder ops; no team workflow; **don't** | ★ |

**Pick at 10 users: Gmail + labels.** Your support volume at 10 customers is ~2–5 tickets/week. Anything else is over-engineering. Set up labels: `support/new`, `support/waiting-customer`, `support/bug`, `support/feature-request`. Use canned responses (Gmail Settings → Advanced).

**Migration trigger to HelpScout: ~25 active customers OR ~10 tickets/week** (whichever first). At that point: (a) you start losing context across threads; (b) you want a customer-facing portal showing past conversations; (c) you want canned replies with snippets.

**Pick at 1000 users: HelpScout Plus** ($45/user) — mature, has Docs built in (closes the "self-serve" loop), AI summary saves time, free 3-month AI Answers trial. Plain is the alternative if your customer base skews B2B/studio-tier (Phase F3) since Plain's threading model fits engineering-led customers better.

Sources: [Plain pricing](https://www.plain.com/pricing), [HelpScout pricing](https://www.helpscout.com/pricing/), [Front pricing](https://front.com/pricing), [Missive pricing](https://missiveapp.com/pricing), [HEY pricing](https://www.hey.com/pricing/).

### 2. Self-serve docs / help center

| Option | Cost | Search | SEO | Customization | Solo-founder fit |
|---|---|---|---|---|---|
| **MkDocs Material** | $0 (free) | Built-in lunr.js (good); Algolia DocSearch (free, great) | Excellent (static HTML) | High (Material theme + overrides) | ★★★★★ (already in stack) |
| Notion published | $0–$10/mo | Notion search (mediocre on public) | Mediocre (Notion crawl quality) | Low (Notion-shaped) | ★★ |
| Mintlify | $300/mo Pro (5 editors) | Built-in AI search | Excellent | High but Mintlify-shaped | ★★ (overkill at our scale) |
| GitBook | $65/mo Premium + $12/extra user | Built-in | Good | Medium | ★★ |
| Docusaurus | $0 | Algolia DocSearch | Excellent | Highest | ★★★ (more JS/React surface than MkDocs) |
| ReadMe | ~$99+/mo | Built-in | Good | High; API-doc-shaped | ★★ |
| Self-hosted on Cloudflare Pages | $0 | Whatever you build | Excellent | Highest | ★★★★ (already implied — host MkDocs there) |

**Pick: MkDocs Material, hosted on Cloudflare Pages.** You already use it for dev docs (per ROADMAP line 45). Single source of truth. The "help center" is just a `/help/` directory in the same repo with a sidebar nav for end users. Built-in search is fine until ~200 docs pages; at that point flip on Algolia DocSearch (free for technical projects, just adds an `<algolia/>` directive).

**Migration path:** none needed. Same tool from 10 → 1000 customers.

**Boring alt:** Notion published pages. Faster to write in but worse SEO (you want "rhino make2d line weights" Google traffic to find you). Skip.

Sources: [MkDocs Material](https://squidfunk.github.io/mkdocs-material/), [Mintlify pricing](https://www.mintlify.com/pricing), [GitBook pricing](https://www.gitbook.com/pricing), [Algolia DocSearch](https://docsearch.algolia.com/), [Cloudflare Pages](https://pages.cloudflare.com/).

### 3. Status page

| Option | Cost | Features | Reliability |
|---|---|---|---|
| **Homepage notice** | $0 | A `<div>` you flip on/off | As reliable as your homepage |
| **Better Stack free** | $0 | Public status page, branded, dark mode, basic uptime monitoring, email/Slack alerts | High (their CDN, separate from yours) |
| **Instatus Pro** | $15/mo (yearly) | 50 monitors, 30-s checks, SMS alerts, multi-page | High |
| Statuspage.io (Atlassian) | $29/mo Hobby → $399/mo Business | Subscriber count limits; per-page pricing got worse in 2024 | Highest brand recognition |
| Cachet self-hosted | Hetzner $5/mo | Open source; you host it (irony: status page that goes down with the rest) | **Bad** — defeats the purpose |

**Pick at 10 users: just a homepage notice** + a Twitter/X account where you announce outages. You don't have any uptime to brag about yet. A status page reading "All systems operational, 1 incident in 30 days" with no traffic is theater.

**Pick at 100 users: Better Stack free.** Public branded page, included with their uptime monitoring (which you should be using anyway). Free covers the indie use case completely.

**Pick at 1000 users: Instatus Pro ($15/mo).** When studio customers (Phase F3) start asking "do you have a status page" in procurement Q&A. SMS alerts are useful when you're solo and need to know about outages while away from the laptop.

**Avoid:** Statuspage.io. Atlassian moved per-page pricing to $300+/mo for audience-specific pages in the last cycle and the indie pricing is no longer competitive.

Sources: [Better Stack pricing](https://betterstack.com/pricing), [Instatus pricing](https://instatus.com/pricing), [Statuspage pricing](https://www.atlassian.com/software/statuspage/pricing).

### 4. Live chat

| Option | Cost | When it pays off | Risk |
|---|---|---|---|
| **Skip** | $0 | Always for v1; usually for v2 | None — async support is fine |
| Tawk.to | $0 (with branding); $29/mo to remove | Free is genuinely free | Constant chat-presence pressure |
| Crisp | Free (2 seats) → €45/mo Mini | When live chat noticeably converts trial → paid | Inbox bloat |
| Intercom | $39+ Essential, scales fast | Never at our scale | Pricing trap |
| Plain (chat) | bundled $35/seat | If you're already on Plain | None marginal |

**Pick: Skip live chat entirely until 1000+ customers.** Live chat adds:
- A psychological obligation to be online
- Fragmented inbox (chat + email + community)
- Conversion lift that usually evaporates for asynchronous-by-nature tools (architects upload a drawing, wait for processing, leave)

Your customer doesn't need real-time. They need (a) good docs, (b) a fast-enough email response, (c) a roadmap they can vote on.

**If you ever turn it on:** Crisp Mini (€45/mo) for the privacy posture (EU-hosted) and the Startup Program 30% lifetime discount if you qualify (<$1M funding, <3 yrs old).

Sources: [Crisp pricing](https://crisp.chat/en/pricing/), [Tawk.to pricing](https://www.tawk.to/pricing/).

### 5. In-product feedback widget

| Option | Cost (free tier) | Cost (paid) | Solo-founder fit |
|---|---|---|---|
| **Featurebase Free** | $0 (1 board, unlimited end-users, 100 changelog emails/mo, 50 KB articles) | $29/seat/mo Starter | ★★★★★ |
| Frill | Has free tier | ~$25–49/mo | ★★★★ |
| Canny | Free up to 100 tracked users | $79–99/mo Pro at 100; scales hard ($579/mo at 1250 users) | ★★ (pricing trap) |
| Roll your own | $0 | engineering time | ★★ |
| Skip | $0 | $0 | ★★★ until ~50 users |

**Pick at 10 users: Skip.** Track feedback in a Notion table, an Obsidian note (you already use it), or a `feedback.md` in the repo. With 10 customers, you remember every conversation.

**Pick at 100 users: Featurebase Free** ($0). Public roadmap + voting widget + changelog all in one. Free covers everything you need until the seat count grows. The fact that Featurebase publishes their own pricing breakdowns of competitors is a green flag for transparency.

**Pick at 1000 users: Featurebase Starter ($29/seat/mo)** — adds embeddable widgets and 4 boards. Stays cheap. **Avoid Canny** above 100 tracked users — switched in May 2025 to per-tracked-user pricing that punishes growth (Pro: $79 at 100 users → $579 at 1250 users).

Sources: [Featurebase pricing](https://www.featurebase.app/pricing), [Frill pricing](https://frill.co/pricing), [Canny pricing](https://canny.io/pricing).

### 6. Community forum

| Option | Cost | When it pays off |
|---|---|---|
| **Skip** | $0 | Until you have ≥50 active users posting to each other |
| **GitHub Discussions** | $0 | When customers start emailing the same questions; opens a public Q&A surface |
| Discord | $0 | If your customer base skews younger / hobbyist; conversations are ephemeral |
| Discourse cloud | $50+/mo Standard | When forum traffic justifies it (rarely <500 users) |
| Discourse self-hosted | $15 hosting + $15 SMTP = $30/mo | If you want full control + can do ops |

**Pick at 10 users: Skip.** A community of 10 is silent and feels dead, which is worse than no community.

**Pick at 100 users: GitHub Discussions.** Free, integrated with the (eventually public) repo, customers searching Stack Overflow / Google find answers. The asynchronous, archived-forever shape fits architects better than Discord's chat-disappears-into-scrollback shape.

**Pick at 1000 users: GitHub Discussions still, OR Discord** if studio-tier customers are asking for real-time. Most architecture studios are async-tolerant; lean Discussions.

**Discourse:** skip — wrong shape for our scale and adds ops burden.

Sources: [GitHub Discussions](https://docs.github.com/en/discussions), [Discourse pricing](https://www.discourse.org/pricing).

### 7. Knowledge base / FAQ search

| Option | Cost | Quality | Solo-founder fit |
|---|---|---|---|
| **MkDocs built-in (lunr.js)** | $0 | Good up to ~200 pages | ★★★★★ |
| **Algolia DocSearch** | $0 (free for technical projects) | Excellent | ★★★★★ |
| Inkeep AI | ~$150+/mo | AI-powered, expensive | ★★ |
| Plausible/PostHog "search" | $0 | Not actually search — analytics on what people search | ★ |

**Pick at 10 users: MkDocs built-in lunr.js.** Already there.

**Pick at 1000 users: Algolia DocSearch** (free). Drop-in upgrade, indexes your MkDocs site, returns instant search-as-you-type. Apply for free tier; approval takes ~1–2 weeks.

**Skip Inkeep** at every scale shown — $150+/mo for AI-search is poor ROI when DocSearch is free.

Sources: [Algolia DocSearch](https://docsearch.algolia.com/docs/docsearch-program/), [Inkeep pricing](https://docs.inkeep.com/cloud/faqs/pricing).

### 8. Customer onboarding flow (in-product)

| Option | Cost | Setup | Solo-founder fit |
|---|---|---|---|
| **Roll-your-own checklist** | $0 | 1 day SvelteKit component | ★★★★★ |
| Userflow | $240+/mo (3k MAUs) | Days | ★★ |
| Userpilot | $299+/mo | Days | ★ |
| Appcues | $249+/mo | Days | ★ |
| Skip | $0 | 0 | ★★★ |

**Pick at every scale: roll-your-own.** A 4-item checklist component on the dashboard ("Upload first drawing → Apply hierarchy → Download → Share feedback") is ~80 lines of Svelte. The off-the-shelf onboarding tools are priced for Series-A consumer SaaS, not indie tools.

The single best onboarding asset for arch-line-weights is a **2-minute Loom video** showing input drawing → output drawing, embedded on the dashboard for first-time users. Cheaper, more honest, more architect-friendly than a tooltip tour.

Sources: [Userflow pricing](https://www.userflow.com/pricing), [Appcues pricing](https://www.appcues.com/pricing), [Userpilot pricing](https://userpilot.com/pricing).

## Cost projection — itemized monthly bill

### At 10 customers (~$120/mo MRR)

| Line item | Monthly |
|---|---|
| Gmail (personal account) | $0 |
| MkDocs Material on Cloudflare Pages | $0 |
| Status notice on homepage | $0 |
| GitHub Discussions (off until ~50 users) | $0 |
| Featurebase (off, just a Notion table) | $0 |
| **Total support stack** | **$0/mo** |
| % of MRR | 0% |

### At 100 customers (~$1,200/mo MRR target per saas-stack.md)

| Line item | Monthly |
|---|---|
| HelpScout Standard (1 user, annual) | $25 |
| MkDocs Material on Cloudflare Pages | $0 |
| Better Stack free | $0 |
| Featurebase Free | $0 |
| GitHub Discussions | $0 |
| **Total support stack** | **$25/mo** |
| % of MRR | 2.1% |

### At 1000 customers (~$12k/mo MRR target)

| Line item | Monthly |
|---|---|
| HelpScout Plus (2 users, annual) | $90 |
| MkDocs Material + Algolia DocSearch | $0 |
| Instatus Pro (yearly) | $15 |
| Featurebase Starter (1 seat) | $29 |
| Crisp Mini (optional, EU privacy) | €45 (~$48) |
| GitHub Discussions | $0 |
| **Total support stack (without Crisp)** | **$134/mo** |
| **Total support stack (with Crisp)** | **$182/mo** |
| % of MRR | 1.1–1.5% |

Adds ~1–2% of MRR at every scale, well under the typical 5–10% support spend benchmarks.

## Setup time per tool

| Tool | First-use setup |
|---|---|
| Gmail + labels | 30 min (labels, signature, canned replies) |
| HelpScout | 2 hr (workflows, mailbox forwarding, Docs site setup) |
| MkDocs Material | already done; per article ~30 min |
| Better Stack status page | 1 hr (incidents config, components, custom domain) |
| Instatus | 1 hr (similar) |
| Featurebase | 30 min (board + widget snippet) |
| Algolia DocSearch | 30 min once approved (1–2 wk wait) |
| GitHub Discussions | 5 min (toggle in settings) |
| Crisp | 1 hr (widget + auto-replies + EU region) |
| Roll-your-own onboarding | 1 day SvelteKit component + Loom video |

## Boring alternatives — the "skip the tool" column

| Category | Boring alt | Cost | Tradeoff |
|---|---|---|---|
| Inbox | Gmail + labels until 200+ tickets/wk | $0 | Loses team-handoff (irrelevant solo) |
| Docs | A single `FAQ.md` in the repo | $0 | Ugly, no nav, but ships in minutes |
| Status page | A `<div class="banner">` on homepage | $0 | No incident history, no subscribe |
| Live chat | Email link in footer | $0 | Slower response perception |
| Feedback | A Notion-shared "Roadmap" page | $0 | Manual upvote tally |
| Community | A pinned tweet "DM me with questions" | $0 | Doesn't archive |
| KB search | Cmd-F on the FAQ page | $0 | Bad once docs grow >5 pages |
| Onboarding | A 2-min Loom on the dashboard | $0 | Doesn't gate progress |

The "boring alt" stack at 10 customers is a viable launch posture for ~6 months.

## Integration matrix — does what we picked talk to each other?

|        | HelpScout | MkDocs | Better Stack | Featurebase | GitHub Discuss | Stripe | Plausible |
|--------|---|---|---|---|---|---|---|
| **HelpScout** | — | Docs site native | Webhook | Zapier | Email-based | Native cust info | n/a |
| **MkDocs**    | Embed | — | Embed widget | Embed widget | Link | n/a | Snippet |
| **Better Stack** | Webhook | Embed | — | Webhook | Manual | Webhook | n/a |
| **Featurebase** | Zapier | Embed | n/a | — | Manual | Webhook | Snippet |
| **GitHub Discussions** | Forward to HS | Link | n/a | Manual | — | n/a | n/a |

**Key integrations that matter:**
- HelpScout → MkDocs Docs site (native — same vendor) — single search box across help articles + tickets.
- Featurebase → SvelteKit widget on dashboard (script tag) — capture in-context feedback.
- Better Stack incidents → HelpScout auto-reply ("we're aware, ETA 30 min") via webhook + Zapier.
- All vendors have Stripe webhooks for syncing customer info.

The picked stack has zero "stuck" integrations. Every tool exposes either a webhook or a Zapier connector.

## Migration paths — when to upgrade each tier

| Current | Trigger to upgrade | Upgrade to |
|---|---|---|
| Gmail | ~25 active customers OR ~10 tickets/wk OR you forget which thread you replied to | HelpScout Standard ($25/user) |
| HelpScout Standard | Need AI summarization, multi-brand, advanced workflows | HelpScout Plus ($45/user) — at 1000 customers |
| MkDocs built-in search | >200 docs pages OR users complain "I can't find X" | Add Algolia DocSearch (free) |
| Homepage notice | Anyone asks "do you have a status page" | Better Stack free |
| Better Stack free | Need SMS alerts when you're AFK / studio-tier RFP requires multi-page | Instatus Pro ($15) |
| No feedback tool | First duplicate feature request | Featurebase Free |
| Featurebase Free | Need embeddable in-app widget | Featurebase Starter ($29) |
| Skip community | Same question asked 3 times in 30 days | GitHub Discussions |
| GitHub Discussions | Real-time feeling matters (studio tier) | Add Discord (free) — keep both |
| Skip live chat | Conversion analysis shows trial→paid drop AT signup page | Crisp Mini |
| Skip onboarding | Activation rate <40% at week 1 | Roll-your-own checklist; only consider Userflow if you ever cross 5000 MAU |

## Risks / unknowns

1. **HelpScout Docs lock-in.** If we use HS Docs (the bundled help-center), migrating away is annoying — articles are in their CMS. Mitigation: keep MkDocs as canonical, only use HS Docs as a customer-facing mirror. Or just don't use it and link MkDocs from HS replies.
2. **Featurebase pricing changes.** Indie tools can flip pricing aggressively (Canny did in May 2025 → per-tracked-user model). Mitigation: Featurebase's founder publishes pricing breakdowns of competitors on their own blog, suggests stability commitment, but watch.
3. **DocSearch approval lag.** Free tier requires Algolia application; takes 1–2 weeks. Mitigation: start using lunr.js, apply for DocSearch in parallel.
4. **Crisp EU residency.** Crisp is French-hosted, EU-native. If their data residency claims change, swap for self-hosted alternative or skip live chat entirely.
5. **Better Stack free tier** could be reduced. Mitigation: Instatus Pro at $15 is the clear backup.

## See also

- [`docs/ROADMAP.md`](../ROADMAP.md) — Phase F6 (customer support)
- [`docs/research/saas-stack.md`](saas-stack.md) — infra side; this doc is the support side
- [`docs/research/pricing-research.md`](pricing-research.md) — MRR targets
- [`docs/research/customer-interviews.md`](customer-interviews.md) — who we're supporting

## Sources

- [Plain pricing 2026](https://www.plain.com/pricing)
- [HelpScout pricing 2026](https://www.helpscout.com/pricing/)
- [Front pricing 2026](https://front.com/pricing)
- [Missive pricing 2026](https://missiveapp.com/pricing)
- [HEY for Domains pricing 2026](https://www.hey.com/pricing/)
- [Mintlify pricing 2026](https://www.mintlify.com/pricing)
- [GitBook pricing 2026](https://www.gitbook.com/pricing)
- [MkDocs Material](https://squidfunk.github.io/mkdocs-material/)
- [Algolia DocSearch program](https://docsearch.algolia.com/docs/docsearch-program/)
- [Better Stack pricing 2026](https://betterstack.com/pricing)
- [Instatus pricing 2026](https://instatus.com/pricing)
- [Atlassian Statuspage pricing 2026](https://www.atlassian.com/software/statuspage/pricing)
- [Crisp pricing 2026](https://crisp.chat/en/pricing/)
- [Tawk.to pricing 2026](https://www.tawk.to/pricing/)
- [Featurebase pricing 2026](https://www.featurebase.app/pricing)
- [Frill pricing 2026](https://frill.co/pricing)
- [Canny pricing 2026](https://canny.io/pricing)
- [Discourse pricing 2026](https://www.discourse.org/pricing)
- [Userflow pricing 2026](https://www.userflow.com/pricing)
- [Appcues vs Userpilot 2026](https://hopscotch.club/blog/appcues-vs-userpilot)
- [Inkeep pricing 2026](https://docs.inkeep.com/cloud/faqs/pricing)
