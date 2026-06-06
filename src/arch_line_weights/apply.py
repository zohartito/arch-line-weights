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
from .linetypes import DASH_PATTERNS_PT, LineType

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
    linetypes_applied: dict[str, int] = field(default_factory=dict)
    excluded_strokes: int = 0


def apply_to_file(
    src: str,
    dst: str,
    rgb_to_weight: dict[tuple[int, int, int], float],
    *,
    default_width: float = 0.25,
    strip_pieceinfo: bool = True,
    rgb_to_linetype: dict[tuple[int, int, int], LineType] | None = None,
) -> ApplyResult:
    """Apply per-color stroke widths to `src`, save to `dst`.

    When ``rgb_to_linetype`` is given, a PDF dash operator is injected before
    each matching stroke (CONTINUOUS emits nothing; NON_PLOTTING is counted in
    ``result.excluded_strokes`` but not deleted — dropping a paint op can orphan
    `q`/clip state, so true exclusion is deferred to the marked-content path).
    With no ``rgb_to_linetype`` the output is byte-identical to a weight-only run.
    """
    if os.path.abspath(src) == os.path.abspath(dst):
        raise ValueError("dst must differ from src to keep the original safe")
    raise_if_unsupported(src, "apply")

    pdf = pikepdf.open(src)
    result = ApplyResult(input_size=os.path.getsize(src))

    for page in pdf.pages:
        instructions = list(pikepdf.parse_content_stream(page))
        new_inst = _rewrite(instructions, rgb_to_weight, default_width, result, rgb_to_linetype)
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


def _dash_operands(linetype: LineType) -> list | None:
    """Build pikepdf operands for a `d` (dash) op, or None for a solid line."""
    pattern = DASH_PATTERNS_PT.get(linetype)
    if pattern is None:
        return None
    on_off, phase = pattern
    return [pikepdf.Array([Decimal(f"{n:g}") for n in on_off]), Decimal(f"{phase:g}")]


def _solid_dash_operands() -> list:
    """Operands for `[] 0 d` — reset the dash state to a solid line."""
    return [pikepdf.Array([]), Decimal("0")]


def _rewrite(
    instructions: Iterable,
    rgb_to_weight: dict[tuple[int, int, int], float],
    default_width: float,
    result: ApplyResult,
    rgb_to_linetype: dict[tuple[int, int, int], LineType] | None = None,
) -> list:
    out: list = []
    current_rgb: tuple[int, int, int] | None = None
    # Only touch the dash state when at least one real dash pattern is requested;
    # then set it on EVERY stroke (solid `[] 0 d` reset by default) so a pattern
    # never leaks into later strokes via persistent graphics state.
    emit_dashes = rgb_to_linetype is not None and any(
        lt in DASH_PATTERNS_PT for lt in rgb_to_linetype.values()
    )

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

            linetype = (
                rgb_to_linetype.get(current_rgb)
                if rgb_to_linetype is not None and current_rgb is not None
                else None
            )
            if linetype is LineType.NON_PLOTTING:
                # v1: count + surface, never delete (dropping a paint op can
                # orphan q/clip state — deferred to the marked-content path).
                result.excluded_strokes += 1
            if emit_dashes:
                dash = _dash_operands(linetype) if linetype is not None else None
                out.append((dash if dash is not None else _solid_dash_operands(), Operator("d")))
                if dash is not None:
                    result.linetypes_applied[linetype.value] = (
                        result.linetypes_applied.get(linetype.value, 0) + 1
                    )

            result.weights_applied[w] = result.weights_applied.get(w, 0) + 1
            result.strokes_processed += 1
            out.append(([Decimal(f"{w:g}")], Operator("w")))
            out.append((operands, op))

        else:
            out.append((operands, op))

    return out
