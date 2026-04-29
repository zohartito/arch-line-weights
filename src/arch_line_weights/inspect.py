"""Read a vector file (.ai or .pdf) and report its color/stroke distribution."""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Optional

import fitz  # pymupdf


def _color_key(c) -> str:
    if c is None:
        return "none"
    if isinstance(c, (list, tuple)):
        if len(c) == 1:
            return f"Gray({round(c[0]*100)})"
        if len(c) == 3:
            return f"RGB({round(c[0]*255)},{round(c[1]*255)},{round(c[2]*255)})"
        if len(c) == 4:
            return f"CMYK({round(c[0]*100)},{round(c[1]*100)},{round(c[2]*100)},{round(c[3]*100)})"
    return str(c)


def color_to_rgb255(color_key: str) -> Optional[tuple[int, int, int]]:
    """Parse 'RGB(r,g,b)' back into a tuple of ints, or return None."""
    if not color_key.startswith("RGB("):
        return None
    inner = color_key[4:-1]
    parts = inner.split(",")
    if len(parts) != 3:
        return None
    try:
        return (int(parts[0]), int(parts[1]), int(parts[2]))
    except ValueError:
        return None


@dataclass
class InspectionReport:
    file: str
    pages: int
    width_pt: float
    height_pt: float
    total_drawings: int
    total_stroked: int
    stroke_widths: dict[str, int] = field(default_factory=dict)
    stroke_colors: dict[str, int] = field(default_factory=dict)
    fill_colors: dict[str, int] = field(default_factory=dict)
    width_by_color: dict[str, dict[str, int]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "file": self.file,
            "pages": self.pages,
            "width_pt": self.width_pt,
            "height_pt": self.height_pt,
            "total_drawings": self.total_drawings,
            "total_stroked": self.total_stroked,
            "stroke_widths": self.stroke_widths,
            "stroke_colors": self.stroke_colors,
            "fill_colors": self.fill_colors,
            "width_by_color": {k: dict(v) for k, v in self.width_by_color.items()},
        }


def inspect_file(path: str) -> InspectionReport:
    """Walk every drawing on every page and bucket by stroke width / color."""
    doc = fitz.open(path)
    page0 = doc[0]
    rep = InspectionReport(
        file=path,
        pages=doc.page_count,
        width_pt=page0.rect.width,
        height_pt=page0.rect.height,
        total_drawings=0,
        total_stroked=0,
    )
    stroke_widths: Counter = Counter()
    stroke_colors: Counter = Counter()
    fill_colors: Counter = Counter()
    width_by_color: defaultdict[str, Counter] = defaultdict(Counter)

    for page in doc:
        for d in page.get_drawings():
            rep.total_drawings += 1
            color = d.get("color")
            width = d.get("width")
            if color is not None and width is not None:
                rep.total_stroked += 1
                wkey = f"{round(float(width), 4)}"
                ckey = _color_key(color)
                stroke_widths[wkey] += 1
                stroke_colors[ckey] += 1
                width_by_color[ckey][wkey] += 1
            fill = d.get("fill")
            if fill is not None:
                fill_colors[_color_key(fill)] += 1

    rep.stroke_widths = dict(stroke_widths)
    rep.stroke_colors = dict(stroke_colors)
    rep.fill_colors = dict(fill_colors)
    rep.width_by_color = {k: dict(v) for k, v in width_by_color.items()}
    return rep
