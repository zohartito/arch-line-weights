#!/usr/bin/env python3
"""Deterministic visual judge for arch-line-weights output.

A *no-LLM, no-network* metric pass that scores a poché/hierarchy result on the
four failure axes the corpus spec (``docs/research/target-look-spec.md`` §1)
keeps flagging on real Rhino-export drawings:

  * ``false_poche``     — solid black fill floating in whitespace, i.e. "black
                          boxes that aren't poché" (spec §1.3, §3.2 defect D1).
  * ``band_continuity`` — a heavy cut band that fragments into dashes instead of
                          reading as one continuous stroke (spec §1.2, §3.2 D3).
  * ``hierarchy_spread``— the cut : texture stroke-weight ratio; the corpus
                          target is >= 3:1 (spec §1.2 "the weight ramp").
  * ``fixture_weight``  — mean darkness of projected/"Visible" fixture regions;
                          catches "why are these squares so thick" (spec §1.3,
                          §3.2 D4). Only scored when a poché --report-json is
                          supplied (needs the layer polygon bounds).

Determinism boundary (AGENTS.md): every threshold lives here in code with a
spec citation; the same inputs always produce the same JSON. The model never
sees a pixel on this path — it only reads the verdict.

Inputs may be vector (``.ai`` / ``.pdf``, rendered with the repo's PyMuPDF
renderer) or a pre-rendered ``.png``. Vector inputs also unlock the exact
stroke-width histogram for ``hierarchy_spread``; PNG inputs fall back to a
raster line-thickness estimate.

Usage::

    python scripts/visual_judge.py --after "section-v4 POCHE.ai"
    python scripts/visual_judge.py --after out.png --before raw.png \
        --report-json poche-report.json --out verdict.json
"""

from __future__ import annotations

import argparse
import contextlib
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
from scipy import ndimage

# --------------------------------------------------------------------------- #
# Thresholds — every one cites the corpus spec section it enforces.
# docs/research/target-look-spec.md
# --------------------------------------------------------------------------- #

# §1.3 "the cut owns the darkest value — and nothing else may reach it" and
# §3.2 defect D1 (a projected foundation strip promoted to poché far outside the
# cut envelope). Up to 5% of solid-fill mass may sit outside the envelope before
# we call it a defect — a small tolerance for legitimate detached cut members.
FALSE_POCHE_MAX = 0.05

# §1.2 "the continuous ground datum" — the cut profile + poché is one continuous
# band. §3.2 defect D3: a slender CLT wall fragmented into ~17 chains reading as
# white dashes. A heavy band losing more than 20% of its run to gaps reads as
# broken rather than continuous.
BAND_GAP_MAX = 0.20

# §1.2 "a consistent 3-4 tier ladder"; the LAI studio conclusion names a genuine
# 3:2:1 step (cut : profile : texture). Below a 3:1 cut:texture ratio the sheet
# slides toward the §1.7 universal failure mode ("weight-flatness").
HIERARCHY_MIN_RATIO = 3.0

# §1.3 / §3.2 D4: projected "Visible::Curves" fixtures must NOT reach cut value.
# Their mean darkness (0=white, 1=black) should stay well below the cut. If the
# fixture regions themselves render darker than this they read as cut mass.
FIXTURE_DARKNESS_MAX = 0.55

# Ink / black thresholds on the 0-255 grey render.
INK_LEVEL = 128  # anything darker than this is "ink"
BLACK_LEVEL = 60  # anything darker than this is "black" (poché / cut candidate)

SCHEMA_VERSION = 1


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #


def render_gray(path: str | Path, dpi: int) -> tuple[np.ndarray, float]:
    """Return (grayscale uint8 array, pixels-per-point) for a vector or PNG input.

    PNGs are assumed to be rendered at ``dpi`` (the caller's responsibility);
    their pixels-per-point is derived from the same dpi so band/erosion radii
    stay in physical units.
    """
    path = Path(path)
    ppp = dpi / 72.0
    if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}:
        img = Image.open(path).convert("L")
        return np.asarray(img), ppp
    # Vector: reuse the repo renderer so judge and `arch-lw preview` agree.
    from arch_line_weights.preview import PyMuPDFRenderer

    img = PyMuPDFRenderer().render_page(path, 0, dpi).convert("L")
    return np.asarray(img), ppp


