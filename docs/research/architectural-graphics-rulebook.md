# Architectural Graphics Rulebook

> Derived research notes for `arch-line-weights`. Evidence came from the local
> SQLite reference index for Ching's *Architectural Graphics* and *Design
> Drawing*, plus `docs/research/standards.md`. This file contains derived rules
> only: no copied diagrams, no reproduced source pages, and no long quotations.

## Evidence Base

Primary page clusters inspected through `data/reference_books/reference_pages.sqlite`:

- Line types, line weights, digital output, and line quality: (Architectural Graphics, pp. 27-30); (Design Drawing, pp. 140-142).
- Floor plans and plan cuts: (Architectural Graphics, pp. 62-69); (Design Drawing, pp. 164-174).
- Building sections and section cuts: (Architectural Graphics, pp. 79-86); (Design Drawing, pp. 196-204).
- Building and interior elevations: (Architectural Graphics, pp. 88-98); (Design Drawing, pp. 183-192, 196).
- Projection systems, axonometric, oblique, and expanded paraline views: (Architectural Graphics, pp. 38-44, 101-108); (Design Drawing, pp. 221-230, 237, 241).
- Tonal depth and output QA cues: (Architectural Graphics, pp. 171-176, 185); (Design Drawing, pp. 101-105).
- Numeric line-weight ladder and print/screen tiers: `docs/research/standards.md`.

Broad FTS searches included `line weight`, `hierarchy`, `profile`, `silhouette`, `section`, `cut`, `poche`, `elevation`, `depth`, `foreground`, `background`, `hidden`, `dashed`, `centerline`, `detail`, `scale`, `axonometric`, `isometric`, `oblique`, and `projection`.

## Core Rule

Line weight is a semantic hierarchy, not decoration. Classify each visible mark by what it represents: cut matter, spatial edge, plane intersection, surface/material change, hidden/removed feature, reference datum, or texture. Only after the semantic role is clear should the output stroke width be assigned.

Use a minimum of three readable tiers in production drawings:

| Role | Graphic Meaning | Weight Direction |
|---|---|---|
| Cut / spatial profile | Solid matter meeting spatial void, or the dominant foreground edge | Heaviest |
| Plane edge / visible object edge | Intersections, corners, major form breaks | Medium |
| Surface / material / texture | Pattern, cladding, tonal or material change without form change | Light |
| Reference / hatch / construction | Grids, centerlines, dense hatch, layout lines | Lightest |

The visible range of weights must match drawing scale: small-scale drawings need a tighter range and less detail; larger scales can carry more tiers, heavier cuts, and more construction information (Architectural Graphics, pp. 28, 50-51; Design Drawing, p. 141).

Use the ISO-aligned ladder from `docs/research/standards.md` for plot output. At 1/4" = 1'-0", the practical print baseline is: section cut 0.70 mm, profile 0.50 mm, object edges 0.35 mm, hidden/centerline 0.25 mm, material 0.18 mm, texture/reference 0.13 mm. Shift one ISO step lighter at 1/8", two steps lighter at 1/16", and one step heavier at 1/2" or larger. Screen-review weights may need amplification because monitor display is not a reliable proof of plotted line quality (Architectural Graphics, pp. 28-29; Design Drawing, pp. 140-141).

## Universal Graphic Rules

1. Solid object lines vary by role. Heavy solid lines define cuts and spatial profiles; medium lines define plane edges and intersections; light lines show material, color, or texture changes; very light lines serve grids, layouts, and surface texture (Architectural Graphics, p. 28; Design Drawing, pp. 141-142).

2. Keep density uniform. A heavier tier should read as a wider stroke, not as a fuzzy, darker, or overdrawn mark. Digital output must be judged from the plotted/exported artifact, not just the monitor preview (Architectural Graphics, pp. 28-29; Design Drawing, p. 141).

3. Preserve the profile hierarchy. A cut/profile line should be continuous where it defines solid matter against void. It should not visually die into a weaker line or be interrupted by surface patterning (Architectural Graphics, pp. 62, 80; Design Drawing, pp. 165, 197).

4. Use dashed and centerline patterns semantically. Dashed lines indicate hidden, removed, above-cut, or otherwise concealed elements; centerlines indicate axes. Dash spacing should be consistent and should carry through corners cleanly enough to preserve the shape being indicated (Architectural Graphics, pp. 27, 29, 67; Design Drawing, pp. 140, 173).

5. Poché is a figure-ground tool. Use it to distinguish solid matter from void, but do not let a fill substitute for the line hierarchy. If the tonal scheme is reversed or moderate in contrast, reinforce the cut profile with a heavy outline (Architectural Graphics, pp. 63, 81, 171-172; Design Drawing, pp. 167, 198).

