"""Material-specific architectural hatch generation.

Given a closed `shapely.Polygon`, return a list of `LineString` segments
that fill the polygon with the canonical hatch pattern for the named
material (concrete diagonal + stipple, CLT cross-grain, insulation zigzag,
etc.).

Usage:
    from arch_line_weights.hatch import hatch_polygon, MATERIALS, register_material
    from shapely.geometry import Polygon

    wall = Polygon([(0, 0), (1000, 0), (1000, 200), (0, 200)])
    lines = hatch_polygon(wall, material="concrete", scale=1/50)

The `lines` returned are in drawing-unit points (1 pt = 1/72 inch). The
caller is responsible for assigning stroke colors/weights and inserting
them into the Illustrator document via JSX or pikepdf.

Solid materials (`concrete_solid`, `clt_solid`, `steel_solid`) return an
empty list — the caller fills the polygon directly with `pathItem.filled`.

Add a custom material:

    from arch_line_weights.hatch import register_material, MaterialRecipe, parallel_hatch, mm_to_pt

    def hatch_my_material(poly, scale, **_):
        return parallel_hatch(poly, mm_to_pt(0.7, scale), 30.0)

    register_material(MaterialRecipe("my_material", hatch_my_material, solid=False))
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Callable, Iterable

import numpy as np
from shapely.affinity import rotate, translate
from shapely.geometry import LineString, MultiLineString, MultiPolygon, Point, Polygon
from shapely.ops import unary_union

PT_PER_MM = 2.83464567


def mm_to_pt(mm: float, scale: float) -> float:
    """Convert real-world millimeters to drawing-unit PostScript points.

    Polygon coords are in pt at 1:1 (full-size). At plot scale 1/50, a 2 mm
    hatch spacing becomes `2 * (1/50) * 2.835 = 0.1134 pt` in drawing units.
    """
    return mm * scale * PT_PER_MM


# --------------------------------------------------------------------------- #
# Geometry helpers
# --------------------------------------------------------------------------- #

def _principal_angle(polygon: Polygon) -> float:
    """Angle (degrees) of the polygon's longest side, for grain alignment."""
    rect = polygon.minimum_rotated_rectangle
    if not isinstance(rect, Polygon):
        return 0.0
    coords = list(rect.exterior.coords)
    edges = [(coords[i], coords[i + 1]) for i in range(len(coords) - 1)]
    longest = max(edges, key=lambda e: math.hypot(e[1][0] - e[0][0], e[1][1] - e[0][1]))
    dx = longest[1][0] - longest[0][0]
    dy = longest[1][1] - longest[0][1]
    return math.degrees(math.atan2(dy, dx))


def _poly_iter(geom) -> Iterable[Polygon]:
    """Yield individual Polygons from a Polygon or MultiPolygon."""
    if isinstance(geom, Polygon):
        yield geom
    elif isinstance(geom, MultiPolygon):
        yield from geom.geoms


