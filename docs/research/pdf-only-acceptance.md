# PDF-only output acceptance — research

> **Question:** If the SaaS web app shipped finished PDF (poché baked, weights
> baked, layers preserved as OCGs) instead of editable `.ai`, what fraction of
> each target segment would find that acceptable?
>
> **Methodology:** ~45 min web search across McNeel Discourse, Adobe community
> forums, architecture-tutorial blogs (Visualizing Architecture, illustrarch,
> archisoup, ArchAdemia, Show It Better, 30X40), school plotting guides
> (Yale, Syracuse, Morgan, UMass), and ArchDaily. Direct quotes capped at
> 15 words each. Reddit threads were not directly indexable in the time
> budget — segment-1 estimates lean on tutorial blogs that document the
> student workflow, not on student self-report.

---

## The load-bearing question

When does the user *finish* with the line-weighted vector? Two patterns
emerge:

1. **Print-and-go** — line weights set in Illustrator, optionally
   poché/hatch added, then File → Print → Adobe PDF. No further edits.
2. **Compose-into-board** — AI file placed (linked) into InDesign as one of
   many drawings; text, scale bars, and layout added in InDesign;
   sometimes drawings revisited in AI to tweak weights based on print-test.

If the user is pattern (1), PDF-only is fine. If pattern (2), they need
either (a) the AI, or (b) a PDF that places cleanly in InDesign at the
working scale.

**Critical finding for pattern (2):**
> "Unlike Illustrator, you cannot change line weights of drawings in InDesign."
> — Adobe community, [arch CAD→InDesign workflow][adobe-cad-id]

Line weights MUST be baked before InDesign placement. So a baked PDF
satisfies pattern (2) IF it places cleanly. There is one wrinkle: small
scales can render thin lines visually thicker in placed PDFs, a known
Acrobat display quirk:

> "Artificial thickening of very thin vectors is a known limitation."
> — [Adobe community discussion][adobe-thicken]

That quirk is a display issue, not a data loss issue — it prints
correctly. So it is annoying, not blocking.

---

## Per-segment estimates

### Segment 1 — Architecture students (USC, GSD, MIT, Cornell, RISD, Sci-Arc, Berlage, AA, Bartlett, ETH)

**PDF-only acceptable: ~65–75%**

Documented student workflow (multiple tutorial blogs aimed at this segment)
ends with PDF export, not AI handoff:

- Micah Goshi's tutorial — line weights → Live Paint hatching → PDF —
  goes weights → hatches → "export the document using File>print." There
  is no further AI editing or InDesign handoff in the documented flow.
  ([Medium][migoshi])
- howtorhino tutorial mentions stroke weights and texture fills as
  optional post-processing but does not lead anywhere beyond the AI
  artboard. ([howtorhino.com][howtorhino])

Where students DO go further, it's into InDesign for board layout:

> "Floor plans and sections are exported as vector files and brought into Illustrator."
> — Quora answer summarizing typical student workflow ([Quora][quora-adobe])

> "Once ready, everything... gets assembled back in InDesign."
> — paraphrase from same source ([Quora][quora-adobe])

But for the InDesign-place workflow, PDF works as the placed asset:

> "InDesign sees Illustrator (AI) files as PDF files."
> — Adobe Tuts+ on placing vector art ([Envato Tuts+][tuts])

School plot infrastructure mostly *requires* PDF for plotting:

> "convert it to PDF, then open the PDF file in Adobe Acrobat and proceed to print"
> — Syracuse Architecture print guide ([Syracuse SOA][syracuse])

Yale's plot lab is "PDF-required" — workflow name.
([Yale Architecture Advanced Tech][yale])

The 25–35% gap is the subset of students who pixel-fuss in Illustrator
after weights are set: tweak strokes after a print test, tighten poché
boundaries, manual color overlays, last-minute label cleanups. They lose
that ability with PDF-only and would feel pinched.

**Confidence:** medium-high. Tutorial blogs document the flow well; the
absence of Reddit student self-report is a real gap — students may
complain about PDF-only more than tutorials predict.

### Segment 2 — Sole-practitioner architects (boutique design-build, freelance Rhino-fluent)

