# Competitive landscape — arch-line-weights

> Sub-agent research, 2026-04-30. Closes the dangling reference at
> `docs/BUSINESS.md` line 67. Inputs to Phase C demand validation
> (`docs/ROADMAP.md`). Pre-launch; refresh quarterly per
> `BUSINESS.md` "existential risks" section, item #2.

## Scope and method

Surveyed three rings of competition:

1. **Direct competitors** — tools that automate line-weight assignment
   on Rhino-derived vector output (Make2D post-processing, Illustrator
   stroke automation, Photoshop architectural workflow packs).
2. **Adjacent threats** — inside-app line-weight systems in BIM tools
   (Revit, ArchiCAD, VectorWorks, AutoCAD) and free open-source vector
   editors (Inkscape).
3. **Future entrants** — McNeel themselves, Adobe UXP marketplace
   opening, AI-first sketch-to-render tools, YC-backed automation
   startups.

For each, captured: positioning, pricing, audience overlap with our
three segments (`BUSINESS.md` §"Target customer segments"),
distribution, what they do better, what they don't do, threat level
(1–5), defensive move.

Quotes from cited sources are kept under 15 words per
copyright-compliance rules.

## Per-competitor matrix

### Ring 1 — Direct competitors (architects' line-weight automation)

| # | Competitor | Positioning (1-line) | Pricing | Audience overlap | Distribution | Better than us | Doesn't do | Threat (1–5) |
|---|---|---|---|---|---|---|---|---|
| D1 | **AutoLineWeight** (Chenzhi Xu, MIT-licensed Rhino plugin) | Free Make2D variant that assigns weights by edge type (outline / convex / concave) | Free, MIT | Segments 1, 2, 3 — same target | Food4Rhino + GitHub | Runs *inside* Rhino (no Illustrator round-trip needed); free; MIT-licensed; intersection + silhouette options | No layer-name semantics; no PDF post-processing; no Illustrator-side fix-up; not actively maintained (1 GitHub star, no recent releases); SubD broken in Rhino 7 per README | **4** |
| D2 | **Show It Better** | "Master architectural representation" — PSD packs, brushes, courses for presentation drawings | Packs $19–39; "Everything Pack" $347 lifetime; Section course (3 hrs, 34 lessons) | Segment 1 heavy (students); Segment 2 medium | Own site + Gumroad; 600k+ followers; YouTube + Instagram cultural presence | Brand recognition; tutorial library; presentation polish (colors, textures, entourage); culture-of-architecture credibility | Not automation — they sell *teaching* and *brushes*, not a tool that fixes a file. They don't touch Rhino exports. They presume you've already done line weights right. | **3** |
| D3 | **Astute Graphics** (WidthScribe + 20+ Illustrator plugins) | Pro-grade Illustrator power tools — variable widths, vector geometry ops | $149/yr individual subscription (no perpetual since 2019); Teams tier higher | Segment 2, 3 (pros); rare in Segment 1 | Own site; ZXP/UXP installer; Adobe ecosystem | Stable Adobe plugin distribution; signed/notarized; deep IP in vector ops; Width Brush is genuinely best-in-class for *artistic* variable strokes | Generic vector tooling — no architectural semantics; doesn't read Rhino layer names; doesn't know "section cut" from "ground line"; expensive subscription is wrong frame for $19 student impulse buy | **2** |
| D4 | **Doodlebug** (Andrew Heumann / Deisher Studio) | Live link Rhino+Grasshopper → Illustrator, bypasses Make2D round-trip | Free, donationware | Segment 2, 3 | Grasshopper community + Deisher blog | Live link is genuinely great when it works — solves the export problem at the source rather than the post-export problem | Compatibility-fragile (per author: "an Illustrator update broke it entirely"); requires Grasshopper expertise; no line-weight intelligence of its own — still leaves you in Illustrator manually fixing strokes | **2** |
| D5 | **HowToRhino-style YouTube tutorials** (manual workflow) | "Here's how to do it yourself in 30 minutes per drawing" | Free; some courses $30–80 | Segment 1 dominant | YouTube + course platforms | Free; teach the *why* not just the *how*; reinforce brand of architects who teach (cultural moat) | Not a tool. Doesn't scale. Every drawing still costs 30 min of human time. | **1** (validates demand more than competes) |

