"""Offline, deterministic tests for the tonal-recede feature.

Covers three scopes, all no-LLM / no-network:

  1. The tone math (:mod:`arch_line_weights.tonal_recede`) — the value ramp, the
     cut-is-never-lightened invariant, hue preservation, and grey mode.
  2. The two apply paths honour ``--tonal-recede`` off-by-default (byte-stable)
     and lighten only beyond-cut strokes when it is on.
  3. The visual judge's fifth axis (``tonal_recede``) scores a value-flat sheet
     as ``review`` and a properly-receded one as ``pass``, and returns ``null``
     when the cut/beyond split is unavailable.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pikepdf
import pytest

from arch_line_weights.apply import apply_to_file
from arch_line_weights.apply_saas import ApplySaasResult, rewrite_payload
from arch_line_weights.classify import auto_by_role
from arch_line_weights.inspect import inspect_file
from arch_line_weights.tonal_recede import (
    MODES,
    TONE_FLOOR,
    describe_ramp,
    recede_rgb,
    tonal_recede_resolver,
    tone_factor_for_weight,
    tone_tier_for_weight,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import visual_judge as vj  # noqa: E402

DEMO_RAW = REPO_ROOT / "examples" / "demo-section.pdf"


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _content_stream_bytes(path: Path) -> bytes:
    """Deterministic content-stream bytes (pikepdf embeds a random /ID in the
    file wrapper, so whole-file byte comparison is not a valid invariant)."""
    with pikepdf.open(str(path)) as pdf:
        return pikepdf.unparse_content_stream(list(pikepdf.parse_content_stream(pdf.pages[0])))


def _stroke_colors(path: Path) -> set[tuple[int, int, int]]:
    colors: set[tuple[int, int, int]] = set()
    with pikepdf.open(str(path)) as pdf:
        for operands, op in pikepdf.parse_content_stream(pdf.pages[0]):
            if str(op) == "RG":
                colors.add(tuple(round(float(o) * 255) for o in operands))
    return colors


def _luminance(rgb: tuple[int, int, int]) -> float:
    r, g, b = rgb
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _write_stroke_pdf(path: Path, strokes: list[tuple[float, tuple[int, int, int]]]) -> None:
    """Write a minimal PDF whose strokes have the given (width_pt, RGB)."""
    lines: list[str] = []
    y = 10
    for width, (r, g, b) in strokes:
        lines.append(f"{r / 255:g} {g / 255:g} {b / 255:g} RG")
        lines.append(f"{width:g} w")
        lines.append(f"10 {y} m 190 {y} l S")
        y += 3
    pdf = pikepdf.new()
    pdf.add_blank_page(page_size=(200, 200))
    pdf.pages[0].Contents = pdf.make_stream("\n".join(lines).encode("ascii"))
    pdf.save(str(path))


def _synthetic_saas_payload() -> bytes:
    """Two-layer AI-native fragment: a black (cut) stroke and a red (beyond) one."""
    return (
        b"%!PS-Adobe-3.0\r"
        b"%AI5_BeginLayer\r"
        b"(Cut) Ln\r"
        b"0 0 0 0 0 0 0 XA\r"  # black stroke (cut)
        b"1 w\r"
        b"0 0 m\r"
        b"10 10 L\r"
        b"S\r"
        b"%AI5_EndLayer--\r"
        b"%AI5_BeginLayer\r"
        b"(Beyond) Ln\r"
        b"0 0 0 0 1 0 0 XA\r"  # red stroke (beyond)
        b"0.3 w\r"
        b"20 20 m\r"
        b"30 30 L\r"
        b"S\r"
        b"%AI5_EndLayer--\r"
    )


# --------------------------------------------------------------------------- #
# 1. Tone math
# --------------------------------------------------------------------------- #


def test_tone_ramp_is_monotone_and_anchored() -> None:
    # The task's anchor ramp: cut 1.00 -> profile 0.72 -> edges 0.55 ->
    # material 0.42 -> texture 0.32.
    assert tone_factor_for_weight(1.0) == 1.00
    assert tone_factor_for_weight(0.5) == 0.72
    assert tone_factor_for_weight(0.3) == 0.55
    assert tone_factor_for_weight(0.13) == 0.42
    assert tone_factor_for_weight(0.08) == 0.32
    # Monotone non-increasing as weight drops.
    factors = [tone_factor_for_weight(w) for w in (2.0, 1.0, 0.5, 0.3, 0.13, 0.08, 0.01)]
    assert factors == sorted(factors, reverse=True)


def test_tier_labels() -> None:
    assert tone_tier_for_weight(1.0) == "cut"
    assert tone_tier_for_weight(0.5) == "profile"
    assert tone_tier_for_weight(0.08) == "texture"


def test_cut_is_never_lightened() -> None:
    """Round-trip invariant: the cut tier keeps full value (returns None)."""
    for rgb in [(0, 0, 0), (25, 25, 30), (230, 120, 40), (255, 255, 255)]:
        assert recede_rgb(rgb, 1.0) is None
        assert recede_rgb(rgb, 2.0) is None  # anything at/above cut weight


def test_beyond_strokes_lighten_but_never_reach_white() -> None:
    black = (0, 0, 0)
    for weight in (0.5, 0.3, 0.13, 0.08):
        toned = recede_rgb(black, weight)
        assert toned is not None
        # Strictly lighter than the source, but never pure white (floor).
        assert _luminance(toned) > _luminance(black)
        assert toned != (255, 255, 255)
        assert max(toned) <= 254


def test_value_mode_preserves_hue_direction() -> None:
    """A saturated stroke keeps its hue ordering (scaled toward white)."""
    toned = recede_rgb((230, 120, 40), 0.3, mode="value")
    assert toned is not None
    r, g, b = toned
    # Original ordering r > g > b is preserved; each channel moved toward 255.
    assert r > g > b
    assert r > 230 and g > 120 and b > 40


def test_grey_mode_neutralizes() -> None:
    toned = recede_rgb((230, 120, 40), 0.3, mode="grey")
    assert toned is not None
    assert toned[0] == toned[1] == toned[2]  # a true grey


def test_floor_bounds_the_darkest_rung() -> None:
    # The lightest ramp rung retains 0.32 of darkness, comfortably above the
    # hard floor, so a black texture stroke stays a visible grey.
    assert TONE_FLOOR < 0.32
    toned = recede_rgb((0, 0, 0), 0.05)  # texture tier
    assert toned is not None
    assert 0 < toned[0] < 255


def test_resolver_rejects_unknown_mode() -> None:
    with pytest.raises(ValueError):
        tonal_recede_resolver("sepia")
    assert set(MODES) == {"value", "grey"}


def test_describe_ramp_mentions_every_rung() -> None:
    text = "\n".join(describe_ramp("value"))
    for label in ("cut", "profile", "edges", "material", "texture"):
        assert label in text


# --------------------------------------------------------------------------- #
# 2a. PDF apply path (examples/demo-section.pdf — color-coded, no layers)
# --------------------------------------------------------------------------- #


def _demo_mapping() -> dict[tuple[int, int, int], float]:
    rep = inspect_file(str(DEMO_RAW))
    mapping, _lt = auto_by_role(rep, "section", "1/4", False)
    return mapping


def test_apply_pdf_off_by_default_is_byte_stable(tmp_path: Path) -> None:
    """No flag → the content stream is exactly the weight-only output."""
    mapping = _demo_mapping()
    baseline = tmp_path / "baseline.pdf"
    with_none = tmp_path / "with_none.pdf"
    apply_to_file(str(DEMO_RAW), str(baseline), mapping)
    apply_to_file(str(DEMO_RAW), str(with_none), mapping, layer_tone_resolver=None)
    assert _content_stream_bytes(baseline) == _content_stream_bytes(with_none)
    # And the untouched drawing keeps its five original stroke colors.
    assert (25, 25, 30) in _stroke_colors(baseline)
    assert (70, 85, 120) in _stroke_colors(baseline)


def test_apply_pdf_recede_lightens_beyond_keeps_cut(tmp_path: Path) -> None:
    mapping = _demo_mapping()
    baseline = tmp_path / "baseline.pdf"
    out = tmp_path / "recede.pdf"
    apply_to_file(str(DEMO_RAW), str(baseline), mapping)
    result = apply_to_file(
        str(DEMO_RAW),
        str(out),
        mapping,
        layer_tone_resolver=tonal_recede_resolver("value"),
    )
    assert result.tonal_recede_applied > 0
    colors = _stroke_colors(out)
    # The cut color (heaviest weight) is preserved verbatim; the toned profile
    # color is emitted (255 - 0.72*(255 - channel) per channel). The source RG
    # op stays in the stream but a toned RG is injected before each beyond
    # stroke, so the stroke renders lighter.
    assert (25, 25, 30) in colors
    assert (122, 133, 158) in colors
    # Effective render: the judge (which reads the *last* color before each
    # stroke) sees beyond geometry recede — a higher cut:beyond ratio than the
    # weight-only baseline, with the cut darkness pinned.
    base = vj.judge(baseline)["details"]["tonal_recede"]
    rec = vj.judge(out)["details"]["tonal_recede"]
    assert rec["beyond_mean_darkness"] < base["beyond_mean_darkness"]
    assert rec["cut_mean_darkness"] == base["cut_mean_darkness"]


# --------------------------------------------------------------------------- #
# 2b. SaaS native-payload path (byte-exact, deterministic bytes)
# --------------------------------------------------------------------------- #


def test_apply_saas_off_by_default_is_byte_identical() -> None:
    payload = _synthetic_saas_payload()
    mapping = {(0, 0, 0): 1.0, (255, 0, 0): 0.3}
    off_a = rewrite_payload(payload, mapping, result=ApplySaasResult())
    off_b = rewrite_payload(payload, mapping, result=ApplySaasResult())
    assert off_a == off_b  # deterministic
    # Both XA stroke colors survive untouched with the flag off.
    assert b"0 0 0 0 0 0 0 XA" in off_a  # black cut
    assert b"0 0 0 0 1 0 0 XA" in off_a  # red beyond


def test_apply_saas_recede_lightens_beyond_keeps_cut() -> None:
    payload = _synthetic_saas_payload()
    mapping = {(0, 0, 0): 1.0, (255, 0, 0): 0.3}
    result = ApplySaasResult()
    on = rewrite_payload(
        payload,
        mapping,
        result=result,
        layer_tone_resolver=tonal_recede_resolver("value"),
    )
    off = rewrite_payload(payload, mapping, result=ApplySaasResult())
    assert on != off
    assert result.tonal_recede_applied == 1
    # The black cut XA is left exactly as-is (cut owns the darkest value).
    assert b"0 0 0 0 0 0 0 XA" in on
    # The red beyond XA was rewritten toward white (no longer the pure-red XA).
    assert b"0 0 0 0 1 0 0 XA" not in on


# --------------------------------------------------------------------------- #
# 3. Judge axis 5 — tonal_recede
# --------------------------------------------------------------------------- #


def test_judge_flat_tone_is_review(tmp_path: Path) -> None:
    """Cut and beyond at the SAME value (only widths differ) → value-flat."""
    flat = tmp_path / "flat.pdf"
    strokes = [(1.0, (0, 0, 0))] * 15 + [(0.25, (0, 0, 0))] * 30
    _write_stroke_pdf(flat, strokes)
    result = vj.judge(flat)
    assert result["scores"]["tonal_recede"] is not None
    assert result["scores"]["tonal_recede"] < vj.TONAL_RECEDE_MIN_RATIO
    assert result["verdict"] == "review"
    assert any("tonal_recede" in w for w in result["why"])


def test_judge_receded_is_pass(tmp_path: Path) -> None:
    """Cut dark, beyond lightened to grey → the value ramp is doing work."""
    receded = tmp_path / "receded.pdf"
    strokes = [(1.0, (0, 0, 0))] * 15 + [(0.25, (150, 150, 150))] * 30
    _write_stroke_pdf(receded, strokes)
    result = vj.judge(receded)
    assert result["scores"]["tonal_recede"] >= vj.TONAL_RECEDE_MIN_RATIO
    assert not any("tonal_recede" in w for w in result["why"])
    assert result["verdict"] == "pass"


def test_judge_tonal_recede_null_on_single_tier(tmp_path: Path) -> None:
    """One weight tier → no cut/beyond split → null (never guessed)."""
    single = tmp_path / "single.pdf"
    _write_stroke_pdf(single, [(0.5, (0, 0, 0))] * 20)
    result = vj.judge(single)
    assert result["scores"]["tonal_recede"] is None


def test_judge_tonal_recede_null_on_raster(tmp_path: Path) -> None:
    """A raster input carries no per-stroke color → null."""
    from PIL import Image

    png = tmp_path / "raster.png"
    Image.new("L", (64, 64), color=255).save(png)
    score, meta = vj.tonal_recede_score(png)
    assert score is None
    assert "note" in meta
