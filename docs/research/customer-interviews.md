# Customer interviews — Phase C runbook

> Sub-agent research, 2026-04-30. Script + methodology for the
> demand-validation interviews in ROADMAP Phase C. Built around Rob
> Fitzpatrick's *The Mom Test* and Van Westendorp's PSM.

## Goal

Decide whether to advance to Phase D (build distribution) or shelve.
The decision gate (per `ROADMAP.md`):

- ≥30% of interviewees commit to a price ≥ list-tier price → **advance**
- 10–30% commit at a reduced price → **re-tier and re-test**
- <10% at the lowest viable tier → **shelve to portfolio piece**

"Commit" means an explicit "yes, I would pay $X for this," not "this
sounds cool." See *The Mom Test* below.

## Sample size

- ≥10 interviews per segment for any signal
- ≥30 across all segments for confidence

For a solo founder running these between studio classes, **5 / segment
in 2 weeks** is a realistic floor. Less = inconclusive.

| Segment | Target | Source |
|---|---|---|
| 1. Architecture students | 10 | USC, GSD, Sci-Arc, MIT, Cornell, RISD via studio Discord, Reddit r/architecture, classmate referrals |
| 2. Sole-practitioner architects | 5 | LinkedIn outreach to Rhino-fluent boutique architects in LA / NYC |
| 3. Small-studio principals (5–20 ppl) | 3 | Cold email to firms whose published portfolios show Rhino + IL workflow |

## Logistics

- **Length:** 30 minutes. Hard-stop at 30; never run over.
- **Format:** Zoom or Google Meet. Record (with permission) for review.
- **Compensation:**
  - Students: $20 Amazon / Starbucks gift card
  - Professionals: $50 gift card OR free year-1 license if/when launched
  - Studios: skip cash; offer free studio license + early-access slot
- **Anonymization:** First name + studio scale only. Strip identifying
  details before storing in `docs/research/interviews/`.

## The Mom Test — three rules

From Rob Fitzpatrick's *The Mom Test*:

1. **Talk about their life, not your idea.** Don't pitch the tool until
   the demo phase. Until then, you're a journalist, not a salesperson.
2. **Ask about specifics in the past, not generics or opinions about the
   future.** "Walk me through your last submission set" beats "would
   you use a tool that fixes line weights?"
3. **Talk less, listen more.** Aim for the interviewee speaking ~70% of
   the time.

### Bad questions (avoid)

- ❌ "Would you buy this?" — hypothetical, biased toward yes
- ❌ "Do you think this is a good idea?" — compliment fishing
- ❌ "What features would you want?" — asks them to design
- ❌ "How much would you pay?" — opens commitment without anchor

### Good questions (use)

- ✅ "Walk me through your last submission set, start to finish."
- ✅ "What was the most painful part of preparing those drawings?"
- ✅ "How long did line-weight cleanup take last time? Show me what
  you actually did."
- ✅ "What did you try before? What didn't work?"
- ✅ "Have you ever paid for a tool that solved a problem in this
  workflow?"
- ✅ "Who else on your team would care about this?"

The pattern: **past behavior > future intent**. Past behavior is data;
future intent is fiction.

## Interview script (30 min)

### 0–3 min: Warm-up

> "Thanks for joining. Quick context: I'm a USC architecture student
> who built a tool for my own use, and I'm trying to figure out if
> anyone else has the same problem. This is research — I'm not selling
> anything today. Mind if I record?
>
> First, just to set the scene: what's your role, where, and what
> software do you mostly use?"

**Listen for:** Rhino + Illustrator workflow confirmation, scale of
work (small studio vs. mid vs. solo), seniority.

### 3–10 min: Pain identification (biggest section)

> "Walk me through your last submission set — like, the last time you
> had to prepare a section drawing for review or a final."

If they're vague:

> "What did you do first? Then what? What was the hardest part?"

Probe for:

- How long line-weight cleanup actually took
- Whether they used Make2D, Vectorworks, AutoCAD, or other vector source
- What "looked off" when they first opened the export in Illustrator
- Whether they manually selected layers and changed weights, or used
  some other workaround (action, plugin, copy/paste from another file)

**Take notes verbatim**, not paraphrased. Direct quotes are useful for
later marketing.

### 10–15 min: Magnitude

Quantify the cost.

> "Roughly how many hours did that cleanup take? How many drawings
> per submission set? How many submission sets per term/year?"

Math it out:

> "So that's roughly N hours per year on this exact problem. If your
> billable rate (or your time, as a student) is $X/hr, that's $Y of
> annual cost."

Anchor the conversation in dollars/hours saved before introducing
price. **Never** mention a price before this step.

### 15–22 min: Demo

If they shared a drawing in advance:

> "I ran your drawing through the tool. Want to see the before/after?"

Otherwise, show the ARCH 202B reference:

