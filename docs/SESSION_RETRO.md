# Session retrospective — 2026-04-29 to 2026-04-30 (~30-hour arc)

> Narrative of how `arch-line-weights` went from "fix line weights on this
> drawing" to "private SaaS-feasible v0.5 with full Phase B closed" in
> roughly thirty hours of agent-collaborative work. Sister to
> `POSTMORTEM.md` (per-attempt) and `LESSONS_LEARNED.md` (distilled bullets) —
> this is the *story*, not the *artifacts*.

## How it started

**One file, one ask.**

Zohar drops a 24 MB `.ai` file into Claude Code and asks for line weights to
be fixed. The drawing is from USC ARCH 202B, exported from Rhino's Make2D +
Clipping Plane workflow, with 340,323 strokes across 62 OCG layers, 21 of
which are cut layers that should become poché-filled black.

The first instinct — "use Adobe's plugin, it'll be 30 minutes" — is wrong
within the first hour. The plugin doesn't know what a section cut is, can't
tell which layers are foreground vs background, and treats every stroke as
arbitrary.

The conversation rapidly expands: build a tool. Make it reusable. Add poché.
Standards-align it. Ship it.

## Phase 1 (v0.1) — the first quick win that broke layers

`pikepdf` lets us walk the PDF content stream and rewrite stroke-width
operators per color. 110 seconds on 340 K strokes. Fast. Clean.

Strip `/PieceInfo` to make Illustrator parse the modified content stream
instead of its private layer cache. Ship as v0.1.

Zohar opens the result. **All 62 layers collapsed into one.**

> "Claude, you turned it into one layer, and all the line weights are off."

This is the project's first hard lesson: **layer fidelity is not
negotiable.** It also opens the project's first deep dive into AI file
format internals — `/PieceInfo /Illustrator /Private` is canonical;
the PDF content stream is rendering fallback. Strip the canonical, lose
the layers.

Lesson 1 lands. Default behavior gets reversed.

## Phase 2 (v0.2) — JSX wins over PDF surgery

If we can't strip PieceInfo, then we can't operate on the PDF content
stream alone. Pivot: hand a JSX (ExtendScript) to Illustrator, walk every
`pathItem`, set its stroke width directly. Layer fidelity preserved by
construction.

The first naïve try is *exponentially slow*. First 10 K paths in 79
seconds, second in 132, third in 280. ETA: 2 hours rising.

Discovery: `app.preferences.setIntegerPreference("maximumUndoDepth", 1)`
turns ExtendScript bulk edits from exponential to linear. Restored at
end of script. 11 minutes for 340 K strokes. All layers preserved.

This is the first time the project does something the manual workflow
genuinely can't: bulk edits at scale, without losing the layer tree.
Ship as v0.2.

Lesson 2 lands: ExtendScript is fast if you know its quirks.

## Phase 3 (v0.3) — poché, three failures, eventually working

Cut layers should become solid black filled regions. The compute is "given
N polylines, find the closed regions, fill them."

**Try 1**: hand Illustrator a `Join` command to chain endpoints.
Catastrophic. Illustrator's Join is not topology-aware — given 100
polylines that should form 10 closed shapes, it chains them into one
self-intersecting blob. Zohar shows screenshots of black bars criss-
crossing the courtyard.

**Try 2**: pikepdf-only OCG-aware stream rewrite. Format mismatch in dict
keys (`"/MC28"` vs `"MC28"`). Hours debugging. Trivial bug, hard to find.

**Try 3**: two-stage pipeline — JSX dumps anchors, Python computes
polygons via shapely's `linemerge + polygonize`, JSX applies. Mostly
works. 13 of 21 cut layers polygonize cleanly with bare linemerge; 7
need a `concave_hull` fallback (lossy); 1 fails outright.

The pattern that wins is **two-stage with shapely doing the topology**.
`linemerge` preserves the connected-component structure that Join
destroys. Lesson lands.

Auto-bridge inference comes next: greedy nearest-endpoint pairing with
shapely STRtree, max-gap 50 pt, direction-compatibility filter. Rescues
4 more layers (14 → 18 of 21).

## Phase 4 (v0.4-v0.6) — make it amazing

Material hatching engine. ISO 128 standards research. MkDocs Material
documentation site. GitHub Actions CI. Hatchling+hatch-vcs versioning.
Auto-bridge module. Visual preview via PyMuPDF + Ghostscript. Layer
classifier with semantic Rhino layer-name parsing.

The project crosses from "script that helps Zohar" to "tool that has a
shape." 26 tests passing. Ruff clean. Documented postmortem of every
failed approach. Comprehensive sub-agent research transcripts.

The work happens in waves of parallel sub-agents researching narrow
questions while engineering proceeds in the foreground. The pattern: spawn
3–5 agents on unknowns, integrate their answers, ship the result.

## Phase 5 (April 30, ~hour 25) — the OSS publish that wasn't

PyPI Trusted Publishing is set up. v1.0.0 builds clean. Zohar approves
the publish. The wheel goes live under MIT.

Fifteen minutes pass.

