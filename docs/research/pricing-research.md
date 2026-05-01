# Pricing — indie architecture tools, 2026 anchors

> Sub-agent research, 2026-04-30. Inputs to Phase C demand validation
> (`docs/ROADMAP.md`). Pre-validation; replace gut numbers with interview
> data before locking the price page.

## Headline recommendation

| Tier | Price | Audience | Form | Notes |
|---|---|---|---|---|
| Founder 100 | $15–29 lifetime | First 100 buyers | One-time | Time-boxed; closes when 100 sold or 60 days pass |
| Student | $29 one-time | Segment 1 | One-time, .edu verify | Annual ID re-check optional |
| Personal | $79 one-time | Segment 2 | One-time | Includes 1 yr of updates; $19 to renew |
| Small studio | $249/yr | Segment 3 (≤20 seats) | Annual subscription | Per-office, not per-seat |
| Mid studio | TBD | Segment 3+ (>20 seats) | Quote | Wait until 3+ small-studio sales before pricing |

Tier ratio **1 : 2.7 : 8.5** (student : personal : studio). Matches the
empirical pattern in indie creative-tool pricing — student tier ≈ ⅓ of
personal, studio ≈ 3× personal.

## Why one-time over subscription (for the launch tier)

Indie architecture-school tools sell better as one-time purchases because:

1. **Buyer mental model.** Architects expect to buy a plug-in once
   (Astute Graphics historically, V-Ray, RhinoGold, etc.) — not rent
   it. Subscription fatigue is real in 2026.
2. **Low support cost.** A CLI tool with a license key has near-zero
   ongoing cost per customer. Subscription overhead (dunning, expiry,
   re-activation) is not worth it at <500 customers.
3. **Word-of-mouth amplification.** A $29 one-time is impulse-shareable
   in a studio Discord; $9/month is not.
4. **Refund pressure.** Subscriptions invite "I forgot to cancel" disputes;
   one-time + 14-day refund window is cleaner.

Switch to subscription **only** when you reach the SaaS web app (Phase F)
where ongoing cost (hosting, processing) justifies recurring revenue.

## Comparable anchors

### Direct adjacencies (architectural visualization / drafting plugins)

| Product | Price (2026) | Notes |
|---|---|---|
| Show It Better — Photoshop Action packs | $19–39 each | Single-purpose; users buy multiple |
| Show It Better — "Ultimate Bundle" | ~$129 | Stacks all packs, lifetime updates |
| Astute Graphics — single plugin | $79 | One-time, perpetual license |
| Astute Graphics — full bundle | ~$299/yr | Subscription, all 20+ plugins |
| VectorScribe (now Astute) | $79 | Historical anchor — perpetual one-time |
| Lands Design (Rhino plugin) | $795 perpetual or $385/yr | Pro tool, higher tier |
| Veras (AI render plug-in) | $19/month | Subscription; the rare exception |
| D5 Render Pro | $35/month | Real-time render, heavy infra cost |
| Enscape | $59.90/month or free for students | EDU-tier important precedent |

### Indirect anchors (creative tooling at the indie scale)

| Product | Price | Notes |
|---|---|---|
| Tot (Iconfactory) | $20 one-time | Reference for "small useful tool" pricing |
| Things 3 (Cultured Code) | $50 one-time | Top of "personal productivity" tier |
| Hookmark | $30 one-time + paid upgrades | Upgrade-cycle model |
| TablePlus | $89 one-time | Personal dev tools tier |
| Setapp ecosystem average | ~$10/month for many tools | Bundle pressure on standalones |

## Pricing math — Year 1 ceiling under each tier mix

Conservative (lower-half of segment volume estimates from
`docs/BUSINESS.md`):

| Tier | Price | Volume | Revenue |
|---|---|---|---|
| Founder 100 | $20 (mid) | 100 | $2,000 |
| Student | $29 | 150 | $4,350 |
| Personal | $79 | 25 | $1,975 |
| Small studio | $249 | 4 | $996 |
| **Total Y1** | | **279** | **~$9,321** |

Aggressive (upper-half + active distribution):

| Tier | Price | Volume | Revenue |
|---|---|---|---|
| Founder 100 | $20 (mid) | 100 | $2,000 |
| Student | $29 | 400 | $11,600 |
| Personal | $79 | 60 | $4,740 |
| Small studio | $249 | 10 | $2,490 |
| **Total Y1** | | **570** | **~$20,830** |

Year 1 likely lands $6k–$18k. Won't replace a salary; will validate
demand and pay for tooling (signing certs, domain, etc.).

## Discount strategies

- **Founder 100** — first 100 buyers at $15–29 lifetime, locks them in
  before the price ramps. Use as a launch story (Tweet the count down).
- **Studio crossgrade** — personal-tier buyer pays the **delta** to
  upgrade to studio if their firm wants seats.
- **Student `.edu` verify** — verify with a one-time email confirmation
  link sent to a `.edu` address. Sheer-Id integration is overkill at
  this scale.
- **Annual updates included; year 2+ renewals are 24% (one-quarter
  price)** — keeps active users on latest version without reselling.

## Van Westendorp Price Sensitivity Meter (PSM) — 4 questions

For each interviewee, capture:

1. **Too cheap** — at what price would the product feel suspiciously
   low-quality?
2. **Bargain** — at what price would it feel like a great deal?
3. **Getting expensive** — at what price would you start to hesitate
   but still consider?
4. **Too expensive** — at what price would you flatly not buy?

Plot the four curves. The intersection of "Too cheap" and "Too
expensive" is the **Optimal Price Point (OPP)**. The intersection of
"Bargain" and "Getting expensive" is the **Indifference Price Point
(IPP)** — the most common "fair" price.

Target: ≥10 interviewees per segment for any signal; ≥30 for confidence.
Aim for IPP ≥ list price; if IPP < list price, reduce or reposition.

## What to NOT do

- ❌ Race-to-the-bottom freemium. The only thing worse than charging
  too much is charging $0 and having users who never convert. A free
  tier without a clear conversion path destroys signal.
- ❌ Per-seat for studios <20 people. Operations overhead exceeds revenue.
- ❌ Charging in EUR/GBP without a Merchant of Record.
  See `distribution-platforms.md`.
- ❌ Anchoring on Adobe-style enterprise SaaS pricing ($600+/yr/seat).
  Wrong frame for an indie tool.

## Decision gate (per ROADMAP Phase C)

If <30% of Phase C interviewees answer "yes, I would buy at $X" for
their segment's list price, **reduce price by one ISO step in the
Fibonacci anchor: $79 → $49 → $29**. Do not abandon — reprice.

If still <30% at the lowest tier, shelve as a portfolio piece per
Phase C decision gate.

## Sources

- Van Westendorp, P. (1976). NSS-Price Sensitivity Meter — Dutch
  Association of Market Research, Amsterdam.
- [Show It Better — pricing page](https://www.showitbetter.co/) (2026)
- [Astute Graphics — plugin pricing](https://astutegraphics.com/) (2026)
- [Lemon Squeezy — indie pricing benchmarks](https://www.lemonsqueezy.com/blog)
- [The Mom Test — Rob Fitzpatrick](https://www.momtestbook.com/) — see
  `customer-interviews.md` for methodology
- [Indie Hackers — pricing roundup, 2024](https://www.indiehackers.com/post/pricing)