> "This is a 24 MB drawing with 340 K strokes and 62 layers. Here's
> what it looks like before — can you see what's wrong with the line
> weights? Now here's the result after running `arch-lw apply-jsx
> --poche`. Took 11 minutes."

Watch for:

- Visible reaction (raised eyebrows, "oh"s)
- Whether they immediately ask "can I try it?"
- Whether they ask about specific edge cases ("does it handle X?")
- Whether they go quiet (= confused or uninterested)

### 22–27 min: Van Westendorp PSM

> "Now I want to ask you about pricing. There are no wrong answers."

Ask **all four** questions, in this order:

1. **Bargain:** "At what price would you say this is a great deal —
   you'd buy it without thinking twice?"
2. **Getting expensive:** "At what price would you start to hesitate
   but still consider it?"
3. **Too expensive:** "At what price would you flatly not buy?"
4. **Too cheap:** "At what price would you suspect the quality
   couldn't be very good?"

Record the four numbers. Don't anchor with your own list price.

### 27–30 min: Distribution + commitment

> "If this existed as a $X one-time purchase, downloadable today, would
> you buy it this week?"

Use the price they themselves named in step 2 (their "getting
expensive" boundary or below).

Listen for:

- "Yes, where do I buy it" → strong signal
- "Yes if it has feature X" → conditional, note feature
- "Maybe later" → no
- "I'd want to see more first" → no

> "Where would you expect to find a tool like this — Gumroad? Lemon
> Squeezy? Adobe Exchange? A standalone website?"

Then:

> "Who else should I talk to who has this problem?"

Always ask for referrals. Cold-outreach hit rate is 5–10%; warm
referrals from interviewees run 40–60%.

## Decision rubric (after 30+ interviews)

For each segment, tally:

| Outcome | Code |
|---|---|
| Strong yes ("when can I buy it?") | A |
| Conditional yes (specific feature gate) | B |
| Lukewarm ("maybe in the future") | C |
| Hard no | D |

**Advance to Phase D if** ≥30% of segment is A or B at the segment's
list price.

**Reprice if** ≥30% A/B at one Fibonacci step below
(e.g., $79 → $49). Re-test with 5 more interviews.

**Shelve if** <30% A/B even at the lowest viable price. The market is
smaller than the engineering effort needed to reach it.

## Pricing math (post-PSM)

After 30+ data points, plot four curves:

- "Too cheap" — cumulative % below price
- "Bargain" — cumulative % at-or-below
- "Getting expensive" — cumulative % at-or-above
- "Too expensive" — cumulative % above

Two key intersections:

- **OPP (Optimal Price Point)** = "too cheap" ∩ "too expensive"
- **IPP (Indifference Price Point)** = "bargain" ∩ "getting expensive"

Target list price ≤ IPP. If IPP < tentative list price, reduce.

## What NOT to do during interviews

- ❌ **Pitch the tool before pain identification.** They'll politely
  agree with whatever you say. Worthless data.
- ❌ **Ask "would you pay $X?"** Hypothetical commitments don't
  predict actual purchases. Use PSM instead.
- ❌ **Skip the demo for time.** The demo is the moment of truth — if
  they don't react visibly, they won't buy.
- ❌ **Argue with their criticism.** "Actually, the tool does
  handle that..." — note it and move on.
- ❌ **Promise features.** "I'll add that next week" is a debt to a
  stranger. Note it as a maybe.

## Storing data

Each interview → one Markdown file in `docs/research/interviews/`:

```
### Interview 7 — 2026-05-12

- Segment: 1 (USC student, M.Arch 2nd year)
- Software: Rhino 8, Illustrator 2024, occasional VRay
- Pain: 3-4 hrs per submission set on line-weight cleanup; 4
  submission sets/yr → ~14 hrs/yr → ~$280/yr at $20/hr equivalent
- Last manual workflow: select-by-color → change stroke weight in
  Appearance panel; tedious, error-prone on 60+ layers
- Demo reaction: "oh that's exactly what I needed last week"; asked
  if it handles Vectorworks output (not yet)
- Van Westendorp:
  - Too cheap: $5
  - Bargain: $19
  - Getting expensive: $39
  - Too expensive: $79
- Would-buy: yes at $19, this week
- Referrals: 2 classmates' names + emails
- Notes: ask about Vectorworks support roadmap
- Decision code: A
```

After the run, aggregate into `docs/research/interview-summary.md`
with the 4-curve PSM plot and decision recommendation.

## Outreach templates

### Student cold email

> Subject: 30 min on architecture-school drawing workflow ($20 gift
> card)
>
> Hi [name] — I'm a USC M.Arch student building a tool to automate
> line-weight cleanup on Rhino → Illustrator section drawings. Before
> I keep building, I'm trying to talk to ~10 students at other schools
> to see if this problem is real for you too.
>
> 30 min on Zoom this week or next? $20 Starbucks/Amazon as thanks.
>
> No sales pitch. Just trying to learn.
>
> — [signature]

### Studio cold email

> Subject: 30 min on Rhino → Illustrator workflow at [firm]
>
> Hi [name] — I'm a USC student researching how small studios handle
> the Rhino-to-print workflow, particularly line-weight standards
> across plan / section / detail drawings. Looking to talk to 3–5
> firm leads who own this part of the process.
>
> 30 min on Zoom this week? Happy to share what I'm learning across
> firms in return — and if/when this turns into a tool, you'd get
> first access.
>
> — [signature]

## Sources

- Rob Fitzpatrick — *The Mom Test* (2013, self-published).
  Definitive primer on customer-development interviews.
- Van Westendorp, P. (1976). NSS-Price Sensitivity Meter — see
  `pricing-research.md` for the math.
- [Steve Blank — Customer Development Manifesto](https://steveblank.com/2010/01/25/the-customer-development-manifesto-the-rules/)
- [Y Combinator — How to Talk to Users](https://www.ycombinator.com/library/6g-how-to-talk-to-users)
- [Lenny Rachitsky — Pricing research playbook](https://www.lennysnewsletter.com/p/pricing-your-product)

## Related

- `docs/ROADMAP.md` Phase C — uses this directly
- `docs/research/pricing-research.md` — feeds the price anchors
- `docs/BUSINESS.md` — segment definitions and target outreach lists
