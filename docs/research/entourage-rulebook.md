# Entourage Rulebook

Date: 2026-05-05

Purpose: define how `arch-line-weights` should add two-dimensional isometric
people to an iso axon drawing after hierarchy and poché are already correct.
The goal is scale and life without turning entourage into a competing graphic
system.

This note is derived from the local private reference index at
`data/reference_books/reference_pages.sqlite`. It intentionally contains only
page-cited rules and implementation notes, not source text or copied diagrams.

## Source Search

- Francis D. K. Ching, *Architectural Graphics*: context, people, digital
  figures, paraline/isometric drawings, line-weight hierarchy, depth cues, and
  drawing composition (pp. 62-64, 80-83, 94-97, 101-102, 110, 113, 193-199,
  201, 206, 214, 216, 236, 250).
- Francis D. K. Ching and Steven P. Juroszek, *Design Drawing*: depth cues,
  elevation/section hierarchy, isometric construction, paraline line-weight
  hierarchy, contextual devices, people, shadows, landscaping, furniture,
  vehicles, and presentation relationships (pp. 101-106, 109, 112, 181,
  187-189, 197-198, 202, 221-223, 240-241, 390, 397, 400-403, 405, 407, 409,
  413, 416, 423, 429).
- Francis D. K. Ching, *Architecture: Form, Space, and Order*: scale,
  figure-ground, qualities of space, circulation, anthropometry, visual scale,
  and hierarchy (pp. 50, 118, 198, 293, 310, 322, 355, 358, 386).
- GitHub issue #20, "P2: Isometric entourage layer/library for scale figures":
  vector standing/walking/seated/leaning iso people, `Entourage::People`,
  light gray/thin weight, placement helpers, and tests that entourage never
  becomes cut weight or poché.

## Principle

Entourage is contextual evidence, not architectural structure. Human figures
help the viewer read scale, use, level changes, and depth, but they should be
subordinate to the building hierarchy (Architectural Graphics, pp. 193-198;
Design Drawing, pp. 400-403). In this repo, that means the hierarchy pipeline
runs first, poché is resolved second, and entourage is added only as a light
presentation layer.

Architecture remains the subject. Contextual devices should be limited to what
clarifies context, scale, and use; they should not hide structural or
space-defining relationships (Design Drawing, p. 400). When everything is
emphasized, hierarchy collapses (Design Drawing, p. 390; Architecture: Form,
Space, and Order, p. 386).

## Style Rules

1. Use a consistent abstract vector style.
   Photorealistic people will usually be too specific for this tool. The source
   guidance treats digital figures like hand-drawn figures: scale, clothing,
   placement, gesture, and abstraction still have to match the architectural
   drawing (Architectural Graphics, p. 198; Design Drawing, p. 403).

2. Make the people isometric-aware, not frontal cutouts.
   Ching explicitly warns against flat frontal figures in paraline and
   perspective views, and recommends giving figures some volume in paraline
   views (Architectural Graphics, pp. 194, 196; Design Drawing, pp. 401-402).
   For issue #20, "2D isometric people" should mean flat vector assets drawn
   with isometric posture and volume cues, not billboard silhouettes copied
   from elevation entourage.

3. Omit faces and fine fashion detail at architectural scale.
   Scale figures should communicate posture, activity, and rough clothing
   category, not identity. At typical drawing scales, fingers and facial detail
   become distracting noise (Design Drawing, p. 401).

4. Use posture to describe use.
   Standing, walking, seated, and leaning figures should answer what activity
   belongs in the space (Architectural Graphics, p. 197; Design Drawing,
   p. 402). A terrace can have a standing pair and one seated figure; a stair or
   ramp can use a walking figure; a facade scale check can use one quiet
   standing figure near an entry.

5. Keep entourage compatible with the drawing's abstraction.
   If the iso axon is mostly vector linework plus poché, people should be line
   and simple light fills. If the drawing has a muted tonal context layer,
   people may use one pale fill and one slightly darker contour, but not a
   separate render aesthetic (Design Drawing, pp. 397, 409; Architectural
   Graphics, p. 198).

## Line Weight and Tonal Rules

Entourage must sit below architectural edges and far below cut hierarchy.
Ching's line-weight rules reserve the heaviest weights for section cuts,
profiles, or nearest planes; lighter lines carry surface texture, distant
context, and subordinate information (Architectural Graphics, pp. 62, 80, 94;
Design Drawing, pp. 187, 197, 241).

Default issue #20 targets:

