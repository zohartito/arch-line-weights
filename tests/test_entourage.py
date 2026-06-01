from __future__ import annotations

from xml.etree import ElementTree

import pytest

from arch_line_weights.architectural import (
    architectural_weight_for_tier,
    classify_architectural_layer,
)
from arch_line_weights.entourage import (
    DEFAULT_ENTOURAGE_LAYER,
    DEFAULT_ENTOURAGE_POSTURES,
    EntourageStyle,
    generate_entourage_library,
    generate_iso_person_svg,
)
from arch_line_weights.poche_saas import _is_cut_layer

SVG_NS = "{http://www.w3.org/2000/svg}"
PURE_BLACK_VALUES = {"#000", "#000000", "black", "rgb(0,0,0)", "rgb(0, 0, 0)"}


def _parse_svg(svg: str) -> ElementTree.Element:
    return ElementTree.fromstring(svg)


def _stroke_widths(root: ElementTree.Element) -> list[float]:
    widths: list[float] = []
    for element in root.iter():
        value = element.attrib.get("stroke-width")
        if value:
            widths.append(float(value.replace("pt", "")))
    return widths


def _attribute_values(root: ElementTree.Element, name: str) -> set[str]:
    return {
        value.strip().lower() for element in root.iter() if (value := element.attrib.get(name)) is not None
    }


def test_generate_entourage_library_creates_minimum_postures_on_light_layers():
    assets = generate_entourage_library()

    assert [asset.posture for asset in assets] == list(DEFAULT_ENTOURAGE_POSTURES)
    assert {asset.layer for asset in assets} == {
        f"{DEFAULT_ENTOURAGE_LAYER}::{posture.title()}" for posture in DEFAULT_ENTOURAGE_POSTURES
    }

    max_entourage_weight = architectural_weight_for_tier("entourage", preset="section")
    for asset in assets:
        root = _parse_svg(asset.svg)
        assert root.tag == f"{SVG_NS}svg"
        assert root.attrib["data-layer"] == asset.layer
        assert root.attrib["data-arch-lw-tier"] == "entourage"

        widths = _stroke_widths(root)
        assert widths
        assert max(widths) <= max_entourage_weight

        assignment = classify_architectural_layer(asset.layer, preset="section")
        assert assignment.tier == "entourage"
        assert assignment.poche is False
        assert (
            _is_cut_layer(
                f"axon::Visible::ClippingPlaneIntersections::{asset.layer}",
                architectural=True,
            )
            is False
        )


@pytest.mark.parametrize(
    "layer",
    [
        "Entourage::People",
        "axon::Visible::Entourage::People::Standing",
        "axon::Visible::ClippingPlaneIntersections::Entourage::People",
        "axon::Visible::ClippingPlaneIntersections::ScaleFigures",
    ],
)
def test_entourage_aliases_are_never_cut_weight_or_poche(layer):
    assignment = classify_architectural_layer(layer, preset="section")

    assert assignment.tier == "entourage"
    assert assignment.weight_pt == architectural_weight_for_tier("entourage", preset="section")
    assert assignment.poche is False
    assert assignment.open_loop_closure is False
    assert _is_cut_layer(layer, architectural=True) is False


@pytest.mark.parametrize("attribute", ["fill", "stroke"])
def test_generated_entourage_uses_gray_editable_vectors_not_pure_black(attribute):
    style = EntourageStyle(stroke_width_pt=0.12, tone=55, shadow=True)
    svg = generate_iso_person_svg("standing", direction="ne", height_pt=96.0, style=style)
    root = _parse_svg(svg)

    values = _attribute_values(root, attribute)

    assert values
    assert values.isdisjoint(PURE_BLACK_VALUES)
    assert "currentcolor" not in values


def test_generated_entourage_has_foot_anchor_and_shadow_review_layer():
    svg = generate_iso_person_svg("leaning", direction="nw", height_pt=84.0)
    root = _parse_svg(svg)

    assert root.attrib["data-layer"] == f"{DEFAULT_ENTOURAGE_LAYER}::Leaning"
    assert root.attrib["data-anchor"] == "foot-contact"
    assert any(
        element.attrib.get("data-layer") == f"{DEFAULT_ENTOURAGE_LAYER}::Shadows" for element in root.iter()
    )
