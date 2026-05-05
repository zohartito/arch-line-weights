"""Tests for the apply_saas module — pure-pikepdf headless apply path.

These tests cover three scopes:

  1. Decompression / recompression round-trip preserves byte content
     (proves the zstd + 64 KB chunking framing is symmetric).
  2. Stroke-width rewrite on a small synthetic AI native payload changes the
     right `<w> w` operators per recent XA color, and leaves other tokens
     (path coords, fill ops, layer headers) untouched.
  3. Color-tier auto-classification on a fixture matches `apply.py`'s
     behavior, since both call into the same `auto_by_luminance` mapping.
"""

from __future__ import annotations

import pytest
import zstandard as zstd

from arch_line_weights.apply import _rewrite as pdf_rewrite
from arch_line_weights.apply_saas import (
    PREFIX,
    ApplySaasResult,
    _format_width,
    rewrite_payload,
)
from arch_line_weights.classify import auto_by_luminance
from arch_line_weights.inspect import InspectionReport
from arch_line_weights.presets import get_preset

# --------------------------------------------------------------------------- #
# 1. Round-trip: decompress + recompress is byte-identical
# --------------------------------------------------------------------------- #


def test_zstd_roundtrip_preserves_bytes():
    """Decompress(compress(x)) == x, for any x — including AI-shaped payloads."""
    payload = b"%!PS-Adobe-3.0\r" + b"0 0 0 0 0 0 0 XA\r" * 50 + b"\r0.5 w\r"
    compressed = zstd.ZstdCompressor(level=19).compress(payload)
    framed = PREFIX + compressed
    # Strip prefix and decompress as the apply_saas pipeline does
    assert framed.startswith(PREFIX)
    decompressed = zstd.ZstdDecompressor().decompress(framed[len(PREFIX) :])
    assert decompressed == payload


def test_chunk_split_and_concat_is_inverse():
    """64 KB chunking is just slicing — concatenation reverses it."""
    payload = b"abc" * 100_000  # 300 KB so we get multiple chunks
    chunks = [payload[i : i + 65536] for i in range(0, len(payload), 65536)]
    assert b"".join(chunks) == payload
    assert len(chunks) == 5  # 300_000 / 65536 = 4.58 -> 5 chunks


# --------------------------------------------------------------------------- #
# 2. Synthetic-payload stroke-width rewrite
# --------------------------------------------------------------------------- #


def _build_synthetic_payload() -> bytes:
    """A tiny AI-native-shaped fragment with two colored layers.

    Layer A: stroke RGB (255, 0, 0) (red), one bare-form `0.25 w` op
    Layer B: stroke RGB (0, 0, 0) (black), one setup-form `1 J 1 j 0.5 w` op
    """
    return (
        b"%!PS-Adobe-3.0\r"
        b"%AI5_BeginLayer\r"
        b"(Layer A) Ln\r"
        b"0 0 0 0 1 0 0 XA\r"  # red stroke
        b"0.25 w\r"
        b"100 200 m\r"
        b"150 250 L\r"
        b"S\r"
        b"%AI5_EndLayer--\r"
        b"%AI5_BeginLayer\r"
        b"(Layer B) Ln\r"
        b"0 0 0 1 0 0 0 XA\r"  # black stroke
        b"1 J 1 j 0.5 w 4 M []0 d\r"
        b"50 50 m\r"
        b"75 75 L\r"
        b"S\r"
        b"%AI5_EndLayer--\r"
    )


def test_rewrite_changes_widths_per_color():
    """red strokes -> 1.0 pt, black strokes -> 0.13 pt."""
    payload = _build_synthetic_payload()
    mapping = {
        (255, 0, 0): 1.0,
        (0, 0, 0): 0.13,
    }
    result = ApplySaasResult()
    new_payload = rewrite_payload(payload, mapping, default_width=0.25, result=result)

    assert result.xa_seen == 2
    assert result.widths_rewritten == 2
    assert result.weights_applied == {1.0: 1, 0.13: 1}
    assert not result.unmatched_colors

    # Confirm the bare-form `0.25 w` got bumped to `1 w` (red layer)
    assert b"\r1 w\r" in new_payload
    assert b"\r0.25 w\r" not in new_payload
    # Confirm the setup-form width became 0.13 (black layer); J/j prefix preserved
    assert b"\r1 J 1 j 0.13 w" in new_payload
    assert b"\r1 J 1 j 0.5 w" not in new_payload
    # Confirm path coords were not touched
    assert b"100 200 m\r" in new_payload
    assert b"50 50 m\r" in new_payload
    # Confirm layer headers preserved
    assert b"(Layer A) Ln\r" in new_payload
    assert b"(Layer B) Ln\r" in new_payload


