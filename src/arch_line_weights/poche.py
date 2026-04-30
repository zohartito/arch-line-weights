"""Poché: turn cut-line geometry into solid black fills.

Pipeline (two-stage; relies on Adobe Illustrator for layer-preserving I/O):

1. **Dump** — JSX walks the open file's `ClippingPlaneIntersections::*` layers
   (and any `__POCHE_CLOSE__` user-marked closing layer) and writes every path's
   anchor points to a JSON file.

2. **Polygonize** — `polygonize_dump()` reads the JSON, runs a sweep of
   tolerances over `shapely.ops.linemerge` + `polygonize`, picks the strategy
   that maximises polygon count per layer, falls back to `concave_hull`,
   `bounding_box`, with a confidence score per fill.

3. **Apply** — JSX (rendered with the polygons baked in) creates new closed
   `pathItem`s in each cut layer with `filled = true; fillColor = black`,
   then `saveAs <src> POCHE.<ext>`.

Per-layer strategy can be overridden via a JSON file:

    {
      "TEC_FOUNDATION":          {"strategy": "bbox"},
      "TEC_CONCRETE_BASE":       {"strategy": "concave_hull", "ratio": 0.4},
      "23_WINDOW_FRAMES_REMAP_*": {"strategy": "skip"}
    }
"""
from __future__ import annotations

import json
import os
import subprocess
import textwrap
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Literal

from shapely import concave_hull, segmentize
from shapely.geometry import LineString, MultiLineString, MultiPoint, Polygon, box
from shapely.ops import linemerge, polygonize, snap, unary_union

from shapely.geometry import Polygon as _ShPolygon

from .apply_jsx import ILLUSTRATOR_APP
from .hatch import hatch_polygon, material_for_layer

POCHE_CLOSE_LAYER = "__POCHE_CLOSE__"
TOLERANCE_SWEEP = (0.0, 0.1, 0.5, 1.0, 2.0, 5.0)  # 0 = bare linemerge, no snap


# ---------------------------------------------------------------------------- #
# Per-fill result metadata
# ---------------------------------------------------------------------------- #

Strategy = Literal[
    "linemerge_bare", "linemerge_snap", "concave_hull", "bbox",
    "user_override", "skipped", "failed",
]


@dataclass
class FillResult:
    layer: str
    strategy: Strategy
    confidence: float
    polygon_count: int
    segment_count: int
    tolerance: float | None = None


@dataclass
class PocheReport:
    fills: list[FillResult] = field(default_factory=list)
    polygons: dict[str, list[list[list[float]]]] = field(default_factory=dict)

    @property
    def total_polygons(self) -> int:
        return sum(f.polygon_count for f in self.fills)

    @property
    def working_layers(self) -> int:
        return sum(1 for f in self.fills if f.confidence >= 0.85)

    @property
    def imperfect_layers(self) -> int:
        return sum(1 for f in self.fills if 0 < f.confidence < 0.85)

    @property
    def failed_layers(self) -> int:
        return sum(1 for f in self.fills if f.confidence == 0)


# ---------------------------------------------------------------------------- #
# Polygonize
# ---------------------------------------------------------------------------- #

def _lines_from_anchors(paths: list[list[list[float]]]) -> list[LineString]:
    out = []
    for pts in paths:
        if len(pts) >= 2:
            try:
                out.append(LineString([(p[0], p[1]) for p in pts]))
            except Exception:
                pass
    return out


def _polys_at_tolerance(lines: list[LineString], tol: float) -> list[Polygon]:
    if not lines:
        return []
    if tol > 0:
        all_geom = unary_union(lines)
        snapped = [snap(ls, all_geom, tol) for ls in lines]
    else:
        snapped = lines
    mls = MultiLineString(snapped)
    merged = linemerge(mls)
    if isinstance(merged, LineString):
        merged_lines = [merged]
    else:
        try:
            merged_lines = list(merged.geoms)
        except AttributeError:
            merged_lines = [merged]
    return list(polygonize(merged_lines))


def _try_concave_hull(lines: list[LineString], ratio: float = 0.3) -> Polygon | None:
    densified = []
    for ls in lines:
        try:
            densified.append(segmentize(ls, max_segment_length=2.0))
        except Exception:
            densified.append(ls)
    pts: list[tuple[float, float]] = []
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