Zohar: *"wait i want this to be my thing for now i dont want anyone to be
able to install what i wanna monotize this eventually."*

Yank from PyPI. Remove the Trusted Publisher. Disable `release.yml`. Make
the GitHub repo private. The Pages site goes 404 within minutes (free
plan doesn't serve private-repo Pages).

What just happened: **the founder hadn't decided the business model
before publishing.** MIT for v1.0.0 is now irrevocable for that exact
distributed wheel — anyone who pulled it during the 15-minute window
keeps MIT rights forever. The project name is reserved on PyPI but the
default `pip install` resolution is hidden by the yank.

Attempt 7 lands in POSTMORTEM. Lesson: pick the license before you
publish to a public registry; don't enable docs auto-deploy and then
immediately privatize the repo on the same day.

## Phase 6 (~hour 26) — the SaaS pivot

The conversation re-orients around: stay private, build until amazing,
sell as a monthly subscription web app.

The natural roadmap rewrite (v3) re-anchors:

- Phase B becomes a **feasibility spike**, not a license swap. Can we
  produce shippable-quality `.ai` output without an Illustrator install
  on the server? If no, no SaaS.
- Phase D becomes a **web app MVP**, not a CLI binary launch.
- Subscription pricing replaces one-time tiers.
- Two existential risks (McNeel ships built-in line weights; arch-school
  workflow shifts to AI-first) are documented as roadmap killers.

Sub-agent queue gets prioritized. P0 wave 1 fires: 4 parallel agents on
the Illustrator-less feasibility, PDF-only acceptance, hybrid
local-helper, and personal-use logging.

## Phase 7 (~hour 27) — the AI24_ZStandard discovery

The feasibility-spike agent comes back in 60 minutes with the project's
single most important discovery:

> The 305 `/AIPrivateData` streams concatenate into a 20-byte ASCII prefix
> `%AI24_ZStandard_Data` followed by Zstandard magic `0x28b52ffd`.
> Decompressed: 55 MB of plain-text Adobe Illustrator native PostScript —
> the same publicly-documented AI3-AI8 syntax we'd been generating from
> JSX for months, just zstd-wrapped + chunked across PDF streams.

The format we'd been treating as proprietary in v0.1 (the one that
flattened 62 layers when we tried to strip it) is **an old format wearing
modern compression.**

8 working spike scripts demonstrate inspect / decompress / null
round-trip / stroke-color modify / stroke-width modify, all verified in
Illustrator with byte-perfect layer preservation.

**The "no Illustrator on Linux server" blocker is gone.** The SaaS path
is open. Phase B closes on its own deliverable.

This becomes Attempt 8 in POSTMORTEM, and lesson 39 in LESSONS_LEARNED:
*"A 'proprietary' format may just be an old format wearing modern
compression. Always check the magic bytes before assuming a format is
locked."*

## Phase 8 (~hour 28-30) — finish what we started

With B1 resolved, the rest of the work falls into place:

- **B6**: port `apply.py` to operate on the decompressed AI native
  PostScript. New module `apply_saas.py`. 9 tests. CLI command
  `arch-lw apply-saas` works on synthetic fixtures.
- **B7**: port the poché pipeline. New module `poche_saas.py`. 17 tests.
  CLI flag `--poche` works.
- **B8**: end-to-end pure-Python pipeline verified.

In parallel: research agents close out the Phase D-G questions.
Stripe vs Lemon Squeezy at SaaS pricing. FastAPI + Fly.io + Neon stack
recommendation. Privacy posture template. Three stubborn cut layers
algorithmic deep-dive (backtracking + DBSCAN + alpha-shape + LLM
fallback ladder). Material hatch library expansion to 19 recipes.
Plan/elevation/detail preset families. AutoCAD/AIA NCS layer classifier
extension that doubles addressable users.

By end of session: **202 tests passing. Ruff clean. 23 research
transcripts. All 16 sub-agent queue items resolved. Phase B fully
closed.**

## What worked (the durable patterns)

1. **Time-boxed feasibility spikes beat trying to design around an
   unknown.** v0.1 tried to dodge `/PieceInfo`. A 60-minute scripted
   investigation in Phase 7 resolved the question v0.1 was avoiding.

2. **Two-stage pipelines** (JSX dump → Python compute → JSX apply)
   are easier to debug than monolithic anything. Same pattern transfers
   to SaaS (web upload → Python compute → result download).

3. **Sub-agents in parallel are how to move fast on unknowns.** A 60–90
   minute wave of 4–9 agents covers what would take a solo dev a week.
   Each agent is self-contained with explicit deliverables.

4. **Working code > research summaries.** The 8 spike scripts in
   `scripts/spike/saas-feasibility/` are the proof of B1, not a 1000-word
   "I think this should work" report.

5. **Topology-aware libraries (shapely) > naive endpoint chaining
   (Illustrator Join).** The Join failure was the moment we learned
   topology matters more than proximity.

6. **`maximumUndoDepth=1` ExtendScript pattern.** Linear time on bulk
   edits.

7. **Documenting failed approaches in the repo** (POSTMORTEM, this file).
   Future-us doesn't repeat them.

