"""Tests for the poché-injection port of the SaaS apply path.

Covers four scopes:

  1. AI-native synthesis — the bytes emitted for a triangle/square/complex
     polygon match the documented `Xa` + `m` + `L` + `f` operator sequence.
  2. Envelope location — `find_layer_envelope` returns offsets that bracket
     the right `%AI5_BeginLayer ... LB` block, even when multiple layers
     are present in the payload.
  3. Round-trip — modified payload (post-injection) zstd-compresses to
     framed bytes, decompresses cleanly, and the new fill operators survive
     the trip byte-for-byte.
  4. End-to-end — `apply_saas_with_poche` against a synthetic .ai fixture
     produces a file whose AIPrivateData payload contains the injected
     polygon path operators.
"""

from __future__ import annotations

import os
import tempfile

import pikepdf
import pytest
from shapely.geometry import Polygon

from arch_line_weights.apply_saas import CHUNK, _read_payload
from arch_line_weights.poche import FillResult
from arch_line_weights.poche_saas import (
    PocheSaasResult,
    _structural_helper_paths_for_layers,
    apply_saas_with_poche,
    compress_test_payload,
    compute_polygons_for_layers,
    decompress_test_payload,
    enumerate_layer_paths_from_payload,
    find_layer_envelope,
    inject_poche_polygons,
    synthesize_polygon_block,
    synthesize_polygon_blocks,
    write_synthetic_test_ai,
)

# --------------------------------------------------------------------------- #
# 1. Synthesize AI native PostScript fragments for filled black polygons
# --------------------------------------------------------------------------- #


def test_synthesize_triangle_emits_3_vertices_and_fill_op():
    """Triangle polygon should produce: Xa + 0 R + m + 2L + f."""
    tri = Polygon([(0, 0), (10, 0), (5, 10)])
    out = synthesize_polygon_block(tri)

    # Fill color: CMYK 0,0,0,1 + RGB 0,0,0 = black
    assert b"0 0 0 1 1 0 0 0 Xa\r" in out
    # Render-mode reset
    assert b"0 R\r" in out
    # First vertex via `m`, two more via `L`
    assert b"\r0 0 m\r" in out
    assert b"\r10 0 L\r" in out
    assert b"\r5 10 L\r" in out
    # Closepath + fill operator
    assert out.endswith(b"f\r")


def test_synthesize_square_emits_4_vertices():
    """Square polygon should produce 1 m-op and 3 L-ops, in order."""
    sq = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
    out = synthesize_polygon_block(sq)

    assert b"\r0 0 m\r" in out
    # The remaining 3 vertices each appear as an L-op
    for vertex in (b"\r10 0 L\r", b"\r10 10 L\r", b"\r0 10 L\r"):
        assert vertex in out, f"missing {vertex!r}"

    # The duplicate closing vertex shouldn't appear (shapely adds it but we
    # strip it since `f` already closes the path). 4 vertices total: 1 m + 3 L.
    assert out.count(b" m\r") == 1
    assert out.count(b" L\r") == 3


def test_synthesize_complex_polygon_preserves_decimal_coords():
    """A polygon with non-integer coords should use g-format decimals."""
    p = Polygon([(0.5, 0.25), (10.75, 0.5), (5.123, 10.875)])
    out = synthesize_polygon_block(p)

    assert b"\r0.5 0.25 m\r" in out
    assert b"\r10.75 0.5 L\r" in out
    assert b"\r5.123 10.875 L\r" in out


def test_synthesize_degenerate_polygon_emits_empty():
    """A polygon with fewer than 3 distinct vertices is degenerate; emit nothing."""
    # An empty Polygon emits empty bytes
    empty = Polygon()
    assert synthesize_polygon_block(empty) == b""
    # `None` polygon also emits empty bytes
    assert synthesize_polygon_block(None) == b""


def test_synthesize_blocks_concatenates_each_polygon():
    """synthesize_polygon_blocks emits one block per polygon, end-to-end."""
    polys = [
        Polygon([(0, 0), (1, 0), (0, 1)]),
        Polygon([(10, 10), (11, 10), (10, 11)]),
    ]
    out = synthesize_polygon_blocks(polys)
    # Two `f\r` operators = 2 polygons emitted
    assert out.count(b"f\r") == 2
    # First polygon's first vertex
    assert b"\r0 0 m\r" in out
    # Second polygon's first vertex
    assert b"\r10 10 m\r" in out


