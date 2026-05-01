# SaaS payments comparison — monthly subscription pricing

> Sub-agent research, 2026-04-30. Inputs to Phase D web-app launch.
>
> This re-runs `distribution-platforms.md` against the new SaaS pricing
> ladder ($9 / $19 / $49 / $149 per month) instead of one-time tiers.
> Result: **Lemon Squeezy still wins for Phase D**, but the margin is
> tighter on the low-price tiers, and the Stripe break-even shifts
> meaningfully closer than under one-time pricing.

## TL;DR

| Phase | Recommendation | Why |
|---|---|---|
| **D — MVP, 10–100 customers** | **Lemon Squeezy** (MoR) | Compliance burden alone exceeds fee savings until ~500 subs. One person, one platform. |
| **F — public, 100–1000 customers** | **Lemon Squeezy until ~$8k+ MRR, then Stripe + Stripe Tax** | Crossover sits at ~$7–12k MRR depending on compliance cost. Migrate when revenue justifies a CPA. |
| **G — scale, 1000+ customers** | **Stripe + own infra + CPA + tax software** | Per-customer net revenue advantage compounds; fixed compliance cost amortizes. |

The key insight that's different from the one-time-tier analysis: at
**$9/mo**, Lemon Squeezy's flat $0.50 fee swallows **5.6%** of every
transaction on top of the 5% percentage — the *effective fee on a
$9 charge is 10.6%*, not 5%. The 50-cent fixed component dominates at
SaaS prices, especially the entry-tier.

This still favors Lemon Squeezy for Phase D because tax compliance for
DIY Stripe runs ~$2–5k/yr in fixed cost (CPA + filings + sales-tax
software), which exceeds the fee savings until you're at ~500
subscribers blended ARPU $19/mo. **Compliance, not fees, is the
deciding factor at Phase D scale.**

## 1. Per-transaction fees at SaaS price points