# --------------------------------------------------------------------------- #
# Shared masks
# --------------------------------------------------------------------------- #


def _solid_fill_mask(gray: np.ndarray, ppp: float) -> np.ndarray:
    """Isolate genuine solid poché fills from thin linework.

    Erode the black mask by ~1.2 pt then dilate back: strokes thinner than the
    kernel vanish, compact fills survive. This is what separates "a filled
    polygon" from "a dense cluster of hairlines".
    """
    black = gray < BLACK_LEVEL
    r = max(1, round(1.2 * ppp))
    cores = ndimage.binary_erosion(black, iterations=r)
    return ndimage.binary_dilation(cores, iterations=r) & black


def _ink_bbox(gray: np.ndarray) -> tuple[int, int, int, int] | None:
    """Axis-aligned bbox (y0, x0, y1, x1) of all ink, or None if blank."""
    ink = gray < INK_LEVEL
    rows = np.any(ink, axis=1)
    cols = np.any(ink, axis=0)
    if not rows.any():
        return None
    y0, y1 = np.where(rows)[0][[0, -1]]
    x0, x1 = np.where(cols)[0][[0, -1]]
    return int(y0), int(x0), int(y1) + 1, int(x1) + 1


# --------------------------------------------------------------------------- #
# Report → render-space transform (optional, bbox-fit)
# --------------------------------------------------------------------------- #


@dataclass
class ReportEnvelope:
    """Expected cut / fixture regions derived from a poché report JSON.

    The report stores geometry in Illustrator-point space; we fit it to render
    pixels by matching the union bbox of report geometry to the rendered-ink
    bbox (with a Y-flip, since AI is y-up and raster y-down). This assumes the
    render frames the drawing content tightly — true for ``arch-lw preview`` on
    a single artboard. For pixel-exact overlay, pre-register the PNGs instead.
    """

    cut_mask: np.ndarray | None = None
    fixture_boxes: list[tuple[int, int, int, int]] = field(default_factory=list)
    ok: bool = False
    note: str = ""


def _iter_report_bounds(report: dict) -> list[tuple[float, float, float, float, str]]:
    """Yield (x0, y0, x1, y1, target_layer) for every geometry bound in a report."""
    out: list[tuple[float, float, float, float, str]] = []
    for cand in report.get("completion_candidates", []) or []:
        b = cand.get("bounds")
        if b and len(b) == 4:
            out.append(
                (float(b[0]), float(b[1]), float(b[2]), float(b[3]), str(cand.get("target_layer", "")))
            )
    for layer in report.get("layers", []) or []:
        b = layer.get("bounds")
        if b and len(b) == 4:
            out.append((float(b[0]), float(b[1]), float(b[2]), float(b[3]), str(layer.get("layer", ""))))
    return out


def _is_fixture_layer(name: str) -> bool:
    """§3.2 D4: projected fixtures live on ::Visible::Curves:: / ::Visible::Tangents::."""
    low = name.lower()
    return "::visible::curves::" in low or "::visible::tangents::" in low


