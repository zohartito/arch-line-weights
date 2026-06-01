#!/usr/bin/env python3
"""
Extract polygons for poché:
  1. Open BACKUP.ai with pikepdf
  2. Walk page content stream, tracking current OCG via BDC/EMC marked content
  3. Per OCG, collect line segments (transformed by current cm matrix)
  4. shapely linemerge + polygonize per ClippingPlaneIntersections layer
  5. Output JSON {layer_name: [polygon coords (pt)]} for the JSX to consume
"""
import json
import sys

import pikepdf
from pikepdf import parse_content_stream
from shapely.geometry import LineString, MultiLineString
from shapely.ops import linemerge, polygonize

SRC = "sample-section BACKUP.ai"
OUT = "/tmp/poche_polygons.json"
TOLERANCE = 0.05  # pt — Make2D output is exact, but be safe

pdf = pikepdf.open(SRC)
page = pdf.pages[0]

# Build MC# -> OCG layer name lookup
props = page.obj["/Resources"].get("/Properties")
mc_to_name = {}
for key in props:
    ocg = props[key]
    if "/Name" in ocg:
        mc_to_name[str(key)] = str(ocg["/Name"])  # e.g. "/MC28" -> "axon...::TEC_FOUNDATION"

# Layers we want poché on
target_mcs = {mc for mc, nm in mc_to_name.items()
              if "ClippingPlaneIntersections" in nm
              and "GLASS" not in nm.upper() and "IGU" not in nm.upper()}
target_layer_by_mc = {mc: mc_to_name[mc] for mc in target_mcs}
print(f"target OCGs: {len(target_mcs)}", file=sys.stderr)

ops = list(parse_content_stream(page))
print(f"page has {len(ops):,} top-level instructions", file=sys.stderr)

# Track stacks
xform_stack = []
current_xform = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)  # identity
mc_stack = []      # stack of "/MCn" strings

# Per-layer collection of segments  {mc: [(x1,y1,x2,y2), ...]}
segments = {mc: [] for mc in target_mcs}

current_pos = None
subpath_start = None

def apply_xform(x, y, m):
    a, b, c, d, e, f = m
    return (a*x + c*y + e, b*x + d*y + f)

def cm_compose(cur, new):
    a1, b1, c1, d1, e1, f1 = cur
    a2, b2, c2, d2, e2, f2 = new
    return (
        a1*a2 + c1*b2,
        b1*a2 + d1*b2,
        a1*c2 + c1*d2,
        b1*c2 + d1*d2,
        a1*e2 + c1*f2 + e1,
        b1*e2 + d1*f2 + f1,
    )

def in_target_now():
    for mc in mc_stack:
        if mc in target_mcs:
            return mc
    return None

for operands, op in ops:
    o = str(op)
    if o == "BDC":
        mc_name = None
        for od in operands:
            s = str(od)
            if s.startswith("/MC"):
                mc_name = s
        mc_stack.append(mc_name)
    elif o == "EMC":
        if mc_stack:
            mc_stack.pop()
    elif o == "q":
        xform_stack.append(current_xform)
    elif o == "Q":
        if xform_stack:
            current_xform = xform_stack.pop()
    elif o == "cm":
        new_m = tuple(float(x) for x in operands)
        current_xform = cm_compose(current_xform, new_m)
    elif o == "m":
        x, y = float(operands[0]), float(operands[1])
        current_pos = apply_xform(x, y, current_xform)
        subpath_start = current_pos
    elif o == "l":
        x, y = float(operands[0]), float(operands[1])
        new_pos = apply_xform(x, y, current_xform)
        target_mc = in_target_now()
        if target_mc and current_pos is not None:
            segments[target_mc].append((current_pos[0], current_pos[1], new_pos[0], new_pos[1]))
        current_pos = new_pos
    elif o == "c":
        # cubic bezier: 6 operands; sample chord plus mid for curvature
        x1, y1, x2, y2, x3, y3 = (float(x) for x in operands)
        end_pos = apply_xform(x3, y3, current_xform)
        target_mc = in_target_now()
        if target_mc and current_pos is not None:
            segments[target_mc].append((current_pos[0], current_pos[1], end_pos[0], end_pos[1]))
        current_pos = end_pos
    elif o == "v":
        # cubic with first control implicit
        x2, y2, x3, y3 = (float(x) for x in operands)
        end_pos = apply_xform(x3, y3, current_xform)
        target_mc = in_target_now()
        if target_mc and current_pos is not None:
            segments[target_mc].append((current_pos[0], current_pos[1], end_pos[0], end_pos[1]))
        current_pos = end_pos
    elif o == "y":
        x1, y1, x3, y3 = (float(x) for x in operands)
        end_pos = apply_xform(x3, y3, current_xform)
        target_mc = in_target_now()
        if target_mc and current_pos is not None:
            segments[target_mc].append((current_pos[0], current_pos[1], end_pos[0], end_pos[1]))
        current_pos = end_pos
    elif o == "re":
        # rectangle: x y w h re
        x, y, w, h = (float(v) for v in operands)
        target_mc = in_target_now()
        if target_mc:
            corners = [
                apply_xform(x, y, current_xform),
                apply_xform(x + w, y, current_xform),
                apply_xform(x + w, y + h, current_xform),
                apply_xform(x, y + h, current_xform),
            ]
            for i in range(4):
                a = corners[i]
                b = corners[(i+1) % 4]
                segments[target_mc].append((a[0], a[1], b[0], b[1]))
        current_pos = apply_xform(x, y, current_xform)
        subpath_start = current_pos
    elif o in ("h", "s", "b", "b*"):
        # close subpath (h closes; s/b/b* also close + stroke/fill)
        target_mc = in_target_now()
        if target_mc and current_pos is not None and subpath_start is not None and current_pos != subpath_start:
            segments[target_mc].append((current_pos[0], current_pos[1], subpath_start[0], subpath_start[1]))
        current_pos = subpath_start

print("\nsegments per target OCG:", file=sys.stderr)
for mc, segs in segments.items():
    print(f"  {mc}  {target_layer_by_mc[mc].split('::')[-1]:50}  {len(segs):>6} segs", file=sys.stderr)

# linemerge + polygonize per layer
out = {}
total_polys = 0
for mc, segs in segments.items():
    if not segs:
        continue
    layer_name = target_layer_by_mc[mc]
    lines = [LineString([(x1, y1), (x2, y2)]) for x1, y1, x2, y2 in segs if (x1, y1) != (x2, y2)]
    if not lines:
        continue
    mls = MultiLineString(lines)
    merged = linemerge(mls)
    # polygonize wants iterable of LineStrings
    if isinstance(merged, LineString):
        merged_lines = [merged]
    elif isinstance(merged, MultiLineString):
        merged_lines = list(merged.geoms)
    else:
        merged_lines = list(merged)
    polys = list(polygonize(merged_lines))
    if polys:
        coords = []
        for p in polys:
            xs_ys = [(x, y) for x, y in p.exterior.coords]
            coords.append(xs_ys)
        out[layer_name] = coords
        total_polys += len(polys)
    print(f"  {layer_name.split('::')[-1]:50}  segs={len(lines):>6}  merged={len(merged_lines):>5}  polys={len(polys):>4}", file=sys.stderr)

print(f"\ntotal polygons: {total_polys}", file=sys.stderr)
with open(OUT, "w") as f:
    json.dump(out, f)
print(f"wrote {OUT}", file=sys.stderr)