**PDF-only acceptable: ~30–45%**

Sole practitioners use Illustrator for client-facing presentation graphics
where iteration is the norm. They:

- redo overlays in Illustrator after client feedback
- combine multiple drawings on a single AI sheet for a presentation
- ship final renders to clients as PDF but keep the AI as their working
  master

Eric Reinholdt (30X40 Design Workshop, the most-cited residential
sole-practitioner voice) uses CAD templates, Procreate, and a strong
graphic identity — a PDF-only locked file conflicts with the identity-
driven graphic iteration his audience aspires to. ([thirtybyforty.com][30x40])

Two countervailing forces:

- Sole practitioners are time-poor and would happily skip Illustrator
  entirely if the output is "good enough to print." That's the 30–45%.
- The remaining 55–70% want the AI because their *brand* lives in
  custom annotation, color overlays, and per-project graphic tweaks
  — they'd consider PDF-only a downgrade.

> "Illustrator should be used solely for presentation purposes."
> — howtorhino tutorial on the workflow ([howtorhino.com][howtorhino])

That phrasing is significant: "presentation" implies a final-product
edit pass, not just a print pass.

**Confidence:** medium. Single-data-point segment — no public forum
captures sole-practitioner workflow well.

### Segment 3 — Small studios (5–20 people, Rhino + Illustrator workflow)

**PDF-only acceptable: ~15–25%**

Studios institutionalize the AI-into-InDesign workflow with linked files
that update across multiple boards:

> "Linking keeps a live connection to the source file."
> — ArchAdemia integration guide ([ArchAdemia][archademia])

A studio principal who places one drawing as a linked AI into ten
InDesign boards loses the live-link advantage if forced to PDF — re-
export means re-place across all ten. That's a hard friction.

Studios also have a privacy concern that students don't:

> "Many architecture firms generally dissuade cloud adoption."
> — ArchDaily on architects and cloud storage ([ArchDaily][archdaily-cloud])

> "concerns about security and the necessity of protecting intellectual property"
> — same source ([ArchDaily][archdaily-cloud])

Cloud-rendering services (Gendo, MyArchitectAI, Visoid) have proven
architects WILL upload drawings to a third-party server — but they sell
specifically on EU hosting, GDPR posture, and "your designs aren't used
for training." A SaaS-PDF tool would need the same posture, and even
then the studio segment will be slower to adopt than students.

**Confidence:** medium. Studio-internal workflows are not publicly
documented; estimate leans on aggregated firm IT-policy posts.

---

## Privacy / upload acceptance (cross-segment)

- **Students:** little to no resistance. Already upload work to Discord,
  Are.na, classmate Drive folders. Confidentiality is not a concept they
  apply to studio projects.
- **Sole practitioners:** moderate resistance. Some clients have NDAs;
  many don't.
- **Studios:** highest resistance. IP and client confidentiality are
  explicit firm policies. Mitigation paths (proven by Gendo et al.):
  EU hosting, no-training-data clauses, clear retention policies, "your
  files are deleted after 24 hours," optional self-host or desktop tier.

---

## Workflow patterns where PDF-only is a **hard non-starter**

1. Studio that places linked AI files into a multi-board InDesign and
   tweaks weights after a print test.
2. Sole practitioner who composites a single Illustrator artboard with
   multiple section drawings + manual annotation/color overlay layers.
3. Anyone whose poché is hand-tuned non-rectangular (cut around weird
   geometry) and gets revisited.
4. Any "boards drawn in Illustrator" workflow (some students, fewer
   pros) — common when the user doesn't own InDesign.

For these, "I'd need to redo the whole pass to fix one weight" is the
deal-breaker.

## Workflow patterns where PDF-only is **fine**

1. Print-to-pin-up flow (most students, most weeks of the semester).
2. AI placed into InDesign with no further AI editing — the PDF places
   identically (modulo the thin-line display quirk).
3. Any user who doesn't iterate on poché — set it, print, done.
4. Quick-turnaround consulting where the deliverable is a printed sheet,
   not an editable file.

---

## Tier recommendation