def build_report_envelope(report: dict, gray: np.ndarray) -> ReportEnvelope:
    bounds = _iter_report_bounds(report)
    ink_bb = _ink_bbox(gray)
    if not bounds or ink_bb is None:
        return ReportEnvelope(ok=False, note="no report geometry or blank render")
    xs0 = min(b[0] for b in bounds)
    ys0 = min(b[1] for b in bounds)
    xs1 = max(b[2] for b in bounds)
    ys1 = max(b[3] for b in bounds)
    if xs1 <= xs0 or ys1 <= ys0:
        return ReportEnvelope(ok=False, note="degenerate report bbox")
    y0, x0, y1, x1 = ink_bb
    sx = (x1 - x0) / (xs1 - xs0)
    sy = (y1 - y0) / (ys1 - ys0)

    def to_px(ax0: float, ay0: float, ax1: float, ay1: float) -> tuple[int, int, int, int]:
        px0 = x0 + (ax0 - xs0) * sx
        px1 = x0 + (ax1 - xs0) * sx
        # Y-flip: AI max-y maps to render top.
        py0 = y0 + (ys1 - ay1) * sy
        py1 = y0 + (ys1 - ay0) * sy
        return (
            int(np.clip(min(py0, py1), 0, gray.shape[0])),
            int(np.clip(min(px0, px1), 0, gray.shape[1])),
            int(np.clip(max(py0, py1), 0, gray.shape[0])),
            int(np.clip(max(px0, px1), 0, gray.shape[1])),
        )

    cut_mask = np.zeros(gray.shape, dtype=bool)
    fixtures: list[tuple[int, int, int, int]] = []
    for ax0, ay0, ax1, ay1, layer in bounds:
        by0, bx0, by1, bx1 = to_px(ax0, ay0, ax1, ay1)
        if _is_fixture_layer(layer):
            fixtures.append((by0, bx0, by1, bx1))
        else:
            cut_mask[by0:by1, bx0:bx1] = True
    return ReportEnvelope(cut_mask=cut_mask, fixture_boxes=fixtures, ok=True, note="bbox-fit AI->render")


# --------------------------------------------------------------------------- #
# Axis 1 — false_poche
# --------------------------------------------------------------------------- #


def false_poche_score(gray: np.ndarray, ppp: float) -> tuple[float, dict]:
    """Fraction of solid-fill mass that is *false* poché — render-intrinsic.

    A false-poché blob is a compact solid fill *floating in whitespace*: its
    surrounding ring is near-empty paper, so it is a "black box that isn't
    poché" (the D1 signature). Genuine poché is embedded in the drawing's
    linework and its ring carries ink.

    This signal needs no cross-file coordinate transform, so it is robust where
    a report→render bbox-fit is not (see ``build_report_envelope``); the report
    is therefore used only for fixtures and override naming, not to gate this.
    """
    fills = _solid_fill_mask(gray, ppp)
    lab, n = ndimage.label(fills)
    if n == 0:
        return 0.0, {"solid_fill_px": 0, "flagged_blobs": [], "mode": "floating-in-whitespace"}
    sizes = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))
    objs = ndimage.find_objects(lab)
    ink = gray < INK_LEVEL

    margin = max(3, round(8 * ppp))
    area_floor = max(30, int((6 * ppp) ** 2))  # ignore fills below a ~6pt square
    solid_mass = 0.0
    false_mass = 0.0
    flagged: list[dict] = []
    H, W = gray.shape

    for i in range(n):
        sz = float(sizes[i])
        if sz < area_floor:
            continue
        sl = objs[i]
        bh = sl[0].stop - sl[0].start
        bw = sl[1].stop - sl[1].start
        if sz / (bh * bw) < 0.5:  # diffuse linework cluster, not a solid fill
            continue
        solid_mass += sz
        cy = int((sl[0].start + sl[0].stop) / 2)
        cx = int((sl[1].start + sl[1].stop) / 2)
        y0 = max(0, sl[0].start - margin)
        y1 = min(H, sl[0].stop + margin)
        x0 = max(0, sl[1].start - margin)
        x1 = min(W, sl[1].stop + margin)
        blob = lab[y0:y1, x0:x1] == (i + 1)
        ring = ndimage.binary_dilation(blob, iterations=margin) & ~blob
        ring_density = float(ink[y0:y1, x0:x1][ring].mean()) if ring.any() else 0.0
        if ring_density < 0.03:  # floating in whitespace
            false_mass += sz
            flagged.append(
                {
                    "area_px": int(sz),
                    "center_frac": [round(cx / W, 3), round(cy / H, 3)],
                    "ring_density": round(ring_density, 3),
                }
            )
    frac = false_mass / solid_mass if solid_mass else 0.0
    flagged.sort(key=lambda d: d["area_px"], reverse=True)
    return round(frac, 4), {
        "solid_fill_px": int(solid_mass),
        "flagged_blobs": flagged[:12],
        "mode": "floating-in-whitespace",
    }


