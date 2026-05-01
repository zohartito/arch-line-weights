# SaaS privacy + security posture — research

> **Question:** What is the minimum-viable privacy + security posture for
> arch-line-weights' SaaS web app, where architects upload confidential
> drawings, get processed output, and download the result?
>
> **Methodology:** ~60-min sub-agent pass over Gendo / MyArchitectAI /
> Visoid public privacy pages, GDPR Article 28 + CCPA primers, SOC 2
> pricing comparisons (Drata vs Vanta 2026 figures), Cloudflare R2
> data-security docs, Plausible/Fathom cookie posture, and SaaS DPA
> templates. Direct quotes capped at 15 words.
>
> **Disclaimer:** Author is not a lawyer. Every clause below should be
> reviewed by a licensed attorney before launch — recommended budget
> $1.5–4k for a one-pass review of Privacy Policy + Terms + DPA before
> Phase D9 (Founders 100 beta).

---

## TL;DR — recommended posture

| Layer | Recommendation | Cost / complexity |
|---|---|---|
| Encryption at rest | Server-side, provider-managed (R2 SSE / S3 SSE-S3, AES-256) | Free, default-on |
| Encryption in transit | TLS 1.2+ everywhere (Cloudflare auto) | Free |
| Retention default | Free tier: 7 days post-last-access. Paid tier: 30 days post-last-access. Hard delete = 24 h grace then purge from object store + DB | Cron job, ~1 day to build |
| Data residency | US-only at v1 (Cloudflare R2 `auto`). EU jurisdiction (`eu` hint) at v2 — gate behind a `EU Data Residency` paid add-on or a Studio tier feature | EU adds ~1 day of work; pricing-tier gating is the lift |
| Subprocessors | Public list on `/subprocessors` page, version-pinned, email-on-change | Half-day |
| Privacy Policy | Plain-English, ~1500 words, GDPR + CCPA + UK DPA in one doc | Use Termly/TermsFeed generator + lawyer pass |
| DPA | Pre-signed PDF auto-emailable to studio customers; SCCs annexed; subprocessor list referenced | $500–1.5k lawyer pass once |
| SOC 2 | Defer until first studio asks (likely month 6–12 post-launch). Vanta Core ~$10k/yr + auditor $5–15k | Defer |
| Cookie banner | Skip — use Plausible/Fathom analytics; cookieless | Free, faster page |
| Incident response | One-page runbook, 72-h GDPR clock, status.archlineweights.com page | Half-day |
| Marketing posture | Lead with: "Your drawings are deleted in 7/30 days. Encrypted at rest. Never used to train AI." | Copy work |

**The one decision that drives engineering complexity:** server-side vs
client-side (E2E) encryption. Server-side is buildable in an afternoon
and is what every architecture-cloud competitor markets as "encrypted".
Client-side E2E adds weeks of work, breaks server-side compute (we
**must** decrypt to run pikepdf+zstd), and would force a desktop
companion architecture (Phase B3) instead of the cleaner pure-server B1
path. **Recommendation: server-side at v1.** Defer client-side to a
"Pro Privacy" tier in Phase G if studio segment demands it.

---

## 1. Encryption at rest — server-side vs client-side (E2E)

### Server-side (provider-managed KMS)

**What it means:** files arrive over TLS, the storage layer (R2 / S3)
encrypts at rest with provider-managed AES-256 keys. The server (us)
can decrypt to compute. Customer trusts us not to peek; the cloud
provider can't see content.

**Cloudflare R2 default:** AES-256-GCM at rest, TLS in transit
([Cloudflare R2 docs][r2-security]). Free. SSE-C (customer-supplied
keys) is also offered for one extra step of key isolation.

**This is what competitors actually ship.** Despite marketing language
implying stronger guarantees, every architecture-cloud service we
checked uses server-side encryption — none ship E2E.

**Marketing claim discipline:** if we say "encrypted at rest" without
qualification, that's accurate at server-side level. Do **not** claim
"end-to-end encrypted" or "zero-knowledge" — those terms have specific
meanings.

### Client-side (E2E)

**What it means:** browser encrypts the .ai file with a key derived
from user passphrase before upload. Server stores ciphertext only.
Server cannot decrypt — therefore **server cannot run pikepdf+zstd
processing**.

**Why this kills our pipeline:** the entire SaaS value prop (Phase B1)
is server-side compute on the .ai. If the server can't decrypt, we
either (a) move compute to the browser (WASM port of pikepdf — months
of work, slow per-user) or (b) push to a desktop helper (Phase B3 —
defeats the SaaS UX). E2E is fundamentally incompatible with the v1
architecture.

**Verdict:** server-side at v1. Add a "Pro Desktop" tier (Phase F4)
where the user runs the binary locally and never uploads — that's the
true zero-knowledge offering for the paranoid-studio segment, and it
reuses `docs/research/binary-distribution.md` work.

### Optional middle ground: per-file ephemeral key

For paranoid users, generate a per-upload AES key on the server,
encrypt-decrypt only in RAM during compute, then destroy the key
post-processing. Files at rest are encrypted. **This is a marketing
upgrade, not a real cryptographic upgrade** — the server still has key
custody during compute. Worth implementing for "we minimize key
exposure" copy in the privacy page; ~half-day of engineering.