# --------------------------------------------------------------------------- #
# 2. Locating the layer envelope inside the payload
# --------------------------------------------------------------------------- #


def _build_minimal_payload(layer_names: list[str]) -> bytes:
    """Build a payload with one stroked path inside each named layer."""
    parts = [b"%!PS-Adobe-3.0\r%%EndComments\r"]
    for name in layer_names:
        parts.append(
            b"%AI5_BeginLayer\r"
            b"1 1 1 1 0 0 1 -1 240 190 130 0 100 0 Lb\r"
            b"(" + name.encode("utf-8") + b") Ln\r"
            b"0 AE\r"
            b"0 0 0 1 0 0 0 XA\r"
            b"1 J 1 j 1 w 4 M []0 d\r"
            b"0 0 m\r"
            b"100 0 L\r"
            b"S\r"
            b"LB\r"
            b"%AI5_EndLayer--\r"
        )
    return b"".join(parts)


def test_find_layer_envelope_returns_offsets_in_order():
    """begin < ln < lb. The injection point sits at the LB marker."""
    payload = _build_minimal_payload(["LayerA", "LayerB"])
    env = find_layer_envelope(payload, "LayerA")
    assert env is not None
    begin, ln, lb = env
    assert begin < ln < lb
    # The 15 bytes starting at `begin` should be `%AI5_BeginLayer`
    assert payload[begin : begin + 15] == b"%AI5_BeginLayer"
    # The bytes starting at `ln` are the (LayerA) Ln marker
    assert payload[ln : ln + 9] == b"(LayerA) "
    # The bytes starting at `lb` are `LB`
    assert payload[lb : lb + 2] == b"LB"


def test_find_layer_envelope_picks_correct_layer_when_multiple():
    """A 2-layer payload with the same path data — must disambiguate by name."""
    payload = _build_minimal_payload(["LayerA", "LayerB"])
    env_a = find_layer_envelope(payload, "LayerA")
    env_b = find_layer_envelope(payload, "LayerB")
    assert env_a is not None and env_b is not None
    assert env_a[2] < env_b[2]  # LayerA's LB comes before LayerB's
    # LayerB's begin is past LayerA's lb
    assert env_b[0] > env_a[2]


def test_find_layer_envelope_returns_none_for_missing_name():
    payload = _build_minimal_payload(["LayerA"])
    assert find_layer_envelope(payload, "NotPresent") is None


def test_find_layer_envelope_ignores_matching_setup_text():
    payload = (
        b"%!PS-Adobe-3.0\r"
        b"(LayerA) Ln\r"
        b"%AI5_BeginLayer\r"
        b"(LayerA) Ln\r"
        b"0 0 m\r"
        b"10 0 L\r"
        b"S\r"
        b"LB\r"
        b"%AI5_EndLayer--\r"
    )

    env = find_layer_envelope(payload, "LayerA")

    assert env is not None
    begin, ln, lb = env
    assert payload[begin : begin + 15] == b"%AI5_BeginLayer"
    assert begin < ln < lb


# --------------------------------------------------------------------------- #
# 3. Injection — splice + round-trip
# --------------------------------------------------------------------------- #


def test_inject_poche_polygons_splices_before_lb():
    """Injected bytes appear immediately before the layer's LB marker."""
    payload = _build_minimal_payload(["LayerA"])
    tri = Polygon([(0, 0), (10, 0), (5, 10)])

    result = PocheSaasResult()
    new_payload = inject_poche_polygons(payload, {"LayerA": [tri]}, result=result)

    assert result.layers_targeted == 1
    assert result.layers_injected == 1
    assert result.polygons_injected == 1
    assert result.bytes_injected > 0
    assert result.layers_missing == []

    # Output is strictly longer than input
    assert len(new_payload) > len(payload)
    # All original markers preserved
    assert b"%AI5_BeginLayer\r" in new_payload
    assert b"(LayerA) Ln\r" in new_payload
    assert b"\rLB\r" in new_payload
    # Injected fill operator present
    assert b"\rf\r" in new_payload
    # Injected fill color present
    assert b"0 0 0 1 1 0 0 0 Xa\r" in new_payload
    # The fragment sits before LB, not after — find LB and check the bytes
    # immediately before it end with `f` (the fill closepath operator). Note
    # that the trailing `\r` of the synthesized fragment is the same byte as
    # the leading `\r` of `\rLB\r`, so we look at `[lb_pos - 1]` for `f`.
    lb_pos = new_payload.find(b"\rLB\r")
    # Last 200 bytes before LB should include our injected `f` operator
    assert b"f" in new_payload[lb_pos - 200 : lb_pos]
    # And specifically: byte just before `\rLB\r` is the `f` of the fill op
    assert new_payload[lb_pos - 1 : lb_pos] == b"f"


