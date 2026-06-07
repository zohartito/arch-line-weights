from __future__ import annotations

import contextlib
import json

import pikepdf
from click.testing import CliRunner

from arch_line_weights.cli import cli
from arch_line_weights.drawing_type import classify_drawing_type


def _write_ai(path, color_blocks, *, layer_names=None, title: str | None = None) -> None:
    pdf = pikepdf.new()
    pdf.add_blank_page(page_size=(240, 180))
    page = pdf.pages[0]
    page.obj["/PieceInfo"] = pikepdf.Dictionary(
        {"/Illustrator": pikepdf.Dictionary({"/Private": pikepdf.Dictionary({"/NumBlock": 0})})}
    )
    if title:
        pdf.docinfo["/Title"] = title

    parts: list[bytes] = []
    for i, (r, g, b) in enumerate(color_blocks):
        parts.append(f"{r / 255:.4f} {g / 255:.4f} {b / 255:.4f} RG".encode())
        parts.append(b"0.5 w")
        parts.append(f"q 1 0 0 1 {i * 8} {i * 6} cm 0 0 m 12 9 l S Q".encode())

    if layer_names:
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

    page.Contents = pdf.make_stream(b"\n".join(parts) + b"\n")
    pdf.save(str(path))
    pdf.close()


def _all_output(result) -> str:
    out = result.output or ""
    with contextlib.suppress(ValueError, AttributeError):
        out += result.stderr or ""
    return out


def test_section_classifier_uses_clipping_plane_layer_signal() -> None:
    guess = classify_drawing_type(
        layer_names=[
            "Make2D::Visible::ClippingPlaneIntersections::TEC_CONCRETE",
            "Make2D::Visible::Curves::WINDOW_FRAME",
        ]
    )

    assert guess.kind == "section"
    assert guess.confidence >= 0.8
    assert "clipping plane" in guess.explanation.lower()


def test_plan_classifier_uses_floor_plan_terms() -> None:
    guess = classify_drawing_type(
        pdf_metadata={"/Title": "Level 02 floor plan"},
        layer_names=["A-WALL-FULL", "A-DOOR", "ROOM_TAGS", "FURNITURE"],
    )

    assert guess.kind == "plan"
    assert guess.confidence >= 0.75
    assert "plan" in guess.explanation.lower()


def test_explicit_preset_overrides_inference() -> None:
    guess = classify_drawing_type(
        explicit_preset="elevation",
        layer_names=["A-WALL-MCUT", "LEVEL 01 FLOOR PLAN", "ROOM_TAGS"],
    )

    assert guess.kind == "elevation"
    assert guess.confidence == 1.0
    assert "explicit --preset elevation" in guess.explanation


def test_inspect_report_surfaces_drawing_type(tmp_path) -> None:
    src = tmp_path / "axon.ai"
    _write_ai(
        src,
        [(10, 10, 10), (120, 120, 120), (220, 220, 220)],
        layer_names=["axon::Visible::Curves::ROOF_EDGE"],
        title="exploded axonometric diagram",
    )

    result = CliRunner().invoke(cli, ["inspect", str(src)])
    assert result.exit_code == 0, _all_output(result)
    data, _end = json.JSONDecoder().raw_decode(result.output)

    assert data["drawing_type"]["kind"] == "axon"
    assert data["drawing_type"]["confidence"] >= 0.8
    assert "# drawing-type: axon" in _all_output(result)


def test_apply_dry_run_names_inferred_type_and_selected_preset(tmp_path) -> None:
    src = tmp_path / "plan.ai"
    _write_ai(
        src,
        [(10, 10, 10), (90, 90, 90), (160, 160, 160)],
        layer_names=["A-WALL-FULL", "A-DOOR", "ROOM_TAGS"],
        title="ground floor plan",
    )

    result = CliRunner().invoke(
        cli,
        ["apply", "--auto", "--dry-run", "--preset", "elevation", str(src)],
    )

    assert result.exit_code == 0, _all_output(result)
    output = _all_output(result)
    assert "# drawing-type: plan" in output
    assert "# selected preset: elevation (explicit --preset override)" in output
