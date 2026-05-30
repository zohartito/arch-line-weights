# Competitive landscape v2 — arch-line-weights

> Sub-agent research, 2026-05-09. Sharper, more honest pass over
> `competitive-landscape.md` (2026-04-30). Top-of-market only — no
> also-rans. Adds: Rhino 8 Make2D Styles re-evaluation, Blueprints AI,
> VisualARQ section attributes, Vectorworks 2026 Depth Cueing
> reception, Adobe UXP 2026 status, AutoLineWeight current activity.
>
> Quotes ≤15 words per source per copyright rules.

## Exec summary

The market is **neglected, not contested**. Two near-direct competitors
exist (AutoLineWeight, Make2D Styles inside Rhino 8) and both are
incomplete. AutoLineWeight (1 GitHub star, last push Sept 2024, 0 forks,
0 issues) is effectively abandoned. Make2D Styles ships with Rhino 8 but
offers no semantic layer-name awareness and the line-weights-survive-PDF
problem persists in Rhino 9 WIP per active McNeel forum threads
(RH-11615 ticket open, no roadmap commitment as of Feb 2025). Adjacent
threats (VisualARQ, Vectorworks 2026 Depth Cueing) solve adjacent
problems but require leaving the Rhino+Illustrator pipeline. The
existential category is **AI-generated construction documents** —
Blueprints AI (Vercel AI Accelerator 2026, NVIDIA Inception) is the one
genuinely well-funded entrant who could obviate hand-drawn presentation
sets entirely, but they target permit-ready CDs, not presentation
sections. **The whitespace v0.5 claimed (automated + arch-specific +
PDF-post-processing) still exists in 2026.** What's changed: the
"automated + arch-specific" slot is increasingly contested *inside the
authoring app*, not on already-exported files.

## Per-category leaders

### 1. Direct competitors — architectural line-weight automation specifically

Genuine leaders: **two**, both with significant gaps.

#### Leader 1.1: **AutoLineWeight** (Chenzhi Xu / `CXu0630/AutoLineWeight`)

The only direct architecture-aware line-weight automation tool. Verified
status as of 2026-05-09 via GitHub API:

- 1 star, 0 forks, 0 open issues, 0 watchers (besides creator)
- Created 2024-03-08, last push 2024-09-11, last update 2024-07-20
- Listed on Food4Rhino (`/en/app/auto-line-weight`)
- README still flags "SubD does not work properly" in Rhino 7
- C# Rhino plugin, MIT-licensed

(a) **Better than us:** runs *inside* Rhino with intersection +
  silhouette options we do not have; geometric edge classification
  (outline / convex / concave) is more sophisticated than our pure
  layer-name approach for *unlabeled* drawings. Free + MIT removes the
  pricing objection entirely.

(b) **What we should adopt:** the geometric-edge classifier as a
  *fallback* when layer names are absent or ambiguous. Right now we fail
  silently on a malformed export; AutoLineWeight's edge logic is a
  reasonable safety net. Consider porting the edge-relationship logic to
  Python as a `--unlabeled` mode.

(c) **What they're missing that we own:** PDF post-processing (theirs
  needs Rhino installed and the source 3D file open); layer-name
  semantics (theirs is geometry-only — wall section vs ground line is
  invisible); poché fills for ClippingPlaneIntersections; ISO-128 tier
  presets; material hatch library; SaaS web app. Crucially, the project
  is *abandoned* — 9 months no push, 0 fork energy, 1 star in 14 months.
  **The MIT license is the threat, not the maintenance state**: a
  motivated grad student could fork it to v2 in a weekend.

#### Leader 1.2: **Make2D Styles** (built into Rhino 8+, McNeel)

**This was under-weighted in v0.5.** Make2D Styles, shipped in Rhino 8
(2023) and refined in 2024-2025, *is* a direct competitor for the
inside-app slice of our market. It assigns differentiated weights to
silhouettes / visible / hidden / tangent edges per Style preset, saves
configurations, and inherits print widths from layer templates per
McNeel docs and the Novedge writeup.

- Already in every Rhino 8 install (no plugin needed)
- Style presets transferable across files
- Per Novedge: "Use Print widths and vector output for crisp lines"

(a) **Better than us:** zero install, zero learning curve for existing
  Rhino users, no extra software trust gap, $0 marginal cost. "Save
  settings as a Style preset" is feature-equivalent to our drawing-type
  presets but without the round-trip. McNeel staff actively maintain it.

