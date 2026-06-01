#!/usr/bin/env python3
"""Rebuild stairs as Make2D-friendly cohesive flight solids.

This is the deadline stair v5 pass. It does not ask Rhino to boolean-union many
little tread/riser boxes. Instead, it computes the 2D union of thick tread slabs
and thick riser plates in section, traces the exterior outline, and extrudes
that one closed profile into one solid per flight.

The result keeps actual riser thickness without creating the disconnected block
look from the boolean spike.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

import rhino3dm as r3

ARCH_202B = Path("<private-arch-202b-root>")
DEFAULT_SRC = ARCH_202B / "stairs.3dm"
DEFAULT_DST = ARCH_202B / "stairs CLEAN MAKE2D v7 cohesive no-stringers.3dm"

TREAD_THICKNESS = 0.167
RISER_THICKNESS = 1.0 / 12.0
RISE_TARGET = 0.5
JOIN_EPS = 0.001

L_LANDINGS = "CLEAN_FIXED_STAIR_LANDINGS"
L_FLIGHTS = "CLEAN_FIXED_STAIR_COHESIVE_FLIGHTS"
L_SPINE = "CLEAN_FIXED_STAIR_SPINE"


Bounds = tuple[float, float, float, float, float, float]
Rect = tuple[float, float, float, float]


def _bbox(geom: r3.GeometryBase) -> Bounds:
    box = geom.GetBoundingBox()
    return (box.Min.X, box.Min.Y, box.Min.Z, box.Max.X, box.Max.Y, box.Max.Z)


def _add_layer(model: r3.File3dm, name: str, color: tuple[int, int, int, int]) -> int:
    layer = r3.Layer()
    layer.Name = name
    layer.Color = color
    layer.Visible = True
    model.Layers.Add(layer)
    return len(model.Layers) - 1


def _add_box(model: r3.File3dm, layer_index: int, name: str, bounds: Bounds) -> None:
    minx, miny, minz, maxx, maxy, maxz = bounds
    bbox = r3.BoundingBox(r3.Point3d(minx, miny, minz), r3.Point3d(maxx, maxy, maxz))
    brep = r3.Brep.CreateFromBox(r3.Box(bbox))
    attr = r3.ObjectAttributes()
    attr.LayerIndex = layer_index
    attr.Name = name
    model.Objects.AddBrep(brep, attr)


def _record_source_parts(source: r3.File3dm) -> tuple[list[tuple[str, Bounds]], list[tuple[str, Bounds]], tuple[str, Bounds] | None]:
    landings: list[tuple[str, Bounds]] = []
    flights: list[tuple[str, Bounds]] = []
    spine: tuple[str, Bounds] | None = None

    for obj in source.Objects:
        name = obj.Attributes.Name or ""
        layer = source.Layers[obj.Attributes.LayerIndex].Name if obj.Attributes.LayerIndex >= 0 else ""
        token = f"{layer} {name}".lower()
        bounds = _bbox(obj.Geometry)

        if "landing" in token and "stair" in token:
            landings.append((name or f"landing_{len(landings) + 1:02d}", bounds))
        elif "flight" in token and "stair" in token:
            flights.append((name or f"flight_{len(flights) + 1:02d}", bounds))
        elif "spine" in token and "stair" in token:
            spine = (name or "stair_spine", bounds)

    landings.sort(key=lambda item: item[1][5])
    flights.sort(key=lambda item: (0.5 * (item[1][2] + item[1][5]), item[0]))
    return landings, flights, spine


def _cell_union_outline(rects: list[Rect]) -> list[tuple[float, float]]:
    """Return the largest exterior rectilinear outline of a rectangle union.

    Coordinates are in (y, z). The union is evaluated on the coordinate grid
    formed by all rectangle edges, so overlaps produce one clean boundary.
    """
    ys = sorted({v for y0, y1, _z0, _z1 in rects for v in (y0, y1)})
    zs = sorted({v for _y0, _y1, z0, z1 in rects for v in (z0, z1)})
    filled: set[tuple[int, int]] = set()

    for yi in range(len(ys) - 1):
        cy = 0.5 * (ys[yi] + ys[yi + 1])
        for zi in range(len(zs) - 1):
            cz = 0.5 * (zs[zi] + zs[zi + 1])
            if any(y0 <= cy <= y1 and z0 <= cz <= z1 for y0, y1, z0, z1 in rects):
                filled.add((yi, zi))

    if not filled:
        raise RuntimeError("No filled cells in stair-flight profile")

    edges: list[tuple[tuple[float, float], tuple[float, float]]] = []
    for yi, zi in filled:
        y0, y1 = ys[yi], ys[yi + 1]
        z0, z1 = zs[zi], zs[zi + 1]
        if (yi, zi - 1) not in filled:
            edges.append(((y0, z0), (y1, z0)))
        if (yi + 1, zi) not in filled:
            edges.append(((y1, z0), (y1, z1)))
        if (yi, zi + 1) not in filled:
            edges.append(((y1, z1), (y0, z1)))
        if (yi - 1, zi) not in filled:
            edges.append(((y0, z1), (y0, z0)))

    outgoing: dict[tuple[float, float], list[tuple[float, float]]] = defaultdict(list)
    for start, end in edges:
        outgoing[start].append(end)

    loops: list[list[tuple[float, float]]] = []
    while outgoing:
        start = min(outgoing)
        loop = [start]
        current = start
        while True:
            ends = outgoing.get(current)
            if not ends:
                raise RuntimeError("Could not trace closed stair-flight outline")
            nxt = ends.pop(0)
            if not ends:
                del outgoing[current]
            if nxt == start:
                break
            loop.append(nxt)
            current = nxt
        loops.append(_simplify_collinear(loop))

    return max(loops, key=lambda pts: abs(_area(pts)))


def _area(points: list[tuple[float, float]]) -> float:
    total = 0.0
    for (x0, y0), (x1, y1) in zip(points, points[1:] + points[:1], strict=False):
        total += x0 * y1 - x1 * y0
    return 0.5 * total


def _simplify_collinear(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if len(points) <= 2:
        return points
    simplified: list[tuple[float, float]] = []
    for point in points:
        simplified.append(point)
        while len(simplified) >= 3 and _is_collinear(simplified[-3], simplified[-2], simplified[-1]):
            middle = simplified.pop(-2)
            if not simplified or simplified[-1] == middle:
                break

    changed = True
    while changed and len(simplified) >= 3:
        changed = False
        for i in range(len(simplified)):
            a = simplified[i - 1]
            b = simplified[i]
            c = simplified[(i + 1) % len(simplified)]
            if _is_collinear(a, b, c):
                simplified.pop(i)
                changed = True
                break
    return simplified


def _is_collinear(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> bool:
    return (a[0] == b[0] == c[0]) or (a[1] == b[1] == c[1])


def _flight_rects(y0: float, y1: float, z0: float, z1: float, risers: int) -> list[Rect]:
    rise = (z1 - z0) / float(risers)
    tread_count = risers - 1
    run_step = (y1 - y0) / float(tread_count)
    y_sign = 1.0 if run_step >= 0 else -1.0
    rects: list[Rect] = []
    y_min = min(y0, y1)
    y_max = max(y0, y1)

    for i in range(tread_count):
        ty0 = y0 + run_step * i
        ty1 = y0 + run_step * (i + 1)
        z_top = z0 + rise * (i + 1)
        rects.append(
            _clamp_rect(
                (
                    min(ty0, ty1),
                    max(ty0, ty1),
                    z_top - TREAD_THICKNESS - JOIN_EPS,
                    z_top + JOIN_EPS,
                ),
                y_min,
                y_max,
                z0,
                z1,
            )
        )

    # The upper landing already supplies the last vertical face. Adding a full
    # final riser to the flight makes a small extra end block in Rhino/Make2D.
    for i in range(tread_count):
        y = y0 + run_step * min(i, tread_count)
        z_bottom = z0 + rise * i
        z_top = z0 + rise * (i + 1)
        y_outer = y + y_sign * RISER_THICKNESS
        rects.append(
            _clamp_rect(
                (
                    min(y, y_outer),
                    max(y, y_outer),
                    z_bottom - JOIN_EPS,
                    z_top + JOIN_EPS,
                ),
                y_min,
                y_max,
                z0,
                z1,
            )
        )

    return rects


def _clamp_rect(rect: Rect, y_min: float, y_max: float, z_min: float, z_max: float) -> Rect:
    y0, y1, z0, z1 = rect
    return (max(y0, y_min), min(y1, y_max), max(z0, z_min), min(z1, z_max))


def _add_cohesive_flight(
    model: r3.File3dm,
    layer_index: int,
    name: str,
    *,
    minx: float,
    maxx: float,
    y0: float,
    y1: float,
    z0: float,
    z1: float,
    risers: int,
) -> None:
    outline = _cell_union_outline(_flight_rects(y0, y1, z0, z1, risers))
    if _area(outline) < 0:
        outline.reverse()

    profile_points = [r3.Point3d(0, y, z) for y, z in outline]
    profile_points.append(profile_points[0])
    curve = r3.Polyline.CreateFromPoints(profile_points).ToPolylineCurve()
    extrusion = r3.Extrusion.Create(curve, maxx - minx, True)
    if extrusion is None:
        raise RuntimeError(f"Could not create cohesive stair flight {name}")
    brep = extrusion.ToBrep(True)
    if brep is None:
        raise RuntimeError(f"Could not convert cohesive stair flight {name} to Brep")

    box = brep.GetBoundingBox()
    brep.Translate(r3.Vector3d(minx - box.Min.X, 0, 0))

    attr = r3.ObjectAttributes()
    attr.LayerIndex = layer_index
    attr.Name = name
    model.Objects.AddBrep(brep, attr)


def rebuild(src: Path, dst: Path) -> None:
    source = r3.File3dm.Read(str(src))
    if source is None:
        raise RuntimeError(f"Could not read {src}")

    model = r3.File3dm()
    model.Settings.ModelUnitSystem = source.Settings.ModelUnitSystem

    layer_landings = _add_layer(model, L_LANDINGS, (96, 62, 32, 255))
    layer_flights = _add_layer(model, L_FLIGHTS, (120, 78, 40, 255))
    layer_spine = _add_layer(model, L_SPINE, (80, 52, 28, 255))

    landings, flights, spine = _record_source_parts(source)
    if len(landings) < 2 or not flights:
        raise RuntimeError(f"Could not find stair landings/flights in {src}")

    for i, (_name, bounds) in enumerate(landings, start=1):
        _add_box(model, layer_landings, f"clean_fixed_stair_landing_{i:02d}", bounds)

    for flight_index, (_name, bounds) in enumerate(flights, start=1):
        if flight_index > len(landings) - 1:
            continue

        minx, _miny, _minz, maxx, _maxy, _maxz = bounds
        lower = landings[flight_index - 1][1]
        upper = landings[flight_index][1]
        z0 = lower[5]
        z1 = upper[5]

        lower_cy = 0.5 * (lower[1] + lower[4])
        upper_cy = 0.5 * (upper[1] + upper[4])
        if lower_cy < upper_cy:
            y0 = lower[4]
            y1 = upper[1]
        else:
            y0 = lower[1]
            y1 = upper[4]

        if z1 <= z0 or abs(y1 - y0) < 0.01:
            continue

        risers = max(2, round((z1 - z0) / RISE_TARGET))
        _add_cohesive_flight(
            model,
            layer_flights,
            f"clean_fixed_stair_cohesive_flight_{flight_index:02d}",
            minx=minx,
            maxx=maxx,
            y0=y0,
            y1=y1,
            z0=z0,
            z1=z1,
            risers=risers,
        )

    if spine is not None:
        _name, bounds = spine
        _add_box(model, layer_spine, "clean_fixed_stair_spine", bounds)

    dst.parent.mkdir(parents=True, exist_ok=True)
    if not model.Write(str(dst), 8):
        raise RuntimeError(f"Could not write {dst}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("src", nargs="?", type=Path, default=DEFAULT_SRC)
    parser.add_argument("dst", nargs="?", type=Path, default=DEFAULT_DST)
    args = parser.parse_args()
    rebuild(args.src, args.dst)
    print(args.dst)


if __name__ == "__main__":
    main()
