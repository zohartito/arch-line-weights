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

**Shipped:**
- Established the build-in-public cadence — this log and `docs/GROWTH.md`.
- First reproducible public demo (`examples/DEMO.md`): `apply --preset section` on the public sample
  maps stroke color → weight (`40,40,40`→1.0 pt; `70,70,70`→0.3 pt; `200,175,130`→0.08 pt).

**Status (honest):** public MIT CLI that inspects a Rhino-exported `.ai`/`.pdf`, remaps stroke
widths by color, adds conservative section-cut poché, and applies material hatching, with presets
(`section`, `plan`, `elevation`, `detail`, `usc`) and layer-preserving commands (`apply-jsx`,
`apply-saas`). The public sample is a 3-stroke fixture — it demonstrates the mechanism but cannot
carry a marketing before/after. Validated proof assets remain **NO-GO** (see `docs/ROADMAP.md`).

**Next:** build a richer **synthetic, public-safe fixture** so a real before/after hero can be
posted — the private USC drawing stays NO-GO.