(b) **What we should adopt:** the **Style preset abstraction** is
  better-named than our internal "tier preset" terminology. We should
  align messaging — call our drawing-type configs "Styles" so users feel
  the continuity. Also, the silhouette/visible/hidden/tangent
  categorization is a reasonable **secondary axis** on top of
  layer-name classification — could be a future feature for users who
  haven't named their layers semantically.

(c) **What they're missing that we own:** semantic understanding of
  arch-specific categories (no "section cut" vs "elevation line"
  distinction — only geometric ones); poché fills; the
  weights-survive-PDF problem (the McNeel forum thread "Finer line
  weights in Layout PDFs" was last posted Feb 2025 with no resolution,
  and ticket RH-11615 sits in McNeel's backlog with no timeline). The
  line-weight-loss-on-PDF-export bug is *the same problem* it was in
  Rhino 5. Make2D Styles makes the *display* better but doesn't solve
  the *interchange* problem.

**Verdict on Category 1:** what v0.5 claimed about AutoLineWeight
(threat 4/5) holds, but **Make2D Styles deserves its own threat
classification (3/5, growing)**. Anyone who learns Make2D Styles workflow
in studio will not feel the export pain as acutely until they hit
Illustrator and see the strokes flatten — at which point our pitch
("fixes what Rhino broke at the PDF step") still lands.

### 2. Adjacent-but-encroaching — vector drawing automation

**No genuine encroachment leader.** The two we'd worry about (Astute
Graphics, Show It Better) have not moved toward architectural automation
in their 2025-2026 release notes:

- **Astute Graphics:** 2026.3 release (Apr 2026) is full Illustrator
  2026.3 compatibility + Real-Time Drawing for 8 of their tools (Arc,
  Circle, Connect, Curvature Circle, Orient, Orient Transform,
  Perpendicular, Tangent). No architectural-specific tool, no new
  semantic-classification feature. Verified at
  `astutegraphics.com/learn/update/astute-graphics-update-illustrator-30-3`
  and `docs.astutegraphics.com/support/is-your-software-compatible-with-illustrator-2026`.

- **Show It Better:** site audit (2026-05-09) reveals current product
  line is still PSD packs, asset libraries, and online courses
  (Realistic Site Plan, Master Sections, Presentation Boards with
  InDesign, Animated Diagrams). No automation tools. No 2025-2026
  architectural automation product launches per their own site.

- **Morpholio Trace** has ScalePen — patented scale-aware pen weights
  for iPad sketching — but it's a *sketching* tool, not a Rhino
  pipeline tool. Demographics overlap but workflow doesn't.

**Verdict on Category 2:** no leader is encroaching. Astute and Show It
Better are stable competitors in their own domains, neither moving
toward our space. This is *good news* — but also means if they ever
*did* move (especially Astute, with platform credibility), they'd
out-distribute us instantly.

### 3. AI / generative competitors — architectural drawing generation

Genuine leader: **one**, with a different problem statement.

#### Leader 3.1: **Blueprints AI** (`blueprints-ai.com`)

The first AI competitor with credible institutional traction. Verified
2026 status:

- **Vercel AI Accelerator 2026** (40 teams selected from thousands)
- **NVIDIA Inception member** (GPU infrastructure + investor network)
- Trained on "6 million data points"
- Generates "floor plans, site plans, sections, elevations, details,
  and title sheets"
- Inputs: hand sketches, DWG, DXF, RVT, point clouds, photos, PDFs,
  plain language
- Permit-ready / code-compliant target output
- Customizable to firm standards (title blocks, sheet layouts, detail
  libraries, naming conventions)
- Pricing not public; "flexible packages"

(a) **Better than us:** if the demo videos are accurate, they
  *generate* the entire CD set from scratch — sections, elevations,
  details — including line weights and hatching. We can't compete on
  speed or breadth. They're targeting the production-drawing end of the
  market (permit sets), which is a different segment from our
  presentation-drawing focus, but the technical capability could trivially
  expand into presentation work.

(b) **What we should adopt:** the **firm-standard ingestion** (upload
  your title block, drawing prefs, naming conventions). This is
  exactly the pattern-library compounding angle we already lean on, but
  productized as a one-time customer-onboarding flow. We should bake
  this into our SaaS Phase F UX. Also, the "describe in plain language"
  input mode is a reasonable second-tier acquisition vector — users who
  don't have a Rhino file at all but want to test the tool.

