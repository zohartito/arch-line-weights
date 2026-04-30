# Blog post outline

> From the marketing sub-agent (2026-04-30). Long-form, SEO-targeted writeup.

## Working title

**Why Adobe Illustrator's Join command can't reconstruct a polygon (and how shapely can)**

## Target

~1,800–2,200 words. SEO targets:
- "illustrator join not working"
- "detect closed polygons from line segments python"
- "shapely polygonize tutorial"
- "pdf content stream rewrite pikepdf"
- "rhino make2d closed polylines"

## Outline

### 1. Hook (~100 words)

Open with the moment it broke. A floor plan section, ten minutes before a
pinup, where Illustrator's Join produced a poché fill that bled into the
courtyard. Screenshot. Set the question: *why?*

### 2. The problem in one paragraph (~150 words)

Architectural drawings need closed regions to fill (walls, columns, ground).
Vector exports from Rhino give you line segments, not polygons. Reconstructing
the polygons is a topology problem. Most vector editors solve it heuristically.

### 3. The naive approach (~200 words)

Walk through what Illustrator's Join does: pick two endpoints within
tolerance, connect them. Show why this works for simple cases and fails for
branching geometry, T-intersections, and segments split mid-edge. Include a
minimal failing example with a diagram.

### 4. Why it fails (~250 words)

The real underlying issue: Join treats the input as a set of polylines with
endpoints, not a planar graph. It has no concept of "this segment continues
through this vertex". Introduce the formal framing: closed-region detection
is finding the faces of a planar straight-line graph (PSLG). Mention CGAL and
the academic context briefly, link to a paper.

### 5. The right approach with shapely (~400 words)

Walk through `linemerge` (combines compatible LineStrings) and `polygonize`
(finds closed polygons from a noded line collection). Explain the layered
fallback: snap geometries to a tolerance grid, then `unary_union` to node
intersections, then `polygonize`. Include a working code snippet (~30 lines)
the reader can paste.

### 6. Demo: before / after (~150 words)

Two images. One screenshot of Illustrator's Join silently dropping a wall
poché. One of `polygonize` getting it right. Same input file. Link to the
input file in the repo so readers can reproduce.

### 7. What we learned (~200 words)

Three takeaways:
1. "join" in vector editors is a UX heuristic, not a geometric guarantee
2. for any non-trivial closed-region problem, treat the input as a graph
3. write a postmortem when something fights you for a week — link to POSTMORTEM.md

### 8. Open source pitch (~100 words)

Quick mention of arch-line-weights as the tool that grew out of this work.
Repo link, install one-liner, invitation to contribute.

### 9. Footer

Cross-links to the HN/Reddit threads, RSS, contact.

## SEO notes

- Use the alt-text on both diagrams for "shapely polygonize closed region detection" and "illustrator join command failure example"
- H2 the section titles
- Internal-link to the repo's POSTMORTEM.md for backlink juice
