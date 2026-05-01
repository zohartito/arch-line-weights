# Hybrid local-helper architecture (B3)

> Sub-agent design doc, 2026-04-30. Roadmap Phase B3 — the hybrid path
> where the web app handles paywall + license issuance + (optionally)
> heavy compute, but Illustrator manipulation runs on the user's
> machine via a tiny signed local helper.
>
> Companion to `binary-distribution.md` (signing infra, reused
> verbatim — not duplicated here) and the eventual
> `saas-architecture.md` (Phase B4 decision record).

## TL;DR

- **Recommended UX:** drag-drop on website → file uploads to server →
  server runs all *headless* compute (classify, poche, weight calc) →
  emits a signed "apply plan" JSON → user's local helper picks it up
  and drives Illustrator → output saved locally.
- **Recommended auth:** OAuth-style device-code flow seeded by a
  magic-link login in the browser. Helper gets a long-lived refresh
  token, swaps for short-lived access tokens.
- **Recommended platform:** macOS only for v1 (osascript + JSX is
  solved); Windows in v1.5 once shape of the helper is proven.
- **Build effort:** ~6 person-weeks for v1 macOS-only helper + web
  side glue, on top of whichever core compute path (B1 or B2) we
  already had to build.
- **Verdict:** B3 is a **fallback**, not the primary SaaS path. Ship
  it as the *Pro Desktop* tier on top of a B2 (PDF-only) web product
  — gives privacy-conscious users a Round-Trip-To-Illustrator option
  without forcing every user through a two-step install.

## Architecture diagram

```
                    ┌────────────────────────┐
                    │       USER             │
                    │  (architect on Mac)    │
                    └────────────────────────┘
                          │             │
                          │             │  (1) drag-drop .ai
                          │             ▼
                          │      ┌───────────────────────────┐
                          │      │      WEB APP (browser)    │
                          │      │  archlineweights.com      │
                          │      │  - magic-link login       │
                          │      │  - upload form / job UI   │
                          │      │  - subscription mgmt      │
                          │      └───────────────────────────┘
                          │                    │
                          │                    │  HTTPS
                          │                    ▼
                          │      ┌───────────────────────────┐
                          │      │   API + COMPUTE (Fly.io)  │
                          │      │  - FastAPI                │
                          │      │  - Postgres (jobs, users) │
                          │      │  - R2/S3 (drawings)       │
                          │      │  - Stripe (billing)       │
                          │      │  - layer_classify, poche, │
                          │      │    bridge, hatch, presets │
                          │      │  - emits "apply plan"     │
                          │      │    (signed JSON + JSX)    │
                          │      └───────────────────────────┘
                          │                    │
                          │                    │  (2) plan + JSX bundle
                          │                    │     (HTTPS, signed)
                          ▼                    ▼
                  ┌──────────────────────────────────────────┐
                  │         LOCAL HELPER (menu bar app)      │
                  │            ~/Applications/archlw         │
                  │  - polls /jobs/next on a timer           │
                  │  - verifies plan signature               │
                  │  - writes /tmp/plan.jsx                  │
                  │  - osascript → Illustrator do javascript │
                  │  - tails progress.txt → POSTs heartbeats │
                  │  - uploads report.txt + receipt          │
                  │  - shows local notifications             │
                  └──────────────────────────────────────────┘
                          │             │
              osascript do javascript  │  (3) saved .ai
                          ▼             │      stays local
                  ┌──────────────────┐  │
                  │   ILLUSTRATOR    │  │
                  │   (user's app)   │──┘
                  │  - opens src.ai  │
                  │  - runs JSX      │
                  │  - saveAs out.ai │
                  └──────────────────┘
```

## Component breakdown

### What's in the web app

- **Frontend** (SvelteKit, per Roadmap D3): login, drag-drop upload,
  job dashboard, subscription mgmt, helper-install prompt.
- **API** (FastAPI on Fly.io, per Roadmap D2):
  - Auth (magic link + device-code endpoints)
  - Job queue (`POST /jobs`, `GET /jobs/next`, `POST /jobs/:id/heartbeat`)
  - Compute workers running existing Python pipeline:
    - `layer_classify.py` — semantic tier inference
    - `bridge.py`, `poche` two-stage — geometry compute
    - `apply.py` — pikepdf path for the *strokes* fallback
    - **NEW:** `plan_emit.py` — produces a self-contained "apply plan"
      = `{plan.json, apply.jsx, report_template.txt}` bundle
  - Stripe webhooks, license issuance, usage metering
  - Helper update feed (signed JSON manifest, see "Update flow")