Sources (all checked 2026-04-30):
- [Lemon Squeezy pricing](https://www.lemonsqueezy.com/pricing) — 5% + $0.50
- [Paddle pricing](https://www.paddle.com/pricing) — 5% + $0.50 (Paddle Billing); historic 10% tier deprecated for SaaS
- [Stripe pricing](https://stripe.com/pricing) — 2.9% + $0.30 (US online cards); + [Stripe Tax](https://stripe.com/tax) — 0.5% per tx
- [FastSpring pricing](https://fastspring.com/pricing/) — 5.9% + $0.95 (or 8.9% flat, lower volume)
- [Gumroad fees](https://help.gumroad.com/article/67-gumroad-fees) — 10% + $0.50 (single flat tier as of 2024 simplification; no longer 5%/9%/etc.)

### Fee per single monthly transaction

| Platform | $9 tx | $19 tx | $49 tx | $149 tx |
|---|---|---|---|---|
| Lemon Squeezy (5% + 50¢) | $0.95 | $1.45 | $2.95 | $7.95 |
| Paddle (5% + 50¢) | $0.95 | $1.45 | $2.95 | $7.95 |
| Stripe + Tax (3.4% + 30¢) | $0.61 | $0.95 | $1.97 | $5.37 |
| FastSpring (5.9% + 95¢) | $1.48 | $2.07 | $3.84 | $9.74 |
| Gumroad (10% + 50¢) | $1.40 | $2.40 | $5.40 | $15.40 |

### Effective fee percentage

| Platform | $9 | $19 | $49 | $149 |
|---|---|---|---|---|
| Lemon Squeezy | **10.6%** | 7.6% | 6.0% | 5.3% |
| Paddle | **10.6%** | 7.6% | 6.0% | 5.3% |
| Stripe + Tax | 6.7% | 5.0% | 4.0% | 3.6% |
| FastSpring | 16.5% | 10.9% | 7.8% | 6.5% |
| Gumroad | 15.6% | 12.6% | 11.0% | 10.3% |

The **$9 tier is brutal on flat-fee platforms**. 10.6% to LS/Paddle is
the SaaS reality at that price; you simply cannot offer $9/mo without
accepting that. The student tier is a marketing/funnel decision, not a
margin decision.

### Net revenue per customer per year (12 monthly payments)

| Platform | $9/mo ($108/yr) | $19/mo ($228/yr) | $49/mo ($588/yr) | $149/mo ($1,788/yr) |
|---|---|---|---|---|
| Lemon Squeezy | $96.60 | $210.60 | $552.60 | $1,692.60 |
| Paddle | $96.60 | $210.60 | $552.60 | $1,692.60 |
| Stripe + Tax | **$100.73** | **$216.65** | **$564.41** | **$1,723.61** |
| FastSpring | $90.23 | $203.15 | $541.91 | $1,671.11 |
| Gumroad | $91.20 | $199.20 | $523.20 | $1,603.20 |

Stripe-vs-LS delta per year, per customer:
- $9 tier: **+$4.13**
- $19 tier: **+$6.05**
- $49 tier: **+$11.81**
- $149 tier: **+$31.01**

That's the *gross* fee advantage. Compliance cost has to come out of it
before you compare apples to apples — see §3.

## 2. Annual revenue impact at scale

Blended ARPU $19/mo (most likely Phase F mix: lots of personal at $9–19,
a few studios at $49+; assume blended $19 for math).

| Subscribers | Gross/yr | LS net | Paddle net | Stripe+Tax net (before compliance) | FastSpring net | Gumroad net |
|---|---|---|---|---|---|---|
| 100 | $22,800 | $21,060 | $21,060 | $21,665 | $20,315 | $19,920 |
| 500 | $114,000 | $105,300 | $105,300 | $108,325 | $101,575 | $99,600 |
| 1,000 | $228,000 | $210,600 | $210,600 | $216,650 | $203,150 | $199,200 |

Stripe-vs-LS gross fee advantage at scale:
- 100 subs: $605 — way under any compliance cost. **LS wins net.**
- 500 subs: $3,025 — roughly equals mid-estimate compliance. **Coin flip.**
- 1,000 subs: $6,050 — clearly above compliance. **Stripe wins net.**

## 3. Operational burden matrix

What does each platform actually do for you operationally? At
recurring-billing scale, the "platform does it" boxes are worth
multiples of the fee delta.

| Capability | Lemon Squeezy | Paddle | Stripe (raw) | Stripe + Stripe Tax | FastSpring | Gumroad |
|---|---|---|---|---|---|---|
| **MoR** (handles global tax registration & filing) | ✅ Yes | ✅ Yes | ❌ No | ❌ No (Tax helps with calc/report only) | ✅ Yes | ❌ No (removed 2022) |
| **Subscription billing primitives** | ✅ Mature | ✅ Mature | ✅ Best-in-class (Billing) | ✅ Best-in-class | ✅ Mature | ⚠️ Bolted on |
| **Failed-payment dunning** (smart retry, customer email) | ✅ Built-in | ✅ Built-in | ⚠️ Configurable, you tune | ⚠️ Configurable | ✅ Built-in | ⚠️ Basic |
| **Customer self-service portal** (cancel, upgrade, change card) | ✅ Hosted | ✅ Hosted | ✅ Customer Portal (free, hosted) | ✅ Customer Portal | ✅ Hosted | ⚠️ Limited |
| **License-key API** | ✅ Native | ⚠️ Via partner (e.g. Keygen) | ❌ Build yourself | ❌ Build yourself | ✅ Native | ⚠️ Manual / Zapier |
| **Webhook reliability in production** (per public SLOs and indie reports) | ✅ Good (Svix-backed retries) | ✅ Good | ✅ Excellent (industry reference) | ✅ Excellent | ⚠️ Mixed reports | ⚠️ Mixed |
| **Refund / dispute handling** | ✅ Platform fights chargebacks | ✅ Platform fights | ❌ You fight every dispute | ❌ You fight every dispute | ✅ Platform fights | ⚠️ Limited |
| **EU VAT MOSS** | ✅ They register | ✅ They register | ❌ You register (then Stripe Tax calculates) | ❌ You register | ✅ They register | ❌ You register |
| **US sales tax (45+ states)** | ✅ They register | ✅ They register | ❌ You register | ⚠️ Stripe Tax monitors thresholds, you register | ✅ They register | ❌ You register |
| **UK VAT (post-Brexit, separate from EU)** | ✅ They register | ✅ They register | ❌ You register | ❌ You register | ✅ They register | ❌ You register |
| **Customer invoices / receipts (tax compliant)** | ✅ Auto | ✅ Auto | ⚠️ You configure | ⚠️ You configure with Tax | ✅ Auto | ✅ Auto |
| **Affiliate program** | ✅ Built-in | ⚠️ Add-on | ❌ Build yourself or PartnerStack | ❌ | ✅ Built-in | ✅ Built-in |
| **Annual billing option** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Multi-currency (display + settlement)** | ✅ 130+ currencies, settles in your local | ✅ | ✅ | ✅ | ✅ | ⚠️ Limited |
| **3DS / fraud handling** | ✅ Platform | ✅ Platform | ⚠️ Stripe Radar (extra 5¢/tx for advanced) | ⚠️ Stripe Radar | ✅ Platform | ⚠️ Limited |

Specific notes per platform on the SaaS-recurring axis:

### Lemon Squeezy
- **Dunning:** "Smart Dunning" retries 3 times over ~7 days, then
  marks subscription past_due, then cancels. Email cadence built in.
- **Customer portal:** hosted at `app.lemonsqueezy.com/my-orders` — works
  but is generic. No deep customization.
- **Tax burden on you:** **zero**. They are MoR for all jurisdictions
  they list (US, EU, UK, AU, CA, NZ, JP, SG, IN). Some smaller markets
  not covered — they'll let you know if a sale is in a non-supported
  jurisdiction.
- **Webhooks:** Svix-powered (industry-standard reliability infra).
  Retry up to 24h on 5xx, exponential backoff. Public retry log in
  dashboard. Indie reports: solid in 2024-2026.
- **Refunds:** they pre-issue and recharge you; chargebacks they fight
  on your behalf, you keep more of net revenue than DIY.
- **Subscription primitives:** prorated upgrades, downgrades, pausing,
  trials, coupon codes, free-tier-with-upgrade. All in the dashboard.

### Paddle
- Functionally similar to LS in 2026 (Paddle Billing replaced Paddle
  Classic in 2023; modern API). Slightly better B2B / invoicing
  features (NET-30, custom POs, multi-seat).
- Onboarding takes longer (compliance review). LS approves in hours;
  Paddle in 1–5 business days.
- For a Phase D solo founder, LS lower friction; for a Phase G B2B push,
  Paddle's enterprise muscle is preferable.

### Stripe + Stripe Tax
- **You** are the merchant of record. **You** sign up for sales tax in
  every state where you cross economic nexus thresholds (most are
  $100k/yr or 200 transactions, except CA = $500k, TX = $500k, NY =
  $500k, etc. — see [Sales Tax Institute thresholds](https://www.salestaxinstitute.com/resources/economic-nexus-state-guide)).
- **Stripe Tax (0.5%/tx)** monitors your nexus thresholds, calculates
  per-jurisdiction rates, prepares filings. **It does not register or
  file for you.** That's still your CPA's job.
- **Stripe Tax filing service** (US-only, in beta as of late 2025,
  costs extra $X/state/filing) — once GA, this changes the math
  meaningfully toward Stripe at lower scale. Watch this.
- **Customer Portal** is free and hosted: pause subscription, change
  card, see invoices, cancel — all from a hosted page. As good as LS's.
- **Smart Retries** (formerly "Recover") — built into Billing, retries
  failed payments with ML-tuned timing. Free.
- **Refunds and disputes:** **you** fight every chargeback. Stripe
  Radar (free tier) helps; Radar for Fraud Teams (5¢/tx extra) helps
  more. At indie scale, you'll see a chargeback every ~$5–10k revenue;
  losing a few isn't catastrophic but the time cost is real.

### FastSpring
- Strongest if you have desktop/installer software with license-key
  enforcement. For a web SaaS, the 5.9% + 95¢ rate is just worse than
  LS at every price point you're considering.
- Plus: enterprise / B2B / NET-30 features.
- Reject for v1.

### Gumroad
- **No MoR since 2022.** That's the killer. You're now responsible for
  every jurisdiction yourself, *and* paying 10% + 50¢ — worst of both.
- Subscription support is bolted-on rather than first-class — no
  smart-dunning, weak portal, weak webhook story.
- Reject.

## 4. Break-even analysis: Stripe + Stripe Tax vs Lemon Squeezy

**Variables:**
- N = number of subscribers
- ARPU = average revenue per user per month (in $)
- A = annual revenue = 12 × ARPU × N
- T = total transactions per year = 12 × N (monthly billing)
- C = annual fixed compliance cost when self-MoR (CPA + sales-tax
  registrations + filings + tax-software). Estimate range: **$2,000
  low, $3,000 mid, $5,000 high.**

**Annual cost on each platform:**
- LS: 0.05 × A + 0.50 × T = 0.05A + 0.50T
- Stripe + Tax: 0.034 × A + 0.30 × T + C = 0.034A + 0.30T + C

**Crossover (LS cost = Stripe cost):**

```
0.05A + 0.50T = 0.034A + 0.30T + C
0.016A + 0.20T = C
```

Substituting A = 12 × ARPU × N and T = 12N:

```
0.016 × 12 × ARPU × N + 0.20 × 12 × N = C
(0.192 × ARPU + 2.40) × N = C
N = C / (0.192 × ARPU + 2.40)
```

**Crossover subscriber count by ARPU and compliance cost:**

| ARPU (mo) | C = $2,000 | C = $3,000 | C = $5,000 |
|---|---|---|---|
| $9 | 484 | 727 | 1,211 |
| $14 (blended low) | 388 | 582 | 970 |
| $19 (blended mid) | 331 | 496 | 827 |
| $29 | 245 | 367 | 612 |
| $49 (studio-5) | 169 | 254 | 423 |
| $79 | 122 | 183 | 305 |
| $149 (studio-20) | 70 | 105 | 175 |

**Translated to MRR at crossover:**

| ARPU | C = $3,000 (mid) | MRR at crossover |
|---|---|---|
| $9 | 727 subs | **$6,540/mo** |
| $19 | 496 subs | **$9,420/mo** |
| $49 | 254 subs | **$12,450/mo** |
| $149 | 105 subs | **$15,640/mo** |

**Sanity check** at the realistic Phase F target (Phase F success = $1k+
MRR per ROADMAP gate; mid-Phase F = $5–10k MRR):
- At $5k MRR blended-$19, that's ~263 subs. Below the 496-sub crossover.
  **LS still wins net.**
- At $10k MRR blended-$19, that's ~526 subs. Just past 496-sub crossover.
  **Stripe begins to win net.**
- At $15k MRR blended-$19, that's ~789 subs. **Stripe clearly wins.**

**The break-even is around $7–12k MRR depending on ARPU mix and
compliance assumptions.** That maps to year 1.5–year 2.5 of the SaaS
in the realistic-growth roadmap, which is also when the founder would
plausibly hire/contract a CPA anyway. Coincides nicely with natural
scaling milestones.

### Sensitivity to compliance cost

The whole break-even hinges on C. Realistic decomposition for a
US-domiciled solo founder selling globally:

| Compliance line item | Low / DIY | Mid / sane | High / outsourced |
|---|---|---|---|
| US state sales tax (5–10 states triggered) — registration $50–300 each, filings via TaxJar/Avalara/Stripe-Tax-Filing | $500 | $1,000 | $2,000 |
| EU OSS (one-stop-shop, register in Ireland) — quarterly filings via local accountant | $0 (DIY) | $700 | $1,500 |
| UK VAT — registration free, quarterly filings | $200 | $400 | $800 |
| Australia GST — once over A$75k threshold | $0 below threshold | $300 | $600 |
| Canada GST/HST/PST | $0 below threshold | $200 | $500 |
| Tax software subscription (TaxJar, Quaderno, Stripe Tax bundles) | $200 | $400 | $1,000 |
| Time (founder hours @ $0 self-cost or $50/hr opportunity cost) | "Free" / hidden | $1,000 hidden | (folded into above) |
| **Total estimate** | **~$900** | **~$3,000** | **~$5,400** |

The "low" column assumes DIY everything and treats founder time at
$0. **That's the wrong framing.** A founder doing tax filings is not
shipping product. Use the mid-column ($3k) for honest comparison.

## 5. Phase D recommendation: Lemon Squeezy

**Decision: launch Phase D on Lemon Squeezy. No change from prior
recommendation; the SaaS pricing reanalysis confirms it.**

Reasons:

1. **Compliance burden far exceeds fee delta at Phase D scale**
   (10–100 subs, $1–2k MRR). At 100 subscribers blended-$19 ARPU, gross
   fee delta is ~$605/yr; compliance cost is $2–5k/yr. Net advantage
   for LS: ~$1.5–4k/yr in your pocket. Plus the time you don't spend
   becoming an amateur tax accountant.
2. **One platform, one integration.** LS handles checkout, subscription
   primitives, dunning, customer portal, license keys, affiliate
   program, webhooks, EU VAT, US sales tax, UK VAT, AU GST, CA GST.
   Stripe-equivalent requires Stripe + Stripe Tax + custom license-key
   service + custom affiliate handling + jurisdiction-by-jurisdiction
   tax registration. The integration time difference is days vs weeks.
3. **The ~Stripe-acquired LS** (2024) means a future Stripe migration is
   plausible: same parent company, similar primitives, customer
   migration tooling likely to improve over time.
4. **The $9-tier exception** — yes, 10.6% effective fee on $9 charges
   stings. But (a) the $9 tier is a funnel/marketing tool, not a margin
   tier, (b) Stripe at the same $9 charge is still 6.7% effective —
   *not free* — and (c) you'll never sell a customer for whom $0.34/mo
   in fees is the dealbreaker.

The previous one-time-tier analysis recommended LS for Phase D and
Stripe at $2-3k MRR. Under SaaS pricing, the Stripe-migration trigger
shifts upward to **$8–12k MRR**, because:

- Recurring billing primitives, dunning, and customer portal — all of
  which LS gives you free — are a much bigger operational savings under
  monthly billing than under one-time. With one-time, you don't need
  dunning at all.
- The flat-50¢ fee component dominates at low ARPU, but compliance
  fixed cost dominates at low subscriber counts. Both factors push the
  crossover later than the one-time analysis.

**Action items for Phase D distribution v1 (revised from
`distribution-platforms.md` Phase D plan):**

1. Create Lemon Squeezy account; verify identity (1–3 days).
2. Set up storefront with **subscription** products (not one-time):
   - Student — $9/mo (limit 100 stock for the founder cohort; raise
     to general avail at $14/mo after)
   - Personal — $19/mo
   - Studio (≤5 seats) — $49/mo
   - Studio (≤20 seats) — $149/mo
   - Annual variants at 2-month discount (10× monthly price)
3. **Free trial** — 14-day trial with credit card upfront (not "no card";
   trials without cards have ~10% conversion vs 30% with). LS supports
   this natively.
4. Configure license-key API + per-seat counts on studio plans.
5. Build a tiny `license-server` (Cloudflare Worker or Fly.io app) that:
   - Receives `subscription_created`, `subscription_updated`,
     `subscription_payment_failed`, `subscription_cancelled` webhooks
   - Stores `account_id → tier → seat_count → status` in Postgres / KV
   - Exposes auth-token-issuing endpoint for the web app frontend
   - Exposes `POST /validate` for any future CLI tool
6. Web app reads the LS-issued auth state on login. Hard pause when
   `status = past_due > 7 days`. Soft warn during dunning window.
7. Email Phase C interviewees a "Founders 100" code (50% lifetime).
8. Don't go public yet — private beta only. Public launch is Phase F.

## 6. Phase F migration plan: Lemon Squeezy → Stripe + Stripe Tax

When MRR crosses ~$8–10k (~year 2 in the optimistic plan), the math
flips. Migrate carefully — don't break customers.

### What stays vs what moves

| Component | Strategy |
|---|---|
| **Existing LS customers** | **Stay on LS.** Do not force-migrate. They keep their subscription on LS until they churn or voluntarily switch plans. Gradual fade. |
| **New customers** | Sign up via Stripe + Stripe Tax. New checkout flow. |
| **License-key DB** | Already platform-agnostic if you built it right (§5 step 5) — a license belongs to an account, not a platform. Webhook handlers add a Stripe handler alongside the LS handler; both write to the same `accounts` table. |
| **Customer portal** | Two portals during transition: LS-hosted for legacy, Stripe-hosted for new. Linked from your app's account-settings page based on `payment_provider` field. |
| **Pricing pages** | Update marketing site to point to Stripe Checkout for new signups. LS continues serving renewals to legacy customers. |

### Migration timeline (3–6 months)

**Month 1: Stripe + Stripe Tax setup, parallel infrastructure.**
- Sign up for Stripe; complete Stripe Tax setup (define product
  tax codes, monitor nexus thresholds).
- Hire CPA to advise on initial registrations: US states already over
  threshold (Stripe Tax tells you which), EU OSS via Ireland or other,
  UK, AU/CA if past thresholds. Budget 2–4 weeks elapsed.
- Build Stripe webhook handler that mirrors the LS handler.
- Deploy to staging; test end-to-end with real test cards.

**Month 2: Cutover for new customers.**
- Switch marketing-site CTAs from LS Checkout to Stripe Checkout.
- LS storefront still alive, but no longer linked. Existing customer
  renewals continue working.
- Monitor: webhook reliability, dunning behavior, churn metrics. Run a
  small cohort of new signups (10–20) before opening fully.

**Month 3–6: Optional carrot to migrate legacy LS customers.**
- Offer a "1 month free" credit to any LS customer who voluntarily
  re-subscribes via Stripe. This is the *only* way to move them
  cleanly — you cannot transfer a card token between platforms.
- Email cadence: 3 emails over 60 days. Don't pressure.
- Expect ~30–50% to switch in 6 months; rest will switch when their
  card expires or they want to change plans.

### Customer impact

| Customer type | What they experience |
|---|---|
| **Legacy LS, no action** | Nothing changes. Same renewal email, same portal link, same charge. |
| **Legacy LS, voluntary migrate** | Cancel LS subscription, sign up via Stripe, get 1 month free credit. Same product access. |
| **Legacy LS, card expires** | LS dunning fires; if they don't update card, they get an "update via new portal (Stripe)" email instead. |
| **New customer post-cutover** | Stripe Checkout, Stripe Customer Portal. Slightly different UI from LS. |
| **Anyone changing plans** | Routed to Stripe; LS subscription cancelled, new Stripe subscription provisioned with credit for unused LS time. |

**Risks:**
- **License-key DB drift.** Mitigation: integration tests that exercise
  both platforms' webhooks before cutover. End-to-end test cases for
  trial → paid → upgrade → cancel → reactivate on each platform.
- **Tax over-collection during transition.** LS collects + remits; once
  on Stripe + Stripe Tax, *you* must register before crossing
  thresholds. Mitigation: Stripe Tax's threshold monitor alerts you
  ~$10k below the trigger; CPA pre-registers in the high-volume states
  (CA, TX, NY, FL, IL) before they trigger.
- **Disputes / chargebacks.** LS fights them for legacy customers;
  Stripe customers are your fight now. Mitigation: enable Stripe Radar
  (free), use 3DS where Strong Customer Authentication applies (EU/UK
  required, US optional), keep transaction descriptors clear so
  customers recognize the charge.
- **Migration fatigue.** Don't move all 1000 customers in a weekend.
  Slow cohort migration with real monitoring.

### What never gets migrated

- **License-key tokens.** They live in your DB, not on either platform.
- **Customer accounts.** They live in your DB.
- **Drawing files.** They live in your object store.
- **Payment cards.** Cannot move between platforms (PCI rules).
  Customer must re-enter on the new platform — this is the source of
  friction in any migration.

## 7. Sources (all checked 2026-04-30)

- [Lemon Squeezy pricing](https://www.lemonsqueezy.com/pricing)
- [Lemon Squeezy MoR explainer](https://www.lemonsqueezy.com/blog/merchant-of-record-101)
- [Lemon Squeezy webhooks docs](https://docs.lemonsqueezy.com/api/webhooks)
- [Paddle pricing](https://www.paddle.com/pricing)
- [Paddle Billing migration guide](https://www.paddle.com/blog/paddle-billing) — context that legacy "Paddle Classic" 10% tier is no longer offered to new sellers in 2026
- [Stripe pricing](https://stripe.com/pricing)
- [Stripe Tax overview](https://stripe.com/tax)
- [Stripe Customer Portal](https://stripe.com/docs/billing/subscriptions/customer-portal)
- [Stripe Smart Retries](https://stripe.com/docs/billing/revenue-recovery/smart-retries)
- [Stripe Radar pricing](https://stripe.com/radar) — free tier vs Radar for Fraud Teams (5¢/tx)
- [FastSpring pricing](https://fastspring.com/pricing/)
- [Gumroad fees](https://help.gumroad.com/article/67-gumroad-fees) — single 10%+50¢ tier post-2024 simplification
- [Sales Tax Institute — economic nexus thresholds](https://www.salestaxinstitute.com/resources/economic-nexus-state-guide)
- [South Dakota v. Wayfair (2018)](https://www.salestaxinstitute.com/resources/wayfair-decision)
- [EU VAT OSS — Commission overview](https://taxation-customs.ec.europa.eu/taxation/vat/vat-e-commerce_en)
- [HMRC VAT for digital services post-Brexit](https://www.gov.uk/guidance/vat-on-services-from-the-uk-to-overseas-customers)
- [TaxJar](https://www.taxjar.com/) and [Quaderno](https://www.quaderno.io/) — third-party tax compliance for self-MoR setups

## 8. Related

- `docs/research/distribution-platforms.md` — original (one-time-tier) comparison; Lemon Squeezy still recommended; this doc supersedes it for SaaS pricing
- `docs/research/pricing-research.md` — willingness-to-pay; informs the price points used here
- `docs/research/licensing.md` — EULA + key handling
- `docs/ROADMAP.md` Phase D5 — payment-provider decision (resolved in this doc: stay on LS)
- `docs/ROADMAP.md` Phase F — public launch + Stripe migration trigger ($8–12k MRR)
- `docs/BUSINESS.md` — segment-by-segment pricing tolerance
