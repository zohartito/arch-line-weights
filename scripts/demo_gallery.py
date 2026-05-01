#!/usr/bin/env python3
"""Demo gallery generator for arch-line-weights.

Takes a directory of `.ai` (or `.pdf`) files and produces portfolio-ready
before/after assets for each one:

  1. Copies the input into the output directory (originals are never mutated).
  2. Runs ``arch-lw apply-saas --auto --poche`` on the copy.
  3. Renders a side-by-side preview PNG via :mod:`arch_line_weights.preview`.
  4. Adds a header strip with file name, layer count, cut-layer count,
     poché success rate, and runtime.
  5. Writes ``{stem}_demo.png`` to the output dir.

Also writes an ``index.html`` gallery that lists every demo with a comparison
table (input / output bytes, layers, cut-layers, polygons injected, runtime).

================================================================
KNOWN RENDERING LIMITATION — please read before judging the PNGs
================================================================

PyMuPDF renders the *legacy PDF content stream* embedded in the .ai file.
That stream is the rendering fallback Adobe Illustrator emits for non-AI
viewers; it is **not** the AI-native ``/PieceInfo /Illustrator /Private``
payload that ``apply-saas`` modifies.

Consequence: for SaaS-modified files, the before/after PNGs from PyMuPDF
look **identical** — both renderers walk the same untouched PDF stream.
The actual visual proof of ``apply-saas`` requires opening both files in
Adobe Illustrator (which prefers the PieceInfo payload).

The PNGs are still useful for:
  * Showing portfolio context (the original drawing).
  * Confirming the file still opens / has not been corrupted.
  * Side-by-side framing once an Illustrator-rendered PNG is available.

This is a documented limitation of the headless preview path, not a bug
in ``apply-saas``. See ``docs/research/demo-gallery-notes.md`` for
background.

Usage::

    python scripts/demo_gallery.py --input ~/path/to/drawings --output ./gallery
"""

from __future__ import annotations

import argparse
import html
import json
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw

# arch-line-weights ships preview helpers; reuse them so the gallery looks
# consistent with `arch-lw preview --mode side-by-side`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from arch_line_weights.inspect import inspect_file
from arch_line_weights.preview import (
    PyMuPDFRenderer,
    _hstack,
    _label_panel,
    _load_font,
    _vstack,
)

HEADER_HEIGHT_PX = 96
DEFAULT_DPI = 96
SUPPORTED_SUFFIXES = (".ai", ".pdf")


@dataclass
class DemoRecord:
    """Per-file gallery entry — used both for the PNG header and index.html."""

    stem: str
    source: str
    layer_count: int
    cut_layer_count: int
    polygons_injected: int
    layers_targeted: int
    layers_injected: int
    input_bytes: int
    output_bytes: int
    runtime_seconds: float
    weights_applied: dict[str, int] = field(default_factory=dict)
    error: str | None = None

    @property
    def success_rate(self) -> float:
        """Fraction of cut layers that received at least one poche polygon."""
        if self.layers_targeted == 0:
            return 0.0
        return self.layers_injected / self.layers_targeted


def _count_cut_layers(layer_names: list[str]) -> int:
    """Number of layer names matching the Rhino ClippingPlaneIntersections shape.

    Mirrors the cheap pre-filter used in ``poche_saas`` (case-insensitive
    substring match on ``clippingplaneintersections``). Glass / IGU
    exclusions in ``_is_cut_layer`` are not applied here — this is a coarse
    portfolio-level count, not the exact poché-target count.
    """
    needle = "clippingplaneintersections"
    return sum(1 for n in layer_names if needle in n.lower())