- **Storage:** R2 for original `.ai` (free tier auto-deletes 7 days
  after last access), Postgres for job state + license records.

### What's in the local helper

- **Menu-bar app** written in Swift (macOS) — *not* Python. Reasons:
  - 10 MB binary vs PyInstaller's 80–120 MB
  - First-launch is instant, not 4 s extracting a Python runtime
  - Native NSStatusItem + UserNotifications + UNNotification = no
    bundled GUI framework
  - Fewer moving parts to notarize
- Single Swift binary, no installer; ships as a notarized `.dmg`
  containing the `.app`. Reuses the **Apple Developer ID +
  notarytool** flow already documented in `binary-distribution.md`.
- Embedded responsibilities:
  - OAuth device-code flow + token storage in macOS Keychain
  - Long-poll `GET /jobs/next?since=...` (server-sent events or
    plain HTTP long-poll; SSE preferred — connection stays warm)
  - Verify plan signature against pinned server pubkey
  - Write JSX + plan to `~/Library/Application Support/archlw/jobs/<id>/`
  - Spawn `osascript` with the same `tell application "Adobe
    Illustrator" / do javascript` pattern proven in
    `apply_jsx.py:run_jsx_in_illustrator()`
  - Tail `/tmp/arch_lw_progress.txt`, POST heartbeats to API
  - On completion: parse `report.txt`, POST as receipt, surface a
    macOS notification with the output path
- **No Python in the helper.** Compute is on the server. The helper
  is a dumb pipe.

### What's in Illustrator

- Pure ExtendScript JSX delivered by the server, executed by the
  helper. Same shape as today's `apply_jsx.py`'s `JSX_TEMPLATE`:
  - `app.userInteractionLevel = DONTDISPLAYALERTS`
  - `maximumUndoDepth = 1` for linear-time iteration
  - Walk leaf layers, set per-pathItem `strokeWidth`
  - `saveAs` with `pdfCompatible = true`
  - Write a report + progress file via `File.write()`
- The JSX is **stateless**; all decisions (which layer → which weight,
  which polygon → which fill) are baked into the JS object literal at
  the top of the script by the server's `plan_emit.py`. Same trick
  Attempt 5 used (`docs/POSTMORTEM.md` Attempt 5) — coordinates baked
  in, no I/O at JSX runtime.

### Data flow — purely-local vs server-compute

Two sub-variants of B3 are worth distinguishing:

**B3a — Server compute, local apply (recommended):**
- `.ai` uploads to server, full poche + classify pipeline runs there,
  server emits a fully-baked JSX, helper just executes it.
- Pros: server can iterate on classifier without re-shipping helper;
  studio tier can offer batch compute parallelized across cloud
  workers; most of the IP stays server-side.
- Cons: drawings *do* leave the user's machine briefly, breaks the
  "purely local" privacy story. Mitigated by 7-day auto-delete +
  encryption at rest.

**B3b — Local compute, server only meters/bills:**
- `.ai` never leaves the user's machine. Server hands out a license
  token and a *bundle* of compute code (Python or JS) that the helper
  runs locally. Server sees only billing events and anonymized
  telemetry.
- Pros: privacy-pure ("your drawings never touch our servers"); no
  R2 bill; no GDPR data-residency story to write.
- Cons: helper is now ~100 MB (PyInstaller bundle) instead of ~10 MB;
  IP is on every customer's disk; server is barely doing anything to
  justify a subscription; classifier updates require helper updates.

**Recommendation: B3a.** The privacy framing is a marketing point but
not a hard constraint for the target architect — they email
PDF drawings to consultants weekly. Server compute is the lower-friction
path and matches what's already built (`layer_classify.py` etc.
are Python and want to stay on Linux). B3b is the fallback if
post-launch interviews reveal a privacy-driven segment large enough
to justify the maintenance cost.

## Auth flow

OAuth-style device-code, lifted from how `gh auth login` and Stripe
CLI do it. The user starts in the browser (where they already pay),
the helper gets a token bound to their account.

```
1. User installs helper, clicks "Sign in" in menu bar
2. Helper → POST /oauth/device → { device_code, user_code,
                                   verification_uri, expires_in }
3. Helper opens https://archlineweights.com/device?user_code=ABCD-1234
   in default browser AND copies user_code to clipboard
4. User logs in with magic link (already paid sub, account exists)
5. User confirms "Authorize archlw helper on this Mac?" — yes
6. Helper polls POST /oauth/token until: { access_token,
                                            refresh_token, expires_in }
7. Helper stores refresh_token in macOS Keychain under
   service="com.archlineweights.helper", account=<email>
8. Future: helper auto-refreshes; if refresh fails (revoked,
   subscription lapsed), helper shows "Reauthorize" notification
```

