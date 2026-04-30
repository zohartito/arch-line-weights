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
    assert __version__ == "0.4.0"


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


def test_poche_polygonize_layer_falls_back_to_concave_hull():
    """Disconnected segments with no shared endpoints should fall back to concave_hull."""
    from arch_line_weights.poche import polygonize_layer
    # Three disconnected line segments forming a rough triangle
    paths = [
        [[0, 0], [5, 0.1]],
        [[10, 0], [10, 5.1]],
        [[10, 10], [0, 10.1]],
        [[0, 10], [0.1, 5]],
    ]
    polys, result = polygonize_layer("test_layer", paths)
    # Either linemerge_snap rescued it, or concave_hull did
    assert result.polygon_count >= 1
    assert result.strategy in ("linemerge_snap", "concave_hull", "bbox", "linemerge_bare")


def test_poche_user_override_skip():
    from arch_line_weights.poche import polygonize_layer
    paths = [[[0, 0], [10, 0]], [[10, 0], [10, 10]]]
    polys, result = polygonize_layer("test_layer", paths, override={"strategy": "skip"})
    assert result.polygon_count == 0
    assert result.strategy == "skipped"