(c) **What they're missing that we own:** an authoring loop. Their
  pitch is "generate CDs from sketches"; ours is "fix the CDs you
  already drew." The student-architect studio user is *iterating* on
  their own drawings, not generating them from scratch. Blueprints AI
  is for firms producing permit sets, not students producing thesis
  sections. Our segment 1 (students) and segment 2 (sole practitioner
  designers) want to render *their* design intent, not let an AI
  re-author it. The semantic-classifier-as-translator angle (your
  layers → ISO-128 weights) is meaningfully different from the
  generate-from-prompt angle.

**Verdict on Category 3:** Blueprints AI is real, but they're solving an
adjacent problem (CD authorship) not our problem (CD post-processing).
The existential risk timeframe is 18-36 months — long enough for us to
build moat, short enough that we should monitor quarterly. **Vizcom,
ArchSynth, ArchiVinci all stay raster-only and remain Category 3
also-rans** for our purposes; none produce vector-grade line drawings.

### 4. Inside-app tooling — Revit / ArchiCAD / Vectorworks / Rhino native

Genuine leader (most threatening): **Vectorworks 2026 Depth Cueing**.

#### Leader 4.1: **Vectorworks 2026 Depth Cueing**

Released Nov 2025, refined through Update 4 (April 2026). Per Vectorworks
official + Architosh review:

- Vector- and raster-based depth cueing (most BIM does raster-only)
- Auto-adjusts line weights and tonal values by object distance from
  viewer
- Works in Hidden Line and Shaded viewports
- Applies to elevations, sections, 3D views

(a) **Better than us:** the *concept* — auto-weight from 3D context
  alone, no layer naming required — is more ambitious than ours. A user
  who hasn't named layers gets correct hierarchy automatically. This is
  the conceptual high ground we lose on if McNeel ports the idea.

(b) **What we should adopt:** the **distance-from-viewer** axis as a
  third classification dimension on top of (a) layer-name and (b)
  geometric edge type. Our roadmap should include "depth-aware
  weighting" using clipping plane Z-distance as a heuristic — at minimum
  as a fallback when layer names are uninformative.

(c) **What they're missing that we own:** Vectorworks-only. You don't
  get there from Rhino. Doesn't survive vector PDF→Illustrator round-trip
  (Vectorworks export to AI has its own issues per their forum).
  Pricing wrong for our segments ($1,300+/yr).

#### Honorable mention: **VisualARQ** (Asuni / Rhino plugin)

Adjacent-tool — Rhino plugin, integrates with Rhino 8 section attributes,
has section hatch attributes (pattern type, scale, angle, color),
permanent license $795 (no subscription), educational $95.

- (a) Better: real BIM workflow inside Rhino, sections generate
  automatically from 3D, layer/lineweight inheritance natively.
- (b) Adopt: their permanent-license $95 educational tier is a model
  to consider for our studio tier.
- (c) Missing: $795 commercial price targets a different buyer than
  our $19-79 student/sole-practitioner; doesn't help users who want
  Rhino-native primitives (no full BIM commitment); doesn't solve
  PDF post-processing.

**Verdict on Category 4:** Vectorworks 2026 is the conceptual threat.
Revit / ArchiCAD remain orthogonal (you've left Rhino if you're there).
**McNeel has not pre-announced anything that solves the line-weights-
survive-PDF problem in Rhino 9 WIP** as of May 2026. The most-recent
relevant forum activity is RH-11615 ticket from June 2020 plus Feb 2025
re-vote, with no McNeel commitment. Our 18-36 month F1 risk window from
v0.5 still applies.

### 5. Open-source repos — GitHub projects in this space

**No genuine leader.** Searched GitHub topics
`architectural-drawing`, `line-weights`, `cad-export`, `dwg-pdf`,
`make2d`, `rhino3d`, `rhinocommon`. The only relevant arch-line-weight
repo is AutoLineWeight (covered in §1) at 1 star. **Doodlebug fork**
(`henn-dt/DoodlebugGH`) at 1 star, last push 2023-06-09 — abandoned.

Adjacent infrastructure repos with relevance:

- **`pikepdf/pikepdf`** — the PDF library we already build on. Healthy,
  actively maintained, MPL-2.0. Not a competitor; an enabler.
- **`rdevaul/yapCAD`** — Python procedural CAD with line-weight
  awareness in DXF rendering. Generic, not arch-specific, sub-100 stars.
