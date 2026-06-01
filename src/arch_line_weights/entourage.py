"""Small generated vector entourage assets.

The generator intentionally stays separate from poché and geometry repair. Its
outputs are presentation context: light, editable SVG groups on
``Entourage::People`` layers.
"""

from __future__ import annotations

from dataclasses import dataclass
from xml.etree import ElementTree

SVG_NS = "http://www.w3.org/2000/svg"
DEFAULT_ENTOURAGE_LAYER = "Entourage::People"
DEFAULT_ENTOURAGE_POSTURES = ("standing", "walking", "seated", "leaning")
DEFAULT_ENTOURAGE_DIRECTIONS = ("ne", "nw", "se", "sw")
MAX_ENTOURAGE_STROKE_PT = 0.13


@dataclass(frozen=True)
class EntourageStyle:
    stroke_width_pt: float = MAX_ENTOURAGE_STROKE_PT
    tone: int = 55
    shadow: bool = True
    figure_opacity: float = 0.88
    shadow_opacity: float = 0.18


@dataclass(frozen=True)
class EntourageAsset:
    name: str
    posture: str
    direction: str
    layer: str
    height_pt: float
    stroke_width_pt: float
    tone: int
    svg: str


def _tag(name: str) -> str:
    return f"{{{SVG_NS}}}{name}"


def _fmt(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".")


def _normalized_posture(posture: str) -> str:
    normalized = posture.lower().strip().replace("-", "_")
    if normalized not in DEFAULT_ENTOURAGE_POSTURES:
        allowed = ", ".join(DEFAULT_ENTOURAGE_POSTURES)
        raise ValueError(f"unsupported entourage posture {posture!r}; expected one of: {allowed}")
    return normalized


def _normalized_direction(direction: str) -> str:
    normalized = direction.lower().strip()
    if normalized not in DEFAULT_ENTOURAGE_DIRECTIONS:
        allowed = ", ".join(DEFAULT_ENTOURAGE_DIRECTIONS)
        raise ValueError(f"unsupported entourage direction {direction!r}; expected one of: {allowed}")
    return normalized


def _clamped_style(style: EntourageStyle) -> EntourageStyle:
    return EntourageStyle(
        stroke_width_pt=max(0.01, min(style.stroke_width_pt, MAX_ENTOURAGE_STROKE_PT)),
        tone=max(25, min(style.tone, 70)),
        shadow=style.shadow,
        figure_opacity=max(0.1, min(style.figure_opacity, 1.0)),
        shadow_opacity=max(0.05, min(style.shadow_opacity, 0.35)),
    )


def _gray_from_black_tone(tone: int) -> str:
    value = round(255 * (1 - tone / 100))
    value = max(1, min(value, 254))
    return f"#{value:02x}{value:02x}{value:02x}"


def _add_line(
    parent: ElementTree.Element,
    *,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    stroke: str,
    width: float,
    opacity: float,
) -> None:
    ElementTree.SubElement(
        parent,
        _tag("line"),
        {
            "x1": _fmt(x1),
            "y1": _fmt(y1),
            "x2": _fmt(x2),
            "y2": _fmt(y2),
            "stroke": stroke,
            "stroke-width": _fmt(width),
            "stroke-linecap": "round",
            "fill": "none",
            "opacity": _fmt(opacity),
        },
    )


def _add_path(
    parent: ElementTree.Element,
    *,
    d: str,
    stroke: str,
    width: float,
    opacity: float,
    fill: str = "none",
    fill_opacity: float | None = None,
) -> None:
    attrs = {
        "d": d,
        "stroke": stroke,
        "stroke-width": _fmt(width),
        "stroke-linecap": "round",
        "stroke-linejoin": "round",
        "fill": fill,
        "opacity": _fmt(opacity),
    }
    if fill_opacity is not None:
        attrs["fill-opacity"] = _fmt(fill_opacity)
    ElementTree.SubElement(parent, _tag("path"), attrs)


