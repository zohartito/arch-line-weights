# Architectural Line-Weight Conventions

This is the drawing-spec target for the preset and classifier. It follows the
architectural hierarchy taught in Ching and Architectural Graphic Standards, and
uses the ISO/technical-pen line-width series as the numeric ladder.

## Core Hierarchy

Read drawings by proximity to the cut plane and by graphic importance:

| Rank | Category | Meaning | Default treatment |
| --- | --- | --- | --- |
| 1 | Poche | Material mass cut by the plane | Solid black or dark fill; boundary is a cut/profile line |
| 2 | Cut | Edges where the plan/section plane slices walls, slabs, columns, ground, stairs, casework, etc. | Heaviest continuous line, used sparingly |
| 3 | Profile | Outer silhouette, ground line, major foreground outline, opening edge that separates figure from field | Heavy continuous line, usually just below cut |
| 4 | Visible | Edges seen beyond the cut plane: walls beyond, apertures, furniture, fixtures, grade, surface breaks | Medium to light continuous line, lighter with depth |
| 5 | Hidden | Objects above, below, behind, or concealed but necessary to understand the view | Thin dashed line, often screened |
| 6 | Surface / Pattern | Hatches, material joints, panel lines, poche hatches, tile, paving, texture | Lightest line; never competes with visible/cut |
| 7 | Construction / Guides | Layout grids, projection guides, reference axes, non-print scaffolding | Extra-light or non-plot unless intentional |

Rules:

- What is cut is darker than what is merely seen.
- Poche is a fill/mass convention, not just a thick outline.
- Use the fewest distinguishable weights that make the drawing legible: usually
  4-6 plotted weights per view.
- Printed black/gray must carry the meaning; screen color is only a working aid.
- Line weight is relative to output scale and board size. Do not classify by
  object type alone; classify by view role first, then object/source layer.

## ISO / Rotring Pen Ladder

Use this ISO technical-pen series as the allowed plotted widths. Rotring-style
technical pens are the physical precedent: constant-width nibs selected from a
small ladder rather than arbitrary stroke values. Adjacent sizes step by about
sqrt(2), so moving one rung is a visible but controlled change.

| Rung | mm | pt | Typical role |
| --- | ---: | ---: | --- |
| 0 | 0.13 | 0.37 | surface hatch, texture, gray guide, very fine hidden |
| 1 | 0.18 | 0.51 | hidden, dimensions, grids, light background |
| 2 | 0.25 | 0.71 | light visible edges, furniture, fixtures, secondary depth |
| 3 | 0.35 | 0.99 | normal visible edges, foreground object outlines |
| 4 | 0.50 | 1.42 | profile/silhouette, strong visible edge, small-scale cut |
| 5 | 0.70 | 1.98 | primary cut, wall/slab/column cut, ground cut |
| 6 | 1.00 | 2.83 | very strong cut/profile, title-grade poche boundary |
| 7 | 1.40 | 3.97 | exceptional diagram/board emphasis only |

Avoid 1.00-1.40 mm for dense plans/details unless the output scale is large
enough that openings and joins remain readable.

## View-Specific Rules

### Plans

A plan is a horizontal section, typically cut through walls/openings above the
floor plane. Prioritize:

1. Poche/cut walls, columns, stair cuts: 0.50-0.70 mm plus fill when appropriate.
2. Major profiles at voids, floor edges, plan silhouettes: 0.35-0.50 mm.
3. Visible elements below the cut plane, including fixtures/furniture: 0.25-0.35 mm.
4. Overhead items, beams/soffits/cabinets above, hidden stairs: 0.13-0.18 mm dashed.
5. Floor pattern, tile, landscape texture: 0.13-0.18 mm.

### Sections

A section is a vertical cut. It must make the cut plane unmistakable:

1. Cut ground, walls, slabs, roofs, columns, stairs: 0.70 mm default; 1.00 mm only
   for a presentation-scale ground/profile line.
2. Poche cut solids: solid/dark fill with a clean boundary; hatch only if material
   differentiation is more important than figure-ground clarity.
3. Profile of major voids/openings and near edges: 0.50 mm.
4. Visible background beyond cut: 0.18-0.35 mm, stepping lighter with distance.
5. Hidden background: show only when necessary; 0.13-0.18 mm dashed.

### Elevations

An elevation is primarily visible projection, not a cut through the building:

1. Overall building silhouette, foreground grade, and major plane breaks: 0.35-0.50 mm.
2. Foreground visible edges/openings: 0.25-0.35 mm.
3. Recessed planes, mullions, trim, joints, material courses: 0.13-0.25 mm.
4. Hidden/overhead features: 0.13-0.18 mm dashed, only if explanatory.
5. Ground may be treated as a cut/profile if the elevation includes the site section.

## Make2D Mapping

Use Rhino Make2D buckets as a first pass, then reclassify by view type and depth.