def test_inject_handles_missing_layer_gracefully():
    """A polygon for a non-existent layer is recorded but doesn't crash."""
    payload = _build_minimal_payload(["LayerA"])
    tri = Polygon([(0, 0), (10, 0), (5, 10)])

    result = PocheSaasResult()
    out = inject_poche_polygons(payload, {"DoesNotExist": [tri]}, result=result)

    assert result.layers_missing == ["DoesNotExist"]
    assert result.layers_injected == 0
    assert out == payload  # unchanged


def test_inject_multiple_layers_in_one_pass():
    """Inject into 2 layers; each should get its own polygon block."""
    payload = _build_minimal_payload(["LayerA", "LayerB"])
    tri_a = Polygon([(0, 0), (10, 0), (5, 10)])
    tri_b = Polygon([(50, 50), (60, 50), (55, 60)])

    result = PocheSaasResult()
    new_payload = inject_poche_polygons(
        payload, {"LayerA": [tri_a], "LayerB": [tri_b]}, result=result
    )

    assert result.layers_injected == 2
    assert result.polygons_injected == 2
    # Each layer should have an `f\r` op now
    assert new_payload.count(b"\rf\r") == 2
    # Both polygon coords should appear
    assert b"\r5 10 L\r" in new_payload
    assert b"\r55 60 L\r" in new_payload


def test_round_trip_through_zstd_preserves_injected_bytes():
    """compress(inject(payload)) → decompress → identical to inject(payload)."""
    payload = _build_minimal_payload(["LayerA"])
    tri = Polygon([(0, 0), (10, 0), (5, 10)])

    new_payload = inject_poche_polygons(payload, {"LayerA": [tri]})
    framed = compress_test_payload(new_payload)
    round_tripped = decompress_test_payload(framed)
    assert round_tripped == new_payload
    # And the fill operator survived
    assert b"\rf\r" in round_tripped


# --------------------------------------------------------------------------- #
# 4. enumerate_layer_paths_from_payload — read paths back from layer blocks
# --------------------------------------------------------------------------- #


def test_enumerate_layer_paths_picks_up_stroked_segments():
    """A simple stroked rectangle should produce 4 sub-paths (one per `S`)."""
    payload = (
        b"%AI5_BeginLayer\r"
        b"(my::ClippingPlaneIntersections::TEST) Ln\r"
        b"0 0 0 1 0 0 0 XA\r"
        b"0 0 m\r"
        b"100 0 L\r"
        b"S\r"
        b"100 0 m\r"
        b"100 100 L\r"
        b"S\r"
        b"LB\r"
        b"%AI5_EndLayer--\r"
    )
    paths = enumerate_layer_paths_from_payload(payload)
    assert "my::ClippingPlaneIntersections::TEST" in paths
    layer_paths = paths["my::ClippingPlaneIntersections::TEST"]
    assert len(layer_paths) == 2
    assert layer_paths[0] == [[0.0, 0.0], [100.0, 0.0]]
    assert layer_paths[1] == [[100.0, 0.0], [100.0, 100.0]]


def test_enumerate_handles_curves_via_endpoint_approximation():
    """A `C` (curveto) op should contribute its endpoint to the polyline."""
    payload = (
        b"%AI5_BeginLayer\r"
        b"(layer::ClippingPlaneIntersections::TEC_X) Ln\r"
        b"0 0 0 1 0 0 0 XA\r"
        b"0 0 m\r"
        b"5 5 8 8 10 10 C\r"
        b"S\r"
        b"LB\r"
        b"%AI5_EndLayer--\r"
    )
    paths = enumerate_layer_paths_from_payload(payload)
    layer = paths["layer::ClippingPlaneIntersections::TEC_X"]
    assert layer == [[[0.0, 0.0], [10.0, 10.0]]]