| Condition | Stroke | Tone/Opacity | Reason |
|---|---:|---:|---|
| Normal generated person | existing `reference`/`texture` tier: `0.13 pt` in current screen classifier, or `0.13 mm` / `0.369 pt` in ISO print presets | 45-60% black, no pure black fill | Reads as scale context, not structure |
| Foreground scale-critical person | at most `material` tier: `0.18 mm` / `0.510 pt` print-equivalent, or current `0.18 pt` screen tier | 60-70% black | Only for the nearest figure when it clarifies scale |
| Background person | `0.13 pt` screen or lighter via opacity | 25-40% black | Atmospheric-depth cue: less contrast recedes |
| Shadow/contact patch | no stroke or `0.08-0.13 pt` | 10-25% black | Grounds the figure without becoming poché |

Never use cut, profile, silhouette, structure, frame, or glazing tiers for
entourage. Never give entourage a solid black fill. Never classify entourage as
poché-eligible, even if it accidentally appears under a clipping-plane layer.

## Opacity and Depth

Depth in orthographic, paraline, and elevation-like drawings depends on
controlled line weight, contrast, overlap, and tonal value because projected
size alone does not create depth (Architectural Graphics, pp. 94-97; Design
Drawing, pp. 101-106, 187-189). Apply that same discipline to people:

- Foreground figures may be darker and more continuous, but still lighter than
  architectural profiles.
- Middleground figures should be the default style.
- Background figures should be grayer, less detailed, and possibly simplified
  to a tonal outline.
- Use overlap intentionally to indicate depth, but do not cover essential
  edges, joints, section cuts, stairs, ramps, doors, or facade openings
  (Architectural Graphics, p. 197; Design Drawing, p. 402).
- Add a small soft contact shadow when the ground plane is readable. Shadows
  are allowed because they keep figures from floating, but their transparency
  should leave the ground linework visible (Design Drawing, p. 405).

## Scale Rules

Use human figures as scale checks, not decoration. Human body dimensions and
activity dimensions are central to architectural scale and ergonomics
(Architecture: Form, Space, and Order, pp. 355, 358). The asset generator
should therefore scale people from a single canonical standing height.

Recommended defaults:

- Standing adult height: 5 ft 8 in / 1.73 m.
- Supported range: 5 ft 0 in to 6 ft 4 in / 1.52 m to 1.93 m.
- Head proportion: keep the asset internally consistent at roughly one seventh
  to one eighth of standing height (Architectural Graphics, p. 196; Design
  Drawing, p. 401).
- Seated people should be generated from the same standing-height reference,
  then posed, not independently scaled (Architectural Graphics, p. 196; Design
  Drawing, p. 402).
- In isometric drawings, place and scale figures along the same drawing scale
  as the three principal axes; do not use perspective shrinkage (Architectural
  Graphics, pp. 101-102; Design Drawing, pp. 221-223).

## Placement Rules

Place people where they explain the building:

- Floor plates and circulation paths: use sparse walking or standing figures to
  show access, pause points, and movement. Circulation spaces should support
  movement, pausing, resting, and viewing (Architecture: Form, Space, and
  Order, pp. 293, 310).
- Roof terraces, balconies, decks, and exterior landings: use one to three
  figures, biased toward the edge or furniture zone, to reveal occupation and
  guardrail scale.
- Near facade openings or entries: use one quiet standing figure to show visual
  scale, especially when the drawing needs a human reference beside tall doors,
  stairs, ramps, or curtain wall modules.
- Sitting zones: place seated figures only when furniture, benches, steps, or
  low walls support the activity. Furniture plus people is a stronger scale cue
  than either alone (Architectural Graphics, p. 199; Design Drawing, p. 413).
- Background context: add fewer, lighter figures; use them to deepen the scene,
  not to create new focal points (Design Drawing, p. 416).

Avoid:

- Dense cut zones and black poché.
- The perimeter of the section cut where heavy cut lines must remain
  continuous and dominant (Architectural Graphics, pp. 62, 80).
- Important spatial features, alignments, stairs, structural frames, facade
  returns, and layer review problem areas.
- Random distribution. A person should imply scale, use, path, level change, or
  a relationship to furniture/site context.

## Layer Naming

Canonical layer convention for issue #20:

```text
Entourage::People
```

For Rhino/Illustrator documents that preserve view hierarchy, generated layers
should nest under the visible drawing branch but never under
`ClippingPlaneIntersections`:

```text
axon::Visible::Entourage::People
axon::Visible::Entourage::People::Standing
axon::Visible::Entourage::People::Walking
axon::Visible::Entourage::People::Seated
axon::Visible::Entourage::People::Leaning
axon::Visible::Entourage::People::Shadows
```

Accepted aliases for imported drawings:

```text
ENTOURAGE
Entourage::People
People
Scale_Figures
ScaleFigures
Human
Figure
Person
```