6. Texture is subordinate to form. Surface patterning, cladding lines, hatch, and material indications must never compete with cut/profile lines or major edges. In dense drawings, reduce texture weight or detail before weakening the cut hierarchy (Architectural Graphics, pp. 51, 64, 83; Design Drawing, pp. 169, 202).

## Floor Plans

A floor plan is a horizontal section, commonly cut around four feet above the floor. Its primary job is to make solid matter, spatial void, and the cut plane legible (Design Drawing, p. 164).

Plan hierarchy:

- Use the heaviest plan tier for walls, columns, and other vertical elements cut by the plan plane. This profile must read as the dominant contour of solid matter (Architectural Graphics, p. 62; Design Drawing, pp. 165-166).
- Use intermediate tiers for horizontal surfaces below the plan cut but above the floor: windowsills, counters, railings, casework, landings, and similar elements. The farther below the cut plane, the lighter the line should become (Architectural Graphics, p. 62; Design Drawing, p. 165).
- Use the lightest tiers for surface lines such as floor pattern, texture, and visual material changes that do not mark a change in form (Architectural Graphics, p. 62; Design Drawing, p. 165).
- Draw windowsills lighter than cut walls, mullions, or other cut elements because they are normally seen below the plan cut rather than sliced by it (Architectural Graphics, p. 66).
- Door swings are explanatory linework, not object profiles. Keep them light enough that wall cuts and jambs remain dominant (Architectural Graphics, p. 66; Design Drawing, p. 173).
- Use dashed conventions to separate above-cut/removed features from hidden features below the cut. Long dashes conventionally read as above or removed; shorter dashes or dots read as hidden below (Architectural Graphics, p. 67; Design Drawing, p. 173).
- At larger plan scales, include more construction thickness, terminations, corners, stair details, trim, finishes, and fittings. At smaller scales, omit detail that would make the plotted image too dense (Architectural Graphics, pp. 68-69; Design Drawing, p. 174).

QA for plans: At thumbnail size, the cut walls/columns should be identifiable before furniture, floor pattern, hatch, or entourage. If the plan reads as a flat pattern, the cut tier is too weak or texture/detail is too strong.

## Building Sections

A building section is a vertical cut through significant spaces. It should usually be continuous and parallel to a major wall system; jogs should be rare and purposeful. Cut through major spatial events such as openings, level changes, roof openings, and important room sequences. Avoid cutting freestanding columns or posts in a way that makes them read as walls (Architectural Graphics, p. 79).

Section hierarchy:

- Use the heaviest tier for elements cut by the section plane: walls, floors, roofs, structural masses, and ground where applicable (Architectural Graphics, pp. 79-81; Design Drawing, pp. 197-198).
- Keep the cut profile continuous and visually dominant. It should not be confused with elevation linework behind the cut (Architectural Graphics, p. 80; Design Drawing, p. 197).
- Use intermediate tiers for elements seen in elevation beyond the section cut. Decrease line weight as elements recede from the cut plane (Architectural Graphics, p. 80; Design Drawing, p. 197).
- Use the lightest tiers for surface lines on vertical planes parallel to the picture plane: patterns, texture, and material indications that do not change the form (Architectural Graphics, p. 80; Design Drawing, p. 197).
- Treat the supporting ground mass as cut material in building and site sections. If foundations are shown, they should read as part of the surrounding cut ground system rather than as a disconnected elevation object (Architectural Graphics, p. 81; Design Drawing, p. 198).
- Use poché or tonal value to strengthen the figure-ground relationship between solid matter and void, especially in small-scale sections. In large-scale sections, moderate the value so large black areas do not overpower the drawing (Architectural Graphics, pp. 81-83; Design Drawing, p. 198).
- Larger sections and detail sections must show more assembly information: wall thicknesses, corner conditions, stairs, and construction layers (Architectural Graphics, p. 86; Design Drawing, p. 204).

QA for sections: A reviewer should immediately distinguish the section plane from the elevation beyond it. If background elevation edges are as heavy as cut material, the section fails.

## Elevations

An elevation is an orthographic projection onto a vertical picture plane. Unlike a section, it normally does not cut through the building; it compresses exterior appearance onto one plane and relies on graphic cues to communicate depth (Architectural Graphics, pp. 88-89; Design Drawing, pp. 183-184).

Elevation hierarchy:

