# Roadmap (post-pivot, 2026-04-30)

> **Status:** v1.0.0 was published to PyPI under MIT for ~15 minutes,
> then yanked. The project is now **private and pre-monetization**. This
> document supersedes the earlier OSS-focused roadmap.

## Where we are now

- 6 minor releases shipped (v0.1 → v0.6.2)
- ~9,000 lines of code + 1,800 lines of docs/research
- 26 tests passing, ruff lint clean
- Auto-bridge module rescues 14→18/21 cut layers on the reference drawing
- Material hatching engine (14 recipes, shapely-backed)
- Three Rhino integration scaffolds (GhPython component, Eto toolbar, pre-export tagger)
- Visual preview via PyMuPDF + Ghostscript fallback
- ISO 128 standards-aligned tier presets with `--scale --for-print`
- MkDocs Material site (offline now since the repo is private on the GH free plan)
- Comprehensive POSTMORTEM documenting every failed approach
- 12 sub-agent research transcripts in `docs/research/`

## Phases A–G

### Phase A — Personal use (now → 1 month) 🚧

**Goal: validate the tool by living on it.**

- [ ] A1. Use it on every remaining ARCH 202B + ARCH 211 drawing this term
- [ ] A2. Build a portfolio with HIERARCHY.ai + POCHE.ai outputs
- [ ] A3. Show classmates the result without explaining the tool — gauge organic "what'd you use?" reactions
- [ ] A4. Fix the 3 stubborn cut layers via `__POCHE_CLOSE__` workflow on actual drawings
- [ ] A5. Track manual fixes still needed per drawing — that's the "remaining work" the tool doesn't yet do

### Phase B — Lock in IP (this week)

**Goal: stop being open-source going forward; preserve future commercial options.**

- [ ] B1. Replace `LICENSE` (MIT) with a proprietary EULA (see `docs/research/licensing.md` once Phase B sub-agent returns)
- [ ] B2. Add `NOTICE.md` documenting the v1.0.0 MIT snapshot is irrevocable for that exact version, but all future versions are proprietary
- [ ] B3. Strip OSS framing from `README.md`, `CONTRIBUTING.md`, marketing drafts
- [ ] B4. Save offline copy of repo + `dist/` + `pyproject.toml`-pinned deps
- [ ] B5. Add internal `BUSINESS.md` for pricing thoughts, target customers, learnings as we go

### Phase C — Demand validation (2 weeks)

**Goal: know if the market exists before building distribution.**

- [ ] C1. Interview 5–10 architecture students (script in `docs/research/customer-interviews.md` once sub-agent returns)
- [ ] C2. Interview 2–3 small-studio (5–20 person offices) reps
- [ ] C3. Define crisp value prop: "saves N hours per submission set"
- [ ] C4. Pick price points based on findings, not gut. Likely tiers:
  - Student: $19 one-time
  - Personal / sole practitioner: $79 one-time or $9/mo
  - Small studio (≤20 seats): $499/yr
  - Mid studio (≤100 seats): $TBD
- [ ] C5. **Decision gate:** if <30% of interviewees say "I'd pay $X for this," shelve to a portfolio piece. If ≥30%, go to Phase D.

### Phase D — Distribution v1 (month 2)

**Goal: first paying customer.**

- [ ] D1. PyInstaller single-binary build for macOS + Windows (no Python install required by buyer)
- [ ] D2. macOS code signing + notarization (Apple Dev $99/yr)
- [ ] D3. Windows code signing (EV cert ~$300/yr OR Azure Trusted Signing if cheaper)
- [ ] D4. Pick distribution platform: Gumroad / Lemon Squeezy / Paddle (research in `docs/research/distribution-platforms.md`)
- [ ] D5. Simple license-key system — UUID per purchase, HMAC verify on first run, no online phone-home
- [ ] D6. Closed beta with the people from Phase C
- [ ] D7. First public sale 🎉

### Phase E — Solve the unsolveds (month 3)

**Goal: tool stops requiring user-side workarounds.**

- [ ] E1. The 3 stubborn cut layers — proper algorithmic fix beyond `__POCHE_CLOSE__`. Probably involves: (a) better endpoint clustering, (b) fallback that queries Rhino's source if available, (c) ML-based topology inference
- [ ] E2. More material hatches: slate, terrazzo, OSB, polished concrete, perforated metal, pavers, mineral wool variants
- [ ] E3. Plan / elevation / detail presets actually distinct from section (currently they share the same ISO ladder)
- [ ] E4. Batch mode — drag a folder of `.ai`s, process all
- [ ] E5. Smarter Rhino layer-name inference (handles non-Make2D Rhino exports — Inkscape, Vectorworks, AutoCAD)

### Phase F — Web app (month 5+)

**Goal: lower friction to "drag and drop, get result."**

- [ ] F1. Domain (`archlineweights.com` or shorter alternative)
- [ ] F2. Web upload → Stripe-paywalled processing → download result
- [ ] F3. Browser-based before/after preview (`preview.py` served as a service)
- [ ] F4. User accounts, magic-link auth, subscription tiers
- [ ] F5. Migrate Gumroad customers to free web accounts as thanks
- [ ] F6. Tax handling via Stripe Tax or Merchant of Record (Paddle / Lemon Squeezy hosted)

### Phase G — Scale (year 2+)

**Goal: move from "indie tool" to "studio-standard.**

- [ ] G1. Studio enterprise plans (per-seat, SSO, on-prem option for security-sensitive offices)
- [ ] G2. Rhino plugin distribution via Food4Rhino marketplace (paid listing)
- [ ] G3. Adobe Exchange listing if/when Adobe ships UXP for Illustrator (still internal-only as of 2026-04)
- [ ] G4. AI-assisted variant: LLM analyzes drawing, suggests stylistic improvements
- [ ] G5. Multi-drawing consistency (apply same hierarchy across plan/section/elevation set)
- [ ] G6. Style transfer ("make this look like the Tatiana Bilbao funeral home section")

## Decision gates

- **End of Phase A:** is the tool good enough that *I* prefer it to manual work? If no, fix the tool. If yes, advance.
- **End of Phase C:** is there demand at viable prices? If no, shelve. If yes, advance.
- **3 months after first sale:** is revenue covering hosting + signing certs + my time at $X/hr? If no, narrow scope. If yes, scale.

## What WILL break this roadmap

Documented for future-me / future contributors:

- **Adobe ships UXP for Illustrator publicly** → opens a much bigger market (Adobe Exchange listing) → accelerate Phase G3
- **Rhino 9 changes Make2D output format** → may need parser rewrites
- **A competitor launches first** → Show It Better, Astute Graphics, or some YC company with venture money — may need to pivot to differentiation rather than feature parity
- **Architecture school tooling shifts to AI-first** (Hyperboloid, etc.) → may make the line-weight problem moot for new students; pivot to AI-augmented mode

## See also

- [`docs/POSTMORTEM.md`](POSTMORTEM.md) — every failed approach, never repeat
- [`docs/LESSONS_LEARNED.md`](LESSONS_LEARNED.md) — what works, kept short
- [`docs/BUSINESS.md`](BUSINESS.md) — pricing, target customers, learnings (private)
- [`docs/research/`](research/) — sub-agent research transcripts informing each phase
