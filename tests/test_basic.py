"""Smoke tests for the apply / classify pipeline."""
from arch_line_weights.classify import _luminance, auto_by_luminance
from arch_line_weights.inspect import InspectionReport, color_to_rgb255
from arch_line_weights.presets import SECTION, get_preset


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
            "RGB(10,10,10)": 1,        # darkest, rare
            "RGB(255,255,255)": 100,   # lightest, common
            "RGB(128,128,128)": 50,
        },
    )
    mapping = auto_by_luminance(rep, get_preset("section"))
    # darkest color must land in heaviest tier (1.0 pt)
    assert mapping[(10, 10, 10)] == max(t.weight_pt for t in SECTION)
    # lightest color must land in lightest tier
    light_weight = min(t.weight_pt for t in SECTION if t.name != "special")
    assert mapping[(255, 255, 255)] == light_weight
