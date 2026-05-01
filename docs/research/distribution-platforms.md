# Distribution platforms — Gumroad vs Lemon Squeezy vs Paddle vs Stripe

> Sub-agent research, 2026-04-30. Inputs to Phase D distribution v1.

## Recommendation

**Lemon Squeezy** for v1 (Phase D, month 2). Migrate to **Stripe + own
infra** at ~$2-3k/month revenue (around the time you'd hire help).

## Comparison matrix

| Platform | Per-tx fee | MoR? | License keys | Sub support | Best fit |
|---|---|---|---|---|---|
| **Gumroad** | 10% + 50¢ | ❌ No | Manual / via Zapier | Weak | One-shot drops, audience-driven |
| **Lemon Squeezy** ⭐ | 5% + 50¢ | ✅ Yes | ✅ Native API | ✅ Strong | Indie SaaS + tools, EU-compliant |
| **Paddle** | 5% + 50¢ or 10% | ✅ Yes | Via integration partners | ✅ Strong | Bigger SaaS, $50k+/yr |
| **FastSpring** | 5.9% + $0.95 | ✅ Yes | ✅ Yes | ✅ Strong | Enterprise / B2B desktop apps |
| **Stripe + own** | 2.9% + 30¢ | ❌ No | Build yourself | ✅ Strong | When volume justifies infra |

## Why Merchant of Record matters

A Merchant of Record (MoR) is the legal entity that sells to your
buyer. **Without an MoR**, you are responsible for:

- US sales tax in 45+ states (each with its own threshold and
  registration). Wayfair v. South Dakota (2018) makes you liable as
  soon as you cross thresholds.
- EU VAT MOSS (~$100/yr, quarterly filings, registration in any one
  EU country to cover the others).
- UK VAT registration (post-Brexit; separate from EU).
- Australian GST.
- Canadian GST/HST/PST per province.
- Chargeback handling.
- Fraud / 3DS compliance.

**With an MoR (Lemon Squeezy, Paddle, FastSpring)**, all of the above
becomes the platform's problem. They charge a higher per-tx fee — 2-3
percentage points more than Stripe — in exchange. That's worth it
until you're large enough to staff or outsource tax compliance.

Gumroad **is not** an MoR — they used to be, then they removed it in
2022. If you go Gumroad, you're on the hook for global sales tax.
This is the main reason against them.

## Lemon Squeezy — deep dive

### Pros

1. **Merchant of Record** — they handle global tax including EU VAT,
   UK VAT, US sales tax, Australian GST, etc.
2. **Native license-key API** — issue, validate, revoke license keys
   as part of checkout. Built for software vendors.
3. **Subscription support** — recurring billing, dunning, tax-inclusive
   pricing, customer portal.
4. **5% + 50¢** — cheaper than Gumroad (10% + 50¢) and Paddle's high
   tier (10%).
5. **Simple checkout** — embeddable JS or hosted page; no PCI compliance
   for you.
6. **Webhook ecosystem** — clean events for `order_created`,
   `subscription_updated`, etc. Integrates with Postmark, ConvertKit,
   Discord, Beehiiv out of the box.
7. **Affiliate program built-in** — pay other architects 20-30% commission
   to promote.
8. **Free trial / pre-order support** — built into product config.
9. **Strong indie reputation** — used by Tailwind UI, Astro, Resend,
   many indie tools in 2024-2026.

### Cons

1. **Newer than Stripe** (founded 2021) — less battle-tested.
2. **Acquired by Stripe** (2024) but operates independently. Implies
   long-term Stripe migration path is plausible.
3. **No 3-D Secure exemption** for low-fraud-risk transactions —
   marginally higher friction than raw Stripe.
4. **Less granular reporting** than Stripe Sigma.

### License-key flow

```
Buyer purchases → Lemon Squeezy issues license key (UUIDv4) →
  Webhook to your server → Local DB stores hash(key) →
    arch-lw on first run prompts for key →
      arch-lw POSTs to https://api.lemonsqueezy.com/v1/licenses/validate →
        Returns { valid: true, expires_at, instances_remaining } →
          arch-lw caches signed token (HMAC, 7-day TTL) →
            Re-validate on update or after TTL expires
```

For offline-first CLI: validate once online, cache HMAC-signed token
locally. No phone-home on every run.

## Gumroad — why not (for this project)

Gumroad is good for:
- Audience-driven creators (newsletter → product)
- One-time digital goods (PDFs, music, courses)
- Buyers who already trust the Gumroad brand

Bad fit here because:
- 10% + 50¢ is 2× Lemon Squeezy's fee
- No MoR — you eat global tax compliance
- No native license-key API (rolled-your-own via Zapier)
- Subscription support is bolted-on rather than first-class
- Developer experience (webhooks, API) is weaker

The only argument for Gumroad: zero setup time. Their checkout page
exists in 5 minutes. Lemon Squeezy takes 30. Not enough to justify
the trade-offs.

## Paddle — why not (yet)

Paddle is the heavyweight in the indie-SaaS space. They were the
default before Lemon Squeezy launched. Their fee is **5% + 50¢
($1k–10k/month tier)** or **10%** for low-volume sellers.

Reject because:
- Onboarding has more compliance friction (more docs, longer review).
- Their dashboard / API are more "enterprise" feeling — slower to
  iterate.
- The fee advantage (5% same as LS) only kicks in at scale we're not
  at yet.

Reconsider Paddle if:
- You hit $5k+/mo and want a more mature analytics dashboard.
- You want B2B-focused features (custom invoicing, NET-30 payment
  terms, vendor onboarding).
- A single enterprise architect studio asks for a custom contract;
  Paddle's invoicing is better for that than Lemon Squeezy's.

## Stripe + own — when to migrate

You graduate from MoR-platforms to Stripe when:

1. Revenue is **$2-3k+/month** and the MoR fee delta exceeds the cost
   of compliance tooling (Stripe Tax: 0.5%, Stripe Atlas, etc.).
2. You want **Stripe Atlas** for company formation in Delaware.
3. You're building a multi-product platform, not a single tool.
4. You hire help (CPA, lawyer) who can manage tax filings.

Stripe Tax (0.5% per tx) handles US states, EU VAT, UK VAT, etc.
**but** you still have to register in each jurisdiction yourself.
Stripe Tax calculates and reports; it doesn't register.

Migration is non-destructive:
- New customers go through Stripe.
- Lemon Squeezy customers stay on Lemon Squeezy until they re-buy.
- Webhooks from both platforms feed your same license-key DB.

## Phase D plan (Lemon Squeezy)

1. Create Lemon Squeezy account + verify identity (1-3 days).
2. Set up storefront with 4 products:
   - Founder 100 — $19 (limit 100 stock)
   - Student — $29
   - Personal — $79
   - Small Studio — $249/yr
3. Configure license-key API access.
4. Build a tiny `license-server` (a Cloudflare Worker or Vercel
   function) that:
   - Receives `order_created` webhooks from Lemon Squeezy
   - Stores `hash(license_key) → tier` in a KV store
   - Exposes `POST /validate` for `arch-lw` to check
5. In `arch-lw`, add `arch-lw activate <key>` command + offline cache.
6. Email Phase C interviewees a 50%-off launch code.
7. Post on Twitter/X, USC Discord, ArchDaily, Hacker News
   (probably HN: "Show HN: arch-line-weights — paid, not OSS").

## Phase F notes (Web app)

When the web app ships, Lemon Squeezy still works — you can mix
self-hosted CLI sales with web SaaS subscriptions in the same
storefront. They support both.

Migrate to Stripe when revenue justifies; until then, the MoR
overhead is worth more than the fee delta.

## Cost projection — Year 1

Assuming aggressive year 1 from `pricing-research.md` (~$20,830 gross):

| Item | Cost |
|---|---|
| Lemon Squeezy fees (5% + 50¢ × 570 tx) | ~$1,326 |
| Stripe alternative (2.9% + 30¢ × 570 tx + tax compliance) | ~$1,275 + $500 tax = $1,775 |
| **Lemon Squeezy net advantage** | **~$449** |

Conservative ($9,321 gross):

| Item | Cost |
|---|---|
| Lemon Squeezy fees (5% + 50¢ × 279 tx) | ~$606 |
| Stripe alt (2.9% + 30¢ × 279 + tax compliance) | ~$554 + $500 = $1,054 |
| **Lemon Squeezy net advantage** | **~$448** |

Lemon Squeezy is cheaper net-of-compliance until ~$30k+/yr. Easy call.

## Sources

- [Lemon Squeezy — pricing](https://www.lemonsqueezy.com/pricing)
- [Lemon Squeezy — license API docs](https://docs.lemonsqueezy.com/api/license-keys)
- [Lemon Squeezy — Merchant of Record explainer](https://www.lemonsqueezy.com/blog/merchant-of-record-101)
- [Paddle — Pricing](https://www.paddle.com/pricing)
- [Gumroad — Fees](https://help.gumroad.com/article/67-gumroad-fees)
- [Stripe Tax — overview](https://stripe.com/tax)
- [South Dakota v. Wayfair (2018) — sales tax thresholds](https://www.salestaxinstitute.com/resources/wayfair-decision)
- [EU VAT MOSS — Commission overview](https://taxation-customs.ec.europa.eu/taxation/vat/vat-e-commerce_en)

## Subscription pricing reanalysis (2026-04-30)

**Status:** This document was written assuming **one-time tiers** ($29 /
$79 / $249). The roadmap has since pivoted to **monthly subscription**
pricing ($9 / $19 / $49 / $149/mo). The fee math, operational burden,
and Stripe-migration trigger are all different under SaaS.

**For the SaaS-pricing analysis, see**
[`saas-payments-comparison.md`](saas-payments-comparison.md).

**Headline findings from the SaaS reanalysis:**

1. **Lemon Squeezy still wins for Phase D.** No change. Compliance cost
   alone (~$2–5k/yr to self-MoR via Stripe + CPA + tax software)
   exceeds gross fee savings until ~500 subscribers blended-$19 ARPU.
2. **The $9-tier is brutal everywhere.** Effective fee at $9 charge:
   LS/Paddle 10.6%, Stripe+Tax 6.7%, FastSpring 16.5%, Gumroad 15.6%.
   The flat 50¢ component dominates at SaaS prices.
3. **Stripe migration trigger shifted later.** Old recommendation:
   migrate to Stripe at ~$2–3k MRR. Under SaaS pricing:
   **migrate at $8–12k MRR** (depending on ARPU mix and compliance
   assumptions). Math, sources, and migration plan in
   `saas-payments-comparison.md`.
4. **Recurring billing primitives matter more than under one-time.**
   Dunning, customer portal, smart retries — all of which LS provides
   free — are operational savings worth more than the fee delta until
   you reach the migration threshold.

The Phase D plan in this document (one-time tiers, Founder 100 at $19
one-time, Student $29, Personal $79, Studio $249/yr) is **superseded**
by the subscription plan in `saas-payments-comparison.md` §5. The
license-key-server architecture in this document is still valid; it
just sits behind subscription webhooks instead of order webhooks.

## Related

- `docs/research/saas-payments-comparison.md` — **read this first for SaaS pricing**; supersedes Phase D plan in §149-167 above
- `docs/ROADMAP.md` Phase D — uses this directly
- `docs/research/binary-distribution.md` — what gets sold via the platform (still relevant for optional Phase F4 paid-CLI tier)
- `docs/research/licensing.md` — the EULA shipped with each license key
- `docs/research/pricing-research.md` — the prices the platform charges
