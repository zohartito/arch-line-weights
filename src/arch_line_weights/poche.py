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

import contextlib
import json
import logging
import os
import subprocess
import textwrap
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from shapely import concave_hull, segmentize
from shapely.geometry import LineString, MultiLineString, MultiPoint, Polygon, box
from shapely.geometry import Polygon as _ShPolygon
from shapely.ops import linemerge, polygonize, snap, unary_union

from .bridge import infer_bridges, infer_bridges_best
from .hatch import hatch_polygon, material_for_layer

_log = logging.getLogger(__name__)

POCHE_CLOSE_LAYER = "__POCHE_CLOSE__"
TOLERANCE_SWEEP = (0.0, 0.1, 0.5, 1.0, 2.0, 5.0)  # 0 = bare linemerge, no snap

# Bridge strategy selector — controlled by the ``bridge_strategy`` argument
# or the ``ARCH_LW_BRIDGE_STRATEGY`` environment variable. Default is
# ``"best"`` as of v0.6.7: routes through :func:`bridge.infer_bridges_best`
# which picks the best of 4 strategies (greedy, backtracking, DBSCAN
# endpoint collapse, DBSCAN+backtrack). ``"greedy"`` is preserved for
# backwards compatibility with v0.5.x and is reachable via explicit
# ``bridge_strategy="greedy"`` or ``ARCH_LW_BRIDGE_STRATEGY=greedy``. See
# ``docs/research/bridge-strategy-wire-notes.md`` for the wiring rationale
# and the v0.6.7 default-flip rationale, and
# ``docs/research/stubborn-layers-deep-dive.md`` for the strategy ladder.
BridgeStrategy = Literal["greedy", "best"]
_VALID_BRIDGE_STRATEGIES: tuple[str, ...] = ("greedy", "best")
_DEFAULT_BRIDGE_STRATEGY: BridgeStrategy = "best"
_BRIDGE_STRATEGY_ENV = "ARCH_LW_BRIDGE_STRATEGY"
_BRIDGE_BEST_BUDGET_ENV = "ARCH_LW_BRIDGE_BEST_LAYER_BUDGET_SEC"
_BRIDGE_BEST_MAX_ENDPOINTS_ENV = "ARCH_LW_BRIDGE_BEST_MAX_ENDPOINTS"
_POCHE_MIN_INJECT_CONFIDENCE_ENV = "ARCH_LW_POCHE_MIN_INJECT_CONFIDENCE"
_POCHE_ALLOW_LOW_CONFIDENCE_ENV = "ARCH_LW_POCHE_ALLOW_LOW_CONFIDENCE"
_DEFAULT_BRIDGE_BEST_BUDGET_SEC = 60.0
_DEFAULT_BRIDGE_BEST_MAX_ENDPOINTS = 1000
_DEFAULT_POCHE_MIN_INJECT_CONFIDENCE = 0.85


def _resolve_bridge_strategy(explicit: str | None) -> BridgeStrategy:
    """Resolve the bridge strategy from an explicit argument or env var.

    Order of precedence: explicit argument > ``ARCH_LW_BRIDGE_STRATEGY`` env
    var > default (``"best"``). Unknown values silently fall back to the
    default — this is a runtime tuning knob and a typo shouldn't break the
    pipeline.
    """
    candidate = explicit or os.environ.get(_BRIDGE_STRATEGY_ENV)
    if candidate is None:
        return _DEFAULT_BRIDGE_STRATEGY
    if candidate not in _VALID_BRIDGE_STRATEGIES:
        return _DEFAULT_BRIDGE_STRATEGY
    return candidate  # type: ignore[return-value]


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


# ---------------------------------------------------------------------------- #
# Per-fill result metadata
# ---------------------------------------------------------------------------- #

Strategy = Literal[
    "linemerge_bare",
    "linemerge_snap",
    "auto_bridge",
    "alpha_shape",
    "llm_topology",
    "concave_hull",
    "bbox",
    "user_override",
    "skipped",
    "failed",
]


