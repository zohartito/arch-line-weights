# Lessons learned

> Short reference card. The full failure stories live in `POSTMORTEM.md`;
> this page is the durable lessons distilled.

## Architecture conventions

1. **Layer fidelity is non-negotiable.** Any change that destroys it must be opt-in, not the default.
2. **Layer-name semantic classification beats color classification** for Rhino exports. `ClippingPlaneIntersections::*` is *always* the cut tier.
3. **ISO 128 (√2 series, 0.13–2.0 mm) is the right backbone** for tier weights. Per-scale shifts come from Ramsey/Sleeper + Ching + NCS.
4. **Print weights ≠ screen weights.** ISO 128 is for print; multiply by 1.5–2× for screen review readability.

## Geometry / topology

5. **Topology-aware geometry libraries (shapely) > naive endpoint chaining (Illustrator Join).** Join is not topology-aware — it chains by proximity in arbitrary order, producing self-intersecting blobs.
6. **`shapely.ops.linemerge + polygonize` is the right primitive** for recovering closed regions from a polyline soup, but only when endpoints are *exactly* coincident.
7. **For near-but-not-touching endpoints:** snap-tolerance sweep + auto-bridge (greedy nearest-endpoint pairing) > concave_hull > bbox, in that fallback order.
8. **Concave_hull is a lossy fallback, not a real solution.** Mark its outputs with low confidence so users can override.
9. **Best-effort sweep over strategies + confidence scoring > picking one tolerance and hoping.** Different layers in the same file want different tolerances.

## ExtendScript / Illustrator

10. **`maximumUndoDepth = 1`** is the single biggest ExtendScript performance win — turns exponential-time bulk edits into linear-time. Restore at end-of-script.
11. **Do NOT call `app.redraw()` inside loops.** Fragments the undo stack, ~10× slowdown.
12. **Switch to Outline view before bulk mutation.** `app.executeMenuCommand("showartwork")`.
13. **`do javascript` AppleScript bridge defaults to 120s timeout.** Wrap with `with timeout of N seconds` for long scripts.
14. **`saveAs` mutates the in-memory document's identity.** After `doc.saveAs(POCHE.ai)`, the previously-open `HIERARCHY.ai` tab is now `POCHE.ai` in memory. Close all and reopen from disk if you need a clean source.
15. **Stripping `/PieceInfo` flattens layers.** The PDF stream is a rendering fallback; Illustrator reads from PieceInfo first. Only strip it if you don't care about layer fidelity.
16. **`app.executeMenuCommand("join")` is NOT topology-aware.** See lesson #5.
17. **ExtendScript is ES3-ish.** No `let`, no arrow functions, no `Array.prototype.find`, no `JSON`. Polyfill or stay vanilla.
18. **Adobe UXP for Illustrator is still internal-only as of 2026-04.** Stay on ExtendScript via `do javascript`.

## Pipeline architecture

19. **Two-stage pipelines** (Illustrator dump → Python compute → Illustrator apply) are easier to debug than monolithic JSX or monolithic pikepdf.
20. **Save the source separately from the modification.** Use `saveAs` to a new file every time. Never modify the user's source in place.
21. **Sub-agents in parallel are how to move fast on unknowns.** A 90-min session with 5 parallel research agents covers what would take a solo dev a week.

## OSS / commercial pivot

22. **Pick the license BEFORE you publish to a public registry.** v1.0.0 was MIT for ~15 min; that snapshot is now perpetually MIT-licensed. Future versions can be any license, but the MIT cat is partially out of the bag.
23. **GitHub Pages on a private repo requires the GH Pro plan.** Going private = docs site goes 404 unless paid.
24. **PyPI Trusted Publishing OIDC works regardless of repo visibility** — but a yanked release blocks plain `pip install` while still allowing `pip install pkg==1.0.0` (explicit pin).
25. **PyPI permanent deletion is one-way.** Yank if you might want it back. Delete only if you want the version number freed (unlikely).
26. **Project name reservation persists** as long as the PyPI account does. Yanking all releases doesn't free the name.

## Process / discipline

27. **The user's verification ritual matters.** "Does it look right in Illustrator's Preview view at the layers panel?" is the ground truth — not "does the JSON say success."
28. **Document failed approaches in the repo**, not just successful ones. `POSTMORTEM.md` is a load-bearing artifact.
29. **Standards-compliant defaults trump aesthetics.** Architects judge by ISO 128 / Ramsey / Ching, not by your taste.
30. **Don't enable docs auto-deploy and then immediately privatize the repo.** Pages will go 404 instantly; emails fire.

## What I'd tell future-me about scope

31. **Open core / dual license is a trap for solo devs.** Either fully OSS or fully commercial. Splitting the brain is too much work.
32. **Architecture-school tools have a small but real market.** Don't expect Stripe-style growth; expect 100s of paying users, not millions.
33. **The hard problem is reaching customers**, not building product. From v1.0 onward, every hour of feature work needs a matching hour of distribution work.

## Strategy / pricing

