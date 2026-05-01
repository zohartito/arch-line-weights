# Licensing — MIT → proprietary pivot, 2026-04-30

> Sub-agent research, 2026-04-30. Decision context: v1.0.0 was
> published to PyPI under MIT for ~15 minutes, then yanked. The MIT
> snapshot of v1.0.0 is **irrevocable for that exact distributed
> version**. All future versions need a new license.

## Recommendation

**Use [PolyForm Free Trial 1.0.0](https://polyformproject.org/licenses/free-trial/1.0.0/)
for the public source tree, paired with a custom commercial EULA for
paid distribution.**

Rationale below.

## License options considered

### A — Pure proprietary closed source

- **What:** Repo private, no source distributed to anyone, ship binaries
  with EULA.
- **Pros:** Maximum control, simplest legal posture.
- **Cons:** Can't link from a portfolio, can't use OSS-only CI services
  (some still exist), potential customers can't audit code.
- **Verdict:** Overkill for this project's audience (architecture
  students who often want to read scripts).

### B — Source-available with PolyForm Free Trial 1.0.0 ⭐ recommended

- **What:** Anyone can read source. Use is restricted to a 32-day
  evaluation. Production use requires a separate commercial license.
- **Pros:**
  - Drafted by Heather Meeker (the OSS commercial lawyer); short and
    enforceable.
  - Compatible with public-repo strategy (if you reverse the privacy
    decision later).
  - Clear "if you keep using this past 32 days, pay" signal.
  - Doesn't pretend to be open source — sets expectations honestly.