- The ground line is the one true cut-like condition in a building elevation: it represents a vertical cut through the ground mass in front of the building and may be the heaviest line in the elevation sheet (Architectural Graphics, pp. 89, 94; Design Drawing, pp. 184, 187, 191).
- For the building itself, use the strongest building tier for the silhouette and nearest major planes. Use progressively lighter tiers for planes farther from the picture plane (Architectural Graphics, pp. 94-96; Design Drawing, pp. 187-188).
- Use middle tiers for major form breaks, corners, roof edges, openings, frames, balconies, and recesses. Use light tiers for cladding joints, panel breaks, material patterns, and surface texture (Architectural Graphics, pp. 89, 91, 94; Design Drawing, pp. 184, 186-187).
- Establish foreground, middle ground, and background. Foreground/cut ground, the building, and background context should not all compete equally (Architectural Graphics, p. 95; Design Drawing, p. 187).
- Draw existing context, landscape, sky, and distant structures with fewer details, lighter lines, softer contrast, or diffuse tone so the design remains dominant (Architectural Graphics, pp. 95-97; Design Drawing, pp. 188-191).
- Interior elevations replace the section-cut emphasis with the boundary of the interior wall surface. They can carry more detail at room scale, but they should not invent a heavy cut tier unless combined with a section (Architectural Graphics, p. 98; Design Drawing, p. 196).

QA for elevations: The silhouette/nearest planes and ground base should read first; material joints should read second; texture and context should read last.

## Details

Details are governed by scale. The larger the drawing scale, the more construction information is required, especially material thicknesses, assembly layering, corner conditions, stair conditions, openings, joints, and trim (Architectural Graphics, pp. 50-51, 69, 86, 91; Design Drawing, pp. 174, 186, 204).

Detail hierarchy:

- Use a heavier cut tier than a normal 1/4" section for primary cut matter at 1/2" scale or larger, following the ISO step-shift baseline in `docs/research/standards.md`.
- Split cut matter when useful: primary cut for structural or mass elements; secondary cut for membranes, insulation boundaries, finish layers, panel layers, or gasket systems.
- Keep material edges and fasteners below the cut tier, but heavy enough to remain readable at detail scale.
- Hatching and material texture can be stronger than in small-scale drawings, but still subordinate to cut outlines and assembly edges.
- Annotation, dimensions, and leaders should remain clearly legible while staying lighter than object geometry.

QA for details: A detail should show more construction truth than a section, not simply the same linework enlarged. If hatch dominates material edges or dimensions compete with cut matter, the detail hierarchy is inverted.

## Axonometric, Oblique, and Section-Axon Views

Paraline drawings communicate three-dimensional form in one view. Axonometric projection is a form of orthographic projection; oblique projection keeps a principal face true to the picture plane while projecting depth at an oblique angle (Architectural Graphics, pp. 38-44; Design Drawing, pp. 221-230).

Paraline hierarchy:

- Pure axonometric and oblique drawings do not automatically have a cut tier. Use the heavy tier for spatial edges, a middle tier for planar corners, and the light tier for surface lines (Design Drawing, pp. 142, 241).
- In isometric drawings, the three principal axes share equal emphasis; all axial lengths are drawn to the same scale in common practice. Watch for ambiguity when foreground and background lines align (Architectural Graphics, pp. 101-102; Design Drawing, pp. 222-223).
- In plan obliques, the horizontal plane is true in size and shape; use them when plan geometry, circulation, or complex horizontal forms matter most (Architectural Graphics, pp. 44, 101, 103).
- In elevation obliques, the selected vertical face is true in size and shape; choose the longest, most significant, or most complex face as the base (Architectural Graphics, pp. 44, 101; Design Drawing, p. 229).
- Reduce or tune receding lengths in oblique drawings when full-depth projection visually distorts the object (Architectural Graphics, pp. 44, 103; Design Drawing, p. 230).
- For cutaway or section-axon views, introduce a cut tier only where the view actually slices the model. The cut should reveal interior space through contrasting line weight or tone (Architectural Graphics, pp. 108, 174; Design Drawing, p. 237).
- In expanded/exploded views, relationship lines should be dotted, dashed, or delicate so they clarify assembly order without becoming object edges (Architectural Graphics, p. 108; Design Drawing, p. 237).

QA for axons: The view should read as spatial structure, not a single-weight wireframe. Spatial edges should be stronger than plane intersections, and surface texture should never obscure the geometry.

## Depth and Projection Conventions

Depth in orthographic drawings is artificial; it must be constructed with line weight, tonal value, overlap, clarity, and detail. Use these conventions consistently:

