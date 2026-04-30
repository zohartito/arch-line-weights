"""Visual preview generation for arch-line-weights.

Renders before/after PDFs side-by-side at multiple plot scales, overlays
stroke-width tiers in distinct colors, and produces pixel-diff images
for QA on hairline strokes.

Dependencies: pymupdf, pikepdf, pillow, numpy. Optional: Ghostscript binary
on PATH for sub-0.25pt hairline accuracy via `-dNOMINLINEWIDTH`.
"""

from __future__ import annotations

import contextlib
import io
import shutil
import subprocess
import tempfile
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pikepdf
import pymupdf
from PIL import Image, ImageDraw, ImageFont

SUPERSAMPLE = 4
LABEL_HEIGHT_PX = 48
LEGEND_PAD_PX = 12
DIFF_THRESHOLD = 12
ADDED_TINT = (220, 30, 30)
REMOVED_TINT = (30, 80, 220)
BG_COLOR = (255, 255, 255)


def _load_font(size: int) -> ImageFont.ImageFont:
    for candidate in (
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        if Path(candidate).exists():
            try:
                return ImageFont.truetype(candidate, size)
            except OSError:
                continue
    return ImageFont.load_default()


@dataclass
class PyMuPDFRenderer:
    """Primary renderer. Fast, accurate strokes, no min-line-width clamping."""

    supersample: int = SUPERSAMPLE

    def render_page(self, src: str | Path, page_index: int, dpi: int) -> Image.Image:
        doc = pymupdf.open(str(src))
        try:
            page = doc.load_page(page_index)
            zoom = (dpi * self.supersample) / 72.0
            mat = pymupdf.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False, colorspace=pymupdf.csRGB)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        finally:
            doc.close()
        if self.supersample > 1:
            img = img.resize(
                (img.width // self.supersample, img.height // self.supersample),
                Image.LANCZOS,
            )
        return img

    def render_all(self, src: str | Path, dpi: int) -> list[Image.Image]:
        doc = pymupdf.open(str(src))
        try:
            return [self.render_page(src, i, dpi) for i in range(doc.page_count)]
        finally:
            doc.close()


@dataclass
class GhostscriptRenderer:
    """Fallback for sub-0.25pt hairline accuracy via -dNOMINLINEWIDTH."""

    binary: str = "gs"
    supersample: int = SUPERSAMPLE

    def __post_init__(self) -> None:
        if shutil.which(self.binary) is None:
            raise RuntimeError(
                f"Ghostscript binary {self.binary!r} not found on PATH. "
                "Install via `brew install ghostscript`."
            )

    def render_page(self, src: str | Path, page_index: int, dpi: int) -> Image.Image:
        page_no = page_index + 1
        effective_dpi = dpi * self.supersample
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / f"page_{page_no}.png"
            cmd = [
                self.binary,
                "-q",
                "-dNOPAUSE",
                "-dBATCH",
                "-dSAFER",
                "-sDEVICE=png16m",
                "-dNOMINLINEWIDTH",
                "-dGraphicsAlphaBits=4",
                "-dTextAlphaBits=4",
                f"-r{effective_dpi}",
                f"-dFirstPage={page_no}",
                f"-dLastPage={page_no}",
                f"-sOutputFile={out_path}",
                str(src),
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            img = Image.open(out_path).convert("RGB").copy()
        if self.supersample > 1:
            img = img.resize(
                (img.width // self.supersample, img.height // self.supersample),
                Image.LANCZOS,
            )
        return img

    def render_all(self, src: str | Path, dpi: int) -> list[Image.Image]:
        doc = pymupdf.open(str(src))
        try:
            count = doc.page_count
        finally:
            doc.close()
        return [self.render_page(src, i, dpi) for i in range(count)]


def _label_panel(img: Image.Image, label: str, sublabel: str = "") -> Image.Image:
    banner = Image.new("RGB", (img.width, LABEL_HEIGHT_PX), BG_COLOR)
    draw = ImageDraw.Draw(banner)
    title_font = _load_font(20)
    sub_font = _load_font(14)
    draw.text((12, 6), label, fill=(0, 0, 0), font=title_font)
    if sublabel:
        draw.text((12, 28), sublabel, fill=(80, 80, 80), font=sub_font)
    draw.line([(0, LABEL_HEIGHT_PX - 1), (img.width, LABEL_HEIGHT_PX - 1)], fill=(180, 180, 180), width=1)
    combined = Image.new("RGB", (img.width, img.height + LABEL_HEIGHT_PX), BG_COLOR)
    combined.paste(banner, (0, 0))
    combined.paste(img, (0, LABEL_HEIGHT_PX))
    return combined


def _hstack(panels: Sequence[Image.Image], gap: int = 8) -> Image.Image:
    height = max(p.height for p in panels)
    width = sum(p.width for p in panels) + gap * (len(panels) - 1)
    out = Image.new("RGB", (width, height), BG_COLOR)
    x = 0
    for p in panels:
        out.paste(p, (x, 0))
        x += p.width + gap
    return out


def _vstack(panels: Sequence[Image.Image], gap: int = 12) -> Image.Image:
    width = max(p.width for p in panels)
    height = sum(p.height for p in panels) + gap * (len(panels) - 1)
    out = Image.new("RGB", (width, height), BG_COLOR)
    y = 0
    for p in panels:
        out.paste(p, (0, y))
        y += p.height + gap
    return out


def side_by_side(
    before: str | Path,
    after: str | Path,
    out: str | Path,
    scales: Sequence[tuple[str, int]] = (("1/4=1'", 96), ("1/8=1'", 48), ("1/16=1'", 24)),
    renderer: PyMuPDFRenderer | GhostscriptRenderer | None = None,
    page_index: int | None = None,
) -> Image.Image:
    """Render before+after at multiple plot scales as a single stacked PNG."""
    renderer = renderer or PyMuPDFRenderer()
    rows: list[Image.Image] = []
    doc = pymupdf.open(str(before))
    try:
        page_count = doc.page_count
    finally:
        doc.close()
    pages = [page_index] if page_index is not None else list(range(page_count))
    for pg in pages:
        for label, dpi in scales:
            b_img = renderer.render_page(before, pg, dpi)
            a_img = renderer.render_page(after, pg, dpi)
            b_panel = _label_panel(
                b_img, f"BEFORE  {Path(before).name}", f"page {pg + 1} @ {label} ({dpi} dpi)"
            )
            a_panel = _label_panel(
                a_img, f"AFTER  {Path(after).name}", f"page {pg + 1} @ {label} ({dpi} dpi)"
            )
            rows.append(_hstack([b_panel, a_panel]))
    composite = _vstack(rows)
    composite.save(str(out), "PNG", optimize=True)
    return composite


_COLOR_TABLE: dict[str, tuple[int, int, int]] = {
    "red": (220, 30, 30),
    "orange": (240, 140, 20),
    "yellow": (235, 200, 20),
    "green": (20, 170, 60),
    "blue": (30, 90, 220),
    "purple": (140, 50, 180),
    "magenta": (220, 40, 180),
    "cyan": (40, 180, 200),
    "black": (0, 0, 0),
}


def _resolve_color(name_or_rgb: str | tuple[int, int, int]) -> tuple[int, int, int]:
    if isinstance(name_or_rgb, tuple):
        return name_or_rgb
    return _COLOR_TABLE.get(name_or_rgb.lower(), (0, 0, 0))


def _nearest_tier(width_pt: float, tiers: Iterable[float]) -> float:
    return min(tiers, key=lambda t: abs(t - width_pt))


def _recolor_pdf_by_tier(
    src: str | Path,
    tier_colors: Mapping[float, str | tuple[int, int, int]],
) -> bytes:
    tiers = sorted(tier_colors.keys())
    rgb_for_tier = {t: _resolve_color(tier_colors[t]) for t in tiers}
    pdf = pikepdf.Pdf.open(str(src))
    for page in pdf.pages:
        instructions = list(pikepdf.parse_content_stream(page))
        new_instructions: list = []
        current_w = 1.0
        for operands, operator in instructions:
            op = bytes(operator).decode("ascii", errors="ignore")
            if op == "w" and operands:
                with contextlib.suppress(TypeError, ValueError):
                    current_w = float(operands[0])
                new_instructions.append((operands, operator))
                tier = _nearest_tier(current_w, tiers)
                r, g, b = rgb_for_tier[tier]
                rgb_ops = [
                    pikepdf.Object.parse(f"{r / 255:.4f}"),
                    pikepdf.Object.parse(f"{g / 255:.4f}"),
                    pikepdf.Object.parse(f"{b / 255:.4f}"),
                ]
                new_instructions.append((rgb_ops, pikepdf.Operator("RG")))
            else:
                new_instructions.append((operands, operator))
        page.Contents = pdf.make_stream(pikepdf.unparse_content_stream(new_instructions))
    buf = io.BytesIO()
    pdf.save(buf)
    pdf.close()
    return buf.getvalue()


def _draw_legend(width: int, tier_colors: Mapping[float, str | tuple[int, int, int]]) -> Image.Image:
    rows = sorted(tier_colors.keys(), reverse=True)
    row_h = 24
    height = LEGEND_PAD_PX * 2 + row_h * len(rows)
    legend = Image.new("RGB", (width, height), BG_COLOR)
    draw = ImageDraw.Draw(legend)
    font = _load_font(14)
    for i, tier in enumerate(rows):
        y = LEGEND_PAD_PX + i * row_h
        rgb = _resolve_color(tier_colors[tier])
        draw.rectangle([(LEGEND_PAD_PX, y), (LEGEND_PAD_PX + 28, y + 16)], fill=rgb, outline=(0, 0, 0))
        draw.text((LEGEND_PAD_PX + 38, y + 1), f"tier {tier:>4.2f} pt", fill=(0, 0, 0), font=font)
    return legend


def tier_overlay(
    src: str | Path,
    out: str | Path,
    tier_colors: Mapping[float, str | tuple[int, int, int]],
    dpi: int = 96,
    renderer: PyMuPDFRenderer | GhostscriptRenderer | None = None,
) -> Image.Image:
    """Render `src` with each stroke recolored by its width-tier."""
    renderer = renderer or PyMuPDFRenderer()
    recolored_bytes = _recolor_pdf_by_tier(src, tier_colors)
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf:
        tf.write(recolored_bytes)
        tmp_path = Path(tf.name)
    try:
        pages = renderer.render_all(tmp_path, dpi)
    finally:
        tmp_path.unlink(missing_ok=True)
    labeled = [
        _label_panel(p, f"TIER OVERLAY  {Path(src).name}", f"page {i + 1} @ {dpi} dpi")
        for i, p in enumerate(pages)
    ]
    body = _vstack(labeled)
    legend = _draw_legend(body.width, tier_colors)
    composite = _vstack([body, legend])
    composite.save(str(out), "PNG", optimize=True)
    return composite


def _tinted_diff(
    before_img: Image.Image,
    after_img: Image.Image,
    threshold: int = DIFF_THRESHOLD,
) -> Image.Image:
    if before_img.size != after_img.size:
        after_img = after_img.resize(before_img.size, Image.LANCZOS)
    b = np.asarray(before_img.convert("L"), dtype=np.int16)
    a = np.asarray(after_img.convert("L"), dtype=np.int16)
    b_ink = b < 240
    a_ink = a < 240
    added = a_ink & ~b_ink
    removed = b_ink & ~a_ink
    common = a_ink & b_ink
    delta = np.abs(b - a)
    added &= delta > threshold
    removed &= delta > threshold
    h, w = b.shape
    canvas = np.full((h, w, 3), 255, dtype=np.uint8)
    canvas[common] = (210, 210, 210)
    canvas[removed] = REMOVED_TINT
    canvas[added] = ADDED_TINT
    return Image.fromarray(canvas, "RGB")


def diff_image(
    before: str | Path,
    after: str | Path,
    out: str | Path,
    dpi: int = 96,
    threshold: int = DIFF_THRESHOLD,
    renderer: PyMuPDFRenderer | GhostscriptRenderer | None = None,
) -> Image.Image:
    """Render both PDFs and produce a tinted pixel-diff PNG."""
    renderer = renderer or PyMuPDFRenderer()
    before_pages = renderer.render_all(before, dpi)
    after_pages = renderer.render_all(after, dpi)
    panels: list[Image.Image] = []
    for i, (b_img, a_img) in enumerate(zip(before_pages, after_pages, strict=False)):
        diff = _tinted_diff(b_img, a_img, threshold=threshold)
        labeled = _label_panel(
            diff,
            f"DIFF  page {i + 1}",
            f"red = added, blue = removed, grey = unchanged ({dpi} dpi)",
        )
        panels.append(labeled)
    composite = _vstack(panels)
    composite.save(str(out), "PNG", optimize=True)
    return composite


__all__ = [
    "GhostscriptRenderer",
    "PyMuPDFRenderer",
    "diff_image",
    "side_by_side",
    "tier_overlay",
]