A two-tier offering is well-supported by the evidence:

| Tier | Output | Audience fit |
|---|---|---|
| **Web (cheap)** | PDF + OCG layers, poché baked, weights baked | Students (~70%), some sole pracs (~35%), few studios (~20%) |
| **Desktop (expensive)** | Editable AI via JSX, plus PDF | Students who want polish (~30%), most sole pracs (~65%), most studios (~80%) |

The PDF tier captures the high-volume, low-price student segment. The
desktop tier captures the lower-volume, higher-willingness-to-pay
professional segment. Pricing alignment with the existing
`docs/BUSINESS.md` table works: $9/mo SaaS for PDF, $79–$499 desktop for
AI.

---

## Recommendation: **viable with desktop companion tier (B3-style hybrid)**

**Verdict:**
- **B1 (pikepdf-only desktop):** matches reality — pikepdf-only on
  desktop preserves the AI workflow for pros who need it, while still
  reusing the same engine for a PDF-only SaaS. Best technical bet.
- **B2 (PDF-only):** would forfeit ~35–40% of paid revenue (most sole
  pracs, most studios). Bad bet alone, fine as a lower tier.
- **B3 (hybrid local-helper):** the right product shape. PDF-only SaaS
  for cheap, high-volume student tier. Optional desktop helper that
  produces AI for pros. Maps to the two-tier table above.

If forced to pick one architecture for Phase B: **B3.** SaaS-PDF alone
captures students but caps growth in the pro segments where willingness
to pay is highest. A desktop companion (or a "download original AI"
upgrade tier in the SaaS) unlocks those segments without forcing them to
adopt cloud-only.

---

## Sources

- [adobe-cad-id]: https://community.adobe.com/t5/indesign-discussions/workflow-from-vector-architectural-cad-drawing-to-digital-published/m-p/9420888
- [adobe-thicken]: https://community.adobe.com/t5/indesign/exporting-to-pdf-makes-line-weights-appear-thicker-cad-plan-pdf-indesign-pdf/td-p/10638719
- [migoshi]: https://medium.com/@migoshi13/rhino-tutorial-exporting-to-adobe-illustrator-setting-line-weights-in-ai-and-exporting-from-ai-2255a7ff1aea
- [howtorhino]: https://howtorhino.com/rhino-grasshopper-tutorials/rhino-to-illustrator-section/
- [quora-adobe]: https://www.quora.com/As-an-architecture-student-I-would-like-to-understand-where-Adobe-applications-like-Photoshop-Illustrator-InDesign-come-in-play-when-creating-one-of-my-project-documents-or-portfolios
- [tuts]: https://design.tutsplus.com/tutorials/how-to-use-multi-layered-illustrator-artwork-in-indesign--vector-2672
- [syracuse]: https://soa.syr.edu/resources/technology/computing/printing-plotting/print-howto/
- [yale]: https://old-advancedtechnology.architecture.yale.edu/printingplotting/plotting-pdf-required-workflow
- [30x40]: https://thirtybyforty.com/
- [archademia]: https://archademia.com/blog/from-cad-to-final-presentation-integrating-indesign-with-architectural-workflows/
- [archdaily-cloud]: https://www.archdaily.com/771175/how-architecture-firms-can-safely-make-the-switch-to-cloud-storage

## Caveats and uncertainty

- **Reddit r/architecture and McNeel Discourse student threads were not
  directly mined** — search returned tutorial blogs, not user
  self-report. Direct quote yield was thin. A 30-min Reddit-only pass
  before launch would tighten the segment-1 estimate.
- **Sole practitioners are the segment with the *least* public
  workflow data.** The 30–45% range reflects that uncertainty — it
  could be 25% or 55%; we won't know until interview-driven validation.
- **Studios may surprise on the upside** if the SaaS markets as
  "weights only — output is your own" with privacy guarantees. The
  20% floor assumes default-skeptical IT posture.
- **OCG round-trip back to AI is one-way.** A user who needs to
  re-edit the PDF in Illustrator loses layer structure — this is a
  baked PDF, not a substitute for AI. Important to communicate
  honestly in the marketing copy.