Classifier rule: if a layer name contains an entourage alias, it should be
assigned to a dedicated `entourage` tier before any cut/clip-plane rule runs.
This guard matters because current Rhino classification treats
`ClippingPlaneIntersections` as cut first. Issue #20 needs the opposite
precedence for accidental entourage-in-cut-layer cases: entourage is never cut.

## Asset Library Rules

Minimum library:

- Standing: front-left isometric, front-right isometric, side-leaning.
- Walking: two stride variants per direction.
- Seated: chair/bench-neutral, low-wall/step-neutral.
- Leaning: rail/parapet/column-neutral.
- Shadows: optional separate simple contact patch.

Each asset should be:

- Vector-only.
- Built from grouped primitives or simple paths.
- Anchorable at a foot/contact point.
- Parameterized by height, direction, tone, stroke weight, and optional shadow.
- Named predictably, e.g. `person_standing_iso_ne_01`.
- Free of source-PDF material and free of copied commercial entourage assets.

Current implementation:

- `arch_line_weights.entourage.generate_entourage_library()` creates the
  minimum standing, walking, seated, and leaning SVG set.
- Generated assets stay on `Entourage::People::<Posture>` layers with optional
  contact shadows on `Entourage::People::Shadows`.
- Stroke weight is clamped to the current `entourage` tier (`0.13 pt` in
  screen-review section mode), and generated vectors avoid pure black fills and
  strokes.
- This is an asset generator only. AI insertion, floor-plate placement, and
  Illustrator panel workflows remain future work.

## CLI Support for Issue #20

Add the feature as a separate presentation step after hierarchy/poché:

```bash
arch-lw entourage add input.ai \
  --output input-ENTOURAGE.ai \
  --view axon \
  --layer "Entourage::People" \
  --library iso-minimal \
  --height "5ft8in" \
  --style line-light \
  --tone 55 \
  --shadow soft \
  --placement manual
```

Future automatic helpers:

```bash
arch-lw entourage add input.ai --placement floor-plates --count 6 --seed 20
arch-lw entourage add input.ai --placement roof-terrace --count 3
arch-lw entourage add input.ai --placement facade-scale --near-entry
```

The command should emit a review report:

- inserted asset count by posture and layer
- final stroke/tone range
- warnings for figures near cut/poché zones
- warnings for figures overlapping architectural focus layers
- whether shadows were added

## Implementation Hooks

Classifier:

- Add a first-pass `ENTOURAGE_ALIASES` guard before Rhino
  `CLIPPINGPLANEINTERSECTIONS`.
- Return `TierAssignment(weight_pt=0.13, tier="entourage", why="scale/context
  figure", confidence=0.95)` for screen mode.
- For ISO print presets, map `entourage` to the lightest context tier, normally
  `0.13 mm`.
- Make `entourage` a poché blacklist tier.

Poché:

- Skip any layer whose normalized name contains an entourage alias.
- If a generated person has closed shapes, do not interpret those shapes as
  fill candidates.
- Add report language: `entourage skipped: presentation/context layer`.

Assets/generator:

- Store or generate assets outside the poché geometry path.
- Use a foot/contact anchor and insertion transform based on drawing scale.
- Keep person groups on `Entourage::People::*`; shadow groups on
  `Entourage::People::Shadows`.
- Keep opacity/tone as editable attributes where Illustrator/PDF output allows.

Placement:

- Manual mode can accept explicit insertion points.
- Auto mode should first use candidate surfaces from non-cut visible curves:
  floor plates, roof terraces, decks, stairs/ramps, entries, and facade-adjacent
  ground.
- Auto mode should reject positions intersecting poché polygons or within a
  configurable buffer of heavy cut paths.
- Auto mode should prefer sparse clusters over uniform scatter.

Tests:

- `classify_layer("Entourage::People")` returns `entourage`, not `default`.
- `classify_layer("axon::Visible::Entourage::People::Standing")` returns
  `entourage`.
- `classify_layer("axon::Visible::ClippingPlaneIntersections::Entourage::People")`
  returns `entourage`, not `cut`.
- Poché generation skips `Entourage::People` even when assets include closed
  paths.
- Generated output keeps entourage stroke weight at or below the configured
  `entourage` tier.
- A report fixture shows entourage in the yellow/green review path, never as a
  red geometry failure and never as poché.

## Open Questions for Visual QA

- Should the default isometric person be a line figure, a pale filled figure,
  or both as style presets?
- Does the current screen-review `0.13 pt` entourage stroke survive Illustrator
  export at the drawing sizes Zohar uses, or should the default floor be
  `0.18 pt` with lighter opacity?
- Should facade-scale insertion prefer one person per major entry/module, or
  one person per drawing to avoid clutter?
- How much contact shadow is enough to ground figures in the iso axon without
  being mistaken for hatch or poché?
