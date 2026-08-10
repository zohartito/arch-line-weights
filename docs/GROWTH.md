# Growth & Build-in-Public Plan

The adoption/distribution layer for arch-line-weights. This complements `ROADMAP.md` (engineering
scope) — it is about getting the tool into architects' hands, not about features or pricing
commitments.

## Operating principles

1. **One public artifact every working day** — a commit, a clip, or a `DEVLOG.md` entry.
   Consistency is the mechanism; the daily cadence is the product as much as the code is.
2. **Serialized counter.** Public updates carry a running number:
   *"Day N — open-sourcing arch-line-weights until 100 architects use it."* A rising counter turns
   scattered work into a story people can follow.
3. **One tool, one audience.** Rhino/Grasshopper users and architecture students. No feature sprawl
   until the line-weight + poché core is genuinely loved.
4. **Open-core.** The CLI core stays MIT and free. Any future paid layer is hosted/convenience only.
   Give the core away to beat obscurity and earn credibility.
5. **Monetization is later-stage.** Judge early progress by streak survival and real usage, not
   revenue. Expect a long flat stretch before adoption inflects.
6. **Ship real, runnable artifacts.** Every update must be something an architect could actually
   run — not a mockup.

## The counter

- **North-star:** 100 architects have used arch-line-weights.
- **Visible proxies:** GitHub stars, `pipx` installs, `DEVLOG.md` streak length.

## Now → next (living checklist)

The first gate is honesty: the repo's proof posture is currently **NO-GO** (`ROADMAP.md`), so public
proof must be cleared before posting results.

- [x] Clear **one** public-safe before/after (synthetic or sample drawing) — unblocks honest
      daily posting. Does not involve the private USC regression.
      *(2026-08-10: the committed hero is a synthetic **demo**, not a proof packet; separately, the
      synthetic packet `public_foundation_window_section_synthetic` materializes and validates
      `passed` with sentinels verified. Harness-green; acceptance-of-record still open — #80.)*
- [x] Record the canonical demo: "uniform 1.0 pt export → graphic-standard hierarchy".
      *(2026-08-10: `examples/generate_demo_section.py` → `examples/demo-section.pdf` (406-stroke
      1:20 DETAIL-grammar wall-section strip)
      → real `arch-lw apply` → `assets/hero-before-after.png`, deterministic and committed. The
      3-stroke `examples/sample-linework.pdf` demo remains in `examples/DEMO.md`.)*
- [ ] First public devlog post carrying the Day-N counter, once the proof asset is cleared.
- [x] Near-term engineering that doubles as daily artifacts (from `ROADMAP.md`): clearer
      `/NumBlock`-missing diagnostics, better low-confidence poché reports, more Make2D
      layer-naming fixtures. *(2026-08-10: all three landed in the stack-integration PR.)*
- [ ] Keep the install story honest (source/`pipx` now; PyPI deliberately deferred).

## Audience surfaces

- **Primary:** the open GitHub repo — the README is the pitch.
- **Secondary (once proof is cleared):** short before/after clips posted with the Day-N counter to
  the Rhino / architecture-student communities where the niche actually is.

> Private strategy notes and competitive research are kept outside this public repository.