def test_enumerate_ignores_text_setup_before_real_layer():
    payload = (
        b"%!PS-Adobe-3.0\r"
        b"%%BeginSetup\r"
        b"(unrelated text setup before %AI5_BeginLayer) Ln\r"
        b"%%EndSetup\r"
        b"%AI5_BeginLayer\r"
        b"(axon::Visible::ClippingPlaneIntersections::TEC_CONCRETE_BASE) Ln\r"
        b"0 0 0 1 0 0 0 XA\r"
        b"0 0 m\r"
        b"100 0 L\r"
        b"S\r"
        b"LB\r"
        b"%AI5_EndLayer--\r"
    )

    paths = enumerate_layer_paths_from_payload(payload)

    assert list(paths) == [
        "axon::Visible::ClippingPlaneIntersections::TEC_CONCRETE_BASE",
    ]
    assert all("%AI5_BeginLayer" not in layer for layer in paths)


def test_structural_helper_paths_match_same_material_leaf_only():
    cut_name = "axon::Visible::ClippingPlaneIntersections::TEC_CLT_SLABS"
    cut_paths = {cut_name: [[[0, 0], [100, 0]]]}
    all_paths = {
        cut_name: [[[0, 0], [100, 0]]],
        "axon::Visible::Curves::TEC_CLT_SLABS": [[[0, 10], [100, 10]]],
        "axon::Visible::Tangents::TEC_CLT_SLABS": [[[100, 0], [100, 10]]],
        "axon::Visible::Curves::15_CU_PUNCH_RETURNS_SOUTH_BAY_ALIGNED_V44": [
            [[0, 20], [100, 20]]
        ],
        "axon::Visible::Curves::TEC_CONCRETE_BASE": [[[0, 30], [100, 30]]],
    }

    helpers = _structural_helper_paths_for_layers(cut_paths, all_paths)

    assert helpers == {
        cut_name: [
            [[0, 10], [100, 10]],
            [[100, 0], [100, 10]],
        ]
    }


def test_compute_polygons_passes_structural_helper_paths(monkeypatch):
    captured = {}
    candidate = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])

    def fake_polygonize(*_args, structural_helper_lines=None, **_kwargs):
        captured["helper_count"] = len(structural_helper_lines or [])
        return [candidate], FillResult("LayerA", "structural_open_loop", 0.9, 1, 3)

    monkeypatch.setattr("arch_line_weights.poche_saas.polygonize_layer", fake_polygonize)

    polygons_by_layer, report = compute_polygons_for_layers(
        {"LayerA": [[[0, 0], [10, 0]]]},
        structural_helper_paths_by_layer={"LayerA": [[[0, 10], [10, 10]]]},
    )

    assert captured == {"helper_count": 1}
    assert polygons_by_layer == {"LayerA": [candidate]}
    assert report.fills[0].strategy == "structural_open_loop"


def test_compute_polygons_does_not_inject_low_confidence_fallback(monkeypatch):
    """Fallback alpha/bbox candidates stay in the report but are not injected."""
    candidate = Polygon([(0, 0), (10, 0), (5, 10)])

    def fake_polygonize(*_args, **_kwargs):
        return [candidate], FillResult("LayerA", "alpha_shape", 0.55, 1, 3)

    monkeypatch.setattr("arch_line_weights.poche_saas.polygonize_layer", fake_polygonize)
    polygons_by_layer, report = compute_polygons_for_layers(
        {"LayerA": [[[0, 0], [10, 0]]]}
    )

    assert polygons_by_layer == {}
    assert report.polygons == {}
    assert report.fills[0].strategy == "alpha_shape"
    assert report.fills[0].polygon_count == 1


def test_compute_polygons_can_opt_into_low_confidence_injection(monkeypatch):
    """The old permissive behavior remains reachable through an env var."""
    candidate = Polygon([(0, 0), (10, 0), (5, 10)])

    def fake_polygonize(*_args, **_kwargs):
        return [candidate], FillResult("LayerA", "bbox", 0.3, 1, 3)

    monkeypatch.setenv("ARCH_LW_POCHE_ALLOW_LOW_CONFIDENCE", "1")
    monkeypatch.setattr("arch_line_weights.poche_saas.polygonize_layer", fake_polygonize)

    polygons_by_layer, report = compute_polygons_for_layers(
        {"LayerA": [[[0, 0], [10, 0]]]}
    )

    assert polygons_by_layer == {"LayerA": [candidate]}
    assert "LayerA" in report.polygons


