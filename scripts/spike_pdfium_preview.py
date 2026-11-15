#!/usr/bin/env python3
"""Compare page 1 of the committed synthetic fixture; never replace the renderer.

Optional local setup: .venv/bin/python -m pip install pypdfium2
Artifacts default to the ignored .venv/pdfium-spike directory.
"""

from __future__ import annotations

import argparse
import json
import statistics
from importlib.metadata import version
from pathlib import Path
from time import perf_counter

import numpy as np
import pikepdf
from PIL import Image, ImageChops, ImageDraw

from arch_line_weights.preview import SUPERSAMPLE, PyMuPDFRenderer

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "eval" / "synthetic-cut.ai"


def pdfium_render(src: Path, dpi: int) -> Image.Image:
    import pypdfium2 as pdfium

    with pdfium.PdfDocument(src) as doc:
        page = doc[0]
        try:
            bitmap = page.render(scale=dpi * SUPERSAMPLE / 72, fill_color=(255, 255, 255, 255))
            try:
                # Detach the PIL pixels before the native bitmap is closed.
                image = bitmap.to_pil().convert("RGB").copy()
            finally:
                bitmap.close()
        finally:
            page.close()
    return image.resize((image.width // SUPERSAMPLE, image.height // SUPERSAMPLE), Image.Resampling.LANCZOS)


def compare(src: Path, out_dir: Path, dpi: int, runs: int) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    renderers = {
        "pymupdf": lambda: PyMuPDFRenderer().render_page(src, 0, dpi),
        "pypdfium2": lambda: pdfium_render(src, dpi),
    }
    timings = {name: [] for name in renderers}
    images = {}
    for render in renderers.values():
        render().close()  # one unmeasured warm-up per renderer
    for run in range(runs):
        # Alternate order to reduce systematic ordering effects.
        for name in list(renderers)[:: 1 if run % 2 == 0 else -1]:
            start = perf_counter()
            image = renderers[name]()
            timings[name].append(perf_counter() - start)
            if name in images:
                images[name].close()
            images[name] = image
    a, b = images["pymupdf"], images["pypdfium2"]
    if a.size != b.size:
        raise ValueError("Renderer dimensions differ; no rescaling or parity claim made.")
    delta = np.abs(np.asarray(a, dtype=np.int16) - np.asarray(b, dtype=np.int16))
    report = {
        "fixture": src.name,
        "page": 1,
        "dpi": dpi,
        "supersample": SUPERSAMPLE,
        "runs": runs,
        "timing_scope": "warm open/render/RGB conversion/downsample; imports and PNG encoding excluded",
        "versions": {name: version(name) for name in renderers},
        "seconds": {
            name: {"median": statistics.median(values), "samples": values} for name, values in timings.items()
        },
        "size_px": list(a.size),
        "mean_absolute_channel_difference": float(delta.mean()),
        "pixels_differing_over_12_percent": float(np.any(delta > 12, axis=2).mean() * 100),
        "ink_pixels_below_240": {
            name: int(np.any(np.asarray(img) < 240, axis=2).sum()) for name, img in images.items()
        },
    }
    for name, img in images.items():
        img.save(out_dir / f"{name}.png")
    diff = ImageChops.difference(a, b)
    diff.save(out_dir / "difference.png")
    comparison = Image.new("RGB", (a.width * 2, a.height + 28), "white")
    draw = ImageDraw.Draw(comparison)
    for index, (name, img) in enumerate(images.items()):
        draw.text((index * a.width + 8, 8), name, fill="black")
        comparison.paste(img, (index * a.width, 28))
    comparison.save(out_dir / "comparison.png")
    report["blank_output"] = any(count == 0 for count in report["ink_pixels_below_240"].values())
    for img in [*images.values(), diff, comparison]:
        img.close()
    return report


def write_control(path: Path) -> None:
    """An independent visible control: thin/thick strokes, a curve, black/gray fills."""
    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page(page_size=(200, 200))
        commands = ["0 0 0 RG"]
        for i, width in enumerate((0.08, 0.25, 0.5, 1.0)):
            y = 175 - i * 20
            commands.append(f"{width} w 20 {y} m 180 {y} l S")
        commands += [
            "0 0 0 rg 20 20 55 55 re f",
            "0.65 0.65 0.65 rg 95 20 35 55 re f",
            "0.5 w 145 20 m 185 40 145 60 180 80 c S",
        ]
        page.Contents = pdf.make_stream(("\n".join(commands) + "\n").encode("ascii"))
        pdf.save(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dpi", type=int, choices=range(1, 301), default=144, metavar="1..300")
    parser.add_argument("--runs", type=int, choices=range(1, 21), default=5, metavar="1..20")
    parser.add_argument("--out-dir", type=Path, default=ROOT / ".venv" / "pdfium-spike")
    args = parser.parse_args()
    try:
        import pypdfium2  # noqa: F401 -- load outside measured rendering
    except ImportError:
        parser.exit(2, "Optional spike dependency missing: install pypdfium2 in the project venv.\n")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    # The requested fixture's public PDF page is blank. Keep its result and also
    # render an independent visible control so blank parity cannot look conclusive.
    control = args.out_dir / "generated-render-control.pdf"
    write_control(control)
    reports = [
        compare(src, args.out_dir / label, args.dpi, args.runs)
        for src, label in [(FIXTURE, "fixture"), (control, "control")]
    ]
    output = json.dumps(reports, indent=2) + "\n"
    (args.out_dir / "results.json").write_text(output, encoding="utf-8")
    print(output, end="")
    if reports[1]["blank_output"]:
        parser.exit(1, "Visible control rendered blank; review before drawing any conclusion.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