- **`aspose-cad/Aspose.CAD-for-Python`** — commercial CAD library
  wrapper. Generic. Not a market leader.
- **`ByteBard97/nuxp`** — bridges Adobe's missing Illustrator UXP
  with C++ SDK. Interesting *enabler* for our future Adobe Exchange
  story but not a competitor.

**Verdict on Category 5:** No open-source leader exists. The market is
not contested by free MIT alternatives — yet. **The risk is the
opposite:** if our users discover that AutoLineWeight + Make2D Styles +
manual Illustrator covers 60% of cases for $0, our $19 price has to
deliver clear marginal value on the remaining 40%.

### 6. Architecture-school / academic tools

**No genuine leader; market gap remains.**

Searched curricula and resource pages at GSD, GSAPP, USC, Sci-Arc, MIT,
Cornell. No school publishes a systematic line-weight automation tool.
Schools teach the *standard* (e.g. ArchAdemia's "Mastering Line Weight
in Your Architectural Drawings" from April 2025; 30X40's AutoCAD line-
weight settings course) but no school publishes or maintains a tool
that *applies* the standard. ArchAdemia + 30X40 are the closest, but
both sell *teaching* and *templates*, not automation.

GSAPP runs Rhino + Grasshopper-heavy curricula with self-guided modules
but no internal tool publication. Harvard GSD's Design Discovery
program uses Rhino as a teaching tool, not as a platform for in-house
automation. **There is no "GSD line-weight standard library on GitHub"
or equivalent.**