def _draw_header(width: int, record: DemoRecord) -> Image.Image:
    """Header strip with name, layer/cut counts, success rate, runtime."""
    banner = Image.new("RGB", (width, HEADER_HEIGHT_PX), (245, 245, 245))
    draw = ImageDraw.Draw(banner)
    title_font = _load_font(22)
    sub_font = _load_font(14)

    draw.text((16, 10), record.stem, fill=(0, 0, 0), font=title_font)

    line2 = (
        f"layers: {record.layer_count}    "
        f"cut layers: {record.cut_layer_count}    "
        f"poché success: {record.success_rate * 100:.0f}%    "
        f"runtime: {record.runtime_seconds:.2f}s"
    )
    draw.text((16, 40), line2, fill=(40, 40, 40), font=sub_font)

    line3 = (
        f"input: {record.input_bytes:,} B   "
        f"output: {record.output_bytes:,} B   "
        f"polygons injected: {record.polygons_injected}"
    )
    draw.text((16, 62), line3, fill=(80, 80, 80), font=sub_font)

    if record.error:
        draw.text(
            (16, 80),
            f"WARNING: {record.error}",
            fill=(180, 30, 30),
            font=sub_font,
        )

    draw.line(
        [(0, HEADER_HEIGHT_PX - 1), (width, HEADER_HEIGHT_PX - 1)],
        fill=(180, 180, 180),
        width=1,
    )
    return banner


def _render_side_by_side_panel(
    before: Path, after: Path, dpi: int
) -> Image.Image:
    """Render a single page side-by-side at a single DPI (compact gallery panel).

    For multi-scale renders, callers should use the full ``preview.side_by_side``
    helper directly. This compact form keeps gallery thumbnails small.
    """
    renderer = PyMuPDFRenderer()
    b_img = renderer.render_page(before, 0, dpi)
    a_img = renderer.render_page(after, 0, dpi)
    b_panel = _label_panel(
        b_img, f"BEFORE  {before.name}", f"page 1 @ {dpi} dpi (PDF stream)"
    )
    a_panel = _label_panel(
        a_img, f"AFTER  {after.name}", f"page 1 @ {dpi} dpi (PDF stream)"
    )
    return _hstack([b_panel, a_panel])


def _run_apply_saas(src: Path, dst: Path) -> tuple[float, str | None]:
    """Run ``arch-lw apply-saas --auto --poche`` on a copied file.

    Returns ``(elapsed_seconds, error_or_None)``. If ``arch-lw`` exits
    non-zero, the error is captured but the demo still gets recorded so the
    gallery shows what failed.
    """
    cmd = [
        "arch-lw",
        "apply-saas",
        str(src),
        "-o",
        str(dst),
        "--auto",
        "--poche",
    ]
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=600
        )
        elapsed = time.perf_counter() - t0
        if proc.returncode != 0:
            tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-3:]
            return elapsed, "apply-saas failed: " + " | ".join(tail)
        return elapsed, None
    except subprocess.TimeoutExpired:
        return time.perf_counter() - t0, "apply-saas timeout (>600s)"
    except FileNotFoundError:
        return 0.0, "arch-lw CLI not on PATH"


def _parse_apply_saas_stats(stderr: str) -> dict:
    """Best-effort: pull poly/layer counts out of `arch-lw apply-saas` stderr.

    Falls back to zeros if the format ever drifts. The benchmark script gets
    these numbers via the structured Python API instead — this is just for
    the gallery summary.
    """
    out = {"polygons_injected": 0, "layers_targeted": 0, "layers_injected": 0}
    for line in stderr.splitlines():
        s = line.strip()
        # "poché: injected 42 polygons across 5/7 cut layers (+12,345 bytes)"
        if s.startswith("poché:") and "polygons across" in s:
            try:
                _, rest = s.split("injected", 1)
                rest = rest.strip()
                # rest = "42 polygons across 5/7 cut layers (+...)"
                polys = int(rest.split(" ", 1)[0])
                across = rest.split("across", 1)[1].strip()
                # "5/7 cut layers ..."
                ratio = across.split(" ", 1)[0]
                inj, tgt = ratio.split("/")
                out["polygons_injected"] = polys
                out["layers_injected"] = int(inj)
                out["layers_targeted"] = int(tgt)
            except (ValueError, IndexError):
                pass
    return out


