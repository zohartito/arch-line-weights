# Postmortem

Every poché attempt and what we learned. This page mirrors the canonical
[`docs/POSTMORTEM.md`](https://github.com/zohartito/arch-line-weights/blob/main/docs/POSTMORTEM.md)
in the repo.

## Why this exists

Three earlier attempts at solving the poché problem either crashed Illustrator,
produced visually wrong fills, or required hand-editing every layer. The
current pipeline is the result of those failures, not a clean-room design.

If you're considering a fork, read this first — it'll save you re-discovering
the same dead ends.

## Read on GitHub

→ **[docs/POSTMORTEM.md](https://github.com/zohartito/arch-line-weights/blob/main/docs/POSTMORTEM.md)**

## Cross-cutting lessons (the durable ones)

1. **Layer fidelity is non-negotiable.** Any change that destroys it must be explicit opt-in, not the default.
2. **Sub-agents in parallel** are how to move fast on unknowns.
3. **Two-stage pipelines** (Illustrator dump → Python compute → Illustrator apply) are easier to debug than monolithic JSX.
4. **Topology-aware geometry libraries** (shapely) > naive endpoint chaining (Illustrator Join) every time.
5. **Best-effort sweep over strategies + confidence scoring** > picking one tolerance and hoping.
6. **Document failed approaches in the repo**, not just successful ones.
7. **The user's verification ritual matters.** "Does it look right in Illustrator's Preview view at the layers panel?" is the ground truth, not "does the JSON say success."
8. **Save the source separately from the modification.** Use `saveAs` to a new file every time. Never modify the user's source in place.
9. **`maximumUndoDepth=1` + Outline view** turns ExtendScript from exponential-time to linear-time on bulk edits.
10. **Standards-compliant defaults trump aesthetics.**
