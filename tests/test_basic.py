"""Smoke tests for the arch-line-weights package."""
import pytest

from arch_line_weights import __version__
from arch_line_weights.classify import _luminance, auto_by_luminance
from arch_line_weights.inspect import InspectionReport, color_to_rgb255
from arch_line_weights.layer_classify import classify_layer, RULES, DEFAULT
from arch_line_weights.presets import (
    SECTION, get_preset, mm, select_preset,
    SECTION_ISO_PRINT, SECTION_ISO_SCREEN,
)


# --------------------------------------------------------------------------- #
# Existing v0.1/v0.2 tests
# --------------------------------------------------------------------------- #

def test_version():
    # Version comes from hatch-vcs (git tag) at install time; just sanity-check format
    assert isinstance(__version__, str)
    assert len(__version__) > 0


def test_color_parse():
    assert color_to_rgb255("RGB(40,40,40)") == (40, 40, 40)
    assert color_to_rgb255("CMYK(0,0,0,100)") is None
    assert color_to_rgb255("Gray(20)") is None


def test_luminance_ordering():
    assert _luminance((0, 0, 0)) < _luminance((128, 128, 128)) < _luminance((255, 255, 255))


def test_auto_classify_buckets_dark_to_heavy():
    rep = InspectionReport(
        file="x", pages=1, width_pt=100, height_pt=100,
        total_drawings=10, total_stroked=10,
        stroke_colors={
            "RGB(10,10,10)": 1,
            "RGB(255,255,255)": 100,
            "RGB(128,128,128)": 50,
        },
    )
    mapping = auto_by_luminance(rep, get_preset("section"))
    assert mapping[(10, 10, 10)] == max(t.weight_pt for t in SECTION)
    light_weight = min(t.weight_pt for t in SECTION if t.name != "special")
    assert mapping[(255, 255, 255)] == light_weight


# --------------------------------------------------------------------------- #
# v0.2 layer_classify tests
# --------------------------------------------------------------------------- #

def test_clipping_plane_intersections_is_always_cut():
    """Per Rhino convention, this path is the section cut tier regardless of material."""
    a = classify_layer("axon::Visible::ClippingPlaneIntersections::TEC_TIMBER_BEAMS")
    assert a.weight_pt == 1.0
    assert a.tier == "cut"


def test_window_glass_is_glazing():
    a = classify_layer("axon::Visible::Curves::03c_WINDOW_IGU_GLASS")
    assert a.tier == "glazing"
    assert a.weight_pt == 0.25


def test_floor_datums_is_reference():
    a = classify_layer("axon::Visible::Curves::FLOOR_DATUMS")
    assert a.tier == "reference"
    assert a.weight_pt == 0.13


def test_unknown_layer_falls_back_to_default():
    a = classify_layer("totally_unknown_layer_name")
    assert a.weight_pt == DEFAULT.weight_pt
    assert a.tier == "default"


# --------------------------------------------------------------------------- #
# v0.4 ISO 128 / standards-aligned presets
# --------------------------------------------------------------------------- #

def test_mm_to_pt_conversion():
    """1 mm = 2.835 PostScript points (rounded)."""
    assert mm(1.0) == 2.835
    assert mm(0.5) == round(0.5 * 2.835, 3)
    assert mm(0.18) == round(0.18 * 2.835, 3)


def test_select_preset_screen_is_lighter_than_print():
    """Screen review weights should be lighter than print weights at any scale."""
    screen = select_preset("section", scale="1/4", for_print=False)
    plot = select_preset("section", scale="1/4", for_print=True)
    cut_screen = next(t for t in screen if t.name == "cut")
    cut_print = next(t for t in plot if t.name == "cut")
    assert cut_screen.weight_pt < cut_print.weight_pt


def test_iso_section_print_cut_is_about_2pt():
    """Section cut at 1/4\"=1' should be 0.7mm = 1.98pt per Ramsey/Sleeper."""
    plot = select_preset("section", scale="1/4", for_print=True)
    cut = next(t for t in plot if t.name == "cut")
    # 0.70 mm × 2.835 = 1.985, round to 1.98 or so
    assert 1.9 < cut.weight_pt < 2.1