**License vs auth:** Don't conflate. The auth token says "this is
zohar@example.com on this Mac." The user's *subscription* state (paid
/ trialing / past_due / canceled) is checked server-side every time a
job is enqueued. No offline grace period in v1 — helper requires
network to start a job. (Acceptable: target customer is online while
working on .ai files.)

**Why not embedded license keys?** They're a pain to revoke on
subscription cancel, and we'd need a clock-rollback story. Device
codes give us per-Mac authorization that's revocable from the web
account page.

## Update flow

We follow `binary-distribution.md`'s posture: **no auto-update in
v1.** For the helper specifically, the recommendation is a tiny
*manual* update prompt with a one-click installer download.

```
1. On launch, helper hits GET /helper/manifest.json
   (cached at Cloudflare, signed with same key as plans)
2. Manifest:
   {
     "latest_version": "0.4.2",
     "min_supported_version": "0.3.0",
     "macos_universal_dmg": {
       "url": "https://cdn.archlineweights.com/helper/0.4.2/archlw-0.4.2.dmg",
       "sha256": "..."
     },
     "release_notes_url": "..."
   }
3. If installed_version < latest_version: menu bar shows badge,
   click → "New version 0.4.2 available [Download] [Skip]"
4. If installed_version < min_supported_version: helper refuses to
   run new jobs and shows blocking "Update required" alert. The
   server enforces the same minimum (rejects heartbeats from old
   helpers so users on stale builds don't silently submit jobs).
5. Download is a notarized .dmg; standard macOS drag-to-Applications
   replace flow. No Sparkle, no in-place patching, no admin prompts.
```

**Why no Sparkle?** Two reasons:
1. Sparkle works fine but we'd need to maintain a Sparkle appcast
   feed *and* a JSON manifest for our existing jobs API. Overkill
   for one binary updated maybe quarterly.
2. Per `binary-distribution.md` rationale: license-key fraud +
   auto-update is a foot-gun. Manual update gives us a chance to
   re-check subscription status on each upgrade.

If the helper proves popular enough (~500+ active installs)
**Phase G** can revisit Sparkle/WinSparkle. Until then, manual
download is fine.

**Delta patches?** No. Whole-DMG download. Helper is small enough
(target ≤ 15 MB compressed) that delta tooling isn't worth it.

## Privacy framing — marketing differentiator

Whether we ship B3a or B3b, the framing language is similar:

- **"Your drawings stay on your machine."** (Strictly true for B3b;
  for B3a it's "your drawings auto-delete in 7 days, encrypted at
  rest, never used for training or shared.")
- **"Works with your existing Illustrator install."** Implicit
  contrast vs cloud-Illustrator competitors that re-render drawings
  server-side and lose layer fidelity.
- **"Round-trip your `.ai` file — no PDF lock-in."** The competitor
  to compete with here is *the user's manual workflow*, not other
  SaaS. The hybrid-local path is the only one that returns a real
  `.ai` with all 62 OCG layers preserved (per `apply_jsx.py`'s
  proven success on the reference drawing).
- **"No cloud Illustrator account, no VDI."** Avoid Adobe's own
  Illustrator-on-the-web; that's a different product targeting a
  different audience.

The marketing landing page can run two tiers side by side: *Web
Plan* (PDF-only output, B2) for casual users; *Desktop Plan* (round-
trip via local helper, B3) for purists and studio leads.

## Failure modes

| Failure | Detection | Fallback |
|---|---|---|
| Illustrator not installed | Helper checks for `/Applications/Adobe Illustrator 202*/Adobe Illustrator.app` on startup; greys out menu | Show "Install Illustrator to enable round-trip" + offer PDF-only fallback (B2 path) |
| Illustrator on a different machine than helper | Same as above — helper is per-machine | Document explicitly: install helper on whichever Mac runs Illustrator |
| AppleScript permissions denied | First osascript call fails with `errAEEventNotPermitted (-1743)`; helper catches and surfaces | Notification + open System Settings → Privacy & Security → Automation directly via `x-apple.systempreferences:` URL |
| Adobe ships UXP and breaks JSX | Job fails with specific JSX exception; server-side stats flag a regression spike | Emit a UXP plugin (.ccx) bundle alongside the JSX, helper picks based on Illustrator version. We already need this for Phase G3 anyway. Worst case: pin users to Illustrator 2026 until UXP port lands. |
| Illustrator open with unsaved doc | JSX `app.activeDocument` mismatch — current `apply_jsx.py` already handles by walking `app.documents[]` looking for matching `fullName.fsName` | Helper retries with `open POSIX file` first; if still fails, surface "close other docs" notification |
| Helper crashes mid-job | Illustrator may be left with `userInteractionLevel = DONTDISPLAYALERTS` and `maximumUndoDepth = 1` | Helper writes a "cleanup.jsx" on every job-start; on next launch, runs cleanup against any active doc to reset prefs |
| User has Illustrator but pirated/old | Helper version-checks via `app.version` JSX; rejects below 2024 | "Illustrator 2024+ required" message; offer PDF-only |
| Subscription lapses mid-job | Server returns 402 on heartbeat | Helper saves the in-flight plan locally; after re-subscribe, "Resume previous job?" notification |
| Network drop mid-job | Plan is already on disk, JSX is already running, output happens locally | Helper retries heartbeats with backoff; on reconnect, posts the final receipt. Job succeeds even if heartbeats lost. |
| Two helpers signed in to same account | Both poll `/jobs/next` | Server uses a single-consumer queue per account (claim-on-pop); only one helper picks any given job |

## Cross-platform

**v1 — macOS only.** Justification:

1. `apply_jsx.py:run_jsx_in_illustrator()` already works on macOS via
   `osascript do javascript`. Battle-tested on the reference 340 K
   stroke drawing.
2. Windows `do javascript` requires JSI (JavaScript Server) or VBScript +
   `CreateObject("Illustrator.Application").DoJavaScriptFile()`. Both
   work but are gnarlier and need separate testing infrastructure
   we don't have.
3. The architecture-student segment skews macOS heavily (USC studios,
   30X40 audience); the studio segment is more mixed. Sole-practitioner
   Windows users can use the **B2 PDF-only** web tier in v1.
4. Adding Windows = +Azure Trusted Signing certificate (already
   budgeted in `binary-distribution.md`, ~$120/yr) + Windows-specific
   menu-bar/tray code + a separate test bench. ~3 extra person-weeks.

**v1.5 — add Windows.** Same Swift→C# port pattern as the
PyInstaller cross-compile path documented in `binary-distribution.md`.
Reuse the same release-binary.yml workflow with an added `build-windows`
job — minimal incremental CI complexity. Don't ship Windows v1 just
because users ask; ship it once the macOS helper is the *known* SaaS
moat.

## Helper distribution

Reuse `binary-distribution.md` end-to-end — do not duplicate signing
analysis here. Specifically:

- **macOS:** Apple Developer Program ($99/yr, already accounted for).
  Notarize via `xcrun notarytool` + staple. Same secrets:
  `APPLE_ID`, `APPLE_PASSWORD`, `APPLE_TEAM_ID`,
  `APPLE_DEVELOPER_ID_CERT`, `APPLE_DEVELOPER_ID_CERT_PASSWORD`.
- **Windows (v1.5):** Azure Trusted Signing (~$120/yr). Same
  `azure/trusted-signing-action@v0.5.0` GitHub Action.
- **Workflow:** add an `archlw-helper` job to the existing
  `.github/workflows-disabled/release-binary.yml.disabled` rather
  than creating a parallel pipeline. The helper isn't `arch-lw` (the
  CLI), it's a separate menu-bar binary, but the signing flow is
  identical. Two output artifacts per release: `arch-lw` (CLI, if/when
  we ever ship it) and `archlw-helper.dmg`.

Distribution channel: direct download from the user's web account
("Download Helper for macOS"). No Mac App Store (sandboxing would
block AppleScript automation), no Homebrew Cask in v1 (private
beta).

## Tradeoff matrix vs B1 and B2