---

## 2. Retention policy

### Defaults

| Tier | Auto-delete trigger | Grace period | User-initiated delete |
|---|---|---|---|
| Free | 7 days after last access OR 30 days after upload, whichever sooner | 24 h soft-delete (recoverable) | Immediate from UI; 24 h purge from object store |
| Personal ($9/mo) | 30 days after last access | 24 h | Immediate |
| Studio ($49/mo+) | 90 days after last access, configurable down to 24 h | 24 h | Immediate |
| Pro Desktop | Never uploaded — N/A | N/A | N/A |

**Why 7 days for free:** matches the
"upload-process-download-and-leave" pattern we see in cloud rendering
services (Gendo, MyArchitectAI). Long enough for a student to redownload
during studio review week; short enough that we don't accumulate a
liability surface.

**Why 30 days as paid baseline:** lets a sole-practitioner come back to
re-process after a print test without re-uploading. Studio tier adds
the configurability they'll demand from IT-policy reviews.

**What "delete" means technically:**

1. Object marked tombstoned in DB (soft delete) — invisible in UI
2. 24-h grace window — user can email support to recover
3. After grace, R2 `DeleteObject` issued — gone from primary storage
4. R2 deletes ripples through CDN cache eventually (no public URL on
   our objects so this is moot)
5. DB row anonymized (file hash kept as a usage counter; PII fields
   nulled)
6. Backups: Neon free tier auto-snapshots — see backup-purge cadence
   below

**Backup-purge cadence:** Neon point-in-time recovery defaults to 7
days on free, 30 days on paid. To honor a deletion request fully, we
must commit to "deletion takes up to N days to propagate through
backups." 30 days is industry-standard. Mention this in Privacy Policy.

### Tier override (sales-driven)

Studio customers will sometimes ask for "files auto-delete in 24 hours"
as an IT requirement. Build the toggle in Studio tier. Don't let
admins set retention longer than 90 days without an Enterprise
agreement (caps our liability surface).

---

## 3. Data residency — EU?

### v1: US-only

- Cloudflare R2 `auto` jurisdiction (lets CF route to nearest region —
  cheapest, fastest)
- Stripe US-based merchant of record
- Neon Postgres in `aws-us-east-2` (Ohio) — cheapest tier
- Resend US-based for magic-link email

**Privacy Policy disclosure:** "We process data in the United States.
EU and UK customers, by using the Service, consent to transfer; we use
Standard Contractual Clauses (SCCs) for cross-border processing per
GDPR Articles 44–49."

**Why this is OK at v1:** SCCs + EU-US Data Privacy Framework (DPF) is
the legally accepted bridge as of 2024+. Schrems II requires
"supplementary measures" — for us those are: encryption at rest,
limited retention, no government data-sharing on volunteer basis.
Document these in the DPA appendix.

### v2: EU residency option

Once any single Studio prospect demands EU data residency in writing
(probable within first 5 studios, near-certain within first 20):

- Switch R2 buckets to `eu` jurisdictional hint
  ([Cloudflare R2 data location][r2-location])
- Add Neon EU region (Frankfurt) — costs ~$20–40/mo extra at low
  scale
- Resend has EU-region option
- Stripe Tax handles VAT for EU sales

Pricing-gate this as `EU Data Residency` add-on at $20–50/mo per
seat, or bundle into a Studio EU tier. **Caveat:** R2's `eu` hint is
not a pin to a named DC — for procurement-grade audits the studio
will eventually want a named DC, which is when we look at AWS S3
EU-region or Hetzner-backed S3-compatible storage. That's Phase G1.

### CN, IN, ZA, etc. residency

Skip. Not a v1 concern. If a customer asks, escalate to Enterprise
custom contract or politely decline.

---

## 4. Privacy Policy — plain-English template

> **Reading-level target:** 10th grade, ~1500 words, scannable
> headings. Architects skim documents before they sign — the policy
> needs to be one they actually read.

### Recommended structure (use as-is, run past lawyer)

