from __future__ import annotations

import json

import pikepdf
from click.testing import CliRunner

from arch_line_weights.classify import auto_by_role
from arch_line_weights.cli import cli
from arch_line_weights.depth import summarize_depth_evidence
from arch_line_weights.inspect import InspectionReport


def _report(depth_by_color: dict[str, dict] | None = None) -> InspectionReport:
    colors = {
        "RGB(20,20,20)": 1,
        "RGB(80,80,80)": 1,
        "RGB(120,120,120)": 1,
        "RGB(160,160,160)": 1,
        "RGB(220,220,220)": 1,
    }
    return InspectionReport(
        file="fixture.ai",
        pages=1,
        width_pt=200,
        height_pt=200,
        total_drawings=5,
        total_stroked=5,
        stroke_colors=colors,
        depth_by_color=depth_by_color or {},
    )


def _write_ai(path, *, layer_names: list[str]) -> None:
    pdf = pikepdf.new()
    pdf.add_blank_page(page_size=(240, 180))
    page = pdf.pages[0]
    page.obj["/PieceInfo"] = pikepdf.Dictionary(
        {"/Illustrator": pikepdf.Dictionary({"/Private": pikepdf.Dictionary({"/NumBlock": 0})})}
    )

    ocgs = []
    props = {}
    for i, name in enumerate(layer_names):
        ocg = pdf.make_indirect(
            pikepdf.Dictionary({"/Type": pikepdf.Name("/OCG"), "/Name": pikepdf.String(name)})
        )
        ocgs.append(ocg)
        props[f"/MC{i}"] = ocg
    page.obj["/Resources"] = pikepdf.Dictionary({"/Properties": pikepdf.Dictionary(props)})
    pdf.Root["/OCProperties"] = pikepdf.Dictionary(
        {
            "/OCGs": pikepdf.Array(ocgs),
            "/D": pikepdf.Dictionary({"/Order": pikepdf.Array(ocgs), "/BaseState": pikepdf.Name("/ON")}),
        }
    )

    page.Contents = pdf.make_stream(
        b"\n".join(
            [
                b"0.0784 0.0784 0.0784 RG",
                b"0.5 w",
                b"0 0 m 10 10 l S",
                b"0.4706 0.4706 0.4706 RG",
                b"0.5 w",
                b"10 10 m 20 20 l S",
            ]
        )
        + b"\n"
    )
    pdf.save(str(path))
    pdf.close()


def _json_prefix(output: str) -> dict:
    data, _end = json.JSONDecoder().raw_decode(output)
    return data


def test_z_backed_depth_grading_recedes_far_equal_role_color() -> None:
    rep = _report(
        {
            "RGB(120,120,120)": {"z": 0.0, "confidence": 0.95},
            "RGB(160,160,160)": {"z": 40.0, "confidence": 0.95},
        }
    )

    weights, _linetypes = auto_by_role(rep, "elevation", "1/4", True)

    assert weights[(120, 120, 120)] > weights[(160, 160, 160)]


def test_overlap_only_depth_grading_uses_confident_occlusion_order() -> None:
    rep = _report(
        {
            "RGB(120,120,120)": {"overlap_index": 0.95, "confidence": 0.75},
            "RGB(160,160,160)": {"overlap_index": 0.10, "confidence": 0.75},
        }
    )

    weights, _linetypes = auto_by_role(rep, "elevation", "1/4", True)

    assert weights[(120, 120, 120)] > weights[(160, 160, 160)]


def test_low_confidence_depth_falls_back_to_v1_role_ladder() -> None:
    baseline, _ = auto_by_role(_report(), "elevation", "1/4", True)
    uncertain = _report(
        {
            "RGB(120,120,120)": {"z": 0.0, "confidence": 0.30},
            "RGB(160,160,160)": {"z": 40.0, "confidence": 0.30},
        }
    )

    weights, _linetypes = auto_by_role(uncertain, "elevation", "1/4", True)

    assert weights == baseline
    summary = summarize_depth_evidence(depth_by_color=uncertain.depth_by_color)
    assert summary.source == "fallback"
    assert "low-confidence" in summary.explanation


def test_inspect_surfaces_depth_source_from_layer_metadata(tmp_path) -> None:
    src = tmp_path / "depth.ai"
    _write_ai(src, layer_names=["Make2D::Visible::Z=0::FOREGROUND", "Make2D::Visible::Z=25::BACKGROUND"])

    result = CliRunner().invoke(cli, ["inspect", str(src)])

    assert result.exit_code == 0, result.output
    data = _json_prefix(result.output)
    assert data["depth_evidence"]["source"] == "z"
    assert data["depth_evidence"]["confidence"] >= 0.8
    assert "# depth: z" in result.output