def test_scale_shifts_weights():
    """1/16 scale should be lighter than 1/4 scale."""
    s_quarter = select_preset("section", scale="1/4", for_print=True)
    s_sixteenth = select_preset("section", scale="1/16", for_print=True)
    cut_quarter = next(t for t in s_quarter if t.name == "cut").weight_pt
    cut_sixteenth = next(t for t in s_sixteenth if t.name == "cut").weight_pt
    assert cut_sixteenth < cut_quarter


# --------------------------------------------------------------------------- #
# v0.4 poche module — pure-Python parts (no Illustrator)
# --------------------------------------------------------------------------- #

def test_poche_polygonize_layer_works_on_closed_polyline():
    """Single closed polyline should produce 1 polygon."""
    from arch_line_weights.poche import polygonize_layer
    paths = [
        # 4 segments forming a closed square
        [[0, 0], [10, 0]],
        [[10, 0], [10, 10]],
        [[10, 10], [0, 10]],
        [[0, 10], [0, 0]],
    ]
    polys, result = polygonize_layer("test_layer", paths)
    assert result.polygon_count == 1
    assert result.confidence == 1.0
    assert result.strategy == "linemerge_bare"


def test_poche_polygonize_layer_returns_failed_for_empty():
    from arch_line_weights.poche import polygonize_layer
    polys, result = polygonize_layer("test_layer", [])
    assert result.polygon_count == 0
    assert result.confidence == 0.0
    assert result.strategy == "failed"


def test_poche_polygonize_layer_falls_back_for_disconnected():
    """Disconnected segments should be rescued by snap, auto_bridge, concave_hull, or bbox."""
    from arch_line_weights.poche import polygonize_layer
    # Four disconnected line segments forming a rough rectangle
    paths = [
        [[0, 0], [5, 0.1]],
        [[10, 0], [10, 5.1]],
        [[10, 10], [0, 10.1]],
        [[0, 10], [0.1, 5]],
    ]
    polys, result = polygonize_layer("test_layer", paths)
    assert result.polygon_count >= 1
    # Any rescue strategy is acceptable
    assert result.strategy in (
        "linemerge_bare", "linemerge_snap", "auto_bridge",
        "concave_hull", "bbox",
    )


def test_bridge_infer_for_almost_closed_square():
    """Auto-bridge should close 4 segments with sub-1pt corner gaps into 1 polygon."""
    from arch_line_weights.bridge import infer_bridges
    from arch_line_weights.poche import _polys_at_tolerance
    from shapely.geometry import LineString
    # Square with 0.2pt gap at each corner
    g = 0.2
    segs = [
        LineString([(0, 0), (10 - g, 0)]),
        LineString([(10, g), (10, 10 - g)]),
        LineString([(10 - g, 10), (g, 10)]),
        LineString([(0, 10 - g), (0, g)]),
    ]
    augmented, conf = infer_bridges(segs, max_gap=2.0, min_gap=0.01)
    assert len(augmented) > len(segs)  # bridges added
    assert conf > 0  # some confidence
    polys = _polys_at_tolerance(augmented, 0.0)
    assert len(polys) >= 1


def test_bridge_refuses_when_gap_too_big():
    """Gap larger than max_gap should produce no bridges and 0 confidence."""
    from arch_line_weights.bridge import infer_bridges
    from shapely.geometry import LineString
    segs = [
        LineString([(0, 0), (10, 0)]),
        LineString([(1000, 1000), (1010, 1000)]),  # far away
    ]
    augmented, conf = infer_bridges(segs, max_gap=50.0, min_gap=0.01)
    assert len(augmented) == len(segs)  # no bridges added
    assert conf == 0.0


def test_bridge_already_closed_is_noop():
    """Already-closed polygon should produce no bridges and high confidence."""
    from arch_line_weights.bridge import infer_bridges
    from shapely.geometry import LineString
    segs = [
        LineString([(0, 0), (10, 0)]),
        LineString([(10, 0), (10, 10)]),
        LineString([(10, 10), (0, 10)]),
        LineString([(0, 10), (0, 0)]),
    ]
    augmented, conf = infer_bridges(segs)
    assert len(augmented) == len(segs)  # no bridges needed
    assert conf >= 0.5  # already valid topology