8. **The user's verification ritual** ("does it look right in
   Illustrator's layers panel?") is ground truth, not "the JSON says
   success."

## What didn't work (the durable anti-patterns)

1. **Stripping `/PieceInfo`** — flattens layers. Don't. Lesson 1.

2. **Naive `app.executeMenuCommand("join")`** — topology-blind.
   Produces tangled self-intersecting blobs.

3. **Single fixed snap tolerance** — over-merges dense cladding layers.
   Different layers want different tolerances.

4. **MIT-licensing v1.0.0 before deciding the business model** —
   irrevocable for that exact wheel snapshot. Always pick license
   *before* publishing to a public registry.

5. **Going private + auto-deploying docs same day** — Pages 404'd
   within minutes. Always check what depends on visibility before
   changing it.

6. **`saveAs` mutates the in-memory document's identity.** After
   `doc.saveAs(POCHE.ai)`, the previously-open `HIERARCHY.ai` tab is now
   `POCHE.ai` in memory. Close all and reopen from disk if you need a
   clean source.

7. **Open core / dual license for solo devs.** Either fully OSS or
   fully commercial. Splitting the brain is too much work.

## What we'd do differently

If starting over today, knowing what we know now:

1. **Skip v0.1 entirely.** Go straight to JSX layer-preserving (v0.2).
   The PDF stream rewrite path was a dead end.

2. **Run the AI24_ZStandard feasibility spike on day 1.** The fact
   that this is "AI3-AI8 PostScript wrapped in zstd" is the central
   technical insight. Knowing this from hour 1 would have saved 20+
   hours of JSX-via-AppleScript work that's now redundant.

3. **Decide license posture before opening any public registry account.**
   The 15-minute MIT window is harmless in practice (probably 0 actual
   downloads) but is the kind of thing that compounds badly at scale.

4. **Set up GitHub Issues from the start.** Tracking "still hanging"
   items in chat is fine for a session but doesn't survive into next
   week.

5. **Sub-agent queue file should exist from session 1.** Knowing what
   to research next is half the work. Having a prioritized queue
   document means parallel waves are obvious to dispatch.

6. **Phase A is the cheapest validation we'll ever get.** The fact
   that we don't have it yet — at hour 30, with the tool fully built —
   is the project's biggest open question. Use the tool on a real
   drawing before Phase B-C-D investments.

## What's hanging (the honest list)

User-side, can't be done by me or any agent:

- [ ] **Phase A1**: run `arch-lw apply-jsx --poche` on the next ARCH 202B
  drawing; fill in `personal-use-log.md` Entry 1.
- [ ] **Phase A2**: post a before/after publicly somewhere (USC studio
  Slack, IG, print at desk); count organic "what'd you use?" reactions.
- [ ] **Phase C1**: schedule one customer interview using
  `customer-interviews.md` script.

Engineering, deferred until product is ready or follow-up sub-task:

- [ ] **B9**: license swap (LICENSE → PolyForm Free Trial 1.0.0 + EULA).
  Do ~3 days before publishing v1.0.1, not earlier.
- [ ] **Wire `infer_bridges_best`** into `poche.polygonize_layer` rescue
  ladder. One-line change; deferred to avoid surprising regressions.
- [ ] **Alpha-shape + LLM topology inference** for the 2 remaining
  stubborn layers (`23_WINDOW_FRAMES_REMAP`, `26_CLT_GAP_ROOF_CAP`).
- [ ] **Real-Illustrator visual validation** of `arch-lw apply-saas
  --poche` output. Easiest done as part of Phase A1.

Each of these gets a GitHub Issue (created same day as this doc).

## What I'd tell future-Zohar

If you come back to this in two weeks, two months, or two years and
re-open the repo:

1. **Read `ROADMAP.md` first**, then this file, then `POSTMORTEM.md`.
   The roadmap is the destination. This file is the trail. POSTMORTEM is
   the warning signs along the trail.

2. **The single biggest lever** is now real-world data — running the
   tool on more drawings, talking to more humans. Not more research.

3. **The single biggest risk** is McNeel shipping built-in line
   weights or arch schools shifting to AI-first tooling. Both are
   real; both have documented mitigations in `BUSINESS.md` existential
   risks.

4. **The single biggest unknown** is whether anyone will pay $9/mo for
   this. Phase C will tell you. Until then, treat all revenue
   projections as fiction.

5. **The single biggest already-solved problem** is the SaaS feasibility
   question. The Wave 1 spike resolved it permanently. Don't re-litigate.

6. **The session that produced this artifact ran from 2026-04-29
   evening to 2026-04-30 evening**, ~30 hours of agent-collaborative
   work, 17 commits, 18 sub-agents fired, 4,099 LOC of source +
   docs + tests. The state of the repo at commit `cf11887` is the
   checkpoint.

If you read this and the immediate next move is "fire more agents" — pause
and ask whether you've used the tool on a real drawing yet. If no, that's
the next move. If yes and the data was disappointing, *iterate on the
tool*, don't pile more research. If yes and the data was good, *talk to
five humans*.

The tool is built. The research is comprehensive. The bottleneck from
here on is the world.