@dataclass
class FillResult:
    layer: str
    strategy: Strategy
    confidence: float
    polygon_count: int
    segment_count: int
    tolerance: float | None = None
    # Set by the auto_bridge rung when ``bridge_strategy="best"`` is in
    # effect — names the inner strategy that ``infer_bridges_best`` picked
    # ("greedy", "backtrack", "dbscan_collapse", "dbscan_collapse+backtrack",
    # or "none"). ``None`` for the default greedy path so reports for
    # pre-existing runs are unchanged.
    bridge_strategy_name: str | None = None


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

    @property
    def injected_polygons(self) -> int:
        return sum(len(polys) for polys in self.polygons.values())


def should_inject_fill(result: FillResult) -> bool:
    """Return True when a polygonize result is trustworthy enough to draw.

    Low-confidence rescue geometry (alpha-shape, concave hull, bbox, LLM) is
    useful diagnostic information, but painting it solid black can create
    visually convincing false poché. Default to conservative output; users
    can still opt into the old behavior with ARCH_LW_POCHE_ALLOW_LOW_CONFIDENCE=1.
    """
    if result.strategy in {"failed", "skipped"} or result.polygon_count <= 0:
        return False
    if result.strategy == "user_override":
        return True
    if os.environ.get(_POCHE_ALLOW_LOW_CONFIDENCE_ENV) == "1":
        return True
    min_conf = _env_float(
        _POCHE_MIN_INJECT_CONFIDENCE_ENV,
        _DEFAULT_POCHE_MIN_INJECT_CONFIDENCE,
    )
    return result.confidence >= min_conf


# ---------------------------------------------------------------------------- #
# Polygonize
# ---------------------------------------------------------------------------- #


def _lines_from_anchors(paths: list[list[list[float]]]) -> list[LineString]:
    out = []
    for pts in paths:
        if len(pts) >= 2:
            with contextlib.suppress(Exception):
                out.append(LineString([(p[0], p[1]) for p in pts]))
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


def _try_alpha_shape(lines: list[LineString]) -> list[Polygon]:
    """Run the alpha-shape rescue over the densified endpoint cloud.

    Returns ``[]`` on any failure. Densification matches what the concave
    hull rung does — sparse Make2D output points produce a degenerate
    α-shape just like they produce a degenerate concave hull, so we
    segmentize first to feed enough vertices to scipy's Delaunay.
    """
    from .alpha_shape import alpha_shape_all_regions

    densified = []
    for ls in lines:
        try:
            densified.append(segmentize(ls, max_segment_length=2.0))
        except Exception:
            densified.append(ls)
    pts: list[tuple[float, float]] = []
    for ls in densified:
        pts.extend((float(x), float(y)) for x, y in ls.coords)
    if len(pts) < 3:
        return []
    polys, _alpha, _n = alpha_shape_all_regions(pts)
    return [p for p in polys if p.is_valid and p.area > 1.0]