```markdown
# Privacy Policy

**Last updated:** [DATE]

We're arch-line-weights, a small SaaS that processes architectural
drawings. This page explains what data we collect, how we use it, and
how we protect it. It's written in plain English because that's the
respectful thing to do.

If you'd rather read the legalese version, ask us — but the meaning is
the same.

## What we collect

**Your drawings.** When you upload a `.ai` or `.pdf`, we store the
file in our object storage (Cloudflare R2) so we can process it. We
need the full file content to do the work. We do **not**:

- read your drawings ourselves
- look at the contents
- use your drawings to train AI models — ours or anyone else's
- share your drawings with anyone outside the subprocessors listed below

**Account info.** Email address (for login via magic link), name (if
you give us one), payment info (handled by Stripe — we never see your
card number).

**Usage data.** What features you used, when, from what country, file
sizes processed. We don't track you across other websites; we don't
use cookies for analytics (we use Plausible, which is cookieless).

**Support tickets.** If you email support, we keep that thread until
you ask us to delete it.

## How long we keep your drawings

| Plan | Auto-deleted |
|---|---|
| Free | 7 days after your last access |
| Personal | 30 days after your last access |
| Studio | 90 days after your last access (configurable down to 24 hours) |

You can delete any drawing immediately from your dashboard. After
deletion: 24-hour soft-delete grace period (email us to recover), then
hard delete from primary storage. Backups roll off within 30 days.

## How we secure it

- **In transit:** TLS 1.2+ everywhere (HTTPS).
- **At rest:** AES-256 encryption (Cloudflare R2 server-side
  encryption).
- **Access:** only the founder and named contractors with NDAs can
  access the production environment. Access is logged.
- **Sub-processors:** see [/subprocessors](/subprocessors) for the
  full list of vendors who can technically access infrastructure (none
  routinely access content).

If you want stronger guarantees — drawings that **never** leave your
machine — we offer the **Pro Desktop** tier, where processing happens
locally on your computer. No upload, no cloud.

## Where your data is stored

By default: United States (Cloudflare R2 `auto` region, AWS US
East). EU-based customers: by using the Service you consent to
this transfer; we rely on Standard Contractual Clauses (SCCs) per
GDPR Articles 44–49 with the U.S. Data Privacy Framework as a
supplementary measure.

EU-resident hosting is available on the Studio EU plan ([upgrade →](/pricing)).

## Your rights

You have rights under GDPR (EU/UK), CCPA (California), and other
privacy laws. Specifically:

- **Access** — what data we have on you ([dashboard → Export](/dash/export))
- **Correction** — we'll fix anything wrong, just email us
- **Deletion** — delete your account at any time; we'll wipe within 30
  days
- **Portability** — export everything as a ZIP
- **Opt out of processing** — for marketing emails, unsubscribe link
  in every email; for processing required to deliver the service,
  this means closing your account
- **No discrimination** — we won't degrade your service or charge you
  more for exercising any of these rights (CCPA §1798.125)

To exercise any right, email **privacy@archlineweights.com**. We
respond within 30 days (often within 24 hours — we're a small
team).

## Children

Service is for adults. We don't knowingly collect data on anyone
under 16. If you're a student under 16, please ask a parent or
teacher before using us.

## Cookies

We use one strictly-necessary cookie: a session token to keep you
logged in. That's it. No analytics cookies, no advertising cookies,
no cross-site tracking. We use Plausible Analytics which is
cookieless.

## AI training

Your drawings are **not** used to train any AI model. Not ours, not
a third party's. We don't have an AI model — the processing is
deterministic Python code (pikepdf + Zstandard) that operates on
the file's stream layer and returns a modified copy. There is no
"data science" use of your work.

## Changes to this policy

If we change anything substantive, we email you 30 days before it
takes effect. The "Last updated" date at the top tracks all
changes. Past versions: [/privacy/history](/privacy/history).

## Contact

- **Privacy & deletion requests:** privacy@archlineweights.com
- **Security disclosures:** security@archlineweights.com (PGP key
  on the page)
- **EU representative (when we have one):** [TBD — required for
  GDPR if we have a substantial EU userbase, ~Phase G]
- **Postal:** [studio address — required for CCPA disclosure]
```

### Notes on what *must* be in a Privacy Policy

| Requirement | Source | Where in template |
|---|---|---|
| Categories of data collected | GDPR Art. 13(1)(c); CCPA §1798.100(a) | "What we collect" |
| Purpose of processing | GDPR Art. 13(1)(c) | Implicit per-section ("so we can process it") |
| Legal basis | GDPR Art. 13(1)(c) | Should explicitly add: "Contract (Art. 6(1)(b)) for processing; Legitimate interest for security logs" |
| Recipients / sub-processors | GDPR Art. 13(1)(e) | "Subprocessors" link |
| Cross-border transfer mechanism | GDPR Ch. V (44–49) | "Where your data is stored" |
| Retention period | GDPR Art. 13(2)(a) | "How long we keep your drawings" |
| Data subject rights | GDPR Art. 13(2)(b); CCPA §1798.105 | "Your rights" |
| Right to lodge a complaint | GDPR Art. 13(2)(d) | Add explicit: "EU/UK users can complain to their data protection authority" |
| Source of data (if not collected from subject) | GDPR Art. 14 | N/A — we collect from subject |
| Sale/share opt-out (CCPA) | CCPA §1798.135 | Cover with explicit "We don't sell or share your data" |

**Lawyer pass adds:** governing-law clause, arbitration / class-action
waiver (or not — depends on Terms strategy), specific California
"Shine the Light" disclosure (§1798.83), Virginia/Colorado/Connecticut
state-specific addenda for VCDPA/CPA/CTDPA.

---

## 5. Data Processing Agreement (DPA) — minimal template

> **When does a customer ask?** Studio tier customers will ask
> ~50–80% of the time before they sign. A pre-signed PDF on the
> pricing page accelerates Studio close-rate dramatically. Sole
> practitioners almost never ask. Students never ask.

### Trigger conditions

1. Studio prospect mentions "we have an IT review" / "compliance
   review" / "data protection officer" / "we need a DPA"
2. Customer is in EU and has GDPR-conscious legal counsel
3. Studio is doing healthcare, government, or finance project
   work (rare, but high-value when it appears)

### Pre-signed DPA — what to put on `/dpa` page

