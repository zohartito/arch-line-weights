#!/usr/bin/env python3
"""Generate ``examples/demo-section.pdf`` — a public-safe DETAIL-grade demo.

The output is a **1:20 vertical wall-section strip** in the drawing grammar of
*DETAIL* magazine construction details: one tall strip cropped into three
stacked sub-details separated by clean white gaps —

  (a) roof edge / parapet with sheet-metal coping,
  (b) intermediate CLT floor edge meeting the facade with the window head below,
  (c) window sill + ground-floor slab + concrete footing into hatched earth.

Every material is drawn as **strokes** (outlines + hatch), colour-coded by their
layer *role* using five distinct RGB stroke colours with strictly increasing
Rec. 709 luminance — exactly how Rhino bakes a layer's display colour into an
exported vector. That single signal — colour, not width — is what
``arch-lw apply --auto`` classifies onto a graphic-standard line-weight
hierarchy (cut darkest/heaviest → annotation lightest/hairline).

Two elements — the coping cap and the sill/head flashings — are thin sheet
steel, so they are drawn as closed profiles AND **filled solid black** with the
PDF fill operator (``f``). ``arch-lw apply`` rewrites *stroke* widths only, so
fills pass through the before/after untouched and read identically on both
sides; that is honest and intentional.

Nothing here comes from a private drawing. The geometry is authored from fixed
constants (no randomness, no timestamps, no external assets), so the PDF is
byte-for-byte deterministic: running this script twice produces identical files.
The PDF is written by hand (stdlib only) rather than via reportlab/pikepdf so the
byte layout is fully under our control.

Usage::

    python examples/generate_demo_section.py            # writes the default path
    python examples/generate_demo_section.py -o out.pdf
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

# --------------------------------------------------------------------------- #
# Role colours — five distinct RGB, STRICTLY increasing Rec. 709 luminance so
# `arch-lw apply --auto` (which sorts distinct colours dark→light and buckets
# them 1:1 across the role ladder) lands each colour on its intended tier:
#
#   CUT      (darkest)  -> CUT_PROFILE   (heaviest)  cut structure: glulam/CLT/
#                                                    concrete/slab/footing/coping
#                                                    outlines, blocking, deck
#   PROFILE  (mid-dark) -> SPATIAL_EDGE              secondary profiles: window &
#                                                    glazing frames, CLT webs,
#                                                    membranes, flashing outlines
#   HATCH    (mid)      -> PLANAR_CORNER             material hatch: timber 45°,
#                                                    concrete, insulation cross-
#                                                    hatch, mineral-wool batts,
#                                                    earth, blocking X-hatch
#   TEXTURE  (light)    -> SURFACE                   fine texture: screed hatch,
#                                                    gravel stipple, aggregate
#   ANNO     (lightest) -> LAYOUT       (lightest)   callout leaders, level datums
#
# Luminances: 0.100 < 0.331 < 0.445 < 0.633 < 0.824 (well separated, monotonic).
# --------------------------------------------------------------------------- #
CUT = (25, 25, 30)
PROFILE = (70, 85, 120)
HATCH = (140, 110, 70)
TEXTURE = (180, 160, 120)
ANNO = (210, 210, 215)

PAGE_W = 400
PAGE_H = 920
STROKE_WIDTH = 1.0  # uniform hairline, like a raw Make2D export
FILL_RGB = (0, 0, 0)  # solid black sheet steel (coping, flashings)

Point = tuple[float, float]
Polyline = list[Point]

# --------------------------------------------------------------------------- #
# Shared wall build-up columns (points, x). PDF origin bottom-left, y up.
# Exterior air is on the LEFT, interior room on the RIGHT. The three panels are
# vertical crops of the SAME wall, so these columns are constant across them.
#
#   150 |161      176            212            250   262
#   CLAD | cavity | mineral wool | structure   | fin |  interior room ->
#   board| +batten| (CLT/glulam) |              |
# --------------------------------------------------------------------------- #
CLAD_O = 150   # cladding outer face (exterior air boundary)
CLAD_I = 161   # cladding inner face
CAV_I = 176    # inner face of ventilated cavity = breather-membrane plane
INS_O = 176    # cavity insulation outer
INS_I = 212    # cavity insulation inner = structure outer
STR_O = 212    # structure (CLT / glulam) outer
STR_I = 250    # structure inner
FIN_I = 262    # interior finish inner face

# Right-hand annotation column.
DATUM_X0 = 300     # level-datum lines start here (into the interior)
DATUM_X1 = 330     # and end here, with an EL triangle
LEADER_TIP = 372   # callout leader circles are centred here
CIRC_R = 4

# Panel vertical bands (y-lo, y-hi); white gaps sit between them.
PC_LO, PC_HI = 44, 300     # (c) sill + slab + footing + earth
PB_LO, PB_HI = 340, 600    # (b) CLT floor edge + window head
PA_LO, PA_HI = 640, 900    # (a) roof edge / parapet / coping


# --------------------------------------------------------------------------- #
# Geometry helpers
# --------------------------------------------------------------------------- #
def _rect_closed(x0: float, y0: float, x1: float, y1: float) -> Polyline:
    """A rectangle as one closed polyline (a single cut outline stroke)."""
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]


def _rect_edges(x0: float, y0: float, x1: float, y1: float) -> list[Polyline]:
    """Four separate edge polylines for a rectangle (kept as strokes)."""
    return [
        [(x0, y0), (x1, y0)],
        [(x1, y0), (x1, y1)],
        [(x1, y1), (x0, y1)],
        [(x0, y1), (x0, y0)],
    ]


def _hseg(x0: float, x1: float, y: float) -> Polyline:
    return [(x0, y), (x1, y)]


def _vseg(x: float, y0: float, y1: float) -> Polyline:
    return [(x, y0), (x, y1)]


def _clip_line(
    x0: float, y0: float, x1: float, y1: float, slope: float, intercept: float
) -> Polyline | None:
    """Clip an infinite line ``y = y0 + slope*(x - x0 - intercept)`` to a box.

    Returns the two entry/exit points, or ``None`` if it misses the box.
    """

    def y_at(x: float) -> float:
        return y0 + slope * (x - x0 - intercept)

    hits: list[Point] = []
    for x in (x0, x1):
        y = y_at(x)
        if y0 - 1e-6 <= y <= y1 + 1e-6:
            hits.append((x, min(max(y, y0), y1)))
    for y in (y0, y1):
        if abs(slope) > 1e-9:
            x = x0 + intercept + (y - y0) / slope
            if x0 - 1e-6 <= x <= x1 + 1e-6:
                hits.append((min(max(x, x0), x1), y))
    uniq: list[Point] = []
    for p in hits:
        if all(abs(p[0] - q[0]) > 1e-4 or abs(p[1] - q[1]) > 1e-4 for q in uniq):
            uniq.append(p)
    if len(uniq) < 2:
        return None
    uniq.sort()
    return [uniq[0], uniq[-1]]


def _diag_hatch(
    x0: float, y0: float, x1: float, y1: float, spacing: float, up: bool = True
) -> list[Polyline]:
    """45-degree hatch lines filling a rectangle, each clipped to its bounds."""
    lines: list[Polyline] = []
    width = x1 - x0
    height = y1 - y0
    slope = 1.0 if up else -1.0
    offset = -height
    while offset <= width + 1e-9:
        pts = _clip_line(x0, y0, x1, y1, slope=slope, intercept=offset)
        if pts:
            lines.append(pts)
        offset += spacing
    return lines


def _cross_hatch(
    x0: float, y0: float, x1: float, y1: float, spacing: float
) -> list[Polyline]:
    """Fine diagonal crosshatch (both slopes) — rigid insulation / concrete."""
    return _diag_hatch(x0, y0, x1, y1, spacing, up=True) + _diag_hatch(
        x0, y0, x1, y1, spacing, up=False
    )


def _zigzag_batt(x0: float, x1: float, y0: float, y1: float, step: float) -> Polyline:
    """Continuous zig-zag batt symbol (mineral-wool cavity insulation)."""
    batt: Polyline = []
    y = y0
    left = True
    while y <= y1 + 1e-9:
        batt.append((x0 if left else x1, y))
        left = not left
        y += step
    return batt


def _vertical_webs(x0: float, x1: float, y0: float, y1: float, step: float) -> list[Polyline]:
    """Evenly spaced vertical webs (CLT hollow-box cells / beam laminations)."""
    webs: list[Polyline] = []
    x = x0 + step
    while x < x1 - 1e-9:
        webs.append([(x, y0), (x, y1)])
        x += step
    return webs


def _stipple(x0: float, x1: float, y0: float, y1: float, dx: float, dy: float) -> list[Polyline]:
    """Gravel ballast: a grid of round-capped dots plus short vertical ticks.

    Dots are 0.4 pt segments; with the round line cap (``1 J``) they render as
    filled dots. Fixed grid → deterministic.
    """
    marks: list[Polyline] = []
    y = y0
    row = 0
    while y <= y1 + 1e-9:
        x = x0 + (dx / 2 if row % 2 else 0.0)
        while x <= x1 + 1e-9:
            marks.append([(x, y), (x + 0.4, y)])                          # dot
            marks.append([(x + dx / 2, y - 1.5), (x + dx / 2, y + 1.5)])  # tick
            x += dx
        y += dy
        row += 1
    return marks


def _triangles(positions: list[Point], size: float) -> list[Polyline]:
    """Small closed triangles — scattered concrete aggregate."""
    out: list[Polyline] = []
    for cx, cy in positions:
        out.append(
            [
                (cx, cy + size),
                (cx + size, cy - size),
                (cx - size, cy - size),
                (cx, cy + size),
            ]
        )
    return out


def _circle(cx: float, cy: float, r: float, segments: int = 16) -> Polyline:
    poly: Polyline = []
    for i in range(segments + 1):
        a = (i / segments) * 2 * math.pi
        poly.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return poly


def _leader(x_from: float, y_from: float, cx: float, cy: float) -> list[Polyline]:
    """A callout leader (hairline) ending at a small circle."""
    return [[(x_from, y_from), (cx - CIRC_R, cy)], _circle(cx, cy, CIRC_R)]


def _level_datum(y: float) -> list[Polyline]:
    """A level datum: a horizontal reference line ending in an open EL triangle."""
    return [
        _hseg(DATUM_X0, DATUM_X1, y),
        [(DATUM_X1, y), (DATUM_X1 + 8, y + 5), (DATUM_X1 + 8, y - 5), (DATUM_X1, y)],
    ]


def _clt_grain(y0: float, y1: float, step: float = 5) -> list[Polyline]:
    """Vertical CLT-panel grain lines across the structure column (material)."""
    return _vertical_webs(STR_O, STR_I, y0, y1, step)


def _cladding_courses(y0: float, y1: float, step: float = 13) -> list[Polyline]:
    """Horizontal board-coursing joints across the cladding board (fine texture)."""
    lines: list[Polyline] = []
    y = y0 + step
    while y < y1 - 1e-9:
        lines.append(_hseg(CLAD_O, CLAD_I, y))
        y += step
    return lines


# --------------------------------------------------------------------------- #
# Panels. Each appends to the shared role buckets (and the fills list).
# --------------------------------------------------------------------------- #
def _panel_c(cut, profile, hatch, texture, anno, fills) -> None:
    """(c) window sill + ground-floor slab + concrete footing into earth."""
    foot_l, foot_r, foot_b, foot_t = 146, 254, 70, 118
    slab_l, slab_r, slab_b, slab_t = 150, 300, 118, 136
    grade = 150            # exterior grade level
    sill_y = 276           # window sill datum (top of panel)
    glz_l, glz_r = 206, 214  # glazing plane

    # -- cut structure --
    cut.append(_rect_closed(foot_l, foot_b, foot_r, foot_t))          # strip footing
    cut.append(_rect_closed(slab_l, slab_b, slab_r, slab_t))          # ground slab
    for x in (STR_O, STR_I, FIN_I):                                   # structure + finish
        cut.append(_vseg(x, slab_t, PC_HI))
    for x in (CLAD_O, CLAD_I):                                        # cladding board
        cut.append(_vseg(x, grade + 2, sill_y - 6))
    cut.append(_hseg(slab_l, slab_r, slab_t))                        # slab top (finished floor)
    cut.append(_hseg(CLAD_O, STR_I, sill_y - 6))                     # wall head at sill
    cut.append(_rect_closed(CLAD_O, sill_y - 6, INS_I, sill_y))      # sub-sill block

    # -- sheet-steel sill flashing: filled black + cut outline (drips outward) --
    flashing = [
        (STR_O, sill_y + 8), (STR_O, sill_y + 4),
        (CLAD_O - 4, sill_y - 6), (CLAD_O - 4, sill_y - 2),
    ]
    fills.append(flashing)
    cut.append([*flashing, flashing[0]])

    # -- secondary profiles --
    profile.append(_vseg(CAV_I, grade + 2, sill_y - 6))              # breather membrane
    profile.extend(_rect_edges(glz_l, sill_y + 4, glz_r, sill_y + 18))  # aluminium sill frame
    profile.append(_hseg(glz_l + 1, glz_r - 1, sill_y + 8))          # sill gasket line
    profile.append(_vseg(glz_l + 2, sill_y + 14, PC_HI))            # glazing rising (double,
    profile.append(_vseg(glz_r - 2, sill_y + 14, PC_HI))           #   cut by the crop gap)

    # -- material hatch --
    hatch.extend(_cross_hatch(foot_l + 2, foot_b + 2, foot_r - 2, foot_t - 2, 7))   # footing
    hatch.extend(_diag_hatch(slab_l + 2, slab_b + 2, slab_r - 2, slab_t - 2, 7))    # slab
    hatch.append(_zigzag_batt(INS_O + 3, INS_I - 3, grade + 4, sill_y - 10, 8))     # mineral wool
    hatch.extend(_clt_grain(slab_t + 3, sill_y - 10))                              # CLT wall grain
    hatch.extend(_diag_hatch(36, 46, foot_l - 2, grade, 10, up=False))            # earth (left)
    hatch.extend(_diag_hatch(foot_l, 46, foot_r, foot_b - 2, 10, up=False))       # earth (below)
    hatch.extend(_diag_hatch(foot_r, 46, 300, foot_b + 8, 18, up=False))          # earth (right, faint)

    # -- fine texture --
    texture.extend(_cladding_courses(grade + 2, sill_y - 6))                       # board coursing
    texture.extend(
        _triangles(
            [(170, 96), (210, 84), (232, 104), (196, 128), (172, 128), (224, 90),
             (188, 100), (240, 92), (206, 108)],
            2.2,
        )
    )

    # -- annotation --
    anno.append(_hseg(30, foot_l - 6, grade))                       # exterior grade line
    anno.append([(foot_l - 6, grade), (foot_l - 6, foot_t + 2), (foot_l, foot_t + 2)])
    anno.extend(_level_datum(slab_t))                               # FFL datum
    anno.extend(_leader(foot_r, 96, LEADER_TIP, 96))               # footing callout
    anno.extend(_leader(slab_r, 127, LEADER_TIP, 127))            # slab callout
    anno.extend(_leader(STR_O, sill_y + 6, LEADER_TIP, sill_y + 6))  # sill callout


def _panel_b(cut, profile, hatch, texture, anno, fills) -> None:
    """(b) intermediate CLT floor edge meeting facade + window head below."""
    flr_b, flr_t = 520, 556       # CLT hollow-box floor flanges
    screed_t = 566                # screed band on top of the floor
    beam_b, beam_t = 498, 520     # glulam edge beam under the floor
    head_y = 380                  # window head datum
    lintel_b, lintel_t = 380, 398 # glulam lintel over the opening
    glz_l, glz_r = 206, 214

    # -- cut structure --
    cut.append(_rect_closed(STR_O, flr_b, DATUM_X0, flr_t))         # CLT box outline
    cut.append(_hseg(STR_O, DATUM_X0, screed_t))                   # screed top
    cut.append(_rect_closed(STR_O, beam_b, STR_I, beam_t))         # glulam edge beam
    cut.append(_rect_closed(STR_O, lintel_b, STR_I, lintel_t))     # glulam lintel
    for x in (STR_O, STR_I, FIN_I):                                # structure + finish
        cut.append(_vseg(x, lintel_t, beam_b))
        cut.append(_vseg(x, flr_t, PB_HI))
    for x in (CLAD_O, CLAD_I):                                     # cladding board
        cut.append(_vseg(x, PB_LO, head_y - 6))
        cut.append(_vseg(x, head_y + 30, PB_HI))
    cut.append(_hseg(CLAD_O, STR_I, head_y - 6))                  # wall soffit at head
    cut.append(_rect_closed(196, 500, STR_O, 520))                # blocking (38/235)

    # -- head flashing: filled black + outline, sloping out over the opening --
    head_flash = [
        (STR_O, head_y + 2), (STR_O, head_y - 2),
        (CLAD_O - 4, head_y - 10), (CLAD_O - 4, head_y - 6),
    ]
    fills.append(head_flash)
    cut.append([*head_flash, head_flash[0]])

    # -- secondary profiles --
    profile.append(_vseg(CAV_I, PB_LO, head_y - 6))               # membrane (lower run)
    profile.append(_vseg(CAV_I, head_y + 30, PB_HI))              # membrane (upper run)
    profile.extend(_vertical_webs(STR_O, DATUM_X0, flr_b, flr_t, 13))  # CLT cell webs
    profile.extend(_rect_edges(glz_l, head_y - 4, glz_r, head_y - 18))  # aluminium head frame
    profile.append(_vseg(glz_l + 2, PB_LO, head_y - 14))          # glazing dropping (double,
    profile.append(_vseg(glz_r - 2, PB_LO, head_y - 14))         #   cut by the crop gap)

    # -- material hatch --
    hatch.extend(_diag_hatch(STR_O + 1, beam_b + 1, STR_I - 1, beam_t - 1, 6))      # glulam beam
    hatch.extend(_diag_hatch(STR_O + 1, lintel_b + 1, STR_I - 1, lintel_t - 1, 6))  # glulam lintel
    hatch.extend(_cross_hatch(196, 501, STR_O - 1, 519, 5))        # blocking X-hatch
    hatch.append(_zigzag_batt(INS_O + 3, INS_I - 3, head_y + 34, flr_b - 4, 8))  # wool (mid)
    hatch.append(_zigzag_batt(INS_O + 3, INS_I - 3, flr_t + 4, PB_HI - 4, 8))    # wool (upper)
    hatch.extend(_clt_grain(lintel_t + 3, beam_b - 3))            # CLT wall grain (mid run)
    hatch.extend(_clt_grain(flr_t + 3, PB_HI - 3))               # CLT wall grain (upper run)

    # -- fine texture: tight screed diagonal band + cladding coursing --
    texture.extend(_diag_hatch(STR_O + 1, flr_t + 1, DATUM_X0 - 1, screed_t - 1, 3))
    texture.extend(_cladding_courses(PB_LO, head_y - 6))
    texture.extend(_cladding_courses(head_y + 30, PB_HI))

    # -- annotation --
    anno.extend(_level_datum(screed_t))                            # floor level datum
    anno.extend(_leader(DATUM_X0, 540, LEADER_TIP, 540))          # CLT floor callout
    anno.extend(_leader(glz_r, head_y - 10, LEADER_TIP, head_y - 10))  # window head callout


def _panel_a(cut, profile, hatch, texture, anno, fills) -> None:
    """(a) roof edge / parapet with sheet-metal coping."""
    beam_b, beam_t = 762, 790     # glulam roof edge beam
    deck_y = 790                  # top of structural deck
    ins_b, ins_t = 790, 814       # rigid PUR roof insulation
    grav_b, grav_t = 816, 828     # gravel ballast
    par_top = 872                 # top of parapet upstand (under coping)
    clad_top = 866

    # -- cut structure --
    cut.append(_rect_closed(STR_O, beam_b, FIN_I, beam_t))       # glulam roof beam
    cut.append(_hseg(STR_O, DATUM_X0, deck_y))                  # structural deck line
    for x in (STR_O, STR_I):                                    # parapet structure verticals
        cut.append(_vseg(x, PA_LO, par_top))
    cut.append(_hseg(STR_O, STR_I, par_top))                   # parapet cap bearing
    for x in (CLAD_O, CLAD_I):                                  # cladding board
        cut.append(_vseg(x, PA_LO, clad_top))
    cut.append(_rect_closed(200, 764, STR_O, 788))             # blocking (38/235) at eave

    # -- sheet-metal coping cap: filled black + outline, with drip legs --
    coping = [
        (146, clad_top - 2), (146, 878), (150, 886), (256, 886),
        (260, 878), (260, clad_top - 2), (254, clad_top - 2),
        (254, 880), (152, 880), (152, clad_top - 2),
    ]
    fills.append(coping)
    cut.append([*coping, coping[0]])

    # -- secondary profiles --
    profile.append(_vseg(CAV_I, PA_LO, clad_top - 4))            # breather membrane
    profile.append([(DATUM_X0, grav_b), (STR_O, grav_b), (STR_O + 2, par_top - 4)])  # roof membrane
    profile.extend(_vertical_webs(STR_O, FIN_I, beam_b, beam_t, 9))  # beam laminations

    # -- material hatch --
    hatch.extend(_diag_hatch(STR_O + 1, beam_b + 1, FIN_I - 1, beam_t - 1, 6))     # glulam beam
    hatch.extend(_cross_hatch(200, 765, STR_O - 1, 787, 5))                        # blocking X
    hatch.extend(_cross_hatch(STR_O + 1, ins_b + 1, DATUM_X0 - 1, ins_t - 1, 6))   # rigid PUR
    hatch.append(_zigzag_batt(INS_O + 3, INS_I - 3, PA_LO + 4, beam_b - 6, 8))     # cavity wool
    hatch.extend(_clt_grain(PA_LO + 3, beam_b - 3))              # CLT parapet grain (lower)
    hatch.extend(_clt_grain(beam_t + 3, par_top - 3))          # CLT parapet grain (upper)

    # -- fine texture: gravel stipple + ticks + cladding coursing --
    texture.extend(_stipple(STR_O + 4, DATUM_X0 - 4, grav_b + 2, grav_t - 2, 9, 5))
    texture.extend(_cladding_courses(PA_LO, clad_top - 2))

    # -- annotation --
    anno.extend(_level_datum(deck_y))                             # roof level datum
    anno.extend(_leader(256, 884, LEADER_TIP, 884))             # coping callout
    anno.extend(_leader(DATUM_X0, 802, LEADER_TIP, 802))       # roof insulation callout


def _author():
    """Author all panels once; return the five role buckets plus fills."""
    cut: list[Polyline] = []
    profile: list[Polyline] = []
    hatch: list[Polyline] = []
    texture: list[Polyline] = []
    anno: list[Polyline] = []
    fills: list[Polyline] = []
    _panel_c(cut, profile, hatch, texture, anno, fills)
    _panel_b(cut, profile, hatch, texture, anno, fills)
    _panel_a(cut, profile, hatch, texture, anno, fills)
    return cut, profile, hatch, texture, anno, fills


def build_strokes() -> list[tuple[tuple[int, int, int], Polyline]]:
    """Author the wall-section strip. Returns (rgb, polyline) pairs by role."""
    cut, profile, hatch, texture, anno, _fills = _author()
    ordered: list[tuple[tuple[int, int, int], Polyline]] = []
    # Draw material/texture first, structural cut and annotation last (on top).
    for rgb, group in (
        (HATCH, hatch),
        (TEXTURE, texture),
        (PROFILE, profile),
        (ANNO, anno),
        (CUT, cut),
    ):
        for poly in group:
            ordered.append((rgb, poly))
    return ordered


def build_fills() -> list[Polyline]:
    """Solid-black sheet-steel polygons (coping + flashings), drawn under strokes.

    Emitted with the PDF fill operator so ``arch-lw apply`` — which rewrites
    stroke widths only — leaves them byte-identical in before/after.
    """
    return _author()[5]


def _content_stream(
    strokes: list[tuple[tuple[int, int, int], Polyline]],
    fills: list[Polyline],
) -> bytes:
    """Emit a PDF content stream: solid fills first, then role-coloured strokes."""
    parts: list[str] = []

    # Solid-black sheet-steel fills (pass through `arch-lw apply` untouched).
    if fills:
        fr, fg, fb = (c / 255 for c in FILL_RGB)
        parts.append(f"{fr:.4f} {fg:.4f} {fb:.4f} rg")
        for poly in fills:
            (x0, y0), *rest = poly
            parts.append(f"{x0:.2f} {y0:.2f} m")
            for x, y in rest:
                parts.append(f"{x:.2f} {y:.2f} l")
            parts.append("h")
            parts.append("f")

    # Uniform-width, colour-coded strokes (the raw Make2D export signal).
    parts += [f"{STROKE_WIDTH:g} w", "1 J", "1 j"]
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
    content = _content_stream(build_strokes(), build_fills())
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
    n_fills = len(build_fills())
    print(f"wrote {args.output} ({len(data):,} bytes, {n_strokes} strokes, {n_fills} fills)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