def _bbox(lines: list[LineString]) -> Polygon | None:
    if not lines:
        return None
    mls = MultiLineString(lines)
    minx, miny, maxx, maxy = mls.bounds
    if maxx - minx < 1 or maxy - miny < 1:
        return None
    return box(minx, miny, maxx, maxy)


def polygonize_layer(
    layer_name: str,
    paths: list[list[list[float]]],
    closing_lines: list[LineString] | None = None,
    override: dict | None = None,
) -> tuple[list[Polygon], FillResult]:
    """Best-effort polygonization of one layer's segments."""
    lines = _lines_from_anchors(paths)
    if closing_lines:
        lines = lines + closing_lines
    n_segments = len(lines)

    if not lines:
        return [], FillResult(layer_name, "failed", 0.0, 0, 0)

    # User override
    if override:
        strat = override.get("strategy", "")
        if strat == "skip":
            return [], FillResult(layer_name, "skipped", 0.0, 0, n_segments)
        if strat == "bbox":
            bb = _bbox(lines)
            if bb is not None:
                return [bb], FillResult(layer_name, "user_override", 0.8, 1, n_segments)
        if strat == "concave_hull":
            ratio = float(override.get("ratio", 0.3))
            ch = _try_concave_hull(lines, ratio)
            if ch is not None:
                return [ch], FillResult(layer_name, "user_override", 0.8, 1, n_segments)

    # Sweep tolerances, pick best (most polygons)
    best: tuple[list[Polygon], float] = ([], 0.0)
    for tol in TOLERANCE_SWEEP:
        polys = _polys_at_tolerance(lines, tol)
        if len(polys) > len(best[0]):
            best = (polys, tol)

    if best[0]:
        polys, tol = best
        if tol == 0:
            return polys, FillResult(layer_name, "linemerge_bare", 1.0, len(polys), n_segments, tol)
        conf = 0.95 if tol <= 0.5 else (0.85 if tol <= 1.0 else 0.7)
        return polys, FillResult(layer_name, "linemerge_snap", conf, len(polys), n_segments, tol)

    # Concave hull fallback
    ch = _try_concave_hull(lines, ratio=0.3)
    if ch is not None:
        return [ch], FillResult(layer_name, "concave_hull", 0.55, 1, n_segments)

    # Bbox last
    bb = _bbox(lines)
    if bb is not None:
        return [bb], FillResult(layer_name, "bbox", 0.3, 1, n_segments)

    return [], FillResult(layer_name, "failed", 0.0, 0, n_segments)


def polygonize_dump(
    geometry_json_path: str,
    overrides: dict[str, dict] | None = None,
) -> PocheReport:
    """Load a JSON dump from `dump_cut_geometry.jsx`, polygonize each layer."""
    with open(geometry_json_path) as f:
        data = json.load(f)

    closing_lines: list[LineString] = []
    closing_layer_data = None
    for k in list(data.keys()):
        if POCHE_CLOSE_LAYER in k:
            closing_layer_data = data.pop(k)
            break
    if closing_layer_data:
        closing_lines = _lines_from_anchors(closing_layer_data)

    overrides = overrides or {}
    report = PocheReport()
    for layer_name, paths in data.items():
        # Match override: exact layer name or fnmatch-style suffix
        ov = overrides.get(layer_name)
        if ov is None:
            for pattern, val in overrides.items():
                if pattern.endswith("*") and layer_name.endswith(pattern[:-1].split("::")[-1]):
                    ov = val
                    break

        polys, result = polygonize_layer(layer_name, paths, closing_lines, ov)
        report.fills.append(result)
        if polys:
            report.polygons[layer_name] = [
                [[round(x, 4), round(y, 4)] for x, y in p.exterior.coords]
                for p in polys
            ]
    return report


# ---------------------------------------------------------------------------- #
# JSX dump + apply
# ---------------------------------------------------------------------------- #

