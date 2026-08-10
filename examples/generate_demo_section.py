#!/usr/bin/env python3
"""Generate ``examples/demo-section.pdf`` — a public-safe demo drawing.

The output mimics a raw Rhino ``Make2D`` export of an architectural wall
section: every stroke is a uniform ``1.0 pt`` hairline, but strokes are
colour-coded by their layer *role* using distinct RGB stroke colours (exactly
how Rhino bakes a layer's display colour into an exported vector). That single
signal — colour, not width — is what ``arch-lw apply --auto`` classifies by
luminance to build a graphic-standard line-weight hierarchy.

Nothing here comes from a private drawing. The geometry is authored from fixed
constants (no randomness, no external assets), so the PDF is byte-for-byte
deterministic: running this script twice produces identical files. The PDF is
written by hand (stdlib only) rather than via reportlab/pikepdf so the byte
layout is fully under our control and free of timestamps or document IDs.

Usage::

    python examples/generate_demo_section.py            # writes the default path
    python examples/generate_demo_section.py -o out.pdf
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

# --------------------------------------------------------------------------- #
# Role colours — distinct RGB, STRICTLY increasing Rec. 709 luminance so the
# darkest colour (concrete cut) lands in the heaviest tier and the lightest
# colour (dimensions) lands in the lightest tier. `arch-lw apply --auto` sorts
# distinct colours dark→light and buckets them across the preset role ladder,
# so with exactly five colours each maps 1:1 onto a role:
#
#   CUT (darkest)   -> CUT_PROFILE   (heaviest)   concrete + assembly cut faces
#   EDGE            -> SPATIAL_EDGE                window frame + glazing
#   CORNER          -> PLANAR_CORNER               ground / floor / ceiling lines
#   SURFACE         -> SURFACE                     hatch + material texture
#   LAYOUT (light)  -> LAYOUT       (lightest)     dimensions + datums
# --------------------------------------------------------------------------- #
CUT = (20, 20, 20)
EDGE = (35, 70, 120)
CORNER = (60, 110, 90)
SURFACE = (150, 120, 80)
LAYOUT = (200, 200, 205)

PAGE_W = 460
PAGE_H = 720
STROKE_WIDTH = 1.0  # uniform hairline, like a raw Make2D export

Point = tuple[float, float]
Polyline = list[Point]


# --------------------------------------------------------------------------- #
# Geometry constants (points; PDF origin is bottom-left, y increases upward).
# Exterior is on the LEFT, building interior on the RIGHT.
# --------------------------------------------------------------------------- #
# Vertical datums
FOOT_BASE = 96      # bottom of spread footing
FOOT_TOP = 176      # top of footing / underside of slab
FFL = 200           # finished floor level (top of ground slab)
SILL = 372          # window sill
HEAD = 500          # window head
PLATE = 592         # top of wall / roof bearing
RIDGE = 636         # high point of the sloped roof deck

# Horizontal datums for the wall assembly
X_CLAD = 176        # exterior cladding face
X_CLT_O = 198       # CLT panel outer face
X_CLT_I = 232       # CLT panel inner face
X_INT = 252         # interior finish face

# Footing (stepped concrete profile)
X_FOOT_L = 150
X_FOOT_R = 268
X_STEM_L = 186
X_STEM_R = 244

# Ground / grade
GRADE_EXT = 172     # exterior grade level (left)
SLAB_RIGHT = 432    # slab extends into the building and is cut on the right


def _rect_edges(x0: float, y0: float, x1: float, y1: float) -> list[Polyline]:
    """Four separate edge polylines for a rectangle (kept as strokes, no fill)."""
    return [
        [(x0, y0), (x1, y0)],
        [(x1, y0), (x1, y1)],
        [(x1, y1), (x0, y1)],
        [(x0, y1), (x0, y0)],
    ]


def _diagonal_hatch(
    x0: float, y0: float, x1: float, y1: float, spacing: float, up: bool = True
) -> list[Polyline]:
    """45-degree hatch lines filling a rectangle, clipped to its bounds.

    Deterministic: lines are placed on a fixed offset grid. ``up`` selects the
    slope direction so two calls can crosshatch the same region.
    """
    lines: list[Polyline] = []
    width = x1 - x0
    height = y1 - y0
    # Sweep the diagonal's intercept across the box so every line is clipped
    # to the rectangle (no strokes escape the material boundary).
    offset = -height
    while offset <= width:
        if up:
            # line: y - y0 = (x - x0) - offset  ->  intersect with box edges
            pts = _clip_line(x0, y0, x1, y1, slope=1.0, intercept=offset)
        else:
            pts = _clip_line(x0, y0, x1, y1, slope=-1.0, intercept=offset)
        if pts:
            lines.append(pts)
        offset += spacing
    return lines


def _clip_line(
    x0: float, y0: float, x1: float, y1: float, slope: float, intercept: float
) -> Polyline | None:
    """Clip an infinite line ``y = y0 + slope*(x - x0 - intercept)`` to a box.

    Returns the two entry/exit points, or ``None`` if it misses the box.
    """
    def y_at(x: float) -> float:
        return y0 + slope * (x - x0 - intercept)

    hits: list[Point] = []
    # Left and right edges
    for x in (x0, x1):
        y = y_at(x)
        if y0 - 1e-6 <= y <= y1 + 1e-6:
            hits.append((x, min(max(y, y0), y1)))
    # Top and bottom edges
    for y in (y0, y1):
        if abs(slope) > 1e-9:
            x = x0 + intercept + (y - y0) / slope
            if x0 - 1e-6 <= x <= x1 + 1e-6:
                hits.append((min(max(x, x0), x1), y))
    # De-duplicate near-identical hits and keep the two furthest apart.
    uniq: list[Point] = []
    for p in hits:
        if all(abs(p[0] - q[0]) > 1e-4 or abs(p[1] - q[1]) > 1e-4 for q in uniq):
            uniq.append(p)
    if len(uniq) < 2:
        return None
    uniq.sort()
    return [uniq[0], uniq[-1]]


def build_strokes() -> list[tuple[tuple[int, int, int], Polyline]]:
    """Author the wall section. Returns (rgb, polyline) pairs, grouped by role."""
    cut: list[Polyline] = []
    edge: list[Polyline] = []
    corner: list[Polyline] = []
    surface: list[Polyline] = []
    layout: list[Polyline] = []

    # ------------------------------------------------------------------ CUT --
    # Stepped concrete footing — a single closed profile (narrow stem on a wider
    # spread base), drawn clockwise from the top-left of the stem.
    base_step = FOOT_BASE + 22
    cut.append(
        [
            (X_STEM_L, FOOT_TOP),
            (X_STEM_L, base_step),
            (X_FOOT_L, base_step),
            (X_FOOT_L, FOOT_BASE),
            (X_FOOT_R, FOOT_BASE),
            (X_FOOT_R, base_step),
            (X_STEM_R, base_step),
            (X_STEM_R, FOOT_TOP),
            (X_STEM_L, FOOT_TOP),
        ]
    )
    # Ground floor slab (cut) — sits on the footing stem, runs into the building.
    cut.append(
        [
            (X_STEM_L, FFL),
            (SLAB_RIGHT, FFL),
            (SLAB_RIGHT, FOOT_TOP),
            (X_STEM_L, FOOT_TOP),
        ]
    )
    # CLT wall panel cut faces (outer + inner), broken at the window opening.
    for x in (X_CLT_O, X_CLT_I):
        cut.append([(x, FFL), (x, SILL)])       # below sill
        cut.append([(x, HEAD), (x, PLATE)])     # above head
    # Cladding outer face (cut), broken at the window.
    cut.append([(X_CLAD, FFL), (X_CLAD, SILL)])
    cut.append([(X_CLAD, HEAD), (X_CLAD, PLATE)])
    # Interior finish face (cut), broken at the window.
    cut.append([(X_INT, FFL), (X_INT, SILL)])
    cut.append([(X_INT, HEAD), (X_INT, PLATE)])
    # Rough opening reveals at sill and head (the wall is cut around the window).
    cut.append([(X_CLAD, SILL), (X_INT, SILL)])
    cut.append([(X_CLAD, HEAD), (X_INT, HEAD)])
    # Concrete sill block under the window (cut).
    cut.extend(_rect_edges(X_CLAD, SILL - 14, X_CLT_I, SILL))

    # Roof assembly cut at the eave — a sloped deck bearing on the wall, with an
    # overhang past the cladding. Drawn as a cut band (deck top + soffit).
    roof_top = [
        (120, PLATE + 16),            # overhang tip (exterior, low side)
        (X_CLT_I, RIDGE),             # rises toward the interior
        (SLAB_RIGHT, RIDGE + 6),
    ]
    roof_soffit = [
        (120, PLATE),
        (X_CLAD, PLATE + 8),
        (X_CLT_I, RIDGE - 26),
        (SLAB_RIGHT, RIDGE - 20),
    ]
    cut.append(roof_top)
    cut.append(roof_soffit)
    # Fascia + eave return closing the roof band at the overhang.
    cut.append([(120, PLATE), (120, PLATE + 16)])
    # Wall-head bearing block (top plate, cut).
    cut.extend(_rect_edges(X_CLAD, PLATE, X_CLT_I, PLATE + 8))

    # ---------------------------------------------------------------- EDGE --
    # Window frame set into the opening (spatial edge — seen, not cut).
    fx0, fx1 = X_CLAD + 6, X_CLT_I - 4
    edge.extend(_rect_edges(fx0, SILL + 4, fx1, HEAD - 4))          # outer frame
    edge.extend(_rect_edges(fx0 + 6, SILL + 10, fx1 - 6, HEAD - 10))  # sash
    # Insulated glazing unit — two lines (double glazing) at mid-frame.
    gx = (fx0 + fx1) / 2
    edge.append([(gx - 2, SILL + 12), (gx - 2, HEAD - 12)])
    edge.append([(gx + 2, SILL + 12), (gx + 2, HEAD - 12)])
    # Head + sill of the frame seen in elevation within the opening.
    edge.append([(fx0 + 6, HEAD - 10), (fx1 - 6, HEAD - 10)])
    edge.append([(fx0 + 6, SILL + 10), (fx1 - 6, SILL + 10)])

    # -------------------------------------------------------------- CORNER --
    # Exterior grade line, stepping down to the footing excavation.
    corner.append(
        [
            (30, GRADE_EXT),
            (X_FOOT_L - 6, GRADE_EXT),
            (X_FOOT_L - 6, FOOT_TOP + 4),
            (X_FOOT_L, FOOT_TOP + 4),
        ]
    )
    # Interior finished floor line + a step of the threshold.
    corner.append([(X_INT, FFL + 2), (SLAB_RIGHT, FFL + 2)])
    # Ceiling line under the roof.
    corner.append([(X_CLT_I, PLATE - 2), (SLAB_RIGHT, PLATE + 4)])
    # Window sill + head finish lines (planar corners at the reveal).
    corner.append([(X_CLAD - 2, SILL), (X_CLAD - 2, SILL - 14)])

    # ------------------------------------------------------------- SURFACE --
    # Concrete footing hatch — crosshatch on the stem, single hatch on the base.
    surface.extend(_diagonal_hatch(X_STEM_L, FOOT_TOP - 60, X_STEM_R, FOOT_TOP, 10, up=True))
    surface.extend(_diagonal_hatch(X_STEM_L, FOOT_TOP - 60, X_STEM_R, FOOT_TOP, 10, up=False))
    surface.extend(_diagonal_hatch(X_FOOT_L, FOOT_BASE, X_FOOT_R, FOOT_BASE + 22, 12, up=True))
    # CLT grain — vertical laminations + a couple of glue-line courses.
    x = X_CLT_O + 4
    while x < X_CLT_I:
        surface.append([(x, FFL + 4), (x, SILL - 2)])
        surface.append([(x, HEAD + 2), (x, PLATE - 2)])
        x += 6
    for y in (FFL + 40, FFL + 90, HEAD + 40):
        surface.append([(X_CLT_O, y), (X_CLT_I, y)])
    # Insulation batts in the service cavity — a continuous zig-zag (two runs).
    for (y_lo, y_hi) in ((FFL + 6, SILL - 6), (HEAD + 6, PLATE - 6)):
        batt: Polyline = []
        y = y_lo
        left = True
        while y <= y_hi:
            batt.append((X_CLT_I + 3 if left else X_INT - 3, y))
            left = not left
            y += 9
        surface.append(batt)
    # Below-grade earth ticks under the exterior grade line.
    for gx0 in range(40, X_FOOT_L - 10, 14):
        surface.append([(gx0, GRADE_EXT - 4), (gx0 + 6, GRADE_EXT - 12)])
    # Roof deck texture — short battens across the slope.
    for t in range(0, 9):
        bx = 150 + t * 30
        surface.append([(bx, PLATE + 8 + t * 4), (bx + 10, PLATE + 12 + t * 4)])

    # -------------------------------------------------------------- LAYOUT --
    # Vertical dimension string on the right (extension lines + ticks + chain).
    dim_x = SLAB_RIGHT + 12
    levels = [FFL, SILL, HEAD, PLATE]
    layout.append([(dim_x, FFL - 4), (dim_x, PLATE + 8)])  # dimension line
    for y in levels:
        layout.append([(SLAB_RIGHT + 4, y), (dim_x + 6, y)])       # extension line
        layout.append([(dim_x - 4, y - 4), (dim_x + 4, y + 4)])    # 45-degree tick
    # Finished-floor datum symbol (a small triangle) at FFL, right side.
    layout.append([(dim_x + 14, FFL), (dim_x + 22, FFL + 6), (dim_x + 22, FFL - 6), (dim_x + 14, FFL)])
    # A vertical grid/centre line through the wall with a datum bubble at top.
    grid_x = (X_CLT_O + X_CLT_I) / 2
    layout.append([(grid_x, FOOT_BASE - 4), (grid_x, RIDGE + 24)])
    _bubble(layout, grid_x, RIDGE + 32, r=10)

    ordered: list[tuple[tuple[int, int, int], Polyline]] = []
    for rgb, group in (
        (CUT, cut),
        (EDGE, edge),
        (CORNER, corner),
        (SURFACE, surface),
        (LAYOUT, layout),
    ):
        for poly in group:
            ordered.append((rgb, poly))
    return ordered


def _bubble(sink: list[Polyline], cx: float, cy: float, r: float) -> None:
    """Approximate a grid-datum circle with a fixed 16-gon polyline."""
    poly: Polyline = []
    for i in range(17):
        a = (i / 16) * 2 * math.pi
        poly.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    sink.append(poly)


def _content_stream(strokes: list[tuple[tuple[int, int, int], Polyline]]) -> bytes:
    """Emit a PDF content stream: uniform width, colour set per role group."""
    parts: list[str] = [f"{STROKE_WIDTH:g} w", "1 J", "1 j"]
    last_rgb: tuple[int, int, int] | None = None
    for rgb, poly in strokes:
        if rgb != last_rgb:
            r, g, b = (c / 255 for c in rgb)
            parts.append(f"{r:.4f} {g:.4f} {b:.4f} RG")
            last_rgb = rgb
        (x0, y0), *rest = poly
        parts.append(f"{x0:.2f} {y0:.2f} m")
        for x, y in rest:
            parts.append(f"{x:.2f} {y:.2f} l")
        parts.append("S")
    return ("\n".join(parts) + "\n").encode("ascii")


def build_pdf_bytes() -> bytes:
    """Assemble the full, deterministic PDF file as bytes."""
    content = _content_stream(build_strokes())
    objs: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_W} {PAGE_H}] "
            f"/Contents 4 0 R /Resources << >> >>"
        ).encode("ascii"),
        4: b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"endstream",
    }

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets: dict[int, int] = {}
    for num in sorted(objs):
        offsets[num] = len(out)
        out += f"{num} 0 obj\n".encode("ascii") + objs[num] + b"\nendobj\n"

    xref_pos = len(out)
    size = len(objs) + 1
    out += f"xref\n0 {size}\n".encode("ascii")
    out += b"0000000000 65535 f \n"
    for num in sorted(objs):
        out += f"{offsets[num]:010d} 00000 n \n".encode("ascii")
    out += f"trailer\n<< /Size {size} /Root 1 0 R >>\nstartxref\n{xref_pos}\n".encode("ascii")
    out += b"%%EOF\n"
    return bytes(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent / "demo-section.pdf",
        help="Output PDF path (default: examples/demo-section.pdf).",
    )
    args = parser.parse_args(argv)
    data = build_pdf_bytes()
    args.output.write_bytes(data)
    n_strokes = len(build_strokes())
    print(f"wrote {args.output} ({len(data):,} bytes, {n_strokes} strokes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