def test_rewrite_tracks_cmyk_k_stroke_colors():
    """Converted AI payloads may use CMYK `K` instead of RGB `XA`."""
    payload = (
        b"%!PS-Adobe-3.0\r"
        b"%AI5_BeginLayer\r"
        b"(CMYK Layer) Ln\r"
        b"0.1765 0.2745 0.4314 0.1765 K\r"
        b"1 J 1 j 1 w 4 M []0 d\r"
        b"0 0 m\r"
        b"10 10 L\r"
        b"S\r"
        b"%AI5_EndLayer--\r"
    )
    # Approximate CMYK->RGB normalization used by apply_saas:
    # (1-C)*(1-K)*255, etc.
    mapping = {(173, 152, 119): 0.35}
    result = ApplySaasResult()

    new_payload = rewrite_payload(payload, mapping, default_width=0.25, result=result)

    assert result.xa_seen == 1
    assert result.widths_rewritten == 1
    assert result.weights_applied == {0.35: 1}
    assert b"\r1 J 1 j 0.35 w" in new_payload


def test_rewrite_can_override_weight_by_layer_semantics():
    """Architectural mode can choose stroke width from layer name before color."""
    payload = (
        b"%!PS-Adobe-3.0\r"
        b"%AI5_BeginLayer\r"
        b"(axon::Visible::Curves::TEC_STEEL_CONNECTOR_L-BRACKET) Ln\r"
        b"0 0 0 1 0 0 0 XA\r"
        b"1 J 1 j 1 w 4 M []0 d\r"
        b"0 0 m\r"
        b"10 10 L\r"
        b"S\r"
        b"LB\r"
        b"%AI5_EndLayer--\r"
    )
    result = ApplySaasResult()
    new_payload = rewrite_payload(
        payload,
        {(0, 0, 0): 1.0},
        default_width=0.25,
        result=result,
        layer_weight_resolver=lambda _name: 0.25,
    )

    assert result.widths_rewritten == 1
    assert result.layer_weight_overrides == 1
    assert result.weights_applied == {0.25: 1}
    assert b"\r1 J 1 j 0.25 w" in new_payload
    assert b"\r1 J 1 j 1 w" not in new_payload


def test_empty_auto_mapping_is_a_cli_error(tmp_path):
    """A blind auto-classifier should not silently default every stroke."""
    from arch_line_weights.cli import _require_nonempty_auto_mapping

    with pytest.raises(Exception) as ex:
        _require_nonempty_auto_mapping({}, src=tmp_path / "blind.ai", preset="section")

    assert "found 0 RGB stroke colors" in str(ex.value)


def test_rewrite_unmatched_color_uses_default():
    """A color not in the mapping should fall back to default_width."""
    payload = (
        b"\r0 0 0 0 0.5 0.5 0.5 XA\r"  # mid-gray
        b"\r3 w\r"
    )
    mapping: dict[tuple[int, int, int], float] = {(255, 0, 0): 1.0}
    result = ApplySaasResult()
    new_payload = rewrite_payload(payload, mapping, default_width=0.25, result=result)

    assert result.widths_rewritten == 1
    assert result.unmatched_colors == {(128, 128, 128): 1}
    assert result.weights_applied == {0.25: 1}
    assert b"\r0.25 w\r" in new_payload
    assert b"\r3 w\r" not in new_payload


def test_rewrite_no_xa_uses_default():
    """A `<w> w` with no preceding XA token should still get the default."""
    payload = b"\r0.5 w\r"
    result = ApplySaasResult()
    new_payload = rewrite_payload(payload, {}, default_width=0.18, result=result)

    assert result.xa_seen == 0
    assert result.widths_rewritten == 1
    assert b"\r0.18 w\r" in new_payload