# --------------------------------------------------------------------------- #
# Axis 2 — band_continuity
# --------------------------------------------------------------------------- #


def band_continuity_score(gray: np.ndarray, ppp: float, intentional_gaps: int = 0) -> tuple[float, dict]:
    """Worst gap fraction among heavy, elongated bands.

    A heavy band is detected from the solid-fill mask (so thin *intentionally*
    dashed hidden lines — which never survive the fill erosion — are excluded by
    construction). Along-axis gaps are recovered by closing over a ~14 pt kernel
    to re-link fragments into one candidate band, then measuring how much of the
    band's long-axis run has no original solid ink.
    """
    fills = _solid_fill_mask(gray, ppp)
    if not fills.any():
        return 0.0, {"bands_examined": 0, "worst": None}
    close_len = max(4, round(14 * ppp))
    v_struct = np.ones((close_len, 1), dtype=bool)
    h_struct = np.ones((1, close_len), dtype=bool)
    area_floor = max(60, int((10 * ppp) ** 2))
    worst = 0.0
    worst_meta: dict | None = None
    examined = 0

    for closed, axis in (
        (ndimage.binary_closing(fills, structure=v_struct), "v"),
        (ndimage.binary_closing(fills, structure=h_struct), "h"),
    ):
        lab, n = ndimage.label(closed)
        objs = ndimage.find_objects(lab)
        sizes = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))
        for i in range(n):
            if sizes[i] < area_floor:
                continue
            sl = objs[i]
            bh = sl[0].stop - sl[0].start
            bw = sl[1].stop - sl[1].start
            long_dim, short_dim = (bh, bw) if bh >= bw else (bw, bh)
            if short_dim <= 0 or long_dim / short_dim < 8.0:
                continue
            examined += 1
            comp = lab[sl] == (i + 1)
            orig = fills[sl] & comp
            # Presence of ORIGINAL solid ink along the long axis (vertical band
            # -> scan rows / axis=1; horizontal band -> scan cols / axis=0).
            present = orig.any(axis=1) if bh >= bw else orig.any(axis=0)
            gap_slices = int((~present).sum())
            gap_frac = gap_slices / present.size
            if gap_frac > worst:
                worst = gap_frac
                cy = (sl[0].start + sl[0].stop) / 2 / gray.shape[0]
                cx = (sl[1].start + sl[1].stop) / 2 / gray.shape[1]
                worst_meta = {
                    "axis": axis,
                    "gap_fraction": round(gap_frac, 3),
                    "long_px": int(long_dim),
                    "center_frac": [round(cx, 3), round(cy, 3)],
                }
    # Intentional gaps (report-declared) relax the score proportionally, floored at 0.
    if intentional_gaps and worst_meta is not None:
        worst = max(0.0, worst - min(0.5, 0.1 * intentional_gaps))
    return round(worst, 4), {"bands_examined": examined, "worst": worst_meta}


# --------------------------------------------------------------------------- #
# Axis 3 — hierarchy_spread
# --------------------------------------------------------------------------- #


def _vector_width_histogram(path: Path) -> dict[float, int] | None:
    """Stroke-width (pt) -> count from a PDF/PDF-compatible .ai content stream."""
    if path.suffix.lower() not in {".ai", ".pdf"}:
        return None
    try:
        import pikepdf
    except Exception:
        return None
    counts: dict[float, int] = {}
    try:
        pdf = pikepdf.Pdf.open(str(path))
    except Exception:
        return None
    try:
        for page in pdf.pages:
            cur: float | None = None
            try:
                stream = pikepdf.parse_content_stream(page)
            except Exception:
                continue
            for operands, operator in stream:
                op = bytes(operator).decode("ascii", "ignore")
                if op == "w" and operands:
                    with contextlib.suppress(TypeError, ValueError):
                        cur = round(float(operands[0]), 3)
                elif op in {"S", "s", "B", "B*", "b", "b*"} and cur is not None:
                    counts[cur] = counts.get(cur, 0) + 1
    finally:
        pdf.close()
    return counts or None