def polygonize_layer(
    layer_name: str,
    paths: list[list[list[float]]],
    closing_lines: list[LineString] | None = None,
    override: dict | None = None,
    *,
    use_alpha_shape: bool = True,
    bridge_strategy: str | None = None,
) -> tuple[list[Polygon], FillResult]:
    """Best-effort polygonization of one layer's segments.

    Parameters
    ----------
    layer_name, paths, closing_lines, override
        See module docstring.
    use_alpha_shape : bool, default True
        When True, the alpha-shape rung runs between auto_bridge and
        concave_hull (v0.5.2 behavior). When False, that rung is skipped
        and the rescue ladder matches v0.5.1 exactly.
    bridge_strategy : str | None, default None
        Selector for the auto-bridge rung. ``"best"`` (the default if
        unset, since v0.6.7) calls :func:`bridge.infer_bridges_best` which
        picks the highest-yield among 4 strategies (greedy, backtrack,
        DBSCAN endpoint collapse, DBSCAN+backtrack). ``"greedy"`` calls
        :func:`bridge.infer_bridges` (the v0.4 nearest-neighbour bridger)
        and is preserved for backwards compatibility. When ``None``, the
        env var ``ARCH_LW_BRIDGE_STRATEGY`` is consulted; if that is also
        unset, the default ``"best"`` applies. Unknown values silently fall
        back to ``"best"``.
    """
    strategy = _resolve_bridge_strategy(bridge_strategy)
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

    # Auto-bridge: infer missing connecting segments and re-run
    # linemerge+polygonize. Default strategy (v0.6.7+) is ``"best"``, which
    # dispatches to the 4-way strategy selector. ``"greedy"`` retains the
    # v0.4 nearest-neighbour bridger for backwards compatibility.
    #
    # Note on the polygonization gate: greedy only adds bridges
    # (``len(augmented) > len(lines)``). The "best" selector includes
    # ``dbscan_collapse``, which mutates endpoints *in place* without adding
    # segments, so the length stays the same. We still want to polygonize
    # the collapsed segments — the gate has to allow the equal-length case
    # for "best".
    try:
        if strategy == "best":
            endpoint_count = 2 * len(lines)
            max_endpoints = _env_int(
                _BRIDGE_BEST_MAX_ENDPOINTS_ENV,
                _DEFAULT_BRIDGE_BEST_MAX_ENDPOINTS,
            )
            budget_sec = _env_float(
                _BRIDGE_BEST_BUDGET_ENV,
                _DEFAULT_BRIDGE_BEST_BUDGET_SEC,
            )
            if endpoint_count > max_endpoints:
                _log.warning(
                    "poche layer %r has %d endpoints, above %s=%d; "
                    "using greedy bridge strategy for this layer",
                    layer_name,
                    endpoint_count,
                    _BRIDGE_BEST_MAX_ENDPOINTS_ENV,
                    max_endpoints,
                )
                aug_best, bridge_conf = infer_bridges(lines, max_gap=50.0, min_gap=0.01)
                strategy_name = "greedy_endpoint_cap"
            else:
                aug_best, bridge_conf, strategy_name = infer_bridges_best(
                    lines,
                    max_gap=50.0,
                    min_gap=0.01,
                    time_budget_sec=budget_sec,
                    layer_name=layer_name,
                )
            augmented = aug_best
            # "best" returns a usable augmented set (possibly the same
            # length as the input if dbscan_collapse won) — always try
            # polygonization on it.
            should_polygonize = bool(augmented)
        else:
            augmented, bridge_conf = infer_bridges(lines, max_gap=50.0, min_gap=0.01)
            strategy_name = None
            # Greedy: only bridges (never collapses), so length increase is
            # the right gate (preserves v0.5.x bit-exact behaviour).
            should_polygonize = len(augmented) > len(lines)
        if should_polygonize:
            polys_with_bridges = _polys_at_tolerance(augmented, 0.0)
            if polys_with_bridges:
                return polys_with_bridges, FillResult(
                    layer_name,
                    "auto_bridge",
                    0.75 * bridge_conf + 0.25,
                    len(polys_with_bridges),
                    n_segments,
                    bridge_strategy_name=strategy_name,
                )
    except Exception:
        pass

    # Alpha-shape: better-than-concave_hull fallback that preserves multi-
    # component topology (e.g. two roof caps with an intentional gap).
    # Opt-out via use_alpha_shape=False to match v0.5.1 behavior.
    if use_alpha_shape:
        try:
            alpha_polys = _try_alpha_shape(lines)
            if alpha_polys:
                return alpha_polys, FillResult(
                    layer_name, "alpha_shape", 0.55, len(alpha_polys), n_segments
                )
        except Exception:
            pass

    # LLM topology inference (rung 5): opt-in via ARCH_LW_LLM_FALLBACK=1 +
    # an Anthropic API key. Hands the layer name + raw endpoint
    # coordinates (no filenames, no metadata) to a small LLM and asks for
    # a closure plan. Default OFF — the rung returns None when the gate
    # is closed, the SDK is missing, the API key is missing, the network
    # call fails, or the response fails schema validation. See
    # ``llm_topology.py`` and
    # ``docs/research/llm-topology-impl-notes.md``.
    try:
        from .llm_topology import bridges_from_plan, infer_closing_plan

        anchors_flat: list[tuple[float, float]] = []
        for ls in lines:
            try:
                anchors_flat.extend((float(x), float(y)) for x, y in ls.coords)
            except Exception:
                continue
        plan = infer_closing_plan(layer_name, anchors_flat, lines)
        if plan is not None:
            llm_bridges = bridges_from_plan(plan, anchors_flat)
            if llm_bridges:
                augmented_llm = lines + llm_bridges
                polys_llm = _polys_at_tolerance(augmented_llm, 0.0)
                if polys_llm:
                    return polys_llm, FillResult(
                        layer_name, "llm_topology", 0.65, len(polys_llm), n_segments
                    )
    except Exception:
        pass

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
    *,
    use_alpha_shape: bool = True,
    bridge_strategy: str | None = None,
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

        polys, result = polygonize_layer(
            layer_name,
            paths,
            closing_lines,
            ov,
            use_alpha_shape=use_alpha_shape,
            bridge_strategy=bridge_strategy,
        )
        report.fills.append(result)
        if polys and should_inject_fill(result):
            report.polygons[layer_name] = [
                [[round(x, 4), round(y, 4)] for x, y in p.exterior.coords] for p in polys
            ]
    return report


