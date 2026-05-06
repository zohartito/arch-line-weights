#!/usr/bin/env python3
"""Rebuild the deadline stair model as Make2D-friendly solids.

The Rhino file inspected on 2026-05-05 had valid landing/stringer/spine solids
but invalid open Breps for every folded stair flight. This script makes a
non-destructive clean 3DM containing:

- copied landing boxes
- copied central spine
- rebuilt treads/risers as individual valid boxes
- copied stringers translated slightly down and placed on a separate layer

It is intentionally a spike for the deadline workflow, not a production CLI.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import rhino3dm as r3

TREAD_THICKNESS = 0.167
RISER_THICKNESS = 1.0 / 12.0
RISE_TARGET = 0.5
STRINGER_DROP_Z = 0.35


def _bbox(geom: r3.GeometryBase) -> tuple[float, float, float, float, float, float]:
    box = geom.GetBoundingBox()
    return (box.Min.X, box.Min.Y, box.Min.Z, box.Max.X, box.Max.Y, box.Max.Z)


def _add_layer(model: r3.File3dm, name: str, color: tuple[int, int, int, int], *, visible: bool = True) -> int:
    layer = r3.Layer()
    layer.Name = name
    layer.Color = color
    layer.Visible = visible
    model.Layers.Add(layer)
    return len(model.Layers) - 1


def _add_box(
    model: r3.File3dm,
    layer_index: int,
    name: str,
    bounds: tuple[float, float, float, float, float, float],
) -> None:
    minx, miny, minz, maxx, maxy, maxz = bounds
    bbox = r3.BoundingBox(r3.Point3d(minx, miny, minz), r3.Point3d(maxx, maxy, maxz))
    brep = r3.Brep.CreateFromBox(r3.Box(bbox))
    attr = r3.ObjectAttributes()
    attr.LayerIndex = layer_index
    attr.Name = name
    model.Objects.AddBrep(brep, attr)


def _add_translated_brep(
    model: r3.File3dm,
    source: r3.Brep,
    layer_index: int,
    name: str,
    *,
    dz: float,
) -> None:
    brep = source.Duplicate()
    brep.Translate(r3.Vector3d(0, 0, dz))
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

    layer_landings = _add_layer(model, "CLEAN_STAIR_LANDINGS", (96, 62, 32, 255))
    layer_treads = _add_layer(model, "CLEAN_STAIR_TREADS", (120, 78, 40, 255))
    layer_risers = _add_layer(model, "CLEAN_STAIR_RISERS", (145, 95, 48, 255))
    layer_spine = _add_layer(model, "CLEAN_STAIR_SPINE", (80, 52, 28, 255))
    layer_stringers = _add_layer(
        model,
        "CLEAN_STAIR_STRINGERS_OPTIONAL",
        (70, 45, 24, 255),
        visible=True,
    )

    landings: list[tuple[str, tuple[float, float, float, float, float, float]]] = []
    flights: list[tuple[str, tuple[float, float, float, float, float, float]]] = []
    stringers: list[tuple[str, r3.Brep]] = []
    spine: tuple[str, tuple[float, float, float, float, float, float]] | None = None

    for obj in source.Objects:
        name = obj.Attributes.Name or ""
        geom = obj.Geometry
        if name.startswith("fixed_stair_landing_"):
            landings.append((name, _bbox(geom)))
        elif name.startswith("fixed_folded_runs_risers_flight_"):
            flights.append((name, _bbox(geom)))
        elif name.startswith("fixed_clean_stringer_flight_") and isinstance(geom, r3.Brep):
            stringers.append((name, geom))
        elif name == "fixed_central_stair_spine":
            spine = (name, _bbox(geom))

    landings.sort(key=lambda item: item[1][5])
    flights.sort(key=lambda item: item[0])

    for name, bounds in landings:
        _add_box(model, layer_landings, name.replace("fixed_", "clean_"), bounds)

    for flight_index, (_name, bounds) in enumerate(flights, start=1):
        minx, _miny, _minz, maxx, _maxy, _maxz = bounds
        if flight_index > len(landings) - 1:
            continue

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
        rise = (z1 - z0) / float(risers)
        tread_count = risers - 1
        run_step = (y1 - y0) / float(tread_count)

        for i in range(tread_count):
            ty0 = y0 + run_step * i
            ty1 = y0 + run_step * (i + 1)
            z_top = z0 + rise * (i + 1)
            _add_box(
                model,
                layer_treads,
                f"clean_tread_flight_{flight_index:02d}_{i + 1:02d}",
                (
                    minx,
                    min(ty0, ty1),
                    z_top - TREAD_THICKNESS,
                    maxx,
                    max(ty0, ty1),
                    z_top,
                ),
            )

        for i in range(risers):
            y = y0 + run_step * i
            z_bottom = z0 + rise * i
            z_top = z0 + rise * (i + 1)
            _add_box(
                model,
                layer_risers,
                f"clean_riser_flight_{flight_index:02d}_{i + 1:02d}",
                (
                    minx,
                    y - RISER_THICKNESS / 2.0,
                    z_bottom,
                    maxx,
                    y + RISER_THICKNESS / 2.0,
                    z_top,
                ),
            )

    for name, brep in stringers:
        _add_translated_brep(
            model,
            brep,
            layer_stringers,
            name.replace("fixed_", "clean_") + "_dropped_below_treads",
            dz=-STRINGER_DROP_Z,
        )

    if spine is not None:
        name, bounds = spine
        _add_box(model, layer_spine, name.replace("fixed_", "clean_"), bounds)

    dst.parent.mkdir(parents=True, exist_ok=True)
    model.Write(str(dst), 8)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("src", type=Path)
    parser.add_argument("dst", type=Path)
    args = parser.parse_args()
    rebuild(args.src, args.dst)


if __name__ == "__main__":
    main()
