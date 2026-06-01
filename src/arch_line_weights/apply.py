"""Rewrite a PDF/AI content stream so each stroke gets a per-color weight.

Strategy:
  * Parse the page's content stream into (operands, operator) instructions
  * Track the current stroke RGB (set by `RG`)
  * Before every stroke operator (S, s, B, B*, b, b*) inject `<width> w`
  * For .ai files, strip /PieceInfo so Illustrator re-parses from the modified
    PDF stream instead of its now-stale private cache

Only RGB stroke colors are supported. CMYK / Gray strokes pass through with
the default weight.
"""

from __future__ import annotations

import os
from collections.abc import Iterable
from dataclasses import dataclass, field
from decimal import Decimal

import pikepdf
from pikepdf import Operator

from .input_format import raise_if_unsupported

STROKE_OPS = {"S", "s", "B", "B*", "b", "b*"}


@dataclass
class ApplyResult:
    rg_seen: int = 0
    strokes_processed: int = 0
    weights_applied: dict[float, int] = field(default_factory=dict)
    unmatched_colors: dict[tuple[int, int, int], int] = field(default_factory=dict)
    output_size: int = 0
    input_size: int = 0
    pieceinfo_stripped: bool = False


def apply_to_file(
    src: str,
    dst: str,
    rgb_to_weight: dict[tuple[int, int, int], float],
    *,
    default_width: float = 0.25,
    strip_pieceinfo: bool = True,
) -> ApplyResult:
    """Apply per-color stroke widths to `src`, save to `dst`."""
    if os.path.abspath(src) == os.path.abspath(dst):
        raise ValueError("dst must differ from src to keep the original safe")
    raise_if_unsupported(src, "apply")

    pdf = pikepdf.open(src)
    result = ApplyResult(input_size=os.path.getsize(src))

    for page in pdf.pages:
        instructions = list(pikepdf.parse_content_stream(page))
        new_inst = _rewrite(instructions, rgb_to_weight, default_width, result)
        new_bytes = pikepdf.unparse_content_stream(new_inst)
        page.Contents = pdf.make_stream(new_bytes)

        if strip_pieceinfo and "/PieceInfo" in page.obj:
            del page.obj["/PieceInfo"]
            result.pieceinfo_stripped = True
        for k in ("/LastModified", "/Thumb"):
            if k in page.obj:
                del page.obj[k]

    pdf.save(dst)
    result.output_size = os.path.getsize(dst)
    return result


def _rewrite(
    instructions: Iterable,
    rgb_to_weight: dict[tuple[int, int, int], float],
    default_width: float,
    result: ApplyResult,
) -> list:
    out: list = []
    current_rgb: tuple[int, int, int] | None = None

    for operands, op in instructions:
        op_str = str(op)

        if op_str == "RG" and len(operands) >= 3:
            try:
                r, g, b = (float(o) for o in operands[:3])
                current_rgb = (round(r * 255), round(g * 255), round(b * 255))
                result.rg_seen += 1
            except Exception:
                current_rgb = None
            out.append((operands, op))

        elif op_str in STROKE_OPS:
            if current_rgb is not None:
                w = rgb_to_weight.get(current_rgb, default_width)
                if current_rgb not in rgb_to_weight:
                    result.unmatched_colors[current_rgb] = result.unmatched_colors.get(current_rgb, 0) + 1
            else:
                w = default_width
            result.weights_applied[w] = result.weights_applied.get(w, 0) + 1
            result.strokes_processed += 1
            out.append(([Decimal(f"{w:g}")], Operator("w")))
            out.append((operands, op))

        else:
            out.append((operands, op))

    return out