- Weight decreases with distance from the cut plane or picture plane. This applies to plan elements below the cut, section/elevation elements behind the cut or projection plane, and elevation background context (Architectural Graphics, pp. 62, 80, 94-96; Design Drawing, pp. 165, 187-188, 197).
- Strong, continuous contours advance; lighter, thinner, broken, or diffuse contours recede (Architectural Graphics, pp. 96-97; Design Drawing, pp. 101-102, 188-189).
- Material texture should transition from identifiable units in the foreground to pattern and then tone in the background. Do not let distant texture contradict atmospheric depth by becoming too crisp or dark (Architectural Graphics, p. 97; Design Drawing, pp. 103, 105).
- Tonal values can reinforce line hierarchy, but line hierarchy must still be legible in a pure-line or low-toner export (Architectural Graphics, pp. 171-174).
- Shadows can clarify projection and relative height, but they are optional in plans and sections and should support, not replace, the cut hierarchy (Architectural Graphics, p. 185).

## Output QA Criteria

Use these checks before accepting an exported drawing:

1. Semantic check: every heavy line has a reason. Heavy strokes should be cut matter, ground cut, primary silhouette, or dominant spatial profile.
2. Monotonicity check: cut/profile > object edges > hidden/material > texture/reference within the selected drawing type.
3. Poché check: fill or tone reinforces figure-ground reading and does not bury the line hierarchy.
4. Density check: small-scale drawings omit excess detail; hatches and surface patterns do not merge into unreadable fields.
5. Dash check: hidden, above-cut, centerline, grid, property, break, and utility lines use distinct patterns and maintain clean corners.
6. Print check: run a plot/export proof for the target output. Monitor display is not sufficient evidence of line quality or weight contrast (Architectural Graphics, pp. 28-29; Design Drawing, pp. 140-141).
7. Thumbnail check: at zoomed-out review scale, the drawing type should still be recognizable: plan cut, section cut, elevation silhouette/ground, detail assembly hierarchy, or axon spatial edge hierarchy.

## Implementation Hooks

Concrete implications for `arch-line-weights`:

- Preserve drawing-type context through classification. A layer classified as `cut` should resolve differently in `section`, `plan`, `elevation`, `detail`, and future `axon` presets. Current preset cross-walks are the right pattern; the rulebook argues for stricter view-specific tests.
- Add or formalize a `hidden` classifier tier. Rhino `::Hidden::Curves::...`, AIA/NCS-style `HIDD`, `OVHD`, `ABOV`, and ceiling/roof-overhang layers should not fall to a generic default when the view is plan or section. The dash convention may need metadata beyond stroke width: long dash for above/removed, shorter dash or dot for hidden below.
- Treat plan windowsills, counters, railings, casework, and stair landings as below-cut/intermediate tiers, not as cut walls. Tests should assert `WINDOW_SILL < WALL_CUT` and `DOOR_SWING <= PATTERN`.
- In elevation presets, distinguish building silhouette/profile from ground cut. A `GROUND`, `GRADE`, `TOPO`, or `SITE_CUT` layer may be as heavy as the sheet's dominant line, while ordinary building material joints and cladding patterns must stay light. Do not blindly promote every clipping-plane intersection to the elevation silhouette tier without view/source evidence.
- In sections, keep ground/foundation logic coherent. Cut ground mass should share or closely follow cut-material weight, while foundations below grade should not appear as unrelated background elevation linework.
- Add an `axon` or `paraline` preset family. Pure axons should map to `spatial_edge`, `planar_corner`, and `surface_line` tiers. Section-axon/cutaway exports can opt into `cut`, but only for actual clipping-plane intersections.
- Expand detail classification with `cut_primary`, `cut_secondary`, `edges`, `material`, `texture`, and `annotation`. Detail-scale hatches may be heavier than small-scale hatches, but tests should keep them below cut and edge tiers.
- Use `select_preset(..., for_print=True)` as the source of truth for plotted output and keep screen presets visually amplified. Add tests that print presets follow ISO-step monotonicity and that screen presets do not leak into print defaults.
- Add hierarchy QA tests over synthetic layer sets: no material/hatch layer is heavier than an edge tier; no annotation/default layer equals cut; at least three distinct weights are emitted for a normal plan/section/elevation sample.
- Add regression fixtures for digital-output risks from the references: single-weight exports should fail a quality warning; tiny-scale drawings with too many hatch/pattern layers should trigger density warnings; target-output proofing should be explicit in CLI/help text.

## Minimal Acceptance Standard

A drawing passes this rulebook when a reviewer can answer, without layer names:

- What is cut?
- What is in front?
- What is behind?
- What is merely surface texture?
- What is hidden, above, or reference-only?
- Is this output tuned for the intended scale and medium?

If those answers are unclear, adjust the semantic classification first, then the line-weight values.