| Dimension | B1 (pikepdf-only) | B2 (PDF-only output) | B3 (hybrid local helper) |
|---|---|---|---|
| **UX install steps** | 0 (web upload only) | 0 (web upload only) | **2** (web upload + helper install) |
| **First-job time-to-value** | <2 min | <2 min | ~10 min (download .dmg, drag, sign in, grant Automation perms) |
| **Output quality (.ai round-trip)** | Risk: PieceInfo write may flatten layers (Attempt 4 unresolved) | None — PDF only, no .ai out | High — proven JSX path, 62/62 layer fidelity |
| **Output quality (PDF)** | Good if pikepdf path works | Good — same as B1 PDF | Good — JSX path emits `pdfCompatible=true` |
| **Privacy story** | Drawings on server | Drawings on server | Strong — drawings can be local only (B3b) or auto-deleted (B3a) |
| **Server compute cost** | High (full pipeline per job) | High (full pipeline per job) | Medium (compute server-side but no Illustrator render) — same as B1/B2 |
| **Build effort to MVP** | 2–3 wk (resolve PieceInfo write OR accept layer loss) | 1–2 wk (already have all the code) | **6 wk** (helper + auth + plan format + signing + Sparkle-or-not + per-OS testing) |
| **Ongoing maintenance** | Low — one Python codebase | Lowest — one Python codebase, simpler output | High — two codebases (Python web + Swift helper), Adobe Illustrator version drift, AppleScript permission UX, notarization renewals |
| **Customer trust / "real tool" feel** | Medium — feels like SaaS | Medium-low — "PDF only" sounds like a downgrade | High — the helper installs on your machine, plays nice with your existing Illustrator, doesn't lock you in |
| **Adobe-shipping-UXP risk** | Zero (no Adobe interaction) | Zero (no Adobe interaction) | Real — JSX deprecation roadmap eventually breaks us; mitigated by `app.version` gating + UXP port (Phase G3) |
| **Studio-tier batch story** | Strong — server-parallel | Strong — server-parallel | Awkward — "kick off 50 jobs, sit at your Mac while Illustrator opens 50 files in a row." Helper can serialize, but it's not concurrent because Illustrator is single-instance. |
| **Goes-down-in-flames if we shut the server off** | Yes (no offline mode) | Yes (no offline mode) | Yes (no offline mode), but worse UX because the helper's already installed, looks like our problem |

## Build-effort estimate (B3 v1 macOS-only)

| Task | Effort |
|---|---|
| Helper Swift app (menu bar, login, polling, JSX dispatch) | 2.0 wk |
| Plan format + signature scheme + `plan_emit.py` server module | 0.5 wk |
| OAuth device-code endpoints + magic-link integration | 0.5 wk |
| Job queue + heartbeat API + Postgres schema | 0.5 wk |
| Reuse `apply_jsx.py` as the JSX template emitter | 0.2 wk |
| Notarization pipeline (clone + adapt `release-binary.yml`) | 0.3 wk |
| Web frontend "install helper" onboarding flow | 0.5 wk |
| Helper update manifest + version-check UX | 0.3 wk |
| AppleScript-permissions UX (deep links to Settings, retry flow) | 0.4 wk |
| Failure-mode handling per the table above | 0.5 wk |
| End-to-end testing (real Illustrator on a real Mac, 3 reference drawings, all six failure modes) | 0.8 wk |
| Buffer (15%) | 0.5 wk |
| **Total** | **~6 person-weeks** |

This **adds to** the B1 or B2 build cost rather than replacing it
— the server still runs the same Python compute pipeline.

## Verdict

**B3 is a fallback / Pro tier — not the primary SaaS path.**

The two-step install adds ~10 min to time-to-first-value, which is
unacceptable as a default for the target architect ("I just want to
upload my drawing and click a button"). However:

1. As a **Pro Desktop tier on top of B2**, it's the differentiator
   that justifies a $19/mo or $49/mo upcharge — round-trip `.ai`
   plus the privacy-friendly "your drawings stay on your machine."
2. As a **fallback if B1 fails**, it preserves SaaS while delivering
   real `.ai` output. Better than retreating to a one-time CLI sale
   per v2 of the roadmap.

**Recommended path:**
- **Phase D MVP:** ship B2 (PDF-only) as the web product. Fastest to
  market, lowest ongoing cost, validates demand at Phase C price
  points without the helper liability.
- **Phase E (parallel with E1–E5):** build B3a as a Pro tier add-on,
  reusing all of B2's compute. 6-week side investment.
- **Phase F:** marketed as two-tier (Web / Desktop). Desktop tier
  is the upsell.

If B1 turns out to work (clean PieceInfo writes, layer-preserving
.ai output entirely from Python), then B3 is **superseded** for the
PDF-out path but **still useful** as a privacy / on-prem story for
studios. Re-evaluate at the Phase B4 decision gate.

## See also

- `docs/ROADMAP.md` Phase B (B1/B2/B3 spike), Phase D (web app MVP),
  Phase F4 (paid CLI as Pro tier alternative)
- `docs/POSTMORTEM.md` Attempt 2 + Attempt 5 (the JSX patterns this
  helper invokes)
- `docs/research/binary-distribution.md` (signing + notarization
  infra — *do not duplicate; reuse*)
- `src/arch_line_weights/apply_jsx.py` (the working JSX dispatch
  pattern that the helper will reimplement in Swift)
- `docs/research/saas-architecture.md` (TBD — Phase B4 decision
  record will record which of B1/B2/B3 we picked, citing this doc)