def _ratio_from_histogram(counts: dict[float, int]) -> tuple[float | None, float, float]:
    total = sum(counts.values())
    widths = sorted(counts)
    if total == 0 or not widths:
        return None, 0.0, 0.0
    floor = max(10, 0.001 * total)  # heaviest tier with >=0.1% of strokes (or >=10)
    cut = max((w for w in widths if counts[w] >= floor), default=widths[-1])
    below = {w: c for w, c in counts.items() if w < cut}
    texture = max(below, key=lambda w: below[w]) if below else min(widths)
    ratio = cut / texture if texture > 0 else None
    return ratio, cut, texture


def _raster_thickness_ratio(gray: np.ndarray) -> tuple[float | None, float, float]:
    """PNG fallback: stroke thickness via distance transform on the ink mask."""
    ink = gray < INK_LEVEL
    if not ink.any():
        return None, 0.0, 0.0
    dist = ndimage.distance_transform_edt(ink)
    thick = 2.0 * dist[ink]  # local stroke thickness in px
    cut = float(np.percentile(thick, 98))
    texture = float(np.percentile(thick, 50))
    ratio = cut / texture if texture > 0 else None
    return ratio, cut, texture


def hierarchy_spread_score(after_path: Path, gray: np.ndarray) -> tuple[float | None, dict]:
    counts = _vector_width_histogram(after_path)
    if counts:
        ratio, cut, texture = _ratio_from_histogram(counts)
        return (None if ratio is None else round(ratio, 3)), {
            "source": "vector",
            "cut_pt": cut,
            "texture_pt": texture,
            "histogram": {str(k): v for k, v in sorted(counts.items())},
        }
    ratio, cut, texture = _raster_thickness_ratio(gray)
    return (None if ratio is None else round(ratio, 3)), {
        "source": "raster",
        "cut_px": round(cut, 2),
        "texture_px": round(texture, 2),
    }


# --------------------------------------------------------------------------- #
# Axis 4 — fixture_weight
# --------------------------------------------------------------------------- #


def fixture_weight_score(gray: np.ndarray, envelope: ReportEnvelope | None) -> tuple[float | None, dict]:
    """Mean darkness (0=white, 1=black) of projected fixture regions.

    Needs the report to know which regions are ::Visible:: fixtures. Without a
    report this axis is not scored (returns None) rather than guessed.
    """
    if envelope is None or not envelope.ok or not envelope.fixture_boxes:
        return None, {"fixture_regions": 0, "note": "no report fixture layers"}
    darkness_vals: list[float] = []
    for by0, bx0, by1, bx1 in envelope.fixture_boxes:
        if by1 <= by0 or bx1 <= bx0:
            continue
        patch = gray[by0:by1, bx0:bx1].astype(np.float64)
        ink = patch < INK_LEVEL
        if ink.any():
            darkness_vals.append(float((1.0 - patch[ink] / 255.0).mean()))
    if not darkness_vals:
        return None, {"fixture_regions": 0, "note": "fixture regions carried no ink"}
    mean_dark = float(np.mean(darkness_vals))
    return round(mean_dark, 4), {"fixture_regions": len(darkness_vals)}


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #


def _suggested_overrides(report: dict | None, band_meta: dict, false_meta: dict) -> dict:
    """Merge-able poché overrides (schema: {layer: {"strategy": "bbox"}}).

    When a report names the fragmented cut layer, suggest the bbox closure that
    §3.2's D3 recipe uses. Floating false-poché fills are surfaced in ``why``
    (their fix is deletion on the ARCH_LW_POCHE_FILL layer, not an override).
    """
    if not report:
        return {}
    out: dict[str, dict] = {}
    if band_meta.get("worst"):
        # Suggest bbox for the lowest-confidence cut layer the report reviewed.
        for layer in report.get("layers", []) or []:
            review = layer.get("review", {}) or {}
            if review.get("needs_review") and layer.get("status") in {
                "low_confidence",
                "inferred",
                "needs_review",
            }:
                name = layer.get("layer")
                if name:
                    out[name] = {"strategy": "bbox"}
    return out