def _pose_lines(
    parent: ElementTree.Element,
    *,
    posture: str,
    stroke: str,
    width: float,
    opacity: float,
    height: float,
) -> None:
    scale = height / 96
    head_y = -84 * scale
    shoulder_y = -66 * scale
    hip_y = -38 * scale
    foot_y = -2 * scale
    shoulder = 8 * scale
    hip = 5 * scale

    head = ElementTree.SubElement(
        parent,
        _tag("circle"),
        {
            "cx": "0",
            "cy": _fmt(head_y),
            "r": _fmt(6 * scale),
            "stroke": stroke,
            "stroke-width": _fmt(width),
            "fill": _gray_from_black_tone(28),
            "fill-opacity": "0.16",
            "opacity": _fmt(opacity),
        },
    )
    head.attrib["data-part"] = "head"

    if posture == "walking":
        _add_path(
            parent,
            d=(f"M {_fmt(-shoulder)} {_fmt(shoulder_y)} L 0 {_fmt(-51 * scale)} L {_fmt(hip)} {_fmt(hip_y)}"),
            stroke=stroke,
            width=width,
            opacity=opacity,
        )
        limbs = [
            (-shoulder, shoulder_y, -17 * scale, -48 * scale),
            (shoulder, shoulder_y, 15 * scale, -56 * scale),
            (hip, hip_y, 18 * scale, foot_y),
            (-hip, hip_y, -13 * scale, -12 * scale),
            (-13 * scale, -12 * scale, -22 * scale, foot_y),
        ]
    elif posture == "seated":
        _add_path(
            parent,
            d=(
                f"M {_fmt(-shoulder)} {_fmt(shoulder_y)} "
                f"L {_fmt(-3 * scale)} {_fmt(-53 * scale)} L {_fmt(hip)} {_fmt(-42 * scale)}"
            ),
            stroke=stroke,
            width=width,
            opacity=opacity,
        )
        limbs = [
            (-shoulder, shoulder_y, -16 * scale, -55 * scale),
            (shoulder, shoulder_y, 13 * scale, -58 * scale),
            (hip, -42 * scale, 19 * scale, -32 * scale),
            (19 * scale, -32 * scale, 22 * scale, -9 * scale),
            (-hip, -42 * scale, -17 * scale, -31 * scale),
            (-17 * scale, -31 * scale, -10 * scale, -8 * scale),
        ]
    elif posture == "leaning":
        _add_path(
            parent,
            d=(
                f"M {_fmt(-shoulder)} {_fmt(shoulder_y)} "
                f"L {_fmt(5 * scale)} {_fmt(-53 * scale)} L {_fmt(hip)} {_fmt(hip_y)}"
            ),
            stroke=stroke,
            width=width,
            opacity=opacity,
        )
        limbs = [
            (-shoulder, shoulder_y, -22 * scale, -58 * scale),
            (shoulder, shoulder_y, 20 * scale, -62 * scale),
            (hip, hip_y, 12 * scale, foot_y),
            (-hip, hip_y, -9 * scale, foot_y),
        ]
        _add_line(
            parent,
            x1=18 * scale,
            y1=-66 * scale,
            x2=23 * scale,
            y2=-12 * scale,
            stroke=stroke,
            width=width * 0.82,
            opacity=opacity * 0.75,
        )
    else:
        _add_path(
            parent,
            d=(f"M {_fmt(-shoulder)} {_fmt(shoulder_y)} L 0 {_fmt(-52 * scale)} L {_fmt(hip)} {_fmt(hip_y)}"),
            stroke=stroke,
            width=width,
            opacity=opacity,
        )
        limbs = [
            (-shoulder, shoulder_y, -14 * scale, -48 * scale),
            (shoulder, shoulder_y, 13 * scale, -50 * scale),
            (hip, hip_y, 9 * scale, foot_y),
            (-hip, hip_y, -8 * scale, foot_y),
        ]

    for x1, y1, x2, y2 in limbs:
        _add_line(
            parent,
            x1=x1,
            y1=y1,
            x2=x2,
            y2=y2,
            stroke=stroke,
            width=width,
            opacity=opacity,
        )