def parallel_hatch(
    polygon: Polygon,
    spacing: float,
    angle_deg: float,
    offset_fn: Callable[[float], float] | None = None,
) -> list[LineString]:
    """Fill `polygon` with parallel lines spaced `spacing` apart, oriented at `angle_deg`.

    Algorithm:
        1. Rotate polygon by -angle_deg so target lines become horizontal
        2. Generate horizontal scanlines at `spacing` interval covering bounds
        3. Intersect each scanline with the polygon
        4. Rotate result back by +angle_deg
    """
    if polygon.is_empty or polygon.area <= 0:
        return []
    cx, cy = polygon.centroid.x, polygon.centroid.y
    rotated = rotate(polygon, -angle_deg, origin=(cx, cy))
    minx, miny, maxx, maxy = rotated.bounds
    span_x = (maxx - minx) * 1.4  # padding for rotation
    span_y = (maxy - miny) * 1.4
    midx, midy = (minx + maxx) / 2, (miny + maxy) / 2

    lines = []
    n_lines = int(span_y / spacing) + 2
    for i in range(-n_lines // 2, n_lines // 2 + 1):
        y = midy + i * spacing
        if offset_fn:
            dx = offset_fn(y)
            scan = LineString([(midx - span_x / 2 + dx, y), (midx + span_x / 2 + dx, y)])
        else:
            scan = LineString([(midx - span_x / 2, y), (midx + span_x / 2, y)])
        clipped = rotated.intersection(scan)
        if clipped.is_empty:
            continue
        if isinstance(clipped, LineString):
            lines.append(clipped)
        elif isinstance(clipped, MultiLineString):
            lines.extend(clipped.geoms)

    return [rotate(ls, angle_deg, origin=(cx, cy)) for ls in lines]


def crosshatch(polygon: Polygon, spacing: float, angle_deg: float, second_angle: float = None) -> list[LineString]:
    """Two passes of parallel_hatch at perpendicular (or specified) angles."""
    if second_angle is None:
        second_angle = angle_deg + 90.0
    return parallel_hatch(polygon, spacing, angle_deg) + parallel_hatch(polygon, spacing, second_angle)


# --------------------------------------------------------------------------- #
# Stipple & dots (Bridson Poisson-disk)
# --------------------------------------------------------------------------- #

def poisson_disk(polygon: Polygon, min_dist: float, k: int = 30, seed: int = 42, max_samples: int = 50_000) -> list[Point]:
    """Generate Poisson-disk samples inside `polygon` with min separation `min_dist`.

    `max_samples` caps the number of samples; if the polygon×min_dist would
    exceed it, `min_dist` is enlarged proportionally so the cap holds.
    """
    if polygon.is_empty or min_dist <= 0:
        return []
    minx, miny, maxx, maxy = polygon.bounds
    area = (maxx - minx) * (maxy - miny)
    # Estimated count using packing density 0.6
    est = int(0.6 * area / (min_dist ** 2))
    if est > max_samples:
        # Enlarge min_dist so that estimated count == max_samples
        min_dist = math.sqrt(0.6 * area / max_samples)
    cell_size = min_dist / math.sqrt(2)
    grid_w = int(math.ceil((maxx - minx) / cell_size)) + 1
    grid_h = int(math.ceil((maxy - miny) / cell_size)) + 1
    if grid_w * grid_h > 5_000_000:
        # Final guard: too many cells = grid takes too much memory
        return []
    grid = [[None] * grid_w for _ in range(grid_h)]

    rng = random.Random(seed)
    samples = []
    active = []

    def grid_xy(p):
        return int((p.x - minx) / cell_size), int((p.y - miny) / cell_size)

    def in_bounds(p):
        return polygon.contains(p)

    def far_enough(p):
        gx, gy = grid_xy(p)
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                nx, ny = gx + dx, gy + dy
                if 0 <= nx < grid_w and 0 <= ny < grid_h and grid[ny][nx] is not None:
                    if p.distance(grid[ny][nx]) < min_dist:
                        return False
        return True

    # Seed with a random point inside polygon (rejection sample)
    for _ in range(50):
        seed_x = rng.uniform(minx, maxx)
        seed_y = rng.uniform(miny, maxy)
        seed_pt = Point(seed_x, seed_y)
        if in_bounds(seed_pt):
            samples.append(seed_pt)
            active.append(seed_pt)
            gx, gy = grid_xy(seed_pt)
            grid[gy][gx] = seed_pt
            break

    while active and len(samples) < max_samples:
        idx = rng.randrange(len(active))
        center = active[idx]
        found = False
        for _ in range(k):
            angle = rng.uniform(0, 2 * math.pi)
            dist = rng.uniform(min_dist, 2 * min_dist)
            cand = Point(center.x + dist * math.cos(angle), center.y + dist * math.sin(angle))
            if in_bounds(cand) and far_enough(cand):
                samples.append(cand)
                active.append(cand)
                gx, gy = grid_xy(cand)
                grid[gy][gx] = cand
                found = True
                break
        if not found:
            active.pop(idx)

    return samples


def stipple_dots(polygon: Polygon, spacing: float, dot_size: float = 0.3) -> list[LineString]:
    """Tiny crosshair markers at Poisson-disk-spaced points (concrete-aggregate style)."""
    pts = poisson_disk(polygon, spacing)
    out = []
    h = dot_size / 2
    for p in pts:
        out.append(LineString([(p.x - h, p.y), (p.x + h, p.y)]))
        out.append(LineString([(p.x, p.y - h), (p.x, p.y + h)]))
    return out


def stipple_triangles(polygon: Polygon, spacing: float, size: float = 0.5) -> list[LineString]:
    """Tiny triangular stipple marks (alternative concrete pattern)."""
    pts = poisson_disk(polygon, spacing)
    out = []
    s = size / 2
    for p in pts:
        out.append(LineString([
            (p.x - s, p.y - s),
            (p.x + s, p.y - s),
            (p.x, p.y + s),
            (p.x - s, p.y - s),
        ]))
    return out


# --------------------------------------------------------------------------- #
# Specialty patterns
# --------------------------------------------------------------------------- #

def sine_zigzag(polygon: Polygon, wavelength: float, amplitude: float, row_spacing: float | None = None) -> list[LineString]:
    """Stack of sine-wave lines (mineral-wool insulation symbol)."""
    if polygon.is_empty:
        return []
    if row_spacing is None:
        row_spacing = wavelength
    angle = _principal_angle(polygon)
    cx, cy = polygon.centroid.x, polygon.centroid.y
    rotated = rotate(polygon, -angle, origin=(cx, cy))
    minx, miny, maxx, maxy = rotated.bounds
    span_x = maxx - minx

    n_samples = max(20, int(span_x / (wavelength / 8)))
    xs = np.linspace(minx, maxx, n_samples)
    rows = []
    n_rows = int((maxy - miny) / row_spacing) + 2
    for r in range(-1, n_rows):
        y_base = miny + r * row_spacing
        ys = y_base + amplitude * np.sin(2 * math.pi * xs / wavelength)
        line = LineString(list(zip(xs, ys)))
        clipped = rotated.intersection(line)
        if clipped.is_empty:
            continue
        if isinstance(clipped, LineString):
            rows.append(clipped)
        elif isinstance(clipped, MultiLineString):
            rows.extend(clipped.geoms)

    return [rotate(ls, angle, origin=(cx, cy)) for ls in rows]


def brick_pattern(polygon: Polygon, brick_w: float, brick_h: float) -> list[LineString]:
    """Stretcher bond brick pattern (alternating horizontal courses)."""
    if polygon.is_empty:
        return []
    angle = _principal_angle(polygon)
    cx, cy = polygon.centroid.x, polygon.centroid.y
    rotated = rotate(polygon, -angle, origin=(cx, cy))
    minx, miny, maxx, maxy = rotated.bounds

    lines = []
    # Horizontal mortar lines
    n_rows = int((maxy - miny) / brick_h) + 2
    for r in range(-1, n_rows):
        y = miny + r * brick_h
        lines.append(LineString([(minx - brick_w, y), (maxx + brick_w, y)]))

    # Vertical mortar lines, offset by half-brick on alternate courses
    n_cols = int((maxx - minx) / brick_w) + 2
    for r in range(-1, n_rows):
        y_top = miny + (r + 1) * brick_h
        y_bot = miny + r * brick_h
        offset = brick_w / 2 if r % 2 else 0
        for c in range(-1, n_cols):
            x = minx + c * brick_w + offset
            lines.append(LineString([(x, y_bot), (x, y_top)]))

    clipped_lines = []
    for ls in lines:
        c = rotated.intersection(ls)
        if c.is_empty:
            continue
        if isinstance(c, LineString):
            clipped_lines.append(c)
        elif isinstance(c, MultiLineString):
            clipped_lines.extend(c.geoms)

    return [rotate(ls, angle, origin=(cx, cy)) for ls in clipped_lines]


def clt_layers(polygon: Polygon, lamella_thickness: float) -> list[LineString]:
    """CLT cross-laminated timber: alternating-direction grain lines per lamella."""
    if polygon.is_empty:
        return []
    angle = _principal_angle(polygon)
    cx, cy = polygon.centroid.x, polygon.centroid.y
    rotated = rotate(polygon, -angle, origin=(cx, cy))
    minx, miny, maxx, maxy = rotated.bounds

    out = []
    n_lams = int((maxy - miny) / lamella_thickness) + 1
    for i in range(n_lams):
        y_top = miny + (i + 1) * lamella_thickness
        y_bot = miny + i * lamella_thickness
        strip = Polygon([
            (minx, y_bot), (maxx, y_bot),
            (maxx, y_top), (minx, y_top),
        ]).intersection(rotated)
        if strip.is_empty:
            continue
        for sub in _poly_iter(strip):
            grain_angle = 0.0 if i % 2 == 0 else 90.0
            grain_lines = parallel_hatch(sub, lamella_thickness * 0.4, grain_angle)
            out.extend(grain_lines)

    return [rotate(ls, angle, origin=(cx, cy)) for ls in out]


# --------------------------------------------------------------------------- #
# Material recipes
# --------------------------------------------------------------------------- #

@dataclass
class MaterialRecipe:
    name: str
    fn: Callable[..., list[LineString]]
    solid: bool = False  # True = caller fills polygon black; fn returns []
    description: str = ""


def hatch_concrete(polygon, scale, **kw):
    if isinstance(polygon, MultiPolygon):
        return sum((hatch_concrete(p, scale, **kw) for p in polygon.geoms), [])
    spacing = mm_to_pt(1.5, scale)
    dot_spacing = mm_to_pt(0.8, scale)
    dot_size = mm_to_pt(0.3, scale)
    return parallel_hatch(polygon, spacing, 45.0) + stipple_dots(polygon, dot_spacing, dot_size)


def hatch_concrete_solid(*a, **kw):
    return []


def hatch_clt_cross_grain(polygon, scale, lamella_mm: float = 25.0, **kw):
    if isinstance(polygon, MultiPolygon):
        return sum((hatch_clt_cross_grain(p, scale, lamella_mm=lamella_mm, **kw) for p in polygon.geoms), [])
    return clt_layers(polygon, mm_to_pt(lamella_mm, scale))


def hatch_clt_solid(*a, **kw):
    return []


def hatch_solid_timber(polygon, scale, **kw):
    if isinstance(polygon, MultiPolygon):
        return sum((hatch_solid_timber(p, scale, **kw) for p in polygon.geoms), [])
    angle = _principal_angle(polygon)
    spacing = mm_to_pt(0.9, scale)

    def grain_offset(y):
        return 0.4 * math.sin(y * 0.7) + 0.2 * math.sin(y * 2.3)

    return parallel_hatch(polygon, spacing, angle, offset_fn=grain_offset)


def hatch_steel_solid(*a, **kw):
    return []


def hatch_steel_hatch_45(polygon, scale, **kw):
    if isinstance(polygon, MultiPolygon):
        return sum((hatch_steel_hatch_45(p, scale, **kw) for p in polygon.geoms), [])
    return parallel_hatch(polygon, mm_to_pt(0.8, scale), 45.0)


def hatch_insulation_mineral_wool(polygon, scale, **kw):
    if isinstance(polygon, MultiPolygon):
        return sum((hatch_insulation_mineral_wool(p, scale, **kw) for p in polygon.geoms), [])
    return sine_zigzag(polygon, wavelength=mm_to_pt(2.0, scale), amplitude=mm_to_pt(1.5, scale))


def hatch_insulation_rigid(polygon, scale, **kw):
    if isinstance(polygon, MultiPolygon):
        return sum((hatch_insulation_rigid(p, scale, **kw) for p in polygon.geoms), [])
    return crosshatch(polygon, mm_to_pt(1.0, scale), 45.0, 135.0)


def hatch_earth(polygon, scale, **kw):
    if isinstance(polygon, MultiPolygon):
        return sum((hatch_earth(p, scale, **kw) for p in polygon.geoms), [])
    return stipple_dots(polygon, mm_to_pt(0.4, scale), dot_size=mm_to_pt(0.15, scale))


def hatch_brick(polygon, scale, **kw):
    if isinstance(polygon, MultiPolygon):
        return sum((hatch_brick(p, scale, **kw) for p in polygon.geoms), [])
    return brick_pattern(polygon, mm_to_pt(215.0, scale), mm_to_pt(65.0, scale))


def hatch_glass(polygon, scale, n_lines: int = 3, **kw):
    if isinstance(polygon, MultiPolygon):
        return sum((hatch_glass(p, scale, n_lines=n_lines, **kw) for p in polygon.geoms), [])
    angle = _principal_angle(polygon)
    spacing = mm_to_pt(1.0, scale)
    return parallel_hatch(polygon, spacing, angle)[:n_lines]


def hatch_gypsum(polygon, scale, **kw):
    if isinstance(polygon, MultiPolygon):
        return sum((hatch_gypsum(p, scale, **kw) for p in polygon.geoms), [])
    return stipple_dots(polygon, mm_to_pt(1.5, scale), dot_size=mm_to_pt(0.2, scale))


def hatch_aluminum(polygon, scale, **kw):
    if isinstance(polygon, MultiPolygon):
        return sum((hatch_aluminum(p, scale, **kw) for p in polygon.geoms), [])
    return parallel_hatch(polygon, mm_to_pt(0.8, scale), 45.0)


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #

MATERIALS: dict[str, MaterialRecipe] = {}


def register_material(recipe: MaterialRecipe) -> None:
    MATERIALS[recipe.name] = recipe


for recipe in [
    MaterialRecipe("concrete", hatch_concrete, description="Cast-in-place concrete: 45° hatch + stipple"),
    MaterialRecipe("concrete_solid", hatch_concrete_solid, solid=True, description="Solid black concrete (small-scale)"),
    MaterialRecipe("clt_cross_grain", hatch_clt_cross_grain, description="CLT alternating grain per lamella"),
    MaterialRecipe("clt_solid", hatch_clt_solid, solid=True, description="Solid black CLT"),
    MaterialRecipe("solid_timber", hatch_solid_timber, description="Solid timber with grain lines"),
    MaterialRecipe("steel_solid", hatch_steel_solid, solid=True, description="Solid black steel section"),
    MaterialRecipe("steel_hatch_45", hatch_steel_hatch_45, description="Steel 45° diagonal hatch"),
    MaterialRecipe("insulation_mineral_wool", hatch_insulation_mineral_wool, description="Mineral wool zigzag"),
    MaterialRecipe("insulation_rigid", hatch_insulation_rigid, description="Rigid XPS/PIR crosshatch"),
    MaterialRecipe("earth", hatch_earth, description="Dense stipple"),
    MaterialRecipe("brick", hatch_brick, description="Stretcher bond pattern"),
    MaterialRecipe("glass", hatch_glass, description="2-3 thin parallel rules"),
    MaterialRecipe("gypsum", hatch_gypsum, description="Light dotted stipple"),
    MaterialRecipe("aluminum", hatch_aluminum, description="Tighter 45° hatch"),
]:
    register_material(recipe)


def hatch_polygon(polygon: Polygon | MultiPolygon, material: str, scale: float, **kw) -> list[LineString]:
    """Dispatch to the named material's recipe."""
    if material not in MATERIALS:
        raise KeyError(f"unknown material {material!r}; available: {sorted(MATERIALS)}")
    recipe = MATERIALS[material]
    if recipe.solid:
        return []
    return recipe.fn(polygon, scale, **kw)


# --------------------------------------------------------------------------- #
# Layer-name → material mapping (for arch-lw poche --style material)
# --------------------------------------------------------------------------- #

# Substring-based: first match wins. Keep in sync with Rhino layer naming
# conventions documented in docs/research/poche-conventions.md.
LAYER_TO_MATERIAL: list[tuple[str, str]] = [
    ("CONCRETE",          "concrete_solid"),
    ("FOUNDATION",        "concrete_solid"),
    ("CLT",               "clt_solid"),
    ("TIMBER",            "solid_timber"),
    ("STEEL",             "steel_solid"),
    ("SHS",               "steel_solid"),
    ("RHS",               "steel_solid"),
    ("BRACKET",           "steel_solid"),
    ("CLEAT",             "steel_solid"),
    ("STAIR",             "concrete_solid"),
    ("WINDOW_FRAME",      "aluminum"),
    ("ALUM",              "aluminum"),
    ("CU_",               "concrete_solid"),  # copper cladding cut
    ("CLADDING",          "concrete_solid"),
    ("INSUL",             "insulation_mineral_wool"),
    ("XPS",               "insulation_rigid"),
    ("PIR",               "insulation_rigid"),
    ("MINERAL",           "insulation_mineral_wool"),
    ("EPDM",              "concrete_solid"),
    ("MEMBRANE",          "concrete_solid"),
    ("EARTH",             "earth"),
    ("GROUND",            "earth"),
    ("BRICK",             "brick"),
    ("GLASS",             "glass"),
    ("IGU",               "glass"),
    ("GYP",               "gypsum"),
    ("GWB",               "gypsum"),
]


def material_for_layer(layer_name: str) -> str:
    """Pick a material recipe based on substring match against layer name."""
    upper = layer_name.upper()
    for substring, material in LAYER_TO_MATERIAL:
        if substring in upper:
            return material
    return "concrete_solid"  # safe default