- **Cons:**
  - Not OSI-approved (because it's source-available, not open source).
    Some users will conflate the two.
  - Enforcement is on you; PolyForm provides the license, not the lawyer.
- **Verdict:** Best fit for the indie-commercial path.

### C — Functional Source License (FSL, Sentry)

- **What:** Source-available immediately; converts to Apache 2.0 / MIT
  after 2 years.
- **Pros:** Honest commercial-now-open-later signal.
- **Cons:** Auto-conversion is a foot-gun if you change your mind; a
  competitor could fork the 2-yr-old code.
- **Verdict:** Reject — the ARCH-line-weights value is in the *current*
  classifier and bridge logic; a 2-year-old version would still be
  competitive.

### D — Business Source License (BUSL, MariaDB)

- **What:** Restricted commercial use until a "Change Date," then
  reverts to GPL v2 or similar.
- **Pros:** Used by Sentry, MariaDB, CockroachDB at much larger scale.
- **Cons:** Heavyweight. Designed for projects where the operator (not
  the buyer) is the customer. Wrong shape here.
- **Verdict:** Reject.

### E — Elastic License v2 (ELv2)

- **What:** Source available; can't host as a competing service.
- **Pros:** Proven at scale.
- **Cons:** "Don't host as a service" clause irrelevant for a CLI tool.
- **Verdict:** Reject.

### F — PolyForm Noncommercial 1.0.0

- **What:** Free for non-commercial use; commercial use prohibited
  without a separate license.
- **Pros:** Students can use it freely without paying.
- **Cons:** Loses revenue from the largest segment (architecture
  students). Strategic mismatch.
- **Verdict:** Reject for revenue reasons; reconsider only if Phase C
  validation shows students won't pay even $19.

### G — PolyForm Strict 1.0.0

- **What:** No use at all without separate commercial license.
- **Pros:** Maximum protection.
- **Cons:** Can't even evaluate the tool without contacting you. Kills
  the discovery funnel.
- **Verdict:** Reject — the eval period is part of the marketing.

## v1.0.0 MIT — what we keep, what we don't

The yank from PyPI:

- ✅ **Hides v1.0.0 from `pip install arch-line-weights`** default
  resolution. New users won't get it.
- ✅ **Preserves the project name reservation.** Anyone trying to
  squat the name fails.
- ✅ **Stops new MIT distributions** from happening through PyPI.
- ❌ **Does NOT revoke MIT rights for v1.0.0 copies already
  downloaded.** Anyone who pulled v1.0.0 in the ~15-min window owns it
  under MIT in perpetuity.
- ❌ **Does NOT prevent explicit-pin install.** `pip install
  arch-line-weights==1.0.0` still works for installations that have
  the version cached.
- ❌ **Does NOT remove the wheel from PyPI's storage.** It's still
  there, just hidden from search and default resolver.

To make v1.0.0 fully unreachable you would need to **delete** (not
yank) the release. Deletion frees the version number for re-upload by
anyone — a worse outcome than yank. Stay yanked.

## 5-step "MIT → Commercial" checklist

- [x] **1. Yank old MIT releases on PyPI** — done 2026-04-30 for v1.0.0.
- [ ] **2. Replace `LICENSE` file** with PolyForm Free Trial 1.0.0
  + a brief project-specific notice. Commit on the repo's main branch.
- [ ] **3. Update `pyproject.toml`** — change `license` to PEP 639
  SPDX expression: `LicenseRef-PolyForm-Free-Trial-1.0.0` (custom
  identifier; SPDX hasn't accepted PolyForm into its registry yet).
- [x] **4. Add `NOTICE.md`** documenting the MIT history. Done.
- [ ] **5. Strip OSS framing** from `README.md`,
  `CONTRIBUTING.md`, `docs/announce/*`. Replace "open-source" with
  "source-available," remove "MIT," remove contributor onboarding (we
  aren't accepting external contributions until product-market fit).
- [ ] **6. Add a commercial EULA** for paid distribution.
  Template recommendation: PolyForm + an addendum specifying tier
  rights (student / personal / studio).

Steps 2, 3, 5, 6 are Phase B in the roadmap — do them this week before
re-publishing anything.

## Custom EULA — sketch of paid-tier addendum

Augment PolyForm Free Trial 1.0.0 with these terms for paid copies:

1. **License grant** — non-exclusive, non-transferable, perpetual
   (one-time tiers) or annual (subscription tiers) right to use.
2. **Seat scope** —
   - Student: 1 user, 2 personal devices.
   - Personal: 1 user, 3 personal devices.
   - Small studio: ≤20 named users in the same legal entity.
3. **No redistribution** of source or binaries to non-licensees.
4. **No reverse-engineering** to build a competing product.
5. **Update entitlement** —
   - Student/Personal: 1 year of updates included; perpetual right to
     use the version current at purchase.
   - Studio: updates for the duration of the active subscription.
6. **Refunds** — 14-day no-questions-asked.
7. **Termination** for material breach.
8. **Warranty disclaimer** — AS-IS, no warranty of fitness for any
   particular purpose.
9. **Governing law** — California.

Have a lawyer review before any paid sale. Estimated cost: $500–1500
for a one-shot review of a template EULA.

## Things you can NOT change retroactively

1. **The MIT terms on the v1.0.0 wheel** that's already on PyPI's
   storage and any `pip` cache, virtualenv, or local copy. Those
   bytes shipped under MIT and that snapshot is forever MIT-licensed.
2. **Project name on PyPI.** It's yours as long as you keep the account
   active, but you can't transfer to another author without consent
   from PyPI admins.
3. **GitHub stars/forks** that happened before going private. They
   persist as "ghost" entries on the public timeline of the user
   accounts that did them.

## Things you CAN do later

1. **Re-publish v1.0.1+** under PolyForm with the same project name.
2. **Switch licenses again** for v2.0.0+ (e.g., go fully commercial,
   or back to OSS if you decide to). Each version's license is fixed
   at publication.
3. **Re-open the repo** by changing GitHub visibility back to public.
   Pages will re-deploy automatically.
4. **Delete the PyPI account entirely** — but this frees `arch-line-weights`
   for squatting. Don't.

## Sources

- [PolyForm Project — Free Trial 1.0.0](https://polyformproject.org/licenses/free-trial/1.0.0/)
- [PolyForm Project — license overview](https://polyformproject.org/licenses/)
- Heather Meeker — *Open Source for Business* (2020), chs. 9, 12
- [Sentry — Functional Source License](https://fsl.software/)
- [PEP 639 — license metadata](https://peps.python.org/pep-0639/)
- [PyPI yank semantics — PEP 592](https://peps.python.org/pep-0592/)
- [SPDX License List](https://spdx.org/licenses/)
- [GitHub — choosealicense.com](https://choosealicense.com/non-software/)

## Related

- `docs/ROADMAP.md` Phase B — license swap is the gating task before
  any further public work.
- `NOTICE.md` — the public-facing license-history doc.
- `docs/POSTMORTEM.md` Attempt 7 — the publish-then-yank story.