### Ring 2 — Adjacent threats (inside-app line-weight systems)

| # | Competitor | Positioning | Pricing | Audience overlap | What they do better | What they don't do | Threat (1–5) |
|---|---|---|---|---|---|---|---|
| A1 | **AutoCAD CTB / STB plot styles** | Color-to-pen lookup baked into 30+ years of practice | AutoCAD LT $545/yr; AutoCAD full $2,030/yr | Segment 3 — but mostly the *non-Rhino* firms we're not targeting | Industry-default mental model; mature templates; print server integration; mature CTB libraries downloadable | AutoCAD users aren't Rhino users — orthogonal market. Doesn't help Rhino exports at all | **1** |
| A2 | **Revit View Templates** | 1–16 numbered pen weights, scale-aware via View Templates | Revit $3,055/yr (or Architecture, Engineering & Construction Collection) | Segment 3 — firms that have *abandoned* the Rhino+Illustrator workflow we serve | Scale-aware (line gets thinner at smaller scale automatically); locked to View Template; office-wide standardization | Requires fully committing to Revit — opposite of our user. If they're on Revit, our problem doesn't exist. Not a switching threat in either direction. | **1** |
| A3 | **ArchiCAD Pen Sets** | 200+ pens organized by element function, switchable per-output | ArchiCAD ~$3,000/yr | Segment 3, niche (mostly EU practice) | Per-output pen-set switching ("plans" vs "electrical") is genuinely elegant; deep BIM integration | Same as Revit — orthogonal; you don't use Rhino+Illustrator if you're on ArchiCAD | **1** |
| A4 | **VectorWorks Classes + Depth Cueing** | 2026 added auto-distance-based line weight in viewports | VectorWorks Architect $3,180 perpetual or ~$1,300/yr | Segment 3, niche | New (2026) Depth Cueing actually attacks our value prop conceptually — auto-weight by depth, no manual work | Inside VectorWorks only; you don't get there from Rhino. Limited to live viewports, not exported PDFs that need post-processing | **2** |
| A5 | **Inkscape PowerStroke (LPE)** | Free open-source vector editor with per-node variable stroke | Free, GPL | Segment 1 (broke students) | Free; runs on Linux; PowerStroke for variable widths | Inkscape SVG model fights architectural conventions — no "stroke alignment" per Inkscape forum, no proportional weights, weak PDF round-trip. Manual workflow even worse than Illustrator. | **1** |

### Ring 3 — Inside-app alternatives within our user's existing toolchain

