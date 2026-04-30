#!/usr/bin/env python3
"""
v4 — corrected pipeline:
  Step 1: bare linemerge + polygonize (no snap; this is what v1 did and it worked)
  Step 2: if 0 polys, snap+linemerge at increasing tolerances 0.5, 1, 2, 5 pt
  Step 3: if still 0, concave_hull(densified, ratio=0.3)
  Step 4: bbox last resort
For each layer, pick the strategy that maximizes polygon count.
"""
import json
import sys
from shapely.geometry import LineString, MultiLineString, MultiPoint, Polygon, box
from shapely.ops import linemerge, polygonize, snap, unary_union
from shapely import concave_hull, segmentize

SRC = "/tmp/cut_geometry.json"
DST = "/tmp/poche_polygons.json"

with open(SRC) as f:
    data = json.load(f)


def lines_from_paths(paths):
    out = []
    for pts in paths:
        if len(pts) >= 2:
            try:
                out.append(LineString([(p[0], p[1]) for p in pts]))
            except Exception:
                pass
    return out


def polys_bare(lines):
    """Bare linemerge — no snapping. This is what worked in v1."""
    if not lines:
        return []
    mls = MultiLineString(lines)
    merged = linemerge(mls)
    if isinstance(merged, LineString):
        merged_lines = [merged]
    else:
        try:
            merged_lines = list(merged.geoms)
        except AttributeError:
            merged_lines = [merged]
    return list(polygonize(merged_lines))


def polys_with_snap(lines, tol):
    if not lines or tol <= 0:
        return polys_bare(lines)
    all_geom = unary_union(lines)
    snapped = [snap(ls, all_geom, tol) for ls in lines]
    return polys_bare(snapped)


def try_concave(lines, ratio=0.3):
    densified = []
    for ls in lines:
        try:
            densified.append(segmentize(ls, max_segment_length=2.0))
        except Exception:
            densified.append(ls)
    pts = []
    for ls in densified:
        pts.extend(list(ls.coords))
    if len(pts) < 3:
        return None
    try:
        h = concave_hull(MultiPoint(pts), ratio=ratio)
    except Exception:
        return None
    if isinstance(h, Polygon) and h.area > 1.0:
        return h
    return None


def bbox_poly(lines):
    if not lines:
        return None
    mls = MultiLineString(lines)
    minx, miny, maxx, maxy = mls.bounds
    if maxx - minx < 1 or maxy - miny < 1:
        return None
    return box(minx, miny, maxx, maxy)


print(f"loaded {len(data)} layers", file=sys.stderr)

out = {}
total_polys = 0
log = []
for layer_name, paths in data.items():
    short = layer_name.split("::")[-1]
    lines = lines_from_paths(paths)
    if not lines:
        log.append((short, "no segments", 0, 0.0, 0))
        continue

    # Try bare first
    polys = polys_bare(lines)
    strat = "bare_linemerge"; conf = 1.0

    # If bare gave 0 OR we suspect under-merging, try snap variants
    # Heuristic: also try snap at each tolerance and keep result with MOST polygons
    best_polys = polys
    best_strat = strat
    best_conf = conf
    for tol in (0.5, 1.0, 2.0, 5.0):
        sp = polys_with_snap(lines, tol)
        if len(sp) > len(best_polys):
            best_polys = sp
            best_strat = f"snap_{tol}pt"
            best_conf = 0.85 if tol <= 1.0 else 0.7

    # If still 0 polys, try concave hull fallback
    if not best_polys:
        ch = try_concave(lines, ratio=0.3)
        if ch is not None:
            best_polys = [ch]
            best_strat = "concave_hull_0.3"; best_conf = 0.55

    # Bbox last
    if not best_polys:
        bb = bbox_poly(lines)
        if bb is not None:
            best_polys = [bb]
            best_strat = "bbox"; best_conf = 0.3

    if best_polys:
        out[layer_name] = [
            [[round(x, 4), round(y, 4)] for x, y in p.exterior.coords]
            for p in best_polys
        ]
        total_polys += len(best_polys)
        log.append((short, best_strat, len(best_polys), best_conf, len(lines)))
    else:
        log.append((short, "FAILED", 0, 0.0, len(lines)))

print(f"\n{'layer':50}  {'strategy':18}  {'polys':>5}  conf  segs", file=sys.stderr)
print("-" * 95, file=sys.stderr)
for nm, st, n, c, s in log:
    print(f"  {nm:50}  {st:18}  {n:>5}  {c:.2f}  {s}", file=sys.stderr)
print(f"\ntotal polygons: {total_polys}", file=sys.stderr)

with open(DST, "w") as f:
    json.dump(out, f)
print(f"wrote {DST}", file=sys.stderr)