DUMP_JSX_TEMPLATE = r'''#target illustrator

(function () {
    var TARGET = "__TARGET__";
    var OUT = "__OUT__";

    function jsonEscape(s) {
        s = String(s); var out = '"';
        for (var i = 0; i < s.length; i++) {
            var c = s.charAt(i), code = s.charCodeAt(i);
            if (c === '\\') out += '\\\\';
            else if (c === '"') out += '\\"';
            else if (c === '\n') out += '\\n';
            else if (c === '\r') out += '\\r';
            else if (code < 0x20) out += '\\u' + ('0000' + code.toString(16)).slice(-4);
            else out += c;
        }
        return out + '"';
    }

    function shouldDump(name) {
        var n = String(name).toUpperCase();
        if (n.indexOf("__POCHE_CLOSE__") !== -1) return true;
        if (n.indexOf("CLIPPINGPLANEINTERSECTIONS") === -1) return false;
        if (n.indexOf("GLASS") !== -1 || n.indexOf("IGU") !== -1) return false;
        return true;
    }

    var doc = null;
    for (var di = 0; di < app.documents.length; di++) {
        try { if (app.documents[di].fullName.fsName === TARGET) { doc = app.documents[di]; break; } } catch (e) {}
    }
    if (!doc) { return; }

    var leaves = [];
    function visit(layer, prefix) {
        var fullName = prefix ? (prefix + "::" + layer.name) : layer.name;
        if (layer.layers.length > 0) {
            for (var s = 0; s < layer.layers.length; s++) visit(layer.layers[s], fullName);
        } else {
            leaves.push({layer: layer, fullName: fullName});
        }
    }
    for (var L = 0; L < doc.layers.length; L++) visit(doc.layers[L], "");

    var json = "{"; var first = true;
    for (var i = 0; i < leaves.length; i++) {
        var meta = leaves[i];
        if (!shouldDump(meta.fullName)) continue;
        if (!first) json += ","; first = false;
        json += "\n  " + jsonEscape(meta.fullName) + ": [";
        var paths = meta.layer.pathItems;
        for (var p = 0; p < paths.length; p++) {
            var pi = paths[p];
            var pts = pi.pathPoints;
            var pathArr = "[";
            for (var pp = 0; pp < pts.length; pp++) {
                if (pp > 0) pathArr += ",";
                var a = pts[pp].anchor;
                pathArr += "[" + a[0].toFixed(4) + "," + a[1].toFixed(4) + "]";
            }
            pathArr += "]";
            if (p > 0) json += ",";
            json += "\n    " + pathArr;
        }
        json += "\n  ]";
    }
    json += "\n}";

    var f = new File(OUT); f.encoding = "UTF-8"; f.open("w"); f.write(json); f.close();
})();
'''