| Make2D output | Classifier category | Default styling |
| --- | --- | --- |
| Visible clipping planes | Cut | 0.70 mm continuous; generate poche fill from closed cut regions |
| Hidden clipping planes | Hidden cut / usually suppress | 0.13-0.18 mm dashed only when explaining concealed cut geometry |
| Visible lines | Visible or Profile | 0.25-0.35 mm; upgrade silhouettes/outer boundaries/foreground edges to 0.50 mm |
| Visible tangents | Surface / light visible | 0.13-0.18 mm, or suppress if they read as unwanted seams |
| Hidden lines | Hidden | 0.13-0.18 mm dashed/screened |
| Hidden tangents | Suppress or Hidden light | 0.13 mm dashed only if essential |
| Annotations | Annotation | 0.13-0.18 mm continuous, independent of model hierarchy |
| Source layers | Modifier, not primary class | Use to refine material/object semantics after view-role classification |

Postprocess requirements:

- Detect closed visible clipping-plane loops and fill them as poche.
- Promote the outermost visible silhouette/profile above ordinary visible edges.
- Demote tangent seams and dense surface isocurves unless they convey material or form.
- Add missing intersection curves before Make2D when objects pass through each other.
- Expect occasional Make2D layer mistakes where silhouettes nearly overlap other curves;
  the classifier should resolve by geometry/context, not layer name alone.

## Default "USC Studio Board" Preset

Recommended for black/gray presentation boards and exported vector linework. Treat
this as the default preset, not a code standard.

| Preset class | mm | pt | Line type | Print tone | Notes |
| --- | ---: | ---: | --- | --- | --- |
| Poche fill | n/a | n/a | fill | 90-100% black | Cut mass; boundary uses cut/profile line |
| Primary cut | 0.70 | 1.98 | continuous | 100% black | Plans/sections: walls, slabs, columns, ground cut |
| Heavy profile | 0.50 | 1.42 | continuous | 100% black | Silhouette, major foreground outline, small-scale cut |
| Visible primary | 0.35 | 0.99 | continuous | 100% black | Main visible edges/openings/foreground objects |
| Visible secondary | 0.25 | 0.71 | continuous | 85-100% black | Furniture, fixtures, mid-depth edges, minor plane breaks |
| Hidden / overhead | 0.18 | 0.51 | dashed | 50-70% black | Above/below/behind lines; keep sparse |
| Surface / hatch | 0.13 | 0.37 | continuous or hatch | 35-60% black | Material joints, tile, texture, poche hatch |
| Guide / grid / dim | 0.13-0.18 | 0.37-0.51 | continuous | 40-70% black | Grids, dimensions, reference marks |
| Exceptional emphasis | 1.00 | 2.83 | continuous | 100% black | Only for large board ground lines or diagram hierarchy |

Preset defaults by view:

| View | Cut | Profile | Visible | Hidden | Surface |
| --- | ---: | ---: | ---: | ---: | ---: |
| Plan | 0.70 | 0.50 | 0.25-0.35 | 0.18 dashed | 0.13 |
| Section | 0.70 | 0.50 | 0.18-0.35 | 0.13-0.18 dashed | 0.13 |
| Elevation | n/a | 0.35-0.50 | 0.13-0.35 | 0.13-0.18 dashed | 0.13 |
| Axon / diagram | optional 0.50-0.70 | 0.50 | 0.18-0.35 | 0.13 dashed | 0.13 |

## Sources

- Francis D. K. Ching, *Architectural Graphics*, 6th ed., Wiley, 2015.
  Reference basis: architectural drawing systems, orthographic projection, line
  weights, scale, sections, and presentation layout.
  https://books.google.com/books/about/Architectural_Graphics.html?id=1OkbBgAAQBAJ
- The American Institute of Architects; Dennis J. Hall and Nina M. Giglio, eds.,
  *Architectural Graphic Standards*, 12th ed., Wiley, 2016.
  Reference basis: construction documentation and architectural graphic standards.
  https://newsroom.wiley.com/press-releases/press-release-details/2016/Wiley-Announces-Architectural-Graphic-Standards-12th-Edition/default.aspx
- ISO 128-1:2020, *Technical product documentation - General principles of
  representation - Part 1*. Reference basis: ISO 128 applies to manual and
  computer-based technical drawings, including architecture and construction.
  https://www.iso.org/standard/65296.html
- ISO 128-2:2022, *Technical product documentation - General principles of
  representation - Part 2: Basic conventions for lines*. Reference basis: basic
  line types and line-drafting conventions.
  https://www.iso.org/standard/83355.html
- ISO 128-3:2022, *Technical product documentation - General principles of
  representation - Part 3: Views, sections and cuts*. Reference basis: general
  principles for presenting views, sections, and cuts.
  https://www.iso.org/es/contents/data/standard/08/33/83356.html
- McNeel, Rhino Make2D command documentation. Reference basis: Make2D output
  classes for visible, hidden, tangent, clipping-plane, and annotation curves.
  https://docs.mcneel.com/rhino/mac/help/en-us/commands/make2d.htm
- Rotring, Isograph technical pen product reference. Reference basis: technical
  pen precedent for constant-width plotted lines.
  https://www.rotring.com/pens-pencils/technical-pens/isograph-set/SP_124525.html