def _collect_record(
    src: Path, dst: Path, runtime: float, error: str | None, stderr: str
) -> DemoRecord:
    rep = inspect_file(str(src))
    layer_names = list(rep.layer_names or [])
    stats = _parse_apply_saas_stats(stderr)
    return DemoRecord(
        stem=src.stem,
        source=str(src),
        layer_count=len(layer_names),
        cut_layer_count=_count_cut_layers(layer_names),
        polygons_injected=stats["polygons_injected"],
        layers_targeted=stats["layers_targeted"],
        layers_injected=stats["layers_injected"],
        input_bytes=src.stat().st_size,
        output_bytes=dst.stat().st_size if dst.exists() else 0,
        runtime_seconds=runtime,
        error=error,
    )


def _make_demo_png(
    src_copy: Path, dst: Path, record: DemoRecord, out_png: Path, dpi: int
) -> None:
    """Compose the final ``{stem}_demo.png`` (header + side-by-side panel)."""
    if not dst.exists():
        # Render a single before-only panel so the gallery still shows
        # something even when apply-saas failed.
        renderer = PyMuPDFRenderer()
        b_img = renderer.render_page(src_copy, 0, dpi)
        side = _label_panel(
            b_img,
            f"BEFORE  {src_copy.name}",
            "after-render skipped (apply-saas failed)",
        )
    else:
        side = _render_side_by_side_panel(src_copy, dst, dpi)
    header = _draw_header(side.width, record)
    composite = _vstack([header, side], gap=0)
    composite.save(str(out_png), "PNG", optimize=True)


def _write_index_html(records: list[DemoRecord], out_dir: Path) -> Path:
    """Write a self-contained gallery page that links every demo PNG."""
    rows: list[str] = []
    for r in records:
        png = f"{r.stem}_demo.png"
        rows.append(
            f"  <tr>"
            f"<td><a href='{html.escape(png)}'>{html.escape(r.stem)}</a></td>"
            f"<td class='num'>{r.layer_count}</td>"
            f"<td class='num'>{r.cut_layer_count}</td>"
            f"<td class='num'>{r.polygons_injected}</td>"
            f"<td class='num'>{r.layers_injected}/{r.layers_targeted}</td>"
            f"<td class='num'>{r.success_rate * 100:.0f}%</td>"
            f"<td class='num'>{r.input_bytes:,}</td>"
            f"<td class='num'>{r.output_bytes:,}</td>"
            f"<td class='num'>{r.runtime_seconds:.2f}s</td>"
            f"<td>{html.escape(r.error or '')}</td>"
            f"</tr>"
        )
    table_rows = "\n".join(rows) if rows else "  <tr><td colspan='10'>no demos</td></tr>"

    figures: list[str] = []
    for r in records:
        png = f"{r.stem}_demo.png"
        figures.append(
            f"<figure>"
            f"<a href='{html.escape(png)}'>"
            f"<img src='{html.escape(png)}' alt='{html.escape(r.stem)}' loading='lazy' />"
            f"</a>"
            f"<figcaption>{html.escape(r.stem)} "
            f"({r.layer_count} layers, {r.runtime_seconds:.2f}s)</figcaption>"
            f"</figure>"
        )
    figures_html = "\n".join(figures)

    note = (
        "<p class='note'><strong>Rendering note:</strong> the before/after "
        "panels are produced by PyMuPDF, which renders the legacy PDF content "
        "stream embedded in each .ai file. <code>apply-saas</code> modifies "
        "the AI-native <code>/PieceInfo /Illustrator /Private</code> payload "
        "instead, so the headless PNGs look identical before/after. "
        "Visual proof of the line-weight rewrite requires opening both files "
        "in Adobe Illustrator. The PNGs above still confirm the file opens "
        "cleanly and provide portfolio context.</p>"
    )

    page = f"""<!doctype html>
<html lang='en'>
<head>
<meta charset='utf-8'>
<title>arch-line-weights — demo gallery</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         margin: 24px; color: #222; }}
  h1 {{ margin-bottom: 4px; }}
  table {{ border-collapse: collapse; margin: 16px 0; font-size: 14px; }}
  th, td {{ padding: 6px 10px; border-bottom: 1px solid #ddd; text-align: left; }}
  th {{ background: #f4f4f4; }}
  td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  .note {{ background: #fff8e1; padding: 12px 16px; border-left: 4px solid #f0b400;
           max-width: 900px; line-height: 1.45; }}
  figure {{ margin: 24px 0; }}
  figure img {{ max-width: 100%; height: auto; border: 1px solid #ddd; }}
  figcaption {{ font-size: 13px; color: #555; margin-top: 4px; }}
</style>
</head>
<body>
<h1>arch-line-weights — demo gallery</h1>
<p>Generated by <code>scripts/demo_gallery.py</code>. Each row: one input
drawing run through <code>arch-lw apply-saas --auto --poche</code>.</p>
{note}
<table>
  <thead><tr>
    <th>file</th><th>layers</th><th>cut</th><th>polys</th>
    <th>injected</th><th>success</th>
    <th>in (B)</th><th>out (B)</th><th>runtime</th><th>error</th>
  </tr></thead>
  <tbody>
{table_rows}
  </tbody>
</table>
{figures_html}
</body>
</html>
"""
    out = out_dir / "index.html"
    out.write_text(page, encoding="utf-8")
    return out