```markdown
# Data Processing Agreement (DPA)

This DPA forms part of the [Terms of Service](/terms) between
arch-line-weights ("Processor") and the Customer ("Controller") who
uploads personal data through the Service.

## 1. Subject matter, duration, nature, purpose

- **Subject matter:** processing of architectural drawing files
  uploaded by Controller
- **Duration:** for the term of the Service subscription
- **Nature:** automated processing (pikepdf-based stream rewrite)
- **Purpose:** delivery of the line-weight hierarchy and poché
  pipeline output back to Controller

## 2. Categories of data subjects, data

- **Subjects:** Controller's employees, clients, end users (none
  routinely processed — drawings rarely contain personal data, but
  could contain client names in title blocks)
- **Categories:** business contact info incidentally embedded in
  drawing metadata; no special-category data per GDPR Art. 9
  expected

## 3. Processing on documented instructions

Processor processes Personal Data only on documented instructions
from the Controller, including transfers, except where required by
EU/Member State law.

## 4. Confidentiality

Processor ensures persons authorized to process Personal Data are
under contractual confidentiality. Founder and contractors sign NDAs.

## 5. Security (Article 32)

Processor implements:
- AES-256 encryption at rest (provider-managed)
- TLS 1.2+ in transit
- Access logging on production
- Regular dependency audits (Renovate, Dependabot)
- Backup tested quarterly
- Incident response plan ([linked](/security/incident-response))

## 6. Sub-processors

Controller authorizes Processor to engage sub-processors listed at
[/subprocessors](/subprocessors). Processor will give Controller
30 days' notice (via email) before adding a new sub-processor;
Controller may object in writing, in which case parties will discuss
in good faith. Processor remains liable for sub-processor acts.

## 7. Data subject rights

Processor will assist Controller in fulfilling Data Subject rights
requests (access, correction, deletion, portability, restriction,
objection) within 7 business days of request.

## 8. Personal data breach notification

Processor will notify Controller within 48 hours of becoming aware
of a Personal Data breach, providing all information reasonably
necessary for Controller's GDPR Art. 33 notification within the
72-hour window.

## 9. Assistance with DPIA / Article 36

Processor provides reasonable assistance with Controller's
Data Protection Impact Assessments and prior consultations.

## 10. End of contract

Upon termination, Processor will, at Controller's choice, return or
delete all Personal Data within 30 days, unless EU/Member State law
requires retention.

## 11. Audits

Processor will make available all information necessary to
demonstrate compliance and allow audits. Audits may be in the form
of (a) Processor's most recent SOC 2 report (when available), or
(b) a self-completed security questionnaire, or (c) on-site audit
at Controller's expense with 30 days' notice (max once per year).

## 12. International transfers

Where Personal Data of EU/UK data subjects is transferred outside
the EU/UK, Processor relies on:
- EU Standard Contractual Clauses (Module 2: Controller to
  Processor) — incorporated by reference, **Annex I**
- UK International Data Transfer Addendum
- Supplementary measures: encryption at rest + in transit,
  retention limits, no voluntary government access

## 13. Annexes

- **Annex I** — Description of processing, list of sub-processors,
  technical and organizational measures
- **Annex II** — SCCs Module 2

## 14. Liability

DPA liability is capped per the [main Service Agreement](/terms).
Nothing in this DPA limits liability for fraud, willful misconduct,
or matters that cannot be excluded under applicable law.

---

**Signed:**

Processor: arch-line-weights, [legal entity, jurisdiction]
Controller: [Customer name + address — fillable]
Effective date: [Subscription start date]
```

### Cost to produce

- DIY using TermsFeed/Promise.legal templates: $0 + 4 h research
- Lawyer-reviewed: $1.5–3k one-time for the bundle (Privacy + Terms +
  DPA). Recommend USA SaaS attorney with GDPR familiarity.
- Per-customer: $0 — the same PDF is signed by every Studio customer

---

## 6. GDPR / CCPA / UK DPA compliance baseline

### Floor (must hit before any paid customer)

- [ ] Privacy Policy live, plain-English, covers GDPR Art. 13/14 +
      CCPA §1798.100 disclosures
- [ ] Terms of Service live with limitation-of-liability clause
- [ ] Cookie posture: cookieless analytics OR cookie banner with
      genuine opt-in (we recommend cookieless)
- [ ] Email-based deletion request mechanism (`privacy@`)
- [ ] Data export functionality (or at least manual on email request,
      automated by Phase E)
