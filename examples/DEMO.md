# Workflow demo — public sample fixture

A **workflow-orientation demo** on the public sample drawing in this folder. It is **not** a
validated proof packet (see `docs/ROADMAP.md` proof posture) and uses **no** private regression
drawing. The sample is a tiny synthetic fixture, so the point is the *mechanism*, not a hero image.

## Reproduce

```
pip install -e ".[test]"
arch-lw apply examples/sample-linework.pdf --auto --preset section
```

## What it does

A Rhino export emits every stroke at one uniform weight. `apply --preset section` maps each stroke
**color** to an architectural line weight:

| Stroke color        | Assigned weight | Role                                   |
|---------------------|-----------------|----------------------------------------|
| `RGB(40, 40, 40)`   | **1.0 pt**      | heaviest — section cut / building edge |
| `RGB(70, 70, 70)`   | **0.3 pt**      | medium — visible edges                 |
| `RGB(200,175,130)`  | **0.08 pt**     | lightest — detail / texture            |

```
# drawing-type: plan (confidence=0.52)   |   selected preset: section (explicit --preset)
# 3 colors mapped using auto:section
applied 3 strokes across 3 color changes
wrote "examples/sample-linework HIERARCHY.pdf"
```

The tool prints its inference context (drawing-type, depth, layer-source) with confidence scores, so
low-confidence calls are visible instead of silent.

## Why this isn't the marketing hero

This sample is a 3-stroke fixture — enough to show the mechanism, not enough for a postable
before/after. A compelling public hero needs a **richer synthetic, public-safe fixture**; a real
architectural drawing would be the private reference regression, which is **NO-GO** for public proof.
Building that synthetic fixture is the next step toward a postable before/after — see
`docs/GROWTH.md`.