# --------------------------------------------------------------------------- #
# 5. End-to-end: apply_saas_with_poche on a synthetic fixture
# --------------------------------------------------------------------------- #


def test_apply_saas_with_poche_end_to_end_on_synthetic_fixture():
    """write_synthetic + apply_saas_with_poche produces a valid file with fills.

    Verifies the full pipeline:
      - synthetic .ai fixture is built and saved by pikepdf
      - apply_saas_with_poche reads it, polygonizes the cut layer, rewrites
        widths, injects polygons, recompresses, saves
      - the resulting .ai's decompressed payload contains the injected fill
        operators in the right layer
    """
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "synthetic.ai")
        dst = os.path.join(tmp, "synthetic_OUT.ai")
        cut_layer = "axon::Visible::ClippingPlaneIntersections::TEST_CUT"
        write_synthetic_test_ai(src, layer_name=cut_layer)
        assert os.path.exists(src)

        apply_res, poche_res, _poche_report = apply_saas_with_poche(
            src,
            dst,
            rgb_to_weight={(0, 0, 0): 0.5},
            default_width=0.25,
        )
        assert os.path.exists(dst)

        # 1 layer was targeted, 1 was injected
        assert poche_res.layers_targeted == 1
        assert poche_res.layers_injected == 1
        assert poche_res.polygons_injected >= 1
        # B6 stroke-width rewrite still ran
        assert apply_res.widths_rewritten >= 1
        assert apply_res.xa_seen >= 1

        # The output decompresses cleanly
        with pikepdf.open(dst) as pdf:
            new_payload = _read_payload(pdf)
        # Fill color setter is in the payload
        assert b"0 0 0 1 1 0 0 0 Xa\r" in new_payload
        # Fill operator is in the payload (the `f` we synthesized)
        assert b"\rf\r" in new_payload
        # The original layer name marker is preserved
        assert (
            b"(axon::Visible::ClippingPlaneIntersections::TEST_CUT) Ln\r"
            in new_payload
        )


def test_inspect_falls_back_to_private_payload_cmyk_colors(tmp_path):
    """Converted AI files can have no public PDF strokes but CMYK native colors."""
    from arch_line_weights.inspect import inspect_file

    payload = (
        b"%!PS-Adobe-3.0\r"
        b"%AI5_BeginLayer\r"
        b"(axon::Visible::ClippingPlaneIntersections::CMYK) Ln\r"
        b"0.1765 0.2745 0.4314 0.1765 K\r"
        b"1 J 1 j 1 w 4 M []0 d\r"
        b"0 0 m\r"
        b"10 10 L\r"
        b"S\r"
        b"LB\r"
        b"%AI5_EndLayer--\r"
    )
    framed = compress_test_payload(payload)
    chunks = [framed[i : i + CHUNK] for i in range(0, len(framed), CHUNK)]

    src = tmp_path / "private-cmyk.ai"
    pdf = pikepdf.new()
    pdf.add_blank_page(page_size=(200, 200))
    page = pdf.pages[0]
    priv = pikepdf.Dictionary({"/NumBlock": len(chunks)})
    for i, chunk in enumerate(chunks, start=1):
        priv[f"/AIPrivateData{i}"] = pdf.make_stream(chunk)
    page.obj["/PieceInfo"] = pikepdf.Dictionary(
        {"/Illustrator": pikepdf.Dictionary({"/Private": priv})}
    )
    pdf.save(str(src))
    pdf.close()

    rep = inspect_file(str(src))

    assert rep.total_stroked == 1
    assert rep.stroke_colors == {"RGB(173,152,119)": 1}
    assert rep.width_by_color["RGB(173,152,119)"]["1.0"] == 1


def test_apply_saas_with_poche_rejects_same_src_dst():
    """Defensive: src == dst should raise to avoid clobbering the original."""
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "x.ai")
        write_synthetic_test_ai(src, layer_name="X")
        with pytest.raises(ValueError):
            apply_saas_with_poche(src, src, rgb_to_weight={})


def test_polygon_with_no_layers_is_safe_noop():
    """An empty polygons_by_layer dict should leave the payload unchanged."""
    payload = _build_minimal_payload(["LayerA"])
    out = inject_poche_polygons(payload, {})
    assert out == payload
