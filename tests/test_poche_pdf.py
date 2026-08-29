"""Tests for pure-PDF poché (issue #83)."""

from __future__ import annotations

import json
from pathlib import Path

import pikepdf
import pytest
from click.testing import CliRunner

from arch_line_weights.cli import cli
from arch_line_weights.poche_pdf import (
    apply_poche_pdf,
    enumerate_cut_layer_paths_from_page,
    polygonize_cut_layers,
)

CUT_LAYER = "axon::Visible::ClippingPlaneIntersections::TEC_CONCRETE_BASE"
CLT_LAYER = "axon::Visible::ClippingPlaneIntersections::TEC_ROOF_CLT"
PROJECTED_LAYER = "axon::Visible::Curves::TEC_CONCRETE_BASE"
STEEL_LAYER = "axon::Visible::ClippingPlaneIntersections::METAL_FLASHING"


def _write_ocg_pdf(path: Path, content: bytes, properties: dict[str, str]) -> None:
    pdf = pikepdf.new()
    pdf.add_blank_page(page_size=(400, 400))
    page = pdf.pages[0]
    property_dict = pikepdf.Dictionary()
    ocgs = []
    for key, layer_name in properties.items():
        ocg = pdf.make_indirect(
            pikepdf.Dictionary(
                {
                    "/Type": pikepdf.Name("/OCG"),
                    "/Name": pikepdf.String(layer_name),
                }
            )
        )
        ocgs.append(ocg)
        property_dict[f"/{key}"] = ocg
    page.obj["/Resources"] = pikepdf.Dictionary({"/Properties": property_dict})
    pdf.Root["/OCProperties"] = pikepdf.Dictionary(
        {
            "/OCGs": pikepdf.Array(ocgs),
            "/D": pikepdf.Dictionary({"/Order": pikepdf.Array(ocgs), "/BaseState": pikepdf.Name("/ON")}),
        }
    )
    page.Contents = pdf.make_stream(content)
    pdf.save(path)
    pdf.close()


def _closed_square_content(mc: str, x0: float, y0: float, size: float = 40.0) -> bytes:
    x1, y1 = x0 + size, y0 + size
    return (
        f"/OC /{mc} BDC\n"
        f"0 0 0 RG\n"
        f"{x0:g} {y0:g} m {x1:g} {y0:g} l {x1:g} {y1:g} l {x0:g} {y1:g} l h S\n"
        f"EMC\n"
    ).encode()


def _open_gap_square_content(mc: str, x0: float, y0: float, size: float = 40.0, gap: float = 8.0) -> bytes:
    """Three sides of a square — low-confidence / open loop without bridging."""
    x1, y1 = x0 + size, y0 + size
    return (
        f"/OC /{mc} BDC\n"
        f"0 0 0 RG\n"
        f"{x0:g} {y0:g} m {x1:g} {y0:g} l S\n"
        f"{x1:g} {y0:g} m {x1:g} {y1:g} l S\n"
        f"{x1:g} {y1:g} m {x0 + gap:g} {y1:g} l S\n"
        f"EMC\n"
    ).encode()


def _ops(path: Path):
    with pikepdf.open(path) as pdf:
        return [(list(operands), str(operator)) for operands, operator in pikepdf.parse_content_stream(pdf.pages[0])]


def _fill_count(path: Path) -> int:
    return sum(1 for _ops, op in _ops(path) if op == "f")


def test_enumerate_extracts_cut_layer_closed_loop(tmp_path: Path) -> None:
    src = tmp_path / "cut.pdf"
    _write_ocg_pdf(src, _closed_square_content("MC0", 10, 10), {"MC0": CUT_LAYER})
    with pikepdf.open(src) as pdf:
        paths, kinds = enumerate_cut_layer_paths_from_page(pdf.pages[0])
    assert kinds["cut"] == 1
    assert kinds["non_cut"] == 0
    assert CUT_LAYER in paths
    assert len(paths[CUT_LAYER]) >= 1
    assert len(paths[CUT_LAYER][0]) >= 4


def test_enumerate_ignores_projected_non_cut_geometry(tmp_path: Path) -> None:
    src = tmp_path / "projected.pdf"
    content = _closed_square_content("MC0", 10, 10) + _closed_square_content("MC1", 80, 80)
    # Rewrite second block's layer name binding to projected curves
    _write_ocg_pdf(
        src,
        content.replace(b"/MC1", b"/MC1"),
        {"MC0": CUT_LAYER, "MC1": PROJECTED_LAYER},
    )
    with pikepdf.open(src) as pdf:
        paths, kinds = enumerate_cut_layer_paths_from_page(pdf.pages[0])
    assert kinds["cut"] == 1
    assert kinds["non_cut"] == 1
    assert CUT_LAYER in paths
    assert PROJECTED_LAYER not in paths