34. **"Flawless" is not the bar; ≥95% on real edge-case-heavy inputs is.** Software with 100% coverage doesn't ship. Define the "amazing" bar in concrete terms (% layer success, library size, scale coverage) so perfectionism doesn't delay launch indefinitely.
35. **Subscription on a desktop CLI binary is hard to sell;** subscription on a web app is natural. The pricing model and the architecture choice are coupled — decide them together, not separately.
36. **License-swap deadlines aren't real until you publish.** v1.0.0 is yanked, repo is private; the LICENSE file doesn't *have* to change today. Don't burn a Saturday on PolyForm + EULA in advance of needing it. Do it ~3 days before v1.0.1 ships.
37. **Snapshot research before pivoting.** A SaaS-first pivot makes the v2 binary-distribution research (`docs/research/binary-distribution.md`, `distribution-platforms.md`) look obsolete — it's not. Keep it for the eventual paid-CLI complementary tier (Phase F4 / G).
38. **Web-app SaaS for a desktop-tool problem requires solving the headless-output question first.** For us, that's: can pikepdf write `.ai` files Illustrator opens with layer fidelity, without an Illustrator install on the server? This is the single biggest unknown gating SaaS, and it's a feasibility spike — not an architecture choice you can defer.

## Format reverse-engineering

39. **A "proprietary" format may just be an old format wearing modern compression.** The Adobe Illustrator `/PieceInfo /Illustrator /Private` payload looked closed. It's actually 305 PDF streams that concatenate into `%AI24_ZStandard_Data` + zstd-compressed plain-text AI3-AI8 PostScript — the same syntax we'd been generating from JSX for months. Always check the magic bytes before assuming a format is locked.
40. **Time-boxed feasibility spikes beat trying to design around an unknown.** Attempt 1 tried to dodge `/PieceInfo` by stripping it (flattened 62 layers to 1). A 60-minute scripted investigation resolved the question Attempt 1 was avoiding. When something is "the make-or-break unknown," spike it directly — don't architect around it.
41. **Working spike scripts > research summaries.** The 8 pikepdf scripts in `scripts/spike/saas-feasibility/` are the proof. They demonstrate inspect / decompress / round-trip / modify operations, verified in Illustrator. A 1000-word "I think this should work" report would have been worth less than 8 small Python files that actually do work.

## Real-world validation (post-Phase-A1)

42. **PyMuPDF and pikepdf disagree on what they can open.** PyMuPDF `fitz.open()` chokes on a 237 MB `.ai` that pikepdf opens cleanly for the rewrite step. The two libraries have different parsers; a tool that uses both must handle each library's failure modes independently. Practical fix: route `.ai` inspection through pikepdf, leave PyMuPDF for `.pdf` only.
43. **Headless wins on big files.** On a 98 MB plan drawing, pure-Python `apply-saas` finished in 5 min while `apply-jsx` hit a 60-min timeout with Illustrator still grinding. Even when the user has Illustrator open, the headless path is faster and more reliable. SaaS architecture choice (pikepdf+zstd, no Illustrator on server) is validated by real workload.
44. **Illustrator's `[Converted]` doc state is a JSX bridge landmine.** When Illustrator opens a non-AI source (older PDF, foreign format) as `<name> [Converted]`, AppleScript `tell ... open` returns silently without actually opening the disk file. The JSX then can't find its target. Detect explicitly and message the user.
45. **Hardcoded subprocess timeouts are wrong both ways.** 60 min is too long for small files (wasted time on hangs) and too short for big files (false aborts past the wire-protocol timeout while the JS engine keeps running). Either configurable or heartbeat-driven; never hardcoded.
46. **Output path collisions are a foot-gun.** When two pipelines (jsx, saas) write to the same default path, running both creates a race. Different default paths (`HIERARCHY-saas.ai` vs `HIERARCHY-jsx.ai`) prevent the issue entirely with zero added user complexity.

## Real-world validation (iso axon section, 2026-05-05)

47. **A faster algorithm can still be architecturally wrong.** The first
    `bridge-best` fix removed the 20+ minute hang and blocked the worst
    fallback blobs, but the drawing still missed legitimate floor, roof,
    foundation, and wall poché. Runtime correctness and architectural
    correctness are separate gates.
48. **Low-confidence geometry should be reported, not drawn.** `alpha_shape`
    and `bbox` are useful diagnostics, but injecting them as black fills
    produced convincing false poché on facade returns. Conservative output
    beats plausible-looking lies.
49. **Poché eligibility is semantic, not just geometric.** Not every
    `ClippingPlaneIntersections` layer is solid cut material. Screens,
    cladding, punch returns, window frames, glass, EPDM, connectors, and
    clips should not be black-filled by default.
50. **Structural open-loop closure is the missing poché rung.** Rhino often
    exports three sides of a cut mass. For structural materials only, the
    program should infer the missing fourth edge when the closure produces
    a plausible slab, roof, wall, or foundation polygon.
51. **Color luminance is not architectural hierarchy.** The converted iso
    axon had dark steel connector colors that mapped to heavy weights.
    Steel connectors, brackets, cleats, and clips should stay secondary
    unless they are the actual cut mass.
52. **Layer-name semantics should lead; color should be fallback.** Rhino
    exports rich layer names. The professional-grade path is semantic
    classifier first, color classifier only when layer confidence is low.
53. **The visual ground truth is Illustrator, not PDF preview.** The PDF
    compatibility stream and `/PieceInfo` native payload can diverge.
    Preview PNGs are helpful for broad checks but can miss native-payload
    modifications; Illustrator remains the authoritative visual QA target.
54. **CMYK support is mandatory.** Converted Illustrator files may use
    native CMYK `K` stroke operators rather than RGB `XA`; both must feed
    the same hierarchy classifier.
55. **Books should become rules, not blobs.** Ching/Ramsey/NCS references
    are most useful as page-cited, project-owned rulebooks that drive code
    and tests. Do not commit copyrighted PDFs or extracted full text.
