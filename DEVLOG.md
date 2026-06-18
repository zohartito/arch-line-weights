# Dev Log

Building arch-line-weights in public: one shippable artifact every working day, posted as a
serialized log. The counter is **architects who have actually used it** — GitHub stars and `pipx`
installs as the visible proxy — not revenue.

Why public-by-default: for a niche tool the real risk is obscurity, not someone copying it. An MIT
core plus daily, visible progress *is* the distribution. Monetization, if any, is a later open-core
layer; early progress is judged by streak survival and real usage.

See `docs/GROWTH.md` for the operating principles and `docs/ROADMAP.md` for engineering scope and
proof posture.

<!-- New entries on top. Keep each entry to three lines: Shipped / Status / Next. One per working day. -->

---

## Day 1 — 2026-06-17

**Shipped:** established the build-in-public cadence — this log and `docs/GROWTH.md`.

**Status (honest):** public MIT CLI that inspects a Rhino-exported `.ai`/`.pdf`, remaps stroke
widths by color, adds conservative section-cut poché, and applies material hatching, with presets
(`section`, `plan`, `elevation`, `detail`, `usc`) and layer-preserving commands (`apply-jsx`,
`apply-saas`). Public proof assets are **not yet cleared** (see `docs/ROADMAP.md` proof posture), so
the next milestone is a public-safe before/after, not a feature.

**Next:** clear one public-safe before/after proof on a synthetic/sample drawing so honest daily
posting can begin.
