from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pikepdf
from click.testing import CliRunner

from arch_line_weights.apply import apply_to_file
from arch_line_weights.architectural import (
    architectural_layer_color_resolver,
    architectural_layer_solid_line_resolver,
    architectural_layer_weight_resolver,
)
from arch_line_weights.cli import cli


def _write_marked_content_pdf(path: Path, content: bytes, properties: dict[str, str] | None = None) -> None:
    pdf = pikepdf.new()
    pdf.add_blank_page(page_size=(200, 200))
    page = pdf.pages[0]
    property_dict = pikepdf.Dictionary()
    ocgs = []
    for key, layer_name in (properties or {}).items():
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
    if ocgs:
        pdf.Root["/OCProperties"] = pikepdf.Dictionary(
            {
                "/OCGs": pikepdf.Array(ocgs),
                "/D": pikepdf.Dictionary({"/Order": pikepdf.Array(ocgs), "/BaseState": pikepdf.Name("/ON")}),
            }
        )
    page.Contents = pdf.make_stream(content)
    pdf.save(path)
    pdf.close()


def _ops(path: Path):
    with pikepdf.open(path) as pdf:
        return [
            (list(operands), str(operator))
            for operands, operator in pikepdf.parse_content_stream(pdf.pages[0])
        ]


def test_apply_uses_marked_content_ocg_layer_to_override_color_mapping(tmp_path: Path) -> None:
    src = tmp_path / "section.pdf"
    dst = tmp_path / "section-out.pdf"
    _write_marked_content_pdf(
        src,
        b"/OC /MC0 BDC\n1 0 0 RG\n[] 0 d\n0 0 m 100 0 l S\nEMC\n",
        {"MC0": "axon::Visible::ClippingPlaneIntersections::TEC_CONCRETE_BASE"},
    )

    result = apply_to_file(
        str(src),
        str(dst),
        {(255, 0, 0): 0.13},
        default_width=0.25,
        layer_weight_resolver=architectural_layer_weight_resolver(preset="section"),
        layer_color_resolver=architectural_layer_color_resolver(preset="section"),
        layer_solid_line_resolver=architectural_layer_solid_line_resolver(preset="section"),
    )
    instructions = _ops(dst)

    assert result.marked_content_layers_seen == 1
    assert result.layer_weight_overrides == 1
    assert result.layer_color_overrides == 1
    assert result.layer_dash_overrides == 1
    assert result.weights_applied == {1.0: 1}
    assert ([Decimal("0"), Decimal("0"), Decimal("0")], "RG") in instructions
    assert ([Decimal("1")], "w") in instructions


def test_apply_warns_and_falls_back_when_marked_content_property_is_missing(tmp_path: Path) -> None:
    src = tmp_path / "missing-property.pdf"
    dst = tmp_path / "missing-property-out.pdf"
    _write_marked_content_pdf(
        src,
        b"/OC /MC_MISSING BDC\n1 0 0 RG\n0 0 m 100 0 l S\nEMC\n",
        {},
    )

    result = apply_to_file(
        str(src),
        str(dst),
        {(255, 0, 0): 0.13},
        default_width=0.25,
        layer_weight_resolver=lambda _name: 1.0,
    )

    assert result.marked_content_layers_seen == 0
    assert result.layer_weight_overrides == 0
    assert result.weights_applied == {0.13: 1}
    assert any("unresolved marked-content OCG property /MC_MISSING" in warning for warning in result.warnings)


def test_apply_warns_and_falls_back_when_marked_content_is_unbalanced(tmp_path: Path) -> None:
    src = tmp_path / "unbalanced.pdf"
    dst = tmp_path / "unbalanced-out.pdf"
    _write_marked_content_pdf(
        src,
        b"EMC\n1 0 0 RG\n0 0 m 100 0 l S\n",
        {},
    )

    result = apply_to_file(
        str(src),
        str(dst),
        {(255, 0, 0): 0.13},
        default_width=0.25,
        layer_weight_resolver=lambda _name: 1.0,
    )

    assert result.layer_weight_overrides == 0
    assert result.weights_applied == {0.13: 1}
    assert result.marked_content_malformed == 1
    assert any("EMC without matching BDC/BMC" in warning for warning in result.warnings)


def test_apply_cli_architectural_uses_marked_content_layer_overrides(tmp_path: Path) -> None:
    src = tmp_path / "section.pdf"
    dst = tmp_path / "section-out.pdf"
    mapping = tmp_path / "mapping.json"
    mapping.write_text('{"RGB(255,0,0)": 0.13}', encoding="utf-8")
    _write_marked_content_pdf(
        src,
        b"/OC /MC0 BDC\n1 0 0 RG\n0 0 m 100 0 l S\nEMC\n",
        {"MC0": "axon::Visible::ClippingPlaneIntersections::TEC_CONCRETE_BASE"},
    )

    result = CliRunner().invoke(
        cli,
        [
            "apply",
            str(src),
            "--mapping",
            str(mapping),
            "--architectural",
            "-o",
            str(dst),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "architectural layer overrides" in result.output
    assert "architectural color overrides" in result.output
    instructions = _ops(dst)
    assert ([Decimal("0"), Decimal("0"), Decimal("0")], "RG") in instructions
    assert ([Decimal("1")], "w") in instructions
