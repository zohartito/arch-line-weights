# Business — internal notes

> **PRIVATE.** This document is for the maintainer's use only. Pricing
> thoughts, customer interviews, partnership conversations, etc.

## Status (2026-04-30)

- v1.0.0 published to PyPI under MIT, yanked after ~15 min
- Repo private on GitHub (free plan; Pages 404 as a side effect)
- PyPI Trusted Publisher removed; release.yml workflow disabled
- Project name `arch-line-weights` reserved on PyPI
- No license enforcement infrastructure built yet
- Zero customers, zero revenue

## Target customer segments

### Segment 1: Architecture students at top schools
USC, GSD, MIT, Cornell, RISD, Sci-Arc, Berlage, AA, Bartlett, ETH.

- Buyer: individual student
- Decision criterion: "is this cheaper than my time × hours saved?"
- Price tolerance: ~$20 (impulse buy on a credit card)
- Acquisition: word-of-mouth in studio, Reddit, Discord, classmate Instagram
- Volume estimate: 100s globally, low hundreds plausible in year 1

### Segment 2: Personal / sole practitioner architects
Boutique design-build firms, freelance Rhino-fluent architects.

- Buyer: individual professional
- Decision criterion: "every billable hour I save = $80–150 back"
- Price tolerance: $50–150 one-time, possibly $20/mo
- Acquisition: harder; partnership with Show It Better, ArchDaily writeups
- Volume estimate: 10s globally year 1

### Segment 3: Small architecture studios
5–20 person offices using Rhino + Illustrator workflow.

- Buyer: principal or office manager
- Decision criterion: "license fee < 1 hour of any architect's time per month"
- Price tolerance: $400–800/yr per office (not per seat) for ≤20 seats
- Acquisition: direct outreach, Food4Rhino visibility, AIA / SAH conferences
- Volume estimate: single digits year 1, 10s year 2

### Segment 4: BIM / drafting consultancies
Outsource drafting shops who'd buy a tool to speed up their per-project deliveries.

- Lower priority — unclear if the workflow even applies to them

## Pricing thoughts (pre-validation, gut-feel)

| Tier | Price | Audience | Volume guess y1 | Revenue ceiling y1 |
|---|---|---|---|---|
| Student | $19 one-time | Segment 1 | 200 | $3,800 |
| Personal | $79 one-time | Segment 2 | 30 | $2,370 |
| Studio | $499/yr | Segment 3 | 5 | $2,495 |
| **Total** | | | **235** | **~$8,665** |

Realistic year 1 revenue: probably $2k–10k. Won't replace a salary; will validate.

After validation, year 2 numbers:
- Web app subscription: $9/mo personal = $108/yr
- Studio plan: $499/yr (multi-seat)
- Conservatively 500 personal-tier × $108 = $54k + 30 studios × $499 = $15k = ~$70k/yr.

## Competitive positioning

(Detailed competitive landscape: `docs/research/competitive-landscape.md` from earlier sub-agent.)

**Direct competitors:** None known. The market gap is real.

**Adjacent threats:**
- Show It Better — cultural competitor (Photoshop actions, brushes). Could expand into automation.
- Astute Graphics — Adobe Illustrator extension publisher. Has the distribution.
- AutoCAD CTB / Revit View Templates / ArchiCAD Pen Sets — solve it inside-app, locked in.
- McNeel themselves — if they ship a "Print Style" PDF export that survives the round-trip, our problem disappears.

**Defensibility:**
- Layer-name semantic classifier → pattern library that gets better with more customer drawings
- POSTMORTEM-driven engineering → speed of iterating on edge cases
- Direct customer relationships → rare for a $19 tool

## Distribution thoughts (pre-validation)

(Detailed distribution comparison: `docs/research/distribution-platforms.md` from sub-agent.)

**v1 (month 2):** Gumroad single-binary download. $19 / $79 / $499 tiers.

**v2 (month 5+):** archlineweights.com SaaS. Stripe subscriptions.

**v3 (year 2+):** Adobe Exchange listing (when UXP ships) + Food4Rhino plugin.

## Marketing / messaging

**Tagline candidates:**
- "Architectural line weights, automatically."
- "From Rhino to print in one command."
- "Stop fixing line weights. Start drawing."

**Anti-tagline (what NOT to lead with):**
- "Open source" — we're not, going forward
- "AI-powered" — we're not, and the credibility is worth more than the buzzword
- "Free" — never was, won't be

**Demo asset:** the user's ARCH 202B section drawing, before/after.

## Customer-interview log

(Format: one entry per interviewee. Move from this file to `docs/research/interviews/` once the list grows beyond 5.)

```
### Interview 1 — TBD
- Date:
- Interviewee: (anonymize)
- Pain points:
- Demo reaction:
- Pricing signals (van Westendorp):
- Would buy at:
- Decision: (build / shelve / pivot)
```

(Empty so far. Run Phase C, populate.)

## Partnership ideas

- **Show It Better** — bundle with their PSD action packs?
- **30X40 Design Workshop** — sponsorship of a video tutorial?
- **Archademia / Upstairs** — guest lecture trade for promotion?
- **Specific YouTube architects** — the audience overlap is high

## Existential risks

1. **I lose interest after ARCH 202B is over.** Most likely outcome. Mitigation: get to first paying customer before semester ends.
2. **Adobe / McNeel ships an equivalent feature** for free, killing the problem. Mitigation: monitor their roadmaps quarterly.
3. **Architecture-school workflow shifts to all-AI** (Hyperboloid, Sketch-to-3D, etc.), making line weights obsolete. Mitigation: pivot to "AI-augmented" mode, leverage existing classifier as training data.
4. **GDPR / data-residency makes hosting awkward.** Mitigation: stay client-side as long as possible (CLI-first, SaaS only when simpler).

## Open questions

- Should this become a YC application down the line? Probably not — too narrow a market — but worth thinking through.
- Brand / domain: `archlineweights.com` is descriptive but long. Shorter options: `archlw.io`, `lineweights.app`, `pochecut.com`?
- Should I trademark? At what tier of revenue does that make sense?
- When does this need a co-founder? Probably at Phase F (web app) — backend + payments + customer support is a lot for one person.