def test_poche_user_override_skip():
    from arch_line_weights.poche import polygonize_layer
    paths = [[[0, 0], [10, 0]], [[10, 0], [10, 10]]]
    polys, result = polygonize_layer("test_layer", paths, override={"strategy": "skip"})
    assert result.polygon_count == 0
    assert result.strategy == "skipped"


# --------------------------------------------------------------------------- #
# v0.5 hatch
# --------------------------------------------------------------------------- #

def test_hatch_concrete_returns_lines():
    from arch_line_weights.hatch import hatch_polygon
    from shapely.geometry import Polygon
    # 100×30 pt polygon at 1:1 — small + dense enough to be fast in test
    wall = Polygon([(0, 0), (100, 0), (100, 30), (0, 30)])
    lines = hatch_polygon(wall, "concrete", scale=1.0)
    assert len(lines) > 0


def test_hatch_solid_materials_return_empty():
    from arch_line_weights.hatch import hatch_polygon
    from shapely.geometry import Polygon
    wall = Polygon([(0, 0), (100, 0), (100, 100), (0, 100)])
    for solid in ("concrete_solid", "clt_solid", "steel_solid"):
        assert hatch_polygon(wall, solid, scale=1.0) == []


def test_hatch_unknown_material_raises():
    from arch_line_weights.hatch import hatch_polygon
    from shapely.geometry import Polygon
    wall = Polygon([(0, 0), (100, 0), (100, 100), (0, 100)])
    with pytest.raises(KeyError):
        hatch_polygon(wall, "no_such_material", scale=1.0)


def test_material_for_layer_picks_right_recipe():
    from arch_line_weights.hatch import material_for_layer
    assert material_for_layer("axon::Visible::Curves::TEC_CONCRETE_BASE") == "concrete_solid"
    assert material_for_layer("axon::Visible::Curves::TEC_TIMBER_BEAMS") == "solid_timber"
    assert material_for_layer("axon::Visible::Curves::03c_WINDOW_IGU_GLASS") == "glass"
    assert material_for_layer("axon::Visible::Curves::INSUL_BATT") == "insulation_mineral_wool"
    assert material_for_layer("axon::Visible::Curves::EARTH_GROUND") == "earth"


def test_hatch_register_custom_material():
    from arch_line_weights.hatch import (
        MATERIALS, MaterialRecipe, hatch_polygon, parallel_hatch, mm_to_pt, register_material
    )
    from shapely.geometry import Polygon

    def custom_fn(poly, scale, **kw):
        return parallel_hatch(poly, mm_to_pt(0.5, scale), 30.0)

    register_material(MaterialRecipe("test_custom", custom_fn))
    assert "test_custom" in MATERIALS
    wall = Polygon([(0, 0), (50, 0), (50, 50), (0, 50)])
    assert len(hatch_polygon(wall, "test_custom", scale=1.0)) > 0


def test_mm_to_pt_at_scale():
    from arch_line_weights.hatch import mm_to_pt
    # 2 mm at 1:50 = 2 * 0.02 * 2.8346 = 0.11338 pt
    assert abs(mm_to_pt(2.0, 1 / 50) - 0.1134) < 0.0001
    # 1 mm at 1:1 = 2.835 pt
    assert abs(mm_to_pt(1.0, 1.0) - 2.835) < 0.001


def test_poisson_disk_safety_cap():
    """A huge polygon with tiny min_dist should NOT hang — cap kicks in."""
    from arch_line_weights.hatch import poisson_disk
    from shapely.geometry import Polygon
    # 10,000 × 10,000 polygon with min_dist=0.01 would naively be 100M points
    huge = Polygon([(0, 0), (10000, 0), (10000, 10000), (0, 10000)])
    samples = poisson_disk(huge, min_dist=0.01, max_samples=1000)
    # Cap holds and no hang
    assert len(samples) <= 1000
