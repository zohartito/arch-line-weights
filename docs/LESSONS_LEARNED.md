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