def judge(
    after: str | Path,
    before: str | Path | None = None,
    report_json: str | Path | None = None,
    dpi: int = 96,
) -> dict[str, Any]:
    after = Path(after)
    gray, ppp = render_gray(after, dpi)
    report: dict | None = None
    if report_json:
        report = json.loads(Path(report_json).read_text())
    envelope = build_report_envelope(report, gray) if report else None
    intentional = int(report.get("intentional_gaps", 0)) if report else 0

    fp, fp_meta = false_poche_score(gray, ppp)
    bc, bc_meta = band_continuity_score(gray, ppp, intentional)
    hs, hs_meta = hierarchy_spread_score(after, gray)
    fw, fw_meta = fixture_weight_score(gray, envelope)

    why: list[str] = []
    if fp > FALSE_POCHE_MAX:
        why.append(
            f"false_poche {fp:.2%} of solid-fill mass sits outside the cut envelope "
            f"(> {FALSE_POCHE_MAX:.0%}); black boxes that aren't poché [spec §1.3/§3.2 D1]."
        )
    if bc > BAND_GAP_MAX:
        why.append(
            f"band_continuity: a heavy band loses {bc:.0%} of its run to gaps "
            f"(> {BAND_GAP_MAX:.0%}); a cut band reading as dashes [spec §1.2/§3.2 D3]."
        )
    if hs is not None and hs < HIERARCHY_MIN_RATIO:
        why.append(
            f"hierarchy_spread cut:texture is {hs:.2f}:1 (< {HIERARCHY_MIN_RATIO:.0f}:1); "
            f"drifting toward weight-flatness [spec §1.2/§1.7]."
        )
    if fw is not None and fw > FIXTURE_DARKNESS_MAX:
        why.append(
            f"fixture_weight: projected fixtures render at darkness {fw:.2f} "
            f"(> {FIXTURE_DARKNESS_MAX:.2f}); fixtures reaching cut value [spec §1.3/§3.2 D4]."
        )

    verdict = "review" if why else "pass"
    if not why:
        why.append("All scored axes within corpus tolerances [spec §1].")

    return {
        "schema_version": SCHEMA_VERSION,
        "inputs": {
            "after": str(after),
            "before": str(before) if before else None,
            "report_json": str(report_json) if report_json else None,
            "dpi": dpi,
        },
        "scores": {
            "false_poche": fp,
            "band_continuity": bc,
            "hierarchy_spread": hs,
            "fixture_weight": fw,
        },
        "thresholds": {
            "false_poche_max": FALSE_POCHE_MAX,
            "band_gap_max": BAND_GAP_MAX,
            "hierarchy_min_ratio": HIERARCHY_MIN_RATIO,
            "fixture_darkness_max": FIXTURE_DARKNESS_MAX,
        },
        "details": {
            "false_poche": fp_meta,
            "band_continuity": bc_meta,
            "hierarchy_spread": hs_meta,
            "fixture_weight": fw_meta,
        },
        "verdict": verdict,
        "why": why,
        "suggested_overrides": _suggested_overrides(report, bc_meta, fp_meta),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Deterministic visual judge for arch-line-weights output.")
    parser.add_argument("--after", required=True, help="Result drawing (.ai/.pdf) or pre-rendered .png")
    parser.add_argument(
        "--before", default=None, help="Optional source drawing / .png (recorded, not scored)"
    )
    parser.add_argument(
        "--report-json", default=None, help="Optional poché --report-json for envelope + fixtures"
    )
    parser.add_argument(
        "--dpi", type=int, default=96, help="Render dpi for vector inputs / assumed dpi for PNGs"
    )
    parser.add_argument("--out", default=None, help="Write verdict JSON here (also printed to stdout)")
    args = parser.parse_args(argv)

    result = judge(args.after, args.before, args.report_json, args.dpi)
    text = json.dumps(result, indent=2)
    if args.out:
        Path(args.out).write_text(text + "\n")
    print(text)
    return 0 if result["verdict"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