| # | Competitor | Positioning | Cost | What they do better | What they don't do | Threat (1–5) |
|---|---|---|---|---|---|---|
| I1 | **Manual Illustrator** (select-by-color + Appearance panel) | "Just do it yourself" — what every architecture student does today | $24.99/mo Illustrator (already paid for) | Already in their workflow; no install; no learning curve beyond Illustrator itself; full creative control | Slow (30–90 min per drawing); error-prone; not repeatable; no semantic awareness of "section cut" vs "elevation line" | **5** — this is our actual baseline competitor. Every prospect is comparing us to "free, plus my time." |
| I2 | **Illustrator Actions** (pre-recorded macro) | Record once, replay forever | Free with Illustrator | Replays exact steps; works offline; no third party | Brittle to layer-name changes; user has to author the action themselves (most don't); no intelligence about which strokes get which weight | **3** |
| I3 | **Rhino PrintWidth display mode + direct PDF print** | "Skip Illustrator entirely" | Already paid for Rhino | Lossless if it works; one tool less in pipeline; print colors + widths live in Rhino properties | Doesn't survive vector PDF→Illustrator round-trip (the original problem). PrintDisplay is for *display*, not interchange. Forum threads (e.g. "Make2D line weights not changing") confirm this is unsolved. | **2** — but their failure is *why our tool exists*. |

### Ring 4 — Future entrants (12–24 month horizon)

| # | Threat | Likelihood | Timeline | Impact if it lands |
|---|---|---|---|---|
| F1 | **McNeel ships "Print Style PDF" that survives round-trip** | Medium. McNeel is conservative on PDF features — Rhino 9 docs (`docs.mcneel.com/rhino/9`) still describe the same vector-export model. But forum demand is loud (multiple multi-year threads). | 18–36 mo | **Kills the problem entirely.** Mitigation: pivot to layer-name semantic library (the part McNeel won't ship — they don't know "WALL_SECTION_CUT" should be 0.7mm). Per `BUSINESS.md` §Defensibility, the classifier *is* the moat. |
| F2 | **Adobe opens UXP for third-party Illustrator plugins** | High *eventually*, low this year. Per Adobe community thread (March 2026): UXP "is just not opened for third-parties" but stock plugins already use it. | 12–18 mo for public SDK; 18–24 mo for stable marketplace | Mixed. Good: Adobe Exchange listing becomes our distribution unlock (Phase F+). Bad: any competitor (incl. Astute) ships a "select-by-architectural-semantic" plugin in UXP and out-distributes us. |
| F3 | **AI-first sketch-to-render tools** (ArchiVinci, mnml.ai, ArchSynth, Vizcom) | Already happening. Per Chaos blog "Best AI tools for architects 2026" and ArchSynth: "sketch to render in 14 seconds." | Now → 24 mo | Lateral, not direct. They render *images*, we deliver *editable line vectors*. But if architecture students stop drawing line drawings entirely (presentation pivots fully to AI render), our market shrinks. Per `BUSINESS.md` §Existential risks #3. |
| F4 | **YC-backed startup in arch automation** | Confirmed entrants: ArchiLabs ("AI CAD for architects/engineers"), Structured AI ("AI agents for QC on technical documents"). | Now → 18 mo | Different problem space (BIM/QC vs presentation drawings). Low overlap with Segments 1, 2. Watch quarterly. |
| F5 | **Open-source MIT alternative** | **Already exists** (D1: AutoLineWeight). Could see a v2 with layer-name parsing if a motivated grad student takes it on. | Now | This is the highest-likelihood disruptor. Defense: ship faster on edge cases, build the pattern library, build customer relationships (`BUSINESS.md` §Defensibility). |

## Positioning canvas

Two-axis: **automation level** (manual ↔ fully automated) ×
**architecture-specificity** (general design tool ↔ purpose-built for
arch line weights).

```
                   automation level (high)
                              ▲
                              │
  F1 (hypothetical Rhino     │     F3 AI sketch-to-render
  Print Style PDF)            │       (ArchiVinci, ArchSynth)
                              │
                              │
  D1 AutoLineWeight  ─────────┼─────────────  ★ arch-line-weights
  (free, basic, MIT)          │               (paid, semantic, MIT
                              │                tier closed)
                              │
                              │
  A4 VectorWorks 2026         │     A2 Revit View Templates
  Depth Cueing                │     A3 ArchiCAD Pen Sets
                              │
   general design ◄───────────┼──────────────► arch-specific
                              │
                              │
  D3 Astute Graphics          │     D4 Doodlebug
  ($149/yr, generic vector)   │     (free, fragile)
                              │
                              │
  I2 Illustrator Actions      │     D2 Show It Better
  (manual macro)              │     (PSD packs, courses)
                              │
                              │
  I1 Manual Illustrator       │     D5 YouTube tutorials
  (default baseline)          │     (the meta-competitor)
                              ▼
                   automation level (low)
```

**Key whitespace:** the upper-right quadrant — *automated* AND
*arch-specific* — has only one occupant today (AutoLineWeight, free,
unmaintained). That is precisely where arch-line-weights sits, with
two advantages D1 doesn't: PDF post-processing (works on already-
exported drawings, not just inside Rhino) and the layer-name semantic
classifier (`BUSINESS.md` §Defensibility).

## Threat assessment with timelines