def build_gallery(
    input_dir: Path, output_dir: Path, dpi: int = DEFAULT_DPI
) -> list[DemoRecord]:
    output_dir.mkdir(parents=True, exist_ok=True)
    inputs = sorted(
        p
        for p in input_dir.iterdir()
        if p.is_file() and p.suffix.lower() in SUPPORTED_SUFFIXES
    )
    if not inputs:
        print(f"no .ai/.pdf files in {input_dir}", file=sys.stderr)
        return []

    records: list[DemoRecord] = []
    for src in inputs:
        # Skip files that look like prior arch-lw outputs to avoid running
        # apply-saas on an already-modified file.
        upper = src.name.upper()
        if "HIERARCHY" in upper or "POCHE" in upper:
            print(f"  skip {src.name} (looks like an arch-lw output)", file=sys.stderr)
            continue

        print(f"-> {src.name}", file=sys.stderr)
        src_copy = output_dir / src.name
        dst = output_dir / f"{src.stem} HIERARCHY{src.suffix}"

        # Step 1: copy the original (never mutate).
        shutil.copy2(src, src_copy)

        # Step 2: run apply-saas --auto --poche on the copy.
        cmd = [
            "arch-lw",
            "apply-saas",
            str(src_copy),
            "-o",
            str(dst),
            "--auto",
            "--poche",
        ]
        t0 = time.perf_counter()
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        elapsed = time.perf_counter() - t0
        error: str | None = None
        if proc.returncode != 0:
            tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-3:]
            error = "apply-saas failed: " + " | ".join(tail)
            print(f"   FAIL ({elapsed:.2f}s): {error}", file=sys.stderr)
        else:
            print(f"   ok ({elapsed:.2f}s)", file=sys.stderr)

        # Step 3: gather diagnostics from inspect + apply-saas stderr.
        record = _collect_record(src_copy, dst, elapsed, error, proc.stderr or "")
        records.append(record)

        # Step 4: render demo PNG.
        out_png = output_dir / f"{src.stem}_demo.png"
        try:
            _make_demo_png(src_copy, dst, record, out_png, dpi)
            print(f"   wrote {out_png.name}", file=sys.stderr)
        except Exception as exc:
            print(f"   render failed: {exc}", file=sys.stderr)
            record.error = (record.error or "") + f" | render: {exc}"

    # Step 5: index.html + JSON dump for downstream tooling.
    _write_index_html(records, output_dir)
    (output_dir / "gallery.json").write_text(
        json.dumps([asdict(r) for r in records], indent=2), encoding="utf-8"
    )
    return records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate a portfolio-ready before/after gallery."
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Directory containing .ai/.pdf source drawings.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output directory for demos + index.html.",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=DEFAULT_DPI,
        help=f"Render DPI for the side-by-side panel (default {DEFAULT_DPI}).",
    )
    args = parser.parse_args(argv)

    if not args.input.is_dir():
        parser.error(f"--input is not a directory: {args.input}")

    records = build_gallery(args.input, args.output, dpi=args.dpi)
    print(
        f"\nbuilt gallery with {len(records)} demos in {args.output}",
        file=sys.stderr,
    )
    return 0 if records else 1


if __name__ == "__main__":
    raise SystemExit(main())