# ---------------------------------------------------------------------------- #
# JSX dump + apply
# ---------------------------------------------------------------------------- #

DUMP_JSX_TEMPLATE = r"""#target illustrator

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
"""


APPLY_JSX_TEMPLATE = r"""#target illustrator

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
"""


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
    return DUMP_JSX_TEMPLATE.replace("__TARGET__", target).replace("__OUT__", out_json)


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


def render_apply_jsx(
    target: str, output: str, report_path: str, polygons: dict, hatch_geometry: dict | None = None
) -> str:
    baked = textwrap.indent(_bake_polygons_jsx(polygons), "    ")
    hatch_baked = textwrap.indent(_bake_hatch_jsx(hatch_geometry or {}), "    ")
    full_baked = baked + "\n\n" + hatch_baked
    return (
        APPLY_JSX_TEMPLATE.replace("__TARGET__", target)
        .replace("__OUTPUT__", output)
        .replace("__REPORT__", report_path)
        .replace("__POLYGONS_BAKED__", full_baked)
    )


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


def _hatch_lines_for_layer(
    layer_name: str, polygons: list[list[list[float]]], scale: float
) -> list[list[list[float]]]:
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
    use_alpha_shape: bool = True,
    bridge_strategy: str | None = None,
) -> PocheReport:
    """Run the full poché pipeline on `src`, save to `dst`.

    style:
        "solid"    — every cut polygon filled solid black (default; v0.4 behavior)
        "material" — also generate per-material hatch geometry (concrete diagonal,
                     CLT cross-grain, etc.) layered on top of the solid fills.
                     Uses `arch_line_weights.hatch.material_for_layer` to choose.
    scale:
        Plot scale as a fraction (1/50, 1/100). Used only when style="material".
    use_alpha_shape:
        When True (v0.5.2 default), the alpha-shape rung sits between
        auto_bridge and concave_hull in the rescue ladder. When False,
        the ladder reverts to v0.5.1 behavior.
    bridge_strategy:
        ``"best"`` (default if unset since v0.6.7) | ``"greedy"``. Controls
        which bridger the auto_bridge rung uses; ``"best"`` runs the 4-way
        strategy selector (greedy, backtrack, DBSCAN, DBSCAN+backtrack) and
        picks the highest yield. ``"greedy"`` preserves the v0.4 nearest-
        neighbour bridger for backwards compatibility. ``None`` consults
        ``ARCH_LW_BRIDGE_STRATEGY`` env var, then defaults.
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
        with contextlib.suppress(FileNotFoundError):
            os.unlink(f)

    # 1. Open source clean
    _osascript_open(src)
    time.sleep(2)

    # 2. Dump geometry
    Path(dump_jsx).write_text(render_dump_jsx(src, geom_json))
    _osascript_run_jsx(dump_jsx)
    if not os.path.exists(geom_json):
        raise RuntimeError(f"dump JSX produced no geometry at {geom_json}")

    # 3. Polygonize
    report = polygonize_dump(
        geom_json,
        overrides,
        use_alpha_shape=use_alpha_shape,
        bridge_strategy=bridge_strategy,
    )

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