def test_polygonize_injects_high_confidence_closed_loop() -> None:
    paths = {
        CUT_LAYER: [
            [[0.0, 0.0], [40.0, 0.0], [40.0, 40.0], [0.0, 40.0], [0.0, 0.0]],
        ]
    }
    report = polygonize_cut_layers(paths, use_alpha_shape=False, bridge_strategy="greedy")
    assert len(report.fills) == 1
    assert report.fills[0].confidence >= 0.85
    assert CUT_LAYER in report.polygons
    assert len(report.polygons[CUT_LAYER]) >= 1


def test_polygonize_holds_back_low_confidence_open_geometry(monkeypatch) -> None:
    monkeypatch.delenv("ARCH_LW_POCHE_ALLOW_LOW_CONFIDENCE", raising=False)
    monkeypatch.setenv("ARCH_LW_POCHE_MIN_INJECT_CONFIDENCE", "0.85")
    # Two short disconnected segments — should not become an injected fill.
    paths = {
        CUT_LAYER: [
            [[0.0, 0.0], [10.0, 0.0]],
            [[100.0, 100.0], [110.0, 100.0]],
        ]
    }
    report = polygonize_cut_layers(paths, use_alpha_shape=False, bridge_strategy="greedy")
    assert len(report.fills) == 1
    assert CUT_LAYER not in report.polygons
    assert report.fills[0].strategy in {"failed", "bbox", "concave_hull", "alpha_shape"} or (
        report.fills[0].confidence < 0.85
    )


def test_apply_poche_pdf_injects_fill_operator(tmp_path: Path) -> None:
    src = tmp_path / "section.pdf"
    dst = tmp_path / "section-out.pdf"
    _write_ocg_pdf(src, _closed_square_content("MC0", 20, 20), {"MC0": CUT_LAYER})
    result = apply_poche_pdf(str(src), str(dst), style="solid", use_alpha_shape=False, bridge_strategy="greedy")
    assert result.fills_injected >= 1
    assert _fill_count(dst) >= 1
    assert result.report_json["schema_version"] == 2
    assert result.report_json["source"]["command"] == "poche-pdf"
    assert result.report_json["summary"]["polygons_injected"] >= 1
    layer = next(L for L in result.report_json["layers"] if L["layer"] == CUT_LAYER)
    assert layer["status"] in {"filled", "inferred"}
    assert layer["action"] == "injected"
    assert "confidence" in layer
    assert "strategy" in layer


def test_apply_poche_pdf_never_fills_projected_geometry(tmp_path: Path) -> None:
    src = tmp_path / "projected.pdf"
    dst = tmp_path / "projected-out.pdf"
    content = (
        _closed_square_content("MC0", 10, 10).replace(b"MC0", b"MC0")
        + b"/OC /MC1 BDC\n0 0 0 RG\n200 200 m 240 200 l 240 240 l 200 240 l h S\nEMC\n"
    )
    _write_ocg_pdf(src, content, {"MC0": PROJECTED_LAYER, "MC1": PROJECTED_LAYER})
    # Use a distinct second projected name
    _write_ocg_pdf(
        src,
        b"/OC /MC0 BDC\n0 0 0 RG\n10 10 m 50 10 l 50 50 l 10 50 l h S\nEMC\n",
        {"MC0": PROJECTED_LAYER},
    )
    result = apply_poche_pdf(str(src), str(dst), style="solid")
    assert result.fills_injected == 0
    assert result.cut_layers_seen == 0
    assert result.non_cut_layers_seen == 1
    assert _fill_count(dst) == 0
    assert result.report_json["summary"]["polygons_injected"] == 0