def generate_iso_person_svg(
    posture: str,
    *,
    direction: str = "ne",
    height_pt: float = 96.0,
    style: EntourageStyle | None = None,
    layer: str = DEFAULT_ENTOURAGE_LAYER,
) -> str:
    """Generate one editable SVG scale figure on an entourage layer."""
    posture_key = _normalized_posture(posture)
    direction_key = _normalized_direction(direction)
    style = _clamped_style(style or EntourageStyle())
    height = max(24.0, float(height_pt))
    stroke = _gray_from_black_tone(style.tone)
    posture_layer = f"{layer}::{posture_key.title()}"

    ElementTree.register_namespace("", SVG_NS)
    root = ElementTree.Element(
        _tag("svg"),
        {
            "viewBox": f"{_fmt(-28 * height / 96)} {_fmt(-100 * height / 96)} "
            f"{_fmt(56 * height / 96)} {_fmt(106 * height / 96)}",
            "data-layer": posture_layer,
            "data-arch-lw-tier": "entourage",
            "data-posture": posture_key,
            "data-direction": direction_key,
            "data-anchor": "foot-contact",
        },
    )

    transform = "scale(-1 1)" if direction_key in {"nw", "sw"} else ""
    figure = ElementTree.SubElement(
        root,
        _tag("g"),
        {
            "id": f"person_{posture_key}_iso_{direction_key}",
            "data-layer": posture_layer,
            "transform": transform,
            "fill": "none",
            "stroke": stroke,
            "stroke-width": _fmt(style.stroke_width_pt),
        },
    )

    if style.shadow:
        shadow = ElementTree.SubElement(
            figure,
            _tag("ellipse"),
            {
                "cx": "0",
                "cy": "0",
                "rx": _fmt(13 * height / 96),
                "ry": _fmt(3 * height / 96),
                "fill": _gray_from_black_tone(38),
                "fill-opacity": _fmt(style.shadow_opacity),
                "stroke": "none",
                "data-layer": f"{layer}::Shadows",
            },
        )
        shadow.attrib["data-part"] = "contact-shadow"

    _pose_lines(
        figure,
        posture=posture_key,
        stroke=stroke,
        width=style.stroke_width_pt,
        opacity=style.figure_opacity,
        height=height,
    )
    return ElementTree.tostring(root, encoding="unicode")


def generate_entourage_library(
    *,
    direction: str = "ne",
    height_pt: float = 96.0,
    style: EntourageStyle | None = None,
    layer: str = DEFAULT_ENTOURAGE_LAYER,
) -> tuple[EntourageAsset, ...]:
    """Return the minimum issue #20 SVG library."""
    direction_key = _normalized_direction(direction)
    style = _clamped_style(style or EntourageStyle())
    assets: list[EntourageAsset] = []
    for posture in DEFAULT_ENTOURAGE_POSTURES:
        assets.append(
            EntourageAsset(
                name=f"person_{posture}_iso_{direction_key}_01",
                posture=posture,
                direction=direction_key,
                layer=f"{layer}::{posture.title()}",
                height_pt=max(24.0, float(height_pt)),
                stroke_width_pt=style.stroke_width_pt,
                tone=style.tone,
                svg=generate_iso_person_svg(
                    posture,
                    direction=direction_key,
                    height_pt=height_pt,
                    style=style,
                    layer=layer,
                ),
            )
        )
    return tuple(assets)


__all__ = [
    "DEFAULT_ENTOURAGE_DIRECTIONS",
    "DEFAULT_ENTOURAGE_LAYER",
    "DEFAULT_ENTOURAGE_POSTURES",
    "MAX_ENTOURAGE_STROKE_PT",
    "EntourageAsset",
    "EntourageStyle",
    "generate_entourage_library",
    "generate_iso_person_svg",
]