def test_rewrite_preserves_payload_outside_w_ops():
    """Rewrite must not change any byte outside the `<w> w` operator span."""
    payload = _build_synthetic_payload()
    mapping = {(255, 0, 0): 1.0, (0, 0, 0): 0.13}
    new_payload = rewrite_payload(payload, mapping)

    # Drop the operator regions and compare the rest. Easiest check: confirm
    # all marker substrings survive verbatim.
    for marker in (
        b"%!PS-Adobe-3.0\r",
        b"%AI5_BeginLayer\r",
        b"(Layer A) Ln\r",
        b"0 0 0 0 1 0 0 XA\r",
        b"100 200 m\r",
        b"150 250 L\r",
        b"%AI5_EndLayer--\r",
        b"(Layer B) Ln\r",
        b"0 0 0 1 0 0 0 XA\r",
        b"50 50 m\r",
    ):
        assert marker in new_payload, f"missing {marker!r}"


def test_format_width_integer_vs_decimal():
    """Integer weights emit as plain ints; non-integers as `g`-formatted."""
    assert _format_width(1.0) == b"1"
    assert _format_width(5.0) == b"5"
    assert _format_width(0.25) == b"0.25"
    assert _format_width(0.13) == b"0.13"


# --------------------------------------------------------------------------- #
# 3. Color-tier classification matches apply.py behavior
# --------------------------------------------------------------------------- #


def test_auto_classify_matches_apply_py_behavior():
    """The auto-classify mapping is the same regardless of which apply path
    consumes it, since both `apply` and `apply-saas` call `auto_by_luminance`.
    """
    rep = InspectionReport(
        file="x",
        pages=1,
        width_pt=100,
        height_pt=100,
        total_drawings=10,
        total_stroked=10,
        stroke_colors={
            "RGB(0,0,0)": 100,  # darkest -> heaviest tier
            "RGB(128,128,128)": 50,
            "RGB(240,240,240)": 1,  # lightest -> lightest tier
        },
    )
    mapping = auto_by_luminance(rep, get_preset("section"))

    # Black should land on the heaviest non-special tier (1.0 pt for SECTION)
    assert mapping[(0, 0, 0)] == 1.0
    # Light gray should land on the lightest non-special tier (0.08 pt)
    assert mapping[(240, 240, 240)] == 0.08

    # Now: feeding that same mapping into both apply paths must produce the
    # same per-color weight on each stroke.
    payload = (
        b"\r0 0 0 0 0 0 0 XA\r"  # black
        b"\r0.5 w\r"
        b"\r0 0 0 0 0.94 0.94 0.94 XA\r"  # ~240/255 light gray
        b"\r0.5 w\r"
    )
    saas_result = ApplySaasResult()
    new_payload = rewrite_payload(payload, mapping, result=saas_result)
    assert b"\r1 w\r" in new_payload
    assert b"\r0.08 w\r" in new_payload
    assert saas_result.weights_applied == {1.0: 1, 0.08: 1}


def test_apply_saas_and_apply_pdf_agree_on_weight_for_color():
    """For a known RGB, both apply paths produce the same final stroke width.

    apply.py walks PDF instructions and emits `<w> w` operators directly.
    apply_saas.py walks AI native PostScript and rewrites existing `<w> w`
    operators. Both must consult the same RGB→weight mapping with the same
    semantics.
    """
    from decimal import Decimal

    from pikepdf import Operator

    mapping = {(255, 0, 0): 1.0, (0, 0, 0): 0.13}

    # PDF-side: simulate one red stroke and one black stroke
    pdf_instructions = [
        ([Decimal("1"), Decimal("0"), Decimal("0")], Operator("RG")),
        ([Decimal("100"), Decimal("100")], Operator("m")),
        ([Decimal("200"), Decimal("200")], Operator("l")),
        ([], Operator("S")),
        ([Decimal("0"), Decimal("0"), Decimal("0")], Operator("RG")),
        ([Decimal("0"), Decimal("0")], Operator("m")),
        ([Decimal("50"), Decimal("50")], Operator("l")),
        ([], Operator("S")),
    ]
    from arch_line_weights.apply import ApplyResult

    pdf_result = ApplyResult()
    pdf_rewrite(pdf_instructions, mapping, default_width=0.25, result=pdf_result)
    assert pdf_result.weights_applied == {1.0: 1, 0.13: 1}

    # AI native side: same two colors, expect same weight distribution
    payload = (
        b"\r0 0 0 0 1 0 0 XA\r"
        b"\r0.5 w\r"
        b"\r0 0 0 1 0 0 0 XA\r"
        b"\r0.5 w\r"
    )
    saas_result = ApplySaasResult()
    rewrite_payload(payload, mapping, default_width=0.25, result=saas_result)
    assert saas_result.weights_applied == pdf_result.weights_applied