def test_apply_poche_pdf_preserves_gap_on_open_cut(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("ARCH_LW_POCHE_ALLOW_LOW_CONFIDENCE", raising=False)
    monkeypatch.setenv("ARCH_LW_POCHE_MIN_INJECT_CONFIDENCE", "0.85")
    src = tmp_path / "gap.pdf"
    dst = tmp_path / "gap-out.pdf"
    _write_ocg_pdf(src, _open_gap_square_content("MC0", 10, 10, size=60, gap=25), {"MC0": CUT_LAYER})
    result = apply_poche_pdf(
        str(src),
        str(dst),
        style="solid",
        use_alpha_shape=False,
        bridge_strategy="greedy",
    )
    # Open geometry with a large gap must not silently fill.
    if result.fills_injected:
        # If a strategy somehow closed it at high confidence, still require report honesty.
        layer = result.report_json["layers"][0]
        assert layer["confidence"] >= 0.85
    else:
        assert result.report_json["summary"]["polygons_injected"] == 0
        assert any(L["status"] in {"low_confidence", "failed"} for L in result.report_json["layers"])


def test_apply_poche_pdf_byte_deterministic(tmp_path: Path) -> None:
    src = tmp_path / "det.pdf"
    a = tmp_path / "a.pdf"
    b = tmp_path / "b.pdf"
    _write_ocg_pdf(
        src,
        _closed_square_content("MC0", 15, 15) + _closed_square_content("MC1", 100, 100),
        {"MC0": CUT_LAYER, "MC1": CLT_LAYER},
    )
    r1 = apply_poche_pdf(str(src), str(a), style="solid", use_alpha_shape=False, bridge_strategy="greedy")
    r2 = apply_poche_pdf(str(src), str(b), style="solid", use_alpha_shape=False, bridge_strategy="greedy")
    assert a.read_bytes() == b.read_bytes()
    assert r1.fills_injected == r2.fills_injected
    assert r1.fills_injected >= 2


def test_material_style_injects_hatch_strokes(tmp_path: Path) -> None:
    src = tmp_path / "mat.pdf"
    dst = tmp_path / "mat-out.pdf"
    _write_ocg_pdf(src, _closed_square_content("MC0", 10, 10, size=80), {"MC0": CUT_LAYER})
    result = apply_poche_pdf(
        str(src),
        str(dst),
        style="material",
        scale=1.0,
        use_alpha_shape=False,
        bridge_strategy="greedy",
    )
    assert result.fills_injected >= 1
    assert result.hatch_segments_injected >= 1
    ops = _ops(dst)
    assert any(op == "S" for _o, op in ops)
    assert any(op == "f" for _o, op in ops)


def test_steel_cut_layer_gets_solid_fill(tmp_path: Path) -> None:
    src = tmp_path / "steel.pdf"
    dst = tmp_path / "steel-out.pdf"
    _write_ocg_pdf(src, _closed_square_content("MC0", 5, 5, size=12), {"MC0": STEEL_LAYER})
    result = apply_poche_pdf(str(src), str(dst), style="solid", use_alpha_shape=False, bridge_strategy="greedy")
    assert result.fills_injected >= 1
    layer = result.report_json["layers"][0]
    assert layer["action"] == "injected"


def test_report_json_parity_fields(tmp_path: Path) -> None:
    src = tmp_path / "rep.pdf"
    dst = tmp_path / "rep-out.pdf"
    report_path = tmp_path / "r.json"
    _write_ocg_pdf(src, _closed_square_content("MC0", 20, 20), {"MC0": CUT_LAYER})
    result = apply_poche_pdf(
        str(src),
        str(dst),
        report_json_path=str(report_path),
        use_alpha_shape=False,
        bridge_strategy="greedy",
    )
    data = json.loads(report_path.read_text())
    assert data == result.report_json
    assert set(data.keys()) >= {"schema_version", "source", "summary", "layers", "limitations"}
    assert "status" in data["summary"]
    assert "why" in data["summary"]
    assert "next_action" in data["summary"]
    layer = data["layers"][0]
    for key in ("status", "action", "confidence", "strategy", "review"):
        assert key in layer
    assert "needs_review" in layer["review"]


def test_cli_poche_pdf_smoke(tmp_path: Path) -> None:
    src = tmp_path / "cli.pdf"
    dst = tmp_path / "cli-out.pdf"
    report = tmp_path / "cli.json"
    _write_ocg_pdf(src, _closed_square_content("MC0", 30, 30), {"MC0": CUT_LAYER})
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["poche-pdf", str(src), "-o", str(dst), "--report-json", str(report), "--bridge-strategy", "greedy"],
    )
    assert result.exit_code == 0, result.output
    assert dst.exists()
    assert report.exists()
    data = json.loads(report.read_text())
    assert data["summary"]["polygons_injected"] >= 1
    assert _fill_count(dst) >= 1


def test_negative_mixed_cut_and_projected_only_fills_cut(tmp_path: Path) -> None:
    src = tmp_path / "mixed.pdf"
    dst = tmp_path / "mixed-out.pdf"
    content = (
        b"/OC /MC0 BDC\n0 0 0 RG\n10 10 m 50 10 l 50 50 l 10 50 l h S\nEMC\n"
        b"/OC /MC1 BDC\n0 0 0 RG\n200 200 m 260 200 l 260 260 l 200 260 l h S\nEMC\n"
    )
    _write_ocg_pdf(src, content, {"MC0": CUT_LAYER, "MC1": PROJECTED_LAYER})
    result = apply_poche_pdf(str(src), str(dst), use_alpha_shape=False, bridge_strategy="greedy")
    assert result.cut_layers_seen == 1
    assert result.non_cut_layers_seen == 1
    assert result.fills_injected >= 1
    assert all(PROJECTED_LAYER not in name for name in result.report.polygons)
    assert CUT_LAYER in result.report.polygons


def test_same_src_dst_rejected(tmp_path: Path) -> None:
    src = tmp_path / "same.pdf"
    _write_ocg_pdf(src, _closed_square_content("MC0", 1, 1), {"MC0": CUT_LAYER})
    with pytest.raises(ValueError, match="dst must differ"):
        apply_poche_pdf(str(src), str(src))