APPLY_JSX_TEMPLATE = r'''#target illustrator

(function () {
    var TARGET = "__TARGET__";
    var OUTPUT = "__OUTPUT__";
    var REPORT = "__REPORT__";

    try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch (e) {}

    function writeFile(p, s) { var f = new File(p); f.encoding = "UTF-8"; f.open("w"); f.write(s); f.close(); }

__POLYGONS_BAKED__

    var doc = null;
    for (var di = 0; di < app.documents.length; di++) {
        try { if (app.documents[di].fullName.fsName === TARGET) { doc = app.documents[di]; break; } } catch (e) {}
    }
    if (!doc) { writeFile(REPORT, "ERROR: target doc not open: " + TARGET); return; }
    if (app.activeDocument !== doc) app.activeDocument = doc;

    var BLACK = new RGBColor(); BLACK.red = 0; BLACK.green = 0; BLACK.blue = 0;

    var layerByName = {};
    function visit(layer, prefix) {
        var fullName = prefix ? (prefix + "::" + layer.name) : layer.name;
        layerByName[fullName] = layer;
        for (var s = 0; s < layer.layers.length; s++) visit(layer.layers[s], fullName);
    }
    for (var L = 0; L < doc.layers.length; L++) visit(doc.layers[L], "");

    var totalCreated = 0;
    var totalHatch = 0;
    var perLayer = [];
    for (var name in POLYGONS) {
        var lyr = layerByName[name];
        if (!lyr) { perLayer.push(name + " :: NO MATCHING LAYER"); continue; }
        var polys = POLYGONS[name];
        var created = 0;
        for (var pi = 0; pi < polys.length; pi++) {
            try {
                var coords = polys[pi];
                if (coords.length < 3) continue;
                var pts = coords;
                if (pts.length > 2 && pts[0][0] === pts[pts.length-1][0] && pts[0][1] === pts[pts.length-1][1]) {
                    pts = pts.slice(0, pts.length - 1);
                }
                var newPath = lyr.pathItems.add();
                newPath.setEntirePath(pts);
                newPath.closed = true;
                newPath.filled = true;
                newPath.fillColor = BLACK;
                newPath.stroked = false;
                created++;
            } catch (e) {}
        }
        totalCreated += created;
        // hatch lines on top of fill
        var hatchCount = 0;
        if (typeof HATCH !== "undefined" && HATCH[name]) {
            var hlines = HATCH[name];
            for (var hi = 0; hi < hlines.length; hi++) {
                try {
                    var hpts = hlines[hi];
                    if (hpts.length < 2) continue;
                    var hpath = lyr.pathItems.add();
                    hpath.setEntirePath(hpts);
                    hpath.closed = false;
                    hpath.filled = false;
                    hpath.stroked = true;
                    hpath.strokeColor = BLACK;
                    hpath.strokeWidth = 0.13;
                    hatchCount++;
                } catch (e) {}
            }
            totalHatch += hatchCount;
        }
        perLayer.push(name.split("::").pop() + "  +" + created + " polys" + (hatchCount > 0 ? " +" + hatchCount + " hatch" : ""));
    }

    var saveFile = new File(OUTPUT);
    var saveOpts = new IllustratorSaveOptions();
    saveOpts.pdfCompatible = true;
    doc.saveAs(saveFile, saveOpts);

    var rep = "POCHE DONE\nnew filled polys created: " + totalCreated + "\nhatch lines created: " + totalHatch + "\nper layer:\n";
    for (var i = 0; i < perLayer.length; i++) rep += "  " + perLayer[i] + "\n";
    rep += "saved as: " + OUTPUT + "\n";
    writeFile(REPORT, rep);
})();
'''


def _bake_polygons_jsx(polygons: dict) -> str:
    """Convert polygon dict to a JSX-compatible JS object literal."""
    def js_str(s: str) -> str:
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    parts = ["var POLYGONS = {"]
    items = list(polygons.items())
    for i, (layer_name, polys) in enumerate(items):
        sep = "," if i < len(items) - 1 else ""
        poly_strs = []
        for poly in polys:
            coord_strs = [f"[{x:g},{y:g}]" for x, y in poly]
            poly_strs.append("[" + ",".join(coord_strs) + "]")
        parts.append(f"  {js_str(layer_name)}: [" + ",".join(poly_strs) + f"]{sep}")
    parts.append("};")
    return "\n".join(parts)


def render_dump_jsx(target: str, out_json: str) -> str:
    return (DUMP_JSX_TEMPLATE
            .replace("__TARGET__", target)
            .replace("__OUT__", out_json))


def _bake_hatch_jsx(hatch_geometry: dict) -> str:
    """Convert hatch-line dict to a JSX-compatible JS object literal."""
    def js_str(s: str) -> str:
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    parts = ["var HATCH = {"]
    items = list(hatch_geometry.items())
    for i, (layer_name, lines) in enumerate(items):
        sep = "," if i < len(items) - 1 else ""
        line_strs = []
        for pts in lines:
            coord_strs = [f"[{x:g},{y:g}]" for x, y in pts]
            line_strs.append("[" + ",".join(coord_strs) + "]")
        parts.append(f"  {js_str(layer_name)}: [" + ",".join(line_strs) + f"]{sep}")
    parts.append("};")
    return "\n".join(parts)


def render_apply_jsx(target: str, output: str, report_path: str, polygons: dict, hatch_geometry: dict | None = None) -> str:
    baked = textwrap.indent(_bake_polygons_jsx(polygons), "    ")
    hatch_baked = textwrap.indent(_bake_hatch_jsx(hatch_geometry or {}), "    ")
    full_baked = baked + "\n\n" + hatch_baked
    return (APPLY_JSX_TEMPLATE
            .replace("__TARGET__", target)
            .replace("__OUTPUT__", output)
            .replace("__REPORT__", report_path)
            .replace("__POLYGONS_BAKED__", full_baked))