| Tier | Threat | Window | Severity | Mitigation status |
|---|---|---|---|---|
| **Now (0–6 mo)** | I1 Manual Illustrator workflow | Always-on. Every prospect will compare $X to "free, plus 30 min of my time." | High | Validation question: ask interviewees "what would you do if this didn't exist?" Per `BUSINESS.md` §Customer-interview log. |
| **Now (0–6 mo)** | D1 AutoLineWeight free MIT plugin | Already in Food4Rhino. Discoverable. | High | Differentiate on PDF-post-processing axis (it doesn't); ship layer-name classifier; Food4Rhino listing of our own (`BUSINESS.md` §Distribution v3). |
| **Now (0–6 mo)** | D2 Show It Better cultural dominance | Always-on. They own the architecture-student attention market. | Medium | Partnership angle (`BUSINESS.md` §Partnership ideas item #1). Don't compete; complement. |
| **6 mo** | A4 VectorWorks 2026 Depth Cueing precedent | Already shipping. Concept validation for "auto-weight by 3D context" — could inspire McNeel. | Low (today) | Watch McNeel changelogs quarterly. |
| **6–12 mo** | F4 YC-backed arch automation startup | Adjacent (BIM QC, not presentation drawings) but well-funded. | Medium | Stay in our narrow lane; Segments 1+2 are too small to attract VC. |
| **12–18 mo** | F2 Adobe opens UXP for third parties | High likelihood. | Mixed (distribution unlock + competitor entry) | Be among first 100 listings on Adobe Exchange when it opens (`BUSINESS.md` §Distribution v3). |
| **18–24 mo** | D3 Astute Graphics adds an arch-aware tool | Possible — they have the platform and the audience to extend into architecture if our segment proves out. | Medium | Move fast on customer relationships; their $149/yr ≠ our $19 impulse buy. |
| **18–36 mo** | F1 McNeel ships "Print Style PDF" that survives | Existential. | High | Pivot to semantic classifier as the moat. The problem changes from "fix what Rhino broke" to "label what Rhino now preserves." |
| **24+ mo** | F3 Architecture pivots fully to AI rendering | Existential, but slow-moving | Low–Medium today | Pivot to "AI-augmented line weights" — feed classifier as training data (`BUSINESS.md` §Existential risks #3). |
| **24+ mo** | F5 Better open-source MIT alternative | Likely if D1 attracts a motivated grad-student maintainer | High | The pattern library is the moat. Customer-drawing corpus compounds. |

## Differentiation strategy — claims arch-line-weights can defensibly make

These are 5 claims our messaging can lead with that no competitor in
any ring above can credibly make. Tested for defensibility against
every competitor in the matrix.

### 1. "Fixes Rhino-exported PDFs that already lost their line weights — no plugin install in Rhino needed."
- D1 AutoLineWeight: requires running inside Rhino, before export. Doesn't help the file that's already on your hard drive.
- D3 Astute Graphics: doesn't read Rhino layer names; not architecture-aware.
- D4 Doodlebug: live-link only, fragile, requires Grasshopper.
- McNeel native: forum threads confirm this is broken.
- **Defense:** the PDF stream rewrite *is* our distinctive engineering — see `docs/research/pdf-only-acceptance.md`.

### 2. "Architecture-specific line-weight intelligence — 'WALL_SECTION_CUT' becomes 0.7mm without you teaching it."
- D1 AutoLineWeight assigns by edge geometry (outline/convex/concave), not by layer semantics. Wall-section vs ground-line is invisible to it.
- All BIM tools (A1–A4): inside their own ecosystem; you'd have to leave Rhino to get this.
- D2 Show It Better: teaches you to do it manually; doesn't automate.
- **Defense:** the layer-name classifier improves with every customer drawing — `BUSINESS.md` §Defensibility item #1.

### 3. "$19–79 one-time, the price of a coffee shop afternoon — not $149/year and not a $347 lifetime bundle."
- D3 Astute Graphics: $149/yr subscription is the wrong mental model for an impulse-buy student tool (`pricing-research.md` §"Why one-time over subscription").
- D2 Show It Better Everything Pack: $347 lifetime, but for *brushes and courses*, not automation.
- A1–A4 (Revit, ArchiCAD, VectorWorks, AutoCAD): $1,300–$3,000/yr; absurd for our segments.
- **Defense:** founder-100 launch tier ($15–29 lifetime) locks in price perception before competitors notice us (`pricing-research.md` §Headline recommendation).

### 4. "Built on edge-cases by an architecture student in studio — not a generic Adobe plugin tuned for illustrators."
- D3 Astute Graphics: WidthScribe is best-in-class for *artistic* variable strokes — but it's tuned for illustration, calligraphy, signage. Not section drawings.
- D2 Show It Better: not a tool company; a media company with a side hustle in PSD packs.
- F4 YC-backed startups: BIM/QC focused; not for presentation drawings.
- **Defense:** demo asset (`BUSINESS.md` §Marketing — "user's ARCH 202B section drawing, before/after") is credibility no competitor has.

### 5. "POSTMORTEM-driven — every edge case fixed becomes a regression test the next user inherits."
- All competitors except D1 are closed-source, so customers can't see what's been fixed.
- D1 AutoLineWeight: 1 GitHub star, sparse maintenance per README.
- **Defense:** `docs/POSTMORTEM.md` is a *marketing asset*, not just internal — it's evidence of how seriously we treat the long tail of bad Rhino exports. Per `BUSINESS.md` §Defensibility item #2.

## Update recommendations for `docs/BUSINESS.md` §"Competitive positioning"

Current text (line 69) says **"Direct competitors: None known. The
market gap is real."** This research updates that:

### Suggested revision

```markdown
## Competitive positioning

(Detailed competitive landscape: `docs/research/competitive-landscape.md`.)

**Direct competitors:**
- **AutoLineWeight** (Chenzhi Xu, MIT, free, Food4Rhino) — the closest direct
  competitor. Runs inside Rhino, assigns weights by edge geometry. No layer
  semantics, no PDF post-processing, sparsely maintained. Threat 4/5.
- **Show It Better** — cultural competitor, not feature competitor.
  Sells PSD packs ($19–39) and a $347 Everything Pack. Doesn't automate.
  Threat 3/5; partnership-eligible.
- **Astute Graphics** — generic Illustrator power tools, $149/yr. No
  architectural awareness. Threat 2/5 today, watch for arch-specific
  pivot at 18–24 mo if our segment proves out.
- **Doodlebug** (Andrew Heumann) — Rhino↔Illustrator live link, free,
  fragile across Illustrator updates. Threat 2/5.

**The actual baseline competitor:** manual Illustrator workflow.
Threat 5/5. Every prospect compares us to "free, plus my time." Phase C
interviews must surface time-cost honestly (`docs/research/customer-interviews.md`).

**Adjacent threats:** AutoCAD CTB, Revit View Templates, ArchiCAD Pen Sets,
VectorWorks 2026 Depth Cueing — all inside-app, all orthogonal to our
Rhino+Illustrator user. Low threat (1–2/5) unless a user fully migrates
toolchain.

**Future entrants (watch quarterly):**
- McNeel "Print Style PDF" survives round-trip (18–36 mo) — kills the
  problem; pivot to semantic classifier as moat.
- Adobe UXP opens to third parties (12–18 mo) — distribution unlock +
  competitor entry; aim for early Adobe Exchange listing.
- Open-source v2 of AutoLineWeight with layer-name parsing — most
  likely disruptor; defend with pattern-library compounding.

**Defensibility (refined):**
1. Layer-name semantic classifier — pattern library compounds with every
   customer drawing.
2. PDF post-processing — uniquely fixes already-exported files; no
   competitor in any ring does this.
3. POSTMORTEM-driven engineering — visible in repo, marketing asset.
4. Direct customer relationships at $19 impulse-buy price — rare.
```

## Honest acknowledgements

Things competitors do better than us today:

- **D1 AutoLineWeight:** runs inside Rhino with intersection + silhouette
  options we don't have. If your problem is *before* export, they win.
- **D2 Show It Better:** brand. 600k followers. We have zero.
- **D3 Astute Graphics:** distribution. Adobe ecosystem trust. Notarized,
  signed, mature billing. We're on Gumroad.
- **D4 Doodlebug:** when it works, the live-link UX is better than our
  CLI round-trip.
- **A4 VectorWorks 2026 Depth Cueing:** the *concept* (auto-weight from
  3D context) is more ambitious than ours. We weight by layer name; they
  weight by viewport depth. If McNeel ports this idea to Rhino, we lose
  the conceptual high ground.
- **I1 Manual Illustrator:** zero install, zero learning curve, zero
  trust gap, $0 marginal cost.

## Sources

Cited per copyright rules: ≤15 words quoted per source.

- [Auto Line Weight — Food4Rhino listing](https://www.food4rhino.com/en/app/auto-line-weight)
- [AutoLineWeight — GitHub repo (CXu0630)](https://github.com/CXu0630/AutoLineWeight)
- [Show It Better — home](https://www.showitbetter.co/)
- [Show It Better — Gumroad bundle](https://showitbetter.gumroad.com/l/QQhBJ)
- [Astute Graphics — pricing](https://astutegraphics.com/pricing)
- [Astute Graphics — WidthScribe plugin](https://astutegraphics.com/plugins/widthscribe)
- [Astute Graphics — Illustrator 2026 compatibility](https://docs.astutegraphics.com/support/is-your-software-compatible-with-illustrator-2026)
- [Doodlebug — Deisher Studio blog](http://www.deisherstudio.com/blog/2017/5/4/plugin-doodlebug)
- [Doodlebug — McNeel forum compatibility thread](https://discourse.mcneel.com/t/is-there-a-direct-rhino7-illustrator-live-link-scenario-that-works/142057)
- [AutoCAD CTB plot styles guide — First In Architecture](https://www.firstinarchitecture.co.uk/architectural-line-weights-and-plotstyles/)
- [Revit Pure — line-weight pamphlet](https://static1.squarespace.com/static/5605a932e4b0055d57211846/t/5c92e1c8b208fc0cdfa22bf4/1553129929112/RP-Pamphlet12-Line-Weights.pdf)
- [Revit line-weight modification — Autodesk](https://www.autodesk.com/support/technical/article/caas/sfdcarticles/sfdcarticles/Revit-How-to-modify-line-weight.html)
- [ArchiCAD predefined Pen Sets — Graphisoft](https://help.graphisoft.com/AC/19/INT/AC19Help/01_Configuration/01_Configuration-38.htm)
- [VectorWorks 2026 — Depth Cueing](https://www.vectorworks.net/en-US/2026)
- [Inkscape PowerStroke — wiki](https://wiki.inkscape.org/wiki/index.php/PowerStroke)
- [Inkscape architectural-drawing limitations — forum](https://inkscape.org/forums/beyond/how-can-i-work-effectively-on-11-architectural-drawings-in-inkscape-scale-dimension-lines/)
- [Adobe UXP for Illustrator — community status thread, March 2026](https://community.adobe.com/questions-652/clarification-needed-is-uxp-publicly-available-for-illustrator-in-2026-1548811)
- [Adobe Creative Cloud Marketplace distribution](https://developer.adobe.com/premiere-pro/uxp/plugins/distribution/adobe-marketplace/)
- [Rhino PrintDisplay command](http://docs.mcneel.com/rhino/5/help/en-us/commands/printdisplay.htm)
- [Rhino 9 PDF Import/Export](https://docs.mcneel.com/rhino/9/help/en-us/fileio/portable_document_format_pdf_import_export.htm)
- [Make2D line weights forum thread — McNeel](https://discourse.mcneel.com/t/make2d-line-weights-not-changing/69089)
- [Illustrator Width tool — Adobe help](https://helpx.adobe.com/illustrator/using/tool-techniques/width-tool.html)
- [Illustrator Stroke + Appearance panel — Adobe help](https://helpx.adobe.com/illustrator/using/stroke-object.html)
- [Best AI rendering tools for architects 2026 — Chaos blog](https://blog.chaos.com/best-ai-rendering-tools-for-architects-compared)
- [ArchiVinci — AI architecture renderer](https://www.archivinci.com/)
- [ArchSynth — sketch-to-render in 14s](https://www.archsynth.com/)
- [mnml.ai — sketch-to-render](https://mnml.ai/)
- [Y Combinator — workflow automation startups 2026](https://www.ycombinator.com/companies/industry/Workflow%20Automation)
- [30X40 Design Workshop — tutorials](https://thirtybyforty.com/architecture-video-tutorials/)
- [HowToRhino — Rhino-to-Illustrator section workflow tutorial](https://howtorhino.com/rhino-grasshopper-tutorials/rhino-to-illustrator-section/)