- [ ] Subprocessor list public
- [ ] TLS everywhere (Cloudflare provides for free)
- [ ] AES-256 at rest (R2 provides for free)
- [ ] Some retention auto-deletion (or "we delete after subscription
      ends")
- [ ] No selling/sharing data (CCPA right to opt-out of "sale" /
      "share" — our default is no)
- [ ] Magic-link auth (no password leaks possible)

### Smart-but-not-paranoid level (target before Founders 100 launch)

- [ ] Pre-signed DPA available on `/dpa`
- [ ] Subprocessor change notification (mailing list, 30 days
      before adding new ones)
- [ ] User self-service delete-account button (not just email
      request)
- [ ] User self-service download-my-data button (ZIP export)
- [ ] Status page (`status.archlineweights.com`) with uptime + past
      incidents
- [ ] One-page security overview at `/security` covering encryption,
      access controls, retention, incident response
- [ ] Quarterly dependency audit + documented patch cadence
- [ ] Backup tested at least once before launch + documented
- [ ] EU representative designated under GDPR Art. 27 (only when
      EU userbase grows; can be a paid service like ePrivacy.eu for
      ~$300/yr)
- [ ] CCPA "Notice at Collection" linked from upload screen for CA
      users (one-line link: "California residents — see our notice
      at collection")

### Paranoid level (Phase G, when going after enterprise)

- [ ] SOC 2 Type 1 report (then Type 2 after 6 months)
- [ ] Penetration test (annually, ~$5–15k)
- [ ] ISO 27001 (probably not — SOC 2 is the US default, ISO is
      EU/global)
- [ ] HIPAA BAA (only if any architect ever does healthcare with
      personal health info — extremely unlikely for line weights)
- [ ] Bug bounty (HackerOne / Bugcrowd, ~$5k/yr minimum)
- [ ] Dedicated CISO contractor (~$2–5k/mo)

### CCPA-specific must-haves

- "Do Not Sell or Share My Personal Information" link in footer (or
  the new "California Privacy Rights" link covering DNS, share,
  limit sensitive PI, opt-out of automated decision-making)
- Even though we *don't* sell or share, the link must be present
  and lead to a page saying so. CCPA §1798.135.
- Verifiable consumer requests (we can verify via "logged-in user
  + magic-link confirmation")
- 12-month look-back disclosure (CCPA §1798.130)

### UK GDPR / DPA 2018

- Largely identical to EU GDPR; ICO is the regulator
- Use UK Addendum to SCCs for UK transfers
- ICO fee tier: pay £40/yr (Tier 1 — "small organization") once
  you have UK customers ([ICO fee][ico-fee])

### Other state laws (US)

| State | Law | Trigger | Effort |
|---|---|---|---|
| Virginia | VCDPA | 100k VA residents OR 25k + 50% revenue from data | Skip until material |
| Colorado | CPA | Same threshold | Skip |
| Connecticut | CTDPA | Same threshold | Skip |
| Texas | TDPSA | Lower threshold but B2B-friendly carve-outs | Skip |
| Delaware, Iowa, etc. | Various | All similar to CCPA | Generic CCPA-style policy covers most |

**Pragmatic call:** a single well-written CCPA-compliant policy +
explicit GDPR coverage is sufficient floor. Add state-specific
language when revenue from a state crosses material thresholds.

---

## 7. SOC 2 readiness — when does it become a sales blocker?

### When studios actually demand it

- **Sole practitioners:** never
- **2–4 person studios:** never
- **5–20 person studios (Segment 3):** rarely; will accept "we'll
  have it by [N] months" with a security questionnaire as a stopgap
- **20+ person studios (Phase G target):** sometimes; Tier-A firms
  almost always
- **Government work (NCARB / federal architect contracts):**
  basically yes

**Heuristic: SOC 2 becomes a sales blocker around the time we have
$5–10k MRR from studios specifically.** Below that threshold, send a
security questionnaire response (1-page PDF) and the DPA — usually
sufficient.

### Timeline + cost (2026 numbers)

| Step | Timeline | Cost (low estimate) | Cost (realistic) |
|---|---|---|---|
| Choose platform (Vanta / Drata / Comp.ai / Secureframe / Drata) | Week 1 | $7,500 / yr (Drata Foundation) | $10–15k / yr (Vanta Core) |
| Run readiness phase (policies, evidence collection) | Months 1–3 | DIY 200 h founder time | + $5–10k consultant if needed |
| Type 1 audit (point-in-time) | Months 3–4 | $3–8k auditor | $5–15k |
| Operate controls for 6 mo | Months 4–10 | (ongoing platform fee) | (ongoing) |
| Type 2 audit (covers 6-mo period) | Months 10–12 | $5–15k | $10–25k |
| **Year-1 total** | **9–12 months** | **~$20k** | **$45–70k** |

[SOC 2 cost breakdown 2026][soc2-cost], [Drata pricing][drata-pricing],
[Vanta pricing][vanta-pricing].

**Solo-founder reality check:** SOC 2 readiness consumes 200–400 h of
founder time plus 6 months of calendar time. At an opportunity-cost
hourly rate of $80–150 (roughly Phase E engineering value), that's
$32k–60k of "disguised" cost on top of cash outlay.

### Recommendation for arch-line-weights

| Phase | Posture |
|---|---|
| D9 (Founders 100, month 4) | No SOC 2. Security questionnaire + DPA covers Studio onboarding. |
| F (public launch, month 6–8) | Still no SOC 2. Add `/security` page with detailed posture. |
| F + first 3 enterprise asks (month 8–14) | Start SOC 2 Type 1 readiness — Vanta Core or Drata Foundation. Budget $20–30k cash. |
| G1 (year 2) | Type 2 + annual renewal, ~$15–25k/yr ongoing |

**Trap to avoid:** doing SOC 2 too early. It's a security-theater tax
that doesn't help anything except enterprise sales. Don't pay it until
the deal-flow demands it.

---

## 8. Subprocessor disclosure list

> Public page at `/subprocessors`, version-pinned (e.g.
> `v2026-04-30`), with mailing list signup for change notifications.

### Template

```markdown
# Subprocessors

We use the following third parties to run the Service. They have
contractually limited access to data, scoped to their function.

**Last updated:** 2026-MM-DD. Subscribe to changes:
[subprocessors@archlineweights.com](mailto:subprocessors-subscribe@archlineweights.com).
We give 30 days' notice before adding a new subprocessor.

| # | Provider | Service | Data accessed | Region | DPA |
|---|---|---|---|---|---|
| 1 | Cloudflare, Inc. | CDN, DNS, R2 object storage | All uploaded files at rest, all HTTP traffic | US (R2 `auto`) or EU (R2 `eu`) | [link][cf-dpa] |
| 2 | Fly.io | Application compute (FastAPI) | Files in-flight during processing only; ephemeral | US (`iad`) | [link][fly-dpa] |
| 3 | Neon | Postgres database | Account info (email, name), file metadata, processing logs | US East / EU Frankfurt | [link][neon-dpa] |
| 4 | Stripe, Inc. | Payment processing | Payment info, billing email | US | [link][stripe-dpa] |
| 5 | Stripe Tax | Sales tax / VAT compliance | Billing address, tax ID | US | (per Stripe DPA) |
| 6 | Resend | Transactional email (magic links, receipts) | Email address, message body | US | [link][resend-dpa] |
| 7 | Sentry | Error tracking (no file content sent) | Stack traces, user ID, request metadata | US (with EU option) | [link][sentry-dpa] |
| 8 | Plausible Analytics | Product analytics (cookieless) | Anonymized page views, no PII | EU (Germany) | [link][plausible-dpa] |
| 9 | GitHub | Source code, CI/CD | No customer data; internal source only | US | (no DPA needed — no customer data) |
| 10 | Cloudflare Registrar | Domain registration | Public WHOIS only | US | (per Cloudflare DPA) |

[cf-dpa]: https://www.cloudflare.com/legal/customer-dpa/
[fly-dpa]: https://fly.io/legal/data-processing-agreement/
[neon-dpa]: https://neon.tech/legal/dpa
[stripe-dpa]: https://stripe.com/legal/dpa
[resend-dpa]: https://resend.com/legal/dpa
[sentry-dpa]: https://sentry.io/legal/dpa/
[plausible-dpa]: https://plausible.io/dpa
```

### What to disclose (every entry)

1. Vendor legal name
2. Service category
3. Data types touched
4. Hosting region
5. Link to vendor DPA (we sub-incorporate)
6. (Optional) sub-sub-processors if vendor lists them

### Vendors NOT to use without thinking

- **Discord / Slack for support** — message contents become a
  subprocessor situation if customer data flows
- **Google Workspace for support email** — fine, but disclose
- **Any AI training-on-by-default tool** (early ChatGPT API was — now
  defaults to off for API but still worth re-checking) — never paste
  customer file contents into AI tools

---

## 9. Incident response runbook — minimum viable

### One-page runbook (paste at `/security/incident-response`)

```markdown
# Incident Response

When we detect a security incident affecting customer data, we follow
this process:

## Severity levels

| Level | Definition | Notification |
|---|---|---|
| SEV-1 | Confirmed unauthorized access to customer files OR PII | All affected users + DPAs (controllers) within 24 h; supervisory authority within 72 h (GDPR Art. 33) |
| SEV-2 | Suspected access; investigation in progress | All affected users within 72 h or upon confirmation |
| SEV-3 | Vulnerability disclosed but no evidence of exploitation | Public security advisory within 7 days |
| SEV-4 | Bug or misconfiguration with no data exposure | Private postmortem; no customer notification required |

## Process (T+0 = detection)

- **T+0 to T+1h:** Triage. Isolate affected services. Page founder.
- **T+1h to T+4h:** Scope assessment. Identify affected users + data
  types. Document everything in incident channel.
- **T+4h to T+24h:** Begin notifications. SEV-1: legal counsel
  contacted. Draft user communication.
- **T+24h to T+72h:** Supervisory authority notification (ICO / EU
  DPAs) for SEV-1. User notification email sent. Public status-page
  update.
- **T+7d:** Public postmortem at `/incidents/[date]-[slug]`.
- **T+30d:** Closing report to affected users + controllers.

## What we tell affected users (template)

- What happened (plain English, no marketing-speak)
- What data was affected
- What we know was NOT affected
- What we've done to contain
- What you should do (rotate API keys if any, watch for phishing)
- How to ask questions (security@)

## Our public commitments

- Initial customer notification within 72 hours of awareness
- Postmortem published within 7 days
- Closing report within 30 days
- We do not gag affected users or require NDAs for breach details
```

### Pre-launch checklist

- [ ] `security@archlineweights.com` mailbox + PGP key published
- [ ] Status page deployed (status.archlineweights.com on Atlassian
      Statuspage free tier or [betterstack.com](https://betterstack.com)
      free)
- [ ] Founder has ICO contact noted (UK supervisory authority for
      UK customers — `casework@ico.org.uk`)
- [ ] DPA vendor list noted with their breach-notification email
- [ ] Snapshot/backup recovery process tested

### What architects expect to see post-breach (from Gendo/Visoid practice)

- Email from a real person, not a "no-reply" address
- Specific data types affected (don't say "personal info" — say
  "name, email, file names, never file content")
- Concrete remediation steps for the user
- Postmortem published on a public URL
- Honesty about root cause (don't claim "sophisticated nation-state
  actor" if it was a misconfigured S3 bucket)

---

## 10. Cookie / consent banner posture

### Recommendation: **skip the banner**

Use cookieless analytics. We don't need user-tracking cookies for
business reasons — line-weight processing is a deterministic Python
job, not an ad-funded behavioral platform. Only cookie set is the
session token (strictly necessary, exempted from consent under
ePrivacy Directive Art. 5(3)).

### Stack

| Need | Tool | Why |
|---|---|---|
| Product analytics | Plausible OR Fathom | Cookieless, GDPR-compliant by default, no consent banner needed ([Plausible privacy-focused][plausible-pf]) |
| Error tracking | Sentry | Disable session-replay; use server-side error capture only |
| Auth | Magic link (Resend) | No password cookies, just session JWT (strictly-necessary) |
| Marketing email | Resend + plain unsubscribe link | No tracking pixels |

### Where a banner becomes mandatory

- If we ever add Google Analytics, Hotjar, FullStory, or Meta Pixel:
  yes, banner needed
- If we ever embed YouTube videos that set cookies: yes, or use
  privacy-enhanced mode (`youtube-nocookie.com`)
- If a customer's marketing team insists: usually their problem

### What to put on the site instead of a banner

A small footer link: "Privacy" → policy. A `/privacy/cookies`
sub-page that explains:

> We use one strictly-necessary cookie (your session). We do not
> use analytics cookies or tracking pixels. If you want to clear
> the session cookie, log out.

That's the whole disclosure.

---

## 11. Comparison: what architecture-cloud services promise publicly

| Service | Encryption claim | Retention | Region | Training-data clause | DPA |
|---|---|---|---|---|---|
| **Gendo** ([gendo.ai/privacy-policy][gendo-priv]) | "no method of transmission is 100% secure"; no specific algo named | "as long as is necessary"; no auto-delete published | UK / EU offices; SCCs for transfers | Policy mentions "data collected through training" but does not specify whether **user-submitted files** are used | Custom DPA on request (per [tech.eu coverage][tech-eu]) |
| **MyArchitectAI** ([myarchitectai.com/privacy-policy][maa-priv]) | Not specified in policy | "as long as necessary to provide Services" | Not specified | Not addressed — silence | Available on request |
| **Visoid** | (Privacy page returned 404 at time of research; rendering details cite cloud processing without retention specifics) | Unknown | EU (Norway-based company) | Unknown | Likely available — enterprise sales |
| **Buildhaus / Architectures of Disbelief** | Not architecture-cloud SaaS in the relevant sense (Buildhaus = various unrelated companies; Architectures of Disbelief = Cornell symposium 2008) | N/A | N/A | N/A | N/A |

### Where we can credibly differentiate

The above competitors mostly say nothing specific. **A clear,
plain-English Privacy Policy is itself a marketing differentiator.**
Specific commitments to make on the public marketing page:

1. **"Your drawings are deleted after 7/30/90 days. Automatically."**
   (specific number > vague "as needed")
2. **"Your drawings are never used to train AI."** (most competitors
   don't say this; saying it loudly is rare)
3. **"AES-256 at rest. TLS in transit. Both turned on by default."**
   (specifics > "industry-standard security")
4. **"Pre-signed DPA available — download from the pricing page."**
   (most competitors require sales conversation)
5. **"Subprocessors disclosed publicly with 30-day change
   notification."** (rare in this segment)
6. **"Pro Desktop tier — your drawings never leave your computer."**
   (the actual zero-knowledge offering for paranoid studios)

### Posture quotes to lift / mirror

From Gendo's posture:
> "Standard Contractual Clauses" or "UK Addendum" for cross-border
> transfers (we should mirror this language)

From MyArchitectAI's posture (privacy page):
> "We will not sell or share your Personal Data" — short, declarative,
> good model

From Plausible's stance:
> "no cookies, no personal data, no consent banner" — we should adapt
> this energy for our analytics page

---

## 12. Recommended decision summary

### v1 launch (Phase D, month 4)

- **Encryption:** server-side AES-256 at rest (R2 default), TLS 1.2+
  in transit. Marketing language: "encrypted at rest, encrypted in
  transit." No "E2E" claim.
- **Retention:** 7 / 30 / 90 day tiers. Implement deletion as
  soft-delete + 24-h grace + R2 hard-delete + DB anonymize +
  acknowledge backup propagation up to 30 d.
- **Region:** US-only, R2 `auto`, SCCs for EU customers. Plan EU
  region as Phase G1 paid feature.
- **Privacy Policy:** publish the plain-English version above + 30 d
  before launch get a $1.5–3k lawyer pass on Privacy + Terms + DPA
  bundle.
- **DPA:** publish pre-signed PDF on `/dpa`. Studio customers can
  countersign in DocuSign or just by accepting via email.
- **GDPR/CCPA floor:** all bullets in §6 floor list complete.
- **SOC 2:** defer.
- **Subprocessors:** publish list in §8.
- **IR plan:** publish one-pager from §9. Wire up `security@`,
  status page, PGP key.
- **Cookies:** none beyond session. Plausible analytics. No banner.

### Post-launch milestones

- **Month 5:** First enterprise security questionnaire arrives. Have
  the response template ready. Don't start SOC 2.
- **Month 6–8:** Public launch (Phase F). Update Privacy Policy with
  any learnings.
- **Month 8–12:** First $10k+ studio MRR. Begin SOC 2 Type 1
  readiness. Budget $20–30k cash + 200 h founder time.
- **Year 2:** SOC 2 Type 2 + EU residency tier + EU representative
  designation under GDPR Art. 27.

### The single decision that drives everything

**Server-side encryption with provider-managed keys is the bet that
makes the SaaS architecture feasible.** Going E2E client-side would
add weeks of crypto engineering, force a desktop-helper architecture
(B3 from Phase B), and break the pure-server compute path (B1) that
the spike already proved out. The trade-off is the marketing-honest
admission that "we technically have access while processing" — which
we mitigate via short retention, clear policy, and the offer of a
**Pro Desktop tier** for studios that cannot accept any upload.

---

## Sources

[r2-security]: https://developers.cloudflare.com/r2/reference/data-security/
[r2-location]: https://developers.cloudflare.com/r2/reference/data-location/
[plausible-pf]: https://plausible.io/privacy-focused-web-analytics
[gendo-priv]: https://www.gendo.ai/privacy-policy
[maa-priv]: https://www.myarchitectai.com/privacy-policy
[soc2-cost]: https://trycomp.ai/soc-2-cost-breakdown
[drata-pricing]: https://soc2auditors.org/insights/drata-pricing/
[vanta-pricing]: https://www.secureleap.tech/blog/vanta-review-pricing-top-alternatives-for-compliance-automation
[tech-eu]: https://tech.eu/2024/07/03/gendo-secures-1-1m-for-generative-ai-for-architects/
[ico-fee]: https://ico.org.uk/for-organisations/data-protection-fee/

- Cloudflare R2 data security: https://developers.cloudflare.com/r2/reference/data-security/
- Cloudflare R2 data location: https://developers.cloudflare.com/r2/reference/data-location/
- Gendo Privacy Policy: https://www.gendo.ai/privacy-policy
- MyArchitectAI Privacy Policy: https://www.myarchitectai.com/privacy-policy
- Plausible cookieless analytics: https://plausible.io/privacy-focused-web-analytics
- Plausible cookie banner discussion: https://plausible.io/blog/cookie-consent-banners
- SOC 2 cost breakdown 2026 (Comp.ai): https://trycomp.ai/soc-2-cost-breakdown
- Drata pricing 2026: https://soc2auditors.org/insights/drata-pricing/
- Vanta pricing 2026: https://www.secureleap.tech/blog/vanta-review-pricing-top-alternatives-for-compliance-automation
- Drata SOC 2 Type 1 vs Type 2: https://drata.com/learn/soc-2/type-1-vs-type-2
- Promise.legal DPA template: https://promise.legal/templates/dpa
- TermsFeed DPA template: https://www.termsfeed.com/blog/gdpr-data-processing-agreement-template/
- ICO Article 28 contracts: https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/accountability-and-governance/contracts-and-liabilities-between-controllers-and-processors-multi/what-needs-to-be-included-in-the-contract/
- Reform: GDPR breach checklist for SaaS: https://www.reform.app/blog/gdpr-breach-notification-checklist-saas
- Promise.legal breach response template: https://promise.legal/templates/breach-response-plan
- ICO data protection fee: https://ico.org.uk/for-organisations/data-protection-fee/
- Tech.eu Gendo coverage: https://tech.eu/2024/07/03/gendo-secures-1-1m-for-generative-ai-for-architects/

## Caveats and uncertainty

- **Visoid privacy page returned 404** at time of research — couldn't
  capture their specific posture. Re-check before launch.
- **Buildhaus and "Architectures of Disbelief" are not relevant
  competitors** — Buildhaus matches multiple unrelated companies;
  "Architecture of Disbelief" is a 2008 Cornell symposium, not a
  SaaS. Likely a list error in the original research brief. The real
  competitive set for privacy posture is Gendo + MyArchitectAI +
  Visoid, plus broader cloud-rendering peers (Krea, Magnific,
  Veras) which have generic AI-startup privacy postures.
- **Gendo training-data language is ambiguous** — their policy
  references "training" generically without saying user uploads are
  off-limits. We should clarify ours explicitly: "your drawings are
  not used to train AI."
- **Author is not a lawyer.** The Privacy Policy + DPA templates above
  are research artifacts, not legal advice. Run past licensed
  counsel before going live, especially:
  - state-specific addenda (VCDPA, CPA, CTDPA, TDPSA) when revenue
    crosses thresholds
  - California "Shine the Light" disclosure
  - arbitration vs class-action posture in Terms
  - merchant-of-record vs direct-Stripe choice (Stripe Tax handles
    most VAT, but liability allocation is a lawyer call)
- **Reading-level metric (10th grade) was not verified** — recommend
  passing draft through Hemingway Editor before publication.
- **EU representative cost (~$300/yr)** is a 2026 ballpark from
  ePrivacy.eu and InstantGDPR; verify current rates.
- **SOC 2 numbers** are 2026 figures; treat as ±20% accurate.