def _osascript_run_jsx(jsx_path: str, timeout: int = 1800) -> None:
    applescript = f'''with timeout of {timeout} seconds
        tell application "Adobe Illustrator"
            do javascript (read POSIX file "{jsx_path}" as «class utf8»)
        end tell
    end timeout'''
    subprocess.run(["osascript", "-e", applescript], check=True, timeout=timeout + 60)


def _osascript_open(path: str, timeout: int = 1800) -> None:
    applescript = f'''with timeout of {timeout} seconds
        tell application "Adobe Illustrator"
            activate
            try
                close every document saving no
            end try
            open POSIX file "{path}"
        end tell
    end timeout'''
    subprocess.run(["osascript", "-e", applescript], check=True, timeout=timeout + 60)


def _hatch_lines_for_layer(layer_name: str, polygons: list[list[list[float]]], scale: float) -> list[list[list[float]]]:
    """For each polygon in `polygons`, generate material-specific hatch lines.

    Returns a list of polylines (each polyline = list of [x,y] pairs).
    Used by `--style material` to add hatch geometry on top of the solid fill.
    """
    material = material_for_layer(layer_name)
    out_lines: list[list[list[float]]] = []
    for poly_coords in polygons:
        if len(poly_coords) < 3:
            continue
        poly = _ShPolygon(poly_coords)
        if not poly.is_valid or poly.is_empty:
            continue
        lines = hatch_polygon(poly, material, scale)
        for ls in lines:
            try:
                out_lines.append([[round(x, 4), round(y, 4)] for x, y in ls.coords])
            except Exception:
                continue
    return out_lines


def apply_poche(
    src: str,
    dst: str | None = None,
    *,
    overrides_path: str | None = None,
    style: str = "solid",
    scale: float = 1 / 50,
    workdir: str = "/tmp",
) -> PocheReport:
    """Run the full poché pipeline on `src`, save to `dst`.

    style:
        "solid"    — every cut polygon filled solid black (default; v0.4 behavior)
        "material" — also generate per-material hatch geometry (concrete diagonal,
                     CLT cross-grain, etc.) layered on top of the solid fills.
                     Uses `arch_line_weights.hatch.material_for_layer` to choose.
    scale:
        Plot scale as a fraction (1/50, 1/100). Used only when style="material".
    """
    src = os.path.abspath(src)
    if dst is None:
        p = Path(src)
        dst = str(p.with_name(f"{p.stem.replace(' HIERARCHY', '')} POCHE{p.suffix}"))
    dst = os.path.abspath(dst)
    if dst == src:
        raise ValueError("dst must differ from src")

    overrides = {}
    if overrides_path:
        with open(overrides_path) as f:
            overrides = json.load(f)

    geom_json = os.path.join(workdir, "arch_lw_cut_geometry.json")
    dump_jsx = os.path.join(workdir, "arch_lw_dump.jsx")
    apply_jsx = os.path.join(workdir, "arch_lw_apply_poche.jsx")
    report_txt = os.path.join(workdir, "arch_lw_poche_report.txt")

    for f in (geom_json, dump_jsx, apply_jsx, report_txt):
        try:
            os.unlink(f)
        except FileNotFoundError:
            pass

    # 1. Open source clean
    _osascript_open(src)
    time.sleep(2)

    # 2. Dump geometry
    Path(dump_jsx).write_text(render_dump_jsx(src, geom_json))
    _osascript_run_jsx(dump_jsx)
    if not os.path.exists(geom_json):
        raise RuntimeError(f"dump JSX produced no geometry at {geom_json}")

    # 3. Polygonize
    report = polygonize_dump(geom_json, overrides)

    # 4a. Optional: generate per-material hatch geometry on top of the fills
    hatch_geometry: dict[str, list[list[list[float]]]] = {}
    if style == "material" and report.polygons:
        for layer_name, polys in report.polygons.items():
            hatch_lines = _hatch_lines_for_layer(layer_name, polys, scale)
            if hatch_lines:
                hatch_geometry[layer_name] = hatch_lines

    # 4b. Build apply JSX
    Path(apply_jsx).write_text(render_apply_jsx(src, dst, report_txt, report.polygons, hatch_geometry))

    # 5. Apply
    _osascript_run_jsx(apply_jsx)
    if not os.path.exists(report_txt):
        raise RuntimeError(f"apply JSX produced no report at {report_txt}")

    return report