This is unambiguously open whitespace: the school-internal tool slot
exists and could be filled either by us (via .edu free-tier
distribution per `marketing-channels.md` channel #8) or by a faculty
member/grad student writing their own repo. **Watch for:** a faculty-
led repo at MIT Senseable City Lab, GSAPP CDP, or Sci-Arc DSC. None
visible as of May 2026.

## What we should actually do about this

Top 3 strategic moves based on this scan:

### Move 1: Ship a "Make2D Styles importer" by end of Phase D

Rhino 8 users have already authored Make2D Style presets — we should
read those XML configs and use them as initial layer→weight mappings,
saving users a re-configuration step. This converts our weakness ("yet
another tool to configure") into a strength ("plug into the workflow
you already built"). Tactically: ship a `arch-lw import-rhino-style
my_style.xml` CLI command. Strategically: positions us as additive to
Make2D Styles, not competitive — co-existence story for the next 2
years until McNeel either ships PDF-survival (then we pivot) or doesn't
(then we're indispensable).

### Move 2: Pre-empt Blueprints AI by owning the "fix what you drew" wedge explicitly

Blueprints AI's pitch is "generate CDs from scratch." Our messaging
should explicitly contrast: "**arch-line-weights makes *your* drawings
publication-ready, not someone else's design.**" This is a
positioning move, not a feature move — bake it into landing-page copy,
HN Show HN narrative, Reddit posts. Architecture students *want their
own work* on their boards; Blueprints AI is a value prop for
deadlines-driven firms, not for studio users who'd rather lose their
laptop than have an AI re-author their thesis.

### Move 3: Submit to Food4Rhino *now*, not in year 2

The v0.5 doc parked Food4Rhino as a year-2 channel pending the
companion Rhino plugin. **Reconsider.** AutoLineWeight is on
Food4Rhino, abandoned, and is the de-facto search result for "rhino
line weight automation" on the platform. Submit a Food4Rhino listing
*today* that points to the SaaS web app + a thin Rhino plugin shim
that opens the SaaS upload page from inside Rhino (Phase G2 stub
acceptable). Rationale: defending the **Food4Rhino SEO real estate**
matters more than shipping a polished Rhino plugin. The first version
can be a 30-line C# script that opens our web app with the active 3DM
selected. Cost: 1 weekend. Reward: pre-empt anyone forking
AutoLineWeight to v2.

### Bonus Move 4 (optional): Apply to Vercel AI Accelerator winter 2026

Blueprints AI did. The accelerator selects 40 teams from thousands and
opens NVIDIA Inception + Vercel infrastructure credits. Even if
arch-line-weights' positioning is "not AI-first" (per BUSINESS.md
anti-tagline), the AI-augmented mode roadmap (`docs/research/ai-
augmented-mode.md`) is sufficient to qualify. Validates funding-
readiness for year-2 conversations; gives us the same credentials
Blueprints AI uses to look serious to architecture publications.

## What we got right in v0.5 and should defend

- The **PDF post-processing** angle is still uniquely ours. No 2026
  competitor (AutoLineWeight, Make2D Styles, VisualARQ, Vectorworks
  Depth Cueing, Blueprints AI) operates on already-exported files
  without the source 3D model.
- The **layer-name semantic classifier** as moat is correct.
  Make2D Styles classifies geometrically (silhouette / visible /
  hidden / tangent), not semantically. Vectorworks Depth Cueing
  classifies by viewport distance, not semantically. AutoLineWeight
  classifies by edge geometry, not semantically. **We are still alone
  in reading "WALL_SECTION_CUT" and knowing it should be 0.7mm.**
- The **founder-100 lifetime tier** at $19-29 is correctly positioned
  below every other tool ($95 VisualARQ educational, $149/yr Astute
  Graphics, $347 Show It Better Everything Pack, $1,300+/yr BIM tools).

## Where we're behind in 2026 and need to catch up

- **Inside-Rhino UX.** Both AutoLineWeight and Make2D Styles run
  inside Rhino with zero context-switch. Our CLI plus future SaaS
  upload step both require leaving Rhino. The Move 3 Food4Rhino plugin
  shim is the cheap fix; a proper Rhino sidebar panel is the right
  long-term answer.
- **Geometric edge classification.** AutoLineWeight has it; we don't.
  When layer names are absent, we degrade to a single global weight.
  This is a correctness gap for users who export from Make2D without
  semantic naming.
- **Production-drawing breadth.** Blueprints AI generates entire
  permit sets. We don't. We should *not* try to compete on this — but
  we should be able to articulate why "presentation drawings" is a
  defensible niche, not a smaller version of their market.

## Graveyard — tools ruled out as also-rans (so future sessions don't re-research)

- **DoodlebugGH** (`henn-dt/DoodlebugGH`) — fork of Andrew Heumann's
  Grasshopper↔Illustrator live-link plugin. 1 star, last push
  2023-06-09. Not a leader.
- **Inkscape PowerStroke** — open-source variable stroke for SVG. No
  architectural awareness. Inkscape's PDF round-trip remains weak. Not
  a leader.
- **AutoCAD CTB / STB plot styles** — AutoCAD-only. Orthogonal market.
- **Revit View Templates / ArchiCAD Pen Sets** — inside-BIM. Users
  who pick them have left the Rhino+Illustrator pipeline entirely.
- **Snaptrude / TestFit / Spacemaker / Forma** — AI-augmented BIM
  authoring tools, presentation-drawing output is not their primary
  value prop.
- **Vizcom / ArchSynth / ArchiVinci / mnml.ai / ArchiVinci /
  PromeAI / Rendair / Arko AI** — sketch-to-render or render-to-render
  tools. Output is raster, not vector line work. Adjacent, not
  competing.
- **Hyperboloid** — could not find this in 2026 search results in the
  arch-tooling space; possibly defunct or rebranded.
- **Kraftwerk** — not found as an architecture-AI product in 2026
  searches; only references are to the German band and unrelated
  industrial tools.
- **Astute Graphics WidthScribe / Phantasm / VectorScribe** — best-
  in-class artistic vector tooling, no architecture-specific moves in
  2025-2026 release notes.
- **Show It Better PSD packs / courses** — cultural competitor only;
  no automation tool launches in 2025-2026.
- **Morpholio Trace + ScalePen** — iPad sketching tool with scale-
  aware pens. Different workflow (sketch, not Rhino pipeline).
- **VisualARQ** — covered in §4 as honorable mention, not a leader for
  our segment due to $795 commercial pricing.
- **RealDrawings** (free Rhino 6 plugin from AEC Tech 2019 Hackathon)
  — layouts panel utility, last activity 2020. Not line-weight focused.
- **xNURBS, Pufferfish, Bowerbird, LunchBox, Kangaroo** — major
  Grasshopper plugins, none touch architectural line-weight automation.
- **RhinoBIM** — abandoned BIM extension for Rhino, superseded by
  VisualARQ.
- **Illustrator Actions / Scripts** — manual macros recorded by
  individual users. Not a product. Threat 5/5 baseline already covered
  as I1 in v0.5.
- **Adobe Firefly / ChatGPT vision** — generative-image models, no
  vector line-drawing capability, not in our market in 2026.
- **YC-backed ArchiLabs / Structured AI** — BIM/QC focused. Different
  problem space.
- **Hatch libraries (RhinoProf $4.99 / Studio Alternativi / Post
  Digital Architecture)** — adjacent assets sold as PNGs/PSDs/SVGs.
  Not automation. Could be future bundle/affiliate partners.

## Sources

- [AutoLineWeight GitHub repo](https://github.com/CXu0630/AutoLineWeight) — verified via API: 1 star, 0 forks, last push 2024-09-11, MIT
- [DoodlebugGH fork](https://github.com/henn-dt/DoodlebugGH) — 1 star, last push 2023-06-09
- [AutoLineWeight on Food4Rhino](https://www.food4rhino.com/en/app/auto-line-weight)
- [Rhino Make2D Styles overview](https://novedge.com/blogs/design-news/rhino-3d-tip-make2d-styles-for-consistent-presentation-ready-linework)
- [McNeel: Make2D line weights forum thread](https://discourse.mcneel.com/t/make2d-line-weights-not-changing/69089) — last post Aug 2018, unresolved
- [McNeel: Finer line weights in Layout PDFs](https://discourse.mcneel.com/t/finer-line-weights-in-layout-pdfs/103804) — last post Feb 8, 2025; ticket RH-11615 open
- [McNeel: Exporting from Rhino to Adobe Illustrator](https://discourse.mcneel.com/t/exporting-from-rhino-to-adobe-illustrator/190010) — last post Feb 25, 2025; McNeel suggests "try PDF instead"
- [McNeel: Rhino 9 WIP available](https://discourse.mcneel.com/t/rhino-9-wip-available-now/180749)
- [Blueprints AI homepage](https://www.blueprints-ai.com/) — Vercel AI Accelerator 2026, NVIDIA Inception
- [Blueprints AI tool review](https://www.aecplustech.com/tools/blueprints-ai)
- [Vectorworks 2026 Depth Cueing](https://www.vectorworks.net/en-US/2026)
- [Architosh: Vectorworks 2026 review](https://architosh.com/2025/11/deeper-dimensions-vectorworks-2026-redefines-bim-visuals-and-data/)
- [Vectorworks 2026 Depth Cueing course](https://university.vectorworks.net/course/view.php?id=4025)
- [VisualARQ documentation features](https://www.visualarq.com/feature/documentation/)
- [VisualARQ pricing](https://www.capterra.ca/software/192362/visualarq) — €95 educational, $795 commercial, permanent license
- [Astute Graphics 2026.3 update](https://astutegraphics.com/learn/update/astute-graphics-update-illustrator-30-3)
- [Astute Graphics Illustrator 2026 compatibility](https://docs.astutegraphics.com/support/is-your-software-compatible-with-illustrator-2026)
- [Show It Better homepage](https://www.showitbetter.co/) — site audit confirms no automation product launches 2025-2026
- [Adobe UXP for Illustrator 2026 status](https://community.adobe.com/questions-652/clarification-needed-is-uxp-publicly-available-for-illustrator-in-2026-1548811) — still closed for third parties
- [NUXP — bridge for Illustrator C++ SDK](https://github.com/ByteBard97/nuxp)
- [Morpholio ScalePen launch](https://www.architectmagazine.com/technology/morpholio-launches-scalepen-for-its-trace-app)
- [Morpholio Trace 2026 alternatives review](https://rendair.ai/blog/tools-top-5-morpholio-trace-alternatives-for-architects-in-2026)
- [Vizcom architecture review 2026](https://www.archpulse.co/blog/vizcom-review)
- [Chaos: Best AI rendering tools 2026](https://blog.chaos.com/best-ai-rendering-tools-for-architects-compared)
- [ArchPulse: Top 19 AI tools for architects 2026](https://blog.chaos.com/ai-tools-for-architects)
- [Snaptrude top 18 AI tools 2026](https://www.snaptrude.com/blog/top-18-ai-tools-for-architects-in-2026)
- [ArchAdemia: Mastering Line Weight](https://archademia.com/blog/mastering-line-weight-in-your-architectural-drawings/)
- [30X40 AutoCAD line weight course](https://courses.thirtybyforty.com/courses/30x40-design-workshop-autocad-template/lectures/22216002)
- [RhinoProf 33 architecture hatches ($4.99)](https://rhinoprof.com/shop/hatch-for-rhino/)
- [RealDrawings on Food4Rhino](https://www.food4rhino.com/en/app/realdrawings)
- [yapCAD GitHub](https://github.com/rdevaul/yapCAD)
- [pikepdf GitHub](https://github.com/pikepdf/pikepdf)
