"""Illustrator layout bridge for Rhino Make2D exports.

The layout pass is intentionally narrower than ``apply-jsx``: it does not
change line weights or poché. It opens a Rhino/Illustrator export, sets a
known artboard size, optionally scales artwork to fit, centers the artwork,
and saves a PDF-compatible Illustrator file that downstream commands can use.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .apply_jsx import (
    _is_converted_match,
    open_in_illustrator,
    query_active_doc,
    resolve_timeout_minutes,
    run_jsx_in_illustrator,
)

POINTS_PER_INCH = 72.0
DEFAULT_OUTPUT_SUFFIX = " LAYOUT-jsx"

_LENGTH_UNITS = {
    "pt": 1.0,
    "pts": 1.0,
    "point": 1.0,
    "points": 1.0,
    "in": POINTS_PER_INCH,
    "inch": POINTS_PER_INCH,
    "inches": POINTS_PER_INCH,
}


def _jsx_string(value: str) -> str:
    return json.dumps(value)


def _format_js_number(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.6f}".rstrip("0").rstrip(".")


def parse_length(raw: str, *, default_unit: str = "in") -> float:
    """Parse a length string into Illustrator points.

    Bare values default to inches because sheet-size CLI input is normally
    written as ``24x36``. When a paired artboard dimension has an explicit unit,
    :func:`parse_artboard_size` passes that unit to both bare sides.
    """
    text = raw.strip().lower().replace(" ", "")
    if not text:
        raise ValueError("empty length")

    i = 0
    while i < len(text) and (text[i].isdigit() or text[i] in ".+-"):
        i += 1
    number_text = text[:i]
    unit = text[i:] or default_unit
    try:
        value = float(number_text)
    except ValueError as exc:
        raise ValueError(f"invalid length {raw!r}") from exc
    if value <= 0:
        raise ValueError(f"length must be positive: {raw!r}")
    factor = _LENGTH_UNITS.get(unit)
    if factor is None:
        raise ValueError(f"unsupported length unit in {raw!r}")
    return value * factor


def _length_unit(raw: str) -> str | None:
    text = raw.strip().lower().replace(" ", "")
    i = 0
    while i < len(text) and (text[i].isdigit() or text[i] in ".+-"):
        i += 1
    return text[i:] or None


def parse_artboard_size(raw: str) -> tuple[float, float]:
    """Parse ``WIDTHxHEIGHT`` into Illustrator points."""
    text = raw.strip().lower().replace("×", "x")
    parts = [p.strip() for p in text.split("x")]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError("artboard must be WIDTHxHEIGHT, e.g. 24x36in")

    left_unit = _length_unit(parts[0])
    right_unit = _length_unit(parts[1])
    shared_unit = right_unit or left_unit or "in"
    width = parse_length(parts[0], default_unit=shared_unit)
    height = parse_length(parts[1], default_unit=shared_unit)
    return width, height


def default_output_path(src: str | os.PathLike[str]) -> str:
    p = Path(src)
    return str(p.with_name(f"{p.stem}{DEFAULT_OUTPUT_SUFFIX}{p.suffix}"))


def _why_list(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(item) for item in raw]
    return [str(raw)]


def _raw_status(raw: dict[str, Any]) -> str:
    summary = raw.get("summary")
    if isinstance(summary, dict) and summary.get("status"):
        return str(summary["status"])
    return str(raw.get("status") or "failed")


def _raw_why(raw: dict[str, Any]) -> list[str]:
    summary = raw.get("summary")
    if isinstance(summary, dict) and "why" in summary:
        return _why_list(summary.get("why"))
    return _why_list(raw.get("why"))


def _raw_layout_value(raw: dict[str, Any], key: str) -> Any:
    layout = raw.get("layout")
    if isinstance(layout, dict) and key in layout:
        return layout[key]
    return raw.get(key)


def _normalize_layout_report(
    *,
    input_path: str,
    output_path: str,
    report_path: Path,
    raw_report: dict[str, Any],
    source: dict[str, Any],
    status: str,
    why: list[str] | None,
    artboard_width_pt: float,
    artboard_height_pt: float,
    margin_pt: float,
) -> dict[str, Any]:
    from .run_report import build_layout_jsx_report

    report = build_layout_jsx_report(
        input_path=input_path,
        output_path=output_path,
        source=source,
        status=status,
        artboard_width_pt=artboard_width_pt,
        artboard_height_pt=artboard_height_pt,
        margin_pt=margin_pt,
        selected_items=_raw_layout_value(raw_report, "selected_items"),
        scale=_raw_layout_value(raw_report, "scale"),
        translation=_raw_layout_value(raw_report, "translation"),
        original_visible_bounds=_raw_layout_value(raw_report, "original_visible_bounds"),
        final_visible_bounds=_raw_layout_value(raw_report, "final_visible_bounds"),
        why=why,
    )
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def _runtime_failure(status: str, why: list[str]) -> RuntimeError:
    detail = "; ".join(why) if why else "see layout report"
    return RuntimeError(f"layout-jsx {status}: {detail}")


def _converted_doc_match_kind(
    active_name: str | None,
    active_path: str | None,
    src_abs: str,
) -> str | None:
    if not active_name or "[Converted]" not in active_name:
        return None
    if not _is_converted_match(active_name, active_path, src_abs):
        return None
    if active_path:
        try:
            if os.path.realpath(active_path) == os.path.realpath(src_abs):
                return "exact_path"
        except OSError:
            return None
    return "pathless_stem"


def _layout_source_context(
    *,
    jsx_abs: str,
    fit_mode: str,
    allow_enlarge: bool,
    use_open_doc: bool,
    active_name: str | None,
    active_path: str | None,
    converted_doc_match: str | None,
) -> dict[str, Any]:
    return {
        "jsx_path": jsx_abs,
        "fit_mode": fit_mode,
        "allow_enlarge": allow_enlarge,
        "use_open_doc": use_open_doc,
        "active_doc_name": active_name,
        "active_doc_path": active_path,
        "converted_doc_match": converted_doc_match,
        "converted_doc_needs_review": converted_doc_match == "pathless_stem",
    }


LAYOUT_JSX_TEMPLATE = r"""#target illustrator

(function () {
    var TARGET = __TARGET__;
    var OUTPUT = __OUTPUT__;
    var REPORT = __REPORT__;
    var USE_OPEN_DOC = __USE_OPEN_DOC__;
    var SHEET_W = __SHEET_W__;
    var SHEET_H = __SHEET_H__;
    var MARGIN = __MARGIN__;
    var FIT_MODE = __FIT_MODE__;
    var ALLOW_ENLARGE = __ALLOW_ENLARGE__;

    try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch (e) {}

    function writeFile(p, s) {
        var f = new File(p);
        f.encoding = "UTF-8";
        f.open("w");
        f.write(s);
        f.close();
    }

    function esc(s) {
        return String(s).replace(/\\/g, "\\\\").replace(/"/g, "\\\"");
    }

    function boundsJson(b) {
        if (!b) return "null";
        return "[" + [b[0], b[1], b[2], b[3]].join(",") + "]";
    }

    function itemIsUsable(item) {
        try {
            if (item.locked || item.hidden) return false;
            var b = item.visibleBounds;
            return isFinite(b[0]) && isFinite(b[1]) && isFinite(b[2]) && isFinite(b[3])
                && Math.abs(b[2] - b[0]) > 0.001
                && Math.abs(b[1] - b[3]) > 0.001;
        } catch (e) {
            return false;
        }
    }

    function unionBounds(items) {
        var b = null;
        for (var i = 0; i < items.length; i++) {
            var item = items[i];
            if (!itemIsUsable(item)) continue;
            var ib = item.visibleBounds; // [left, top, right, bottom]
            if (b === null) {
                b = [ib[0], ib[1], ib[2], ib[3]];
            } else {
                if (ib[0] < b[0]) b[0] = ib[0];
                if (ib[1] > b[1]) b[1] = ib[1];
                if (ib[2] > b[2]) b[2] = ib[2];
                if (ib[3] < b[3]) b[3] = ib[3];
            }
        }
        return b;
    }

    function selectionItems(doc) {
        try { app.executeMenuCommand("deselectall"); } catch (e) {}
        try { app.executeMenuCommand("selectall"); } catch (e2) {}
        var out = [];
        try {
            for (var i = 0; i < doc.selection.length; i++) {
                if (itemIsUsable(doc.selection[i])) out.push(doc.selection[i]);
            }
        } catch (e3) {}
        if (out.length > 0) return out;

        // Fallback for documents where select-all does not populate selection.
        for (var p = 0; p < doc.pageItems.length; p++) {
            if (itemIsUsable(doc.pageItems[p])) out.push(doc.pageItems[p]);
        }
        return out;
    }

    function scaleItems(items, scalePct) {
        for (var i = 0; i < items.length; i++) {
            try {
                items[i].resize(
                    scalePct,
                    scalePct,
                    true,
                    true,
                    true,
                    true,
                    scalePct,
                    Transformation.DOCUMENTORIGIN
                );
            } catch (e) {
                try { items[i].resize(scalePct, scalePct); } catch (e2) {}
            }
        }
    }

    function translateItems(items, dx, dy) {
        for (var i = 0; i < items.length; i++) {
            var item = items[i];
            try { item.translate(dx, dy); } catch (e) {}
        }
    }

    try {
        var doc = null;
        if (USE_OPEN_DOC) {
            try { doc = app.activeDocument; } catch (e0) {}
        } else {
            for (var di = 0; di < app.documents.length; di++) {
                try {
                    if (app.documents[di].fullName.fsName === TARGET) {
                        doc = app.documents[di];
                        break;
                    }
                } catch (e1) {}
            }
        }
        if (!doc) {
            writeFile(REPORT, "{\"status\":\"failed\",\"why\":[\"target document not open\"]}\n");
            return;
        }
        if (app.activeDocument !== doc) app.activeDocument = doc;

        if (doc.artboards.length < 1) doc.artboards.add([0, SHEET_H, SHEET_W, 0]);
        doc.artboards[0].artboardRect = [0, SHEET_H, SHEET_W, 0];
        doc.artboards.setActiveArtboardIndex(0);

        var items = selectionItems(doc);
        var original = unionBounds(items);
        if (!original) {
            writeFile(REPORT, "{\"status\":\"no_go\",\"why\":[\"no visible unlocked artwork found\"]}\n");
            return;
        }

        var scale = 1.0;
        if (FIT_MODE === "fit") {
            var artW = Math.abs(original[2] - original[0]);
            var artH = Math.abs(original[1] - original[3]);
            var availW = Math.max(1, SHEET_W - (MARGIN * 2));
            var availH = Math.max(1, SHEET_H - (MARGIN * 2));
            scale = Math.min(availW / artW, availH / artH);
            if (!ALLOW_ENLARGE && scale > 1.0) scale = 1.0;
            if (isFinite(scale) && scale > 0 && Math.abs(scale - 1.0) > 0.0001) {
                scaleItems(items, scale * 100.0);
            }
        }

        var fitted = unionBounds(items);
        if (!fitted) fitted = original;
        var artCx = (fitted[0] + fitted[2]) / 2.0;
        var artCy = (fitted[1] + fitted[3]) / 2.0;
        var targetCx = SHEET_W / 2.0;
        var targetCy = SHEET_H / 2.0;
        var dx = targetCx - artCx;
        var dy = targetCy - artCy;
        translateItems(items, dx, dy);

        var finalBounds = unionBounds(items);

        try { app.executeMenuCommand("preview"); } catch (e2) {}
        var saveFile = new File(OUTPUT);
        var saveOpts = new IllustratorSaveOptions();
        saveOpts.pdfCompatible = true;
        doc.saveAs(saveFile, saveOpts);

        var rep = "{\n"
            + "  \"status\": \"passed\",\n"
            + "  \"command\": \"layout-jsx\",\n"
            + "  \"source\": \"" + esc(TARGET) + "\",\n"
            + "  \"output\": \"" + esc(OUTPUT) + "\",\n"
            + "  \"artboard\": {\"width_pt\": " + SHEET_W + ", \"height_pt\": " + SHEET_H + "},\n"
            + "  \"margin_pt\": " + MARGIN + ",\n"
            + "  \"fit_mode\": \"" + esc(FIT_MODE) + "\",\n"
            + "  \"allow_enlarge\": " + (ALLOW_ENLARGE ? "true" : "false") + ",\n"
            + "  \"selected_items\": " + items.length + ",\n"
            + "  \"scale\": " + scale + ",\n"
            + "  \"translation\": {\"dx\": " + dx + ", \"dy\": " + dy + "},\n"
            + "  \"original_visible_bounds\": " + boundsJson(original) + ",\n"
            + "  \"final_visible_bounds\": " + boundsJson(finalBounds) + "\n"
            + "}\n";
        writeFile(REPORT, rep);
    } catch (e) {
        writeFile(REPORT, "{\"status\":\"failed\",\"why\":[\"" + esc(e.toString()) + "\"]}\n");
    }
})();
"""


def render_layout_jsx(
    *,
    target: str,
    output: str,
    report_json: str,
    artboard_width_pt: float,
    artboard_height_pt: float,
    margin_pt: float,
    fit_mode: str = "center",
    allow_enlarge: bool = False,
    use_open_doc: bool = False,
) -> str:
    if fit_mode not in {"center", "fit"}:
        raise ValueError("fit_mode must be 'center' or 'fit'")
    return (
        LAYOUT_JSX_TEMPLATE.replace("__TARGET__", _jsx_string(target))
        .replace("__OUTPUT__", _jsx_string(output))
        .replace("__REPORT__", _jsx_string(report_json))
        .replace("__USE_OPEN_DOC__", "true" if use_open_doc else "false")
        .replace("__SHEET_W__", _format_js_number(artboard_width_pt))
        .replace("__SHEET_H__", _format_js_number(artboard_height_pt))
        .replace("__MARGIN__", _format_js_number(margin_pt))
        .replace("__FIT_MODE__", _jsx_string(fit_mode))
        .replace("__ALLOW_ENLARGE__", "true" if allow_enlarge else "false")
    )


def layout_via_jsx(
    src: str,
    *,
    dst: str | None = None,
    artboard: str = "24x36in",
    fit_mode: str = "center",
    margin: str = "0.5in",
    allow_enlarge: bool = False,
    report_json: str | None = None,
    jsx_path: str | None = None,
    timeout_min: int | None = None,
    dry_run: bool = False,
) -> dict:
    """Open ``src`` in Illustrator, frame artwork, save to ``dst``."""
    from .run_report import build_layout_jsx_report

    src_abs = os.path.abspath(src)
    resolved_dst = os.path.abspath(dst or default_output_path(src_abs))
    if src_abs == resolved_dst:
        raise ValueError("dst must differ from src")

    artboard_width, artboard_height = parse_artboard_size(artboard)
    margin_pt = parse_length(margin)
    if fit_mode not in {"center", "fit"}:
        raise ValueError("fit_mode must be 'center' or 'fit'")

    if report_json is None:
        report_json = "/tmp/arch_lw_layout_report.json"
    report_abs = os.path.abspath(report_json)
    if jsx_path is None:
        jsx_path = "/tmp/arch_lw_layout.jsx"
    jsx_abs = os.path.abspath(jsx_path)

    def write_rendered_jsx(*, use_open_doc: bool) -> None:
        Path(jsx_abs).parent.mkdir(parents=True, exist_ok=True)
        Path(jsx_abs).write_text(
            render_layout_jsx(
                target=src_abs,
                output=resolved_dst,
                report_json=report_abs,
                artboard_width_pt=artboard_width,
                artboard_height_pt=artboard_height,
                margin_pt=margin_pt,
                fit_mode=fit_mode,
                allow_enlarge=allow_enlarge,
                use_open_doc=use_open_doc,
            )
        )

    active_name = None
    active_path = None
    use_open_doc = False
    converted_doc_match = None

    if dry_run:
        write_rendered_jsx(use_open_doc=False)
        dry_report = build_layout_jsx_report(
            input_path=src_abs,
            output_path=resolved_dst,
            source=_layout_source_context(
                jsx_abs=jsx_abs,
                fit_mode=fit_mode,
                allow_enlarge=allow_enlarge,
                use_open_doc=False,
                active_name=None,
                active_path=None,
                converted_doc_match=None,
            ),
            status="dry_run",
            artboard_width_pt=artboard_width,
            artboard_height_pt=artboard_height,
            margin_pt=margin_pt,
        )
        Path(report_abs).parent.mkdir(parents=True, exist_ok=True)
        Path(report_abs).write_text(json.dumps(dry_report, indent=2, sort_keys=True) + "\n")
        return {
            "output": resolved_dst,
            "report_json": report_abs,
            "jsx_path": jsx_abs,
            "report": json.dumps(dry_report, indent=2, sort_keys=True),
            "dry_run": True,
            "use_open_doc": False,
        }

    active_name, active_path = query_active_doc()
    if active_name and "[Converted]" in active_name:
        converted_doc_match = _converted_doc_match_kind(active_name, active_path, src_abs)
        if converted_doc_match:
            use_open_doc = True
        else:
            raise RuntimeError(
                f"Illustrator has '{active_name}' open. Save or close that [Converted] "
                "document before running layout-jsx on another source."
            )

    write_rendered_jsx(use_open_doc=use_open_doc)

    timeout_sec = resolve_timeout_minutes(timeout_min) * 60
    Path(report_abs).parent.mkdir(parents=True, exist_ok=True)
    if not use_open_doc:
        open_in_illustrator(src_abs, timeout_sec=min(timeout_sec, 1800))
        active_name, active_path = query_active_doc()
        if active_name and "[Converted]" in active_name:
            converted_doc_match = _converted_doc_match_kind(active_name, active_path, src_abs)
            if converted_doc_match:
                use_open_doc = True
                write_rendered_jsx(use_open_doc=True)
            else:
                failed_report = build_layout_jsx_report(
                    input_path=src_abs,
                    output_path=resolved_dst,
                    source=_layout_source_context(
                        jsx_abs=jsx_abs,
                        fit_mode=fit_mode,
                        allow_enlarge=allow_enlarge,
                        use_open_doc=False,
                        active_name=active_name,
                        active_path=active_path,
                        converted_doc_match=None,
                    ),
                    status="failed",
                    artboard_width_pt=artboard_width,
                    artboard_height_pt=artboard_height,
                    margin_pt=margin_pt,
                    why=["Illustrator opened converted document that does not match requested source"],
                )
                Path(report_abs).write_text(json.dumps(failed_report, indent=2, sort_keys=True) + "\n")
                raise RuntimeError(
                    f"Illustrator opened '{active_name}' as a [Converted] document, "
                    "but it does not match the requested source."
                )
    run_jsx_in_illustrator(jsx_abs, timeout=timeout_sec)
    report_path = Path(report_abs)
    if not report_path.exists():
        failed_report = build_layout_jsx_report(
            input_path=src_abs,
            output_path=resolved_dst,
            source=_layout_source_context(
                jsx_abs=jsx_abs,
                fit_mode=fit_mode,
                allow_enlarge=allow_enlarge,
                use_open_doc=use_open_doc,
                active_name=active_name,
                active_path=active_path,
                converted_doc_match=converted_doc_match,
            ),
            status="failed",
            artboard_width_pt=artboard_width,
            artboard_height_pt=artboard_height,
            margin_pt=margin_pt,
            why=["did not write a report"],
        )
        report_path.write_text(json.dumps(failed_report, indent=2, sort_keys=True) + "\n")
        raise RuntimeError("layout-jsx failed: did not write a report")

    raw_text = report_path.read_text()
    try:
        raw_report = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        failed_report = build_layout_jsx_report(
            input_path=src_abs,
            output_path=resolved_dst,
            source=_layout_source_context(
                jsx_abs=jsx_abs,
                fit_mode=fit_mode,
                allow_enlarge=allow_enlarge,
                use_open_doc=use_open_doc,
                active_name=active_name,
                active_path=active_path,
                converted_doc_match=converted_doc_match,
            ),
            status="failed",
            artboard_width_pt=artboard_width,
            artboard_height_pt=artboard_height,
            margin_pt=margin_pt,
            why=["layout report was not valid JSON"],
        )
        report_path.write_text(json.dumps(failed_report, indent=2, sort_keys=True) + "\n")
        raise RuntimeError("layout-jsx failed: layout report was not valid JSON") from exc

    raw_status = str(raw_report.get("status") or "failed")
    why = [str(reason) for reason in raw_report.get("why") or []]
    if raw_status in {"failed", "no_go"}:
        normalized_report = build_layout_jsx_report(
            input_path=src_abs,
            output_path=resolved_dst,
            source=_layout_source_context(
                jsx_abs=jsx_abs,
                fit_mode=fit_mode,
                allow_enlarge=allow_enlarge,
                use_open_doc=use_open_doc,
                active_name=active_name,
                active_path=active_path,
                converted_doc_match=converted_doc_match,
            ),
            status=raw_status,
            artboard_width_pt=artboard_width,
            artboard_height_pt=artboard_height,
            margin_pt=margin_pt,
            why=why or [raw_status],
        )
        report_path.write_text(json.dumps(normalized_report, indent=2, sort_keys=True) + "\n")
        raise RuntimeError(f"layout-jsx failed: {'; '.join(normalized_report['summary']['why'])}")

    if not Path(resolved_dst).exists():
        normalized_report = build_layout_jsx_report(
            input_path=src_abs,
            output_path=resolved_dst,
            source=_layout_source_context(
                jsx_abs=jsx_abs,
                fit_mode=fit_mode,
                allow_enlarge=allow_enlarge,
                use_open_doc=use_open_doc,
                active_name=active_name,
                active_path=active_path,
                converted_doc_match=converted_doc_match,
            ),
            status="failed",
            artboard_width_pt=artboard_width,
            artboard_height_pt=artboard_height,
            margin_pt=margin_pt,
            why=["output file was not written"],
        )
        report_path.write_text(json.dumps(normalized_report, indent=2, sort_keys=True) + "\n")
        raise RuntimeError("layout-jsx failed: output file was not written")

    converted_doc_needs_review = converted_doc_match == "pathless_stem"
    normalized_report = build_layout_jsx_report(
        input_path=src_abs,
        output_path=resolved_dst,
        source=_layout_source_context(
            jsx_abs=jsx_abs,
            fit_mode=fit_mode,
            allow_enlarge=allow_enlarge,
            use_open_doc=use_open_doc,
            active_name=active_name,
            active_path=active_path,
            converted_doc_match=converted_doc_match,
        ),
        status="needs_review" if converted_doc_needs_review else "passed",
        artboard_width_pt=artboard_width,
        artboard_height_pt=artboard_height,
        margin_pt=margin_pt,
        selected_items=raw_report.get("selected_items"),
        scale=raw_report.get("scale"),
        translation=raw_report.get("translation"),
        original_visible_bounds=raw_report.get("original_visible_bounds"),
        final_visible_bounds=raw_report.get("final_visible_bounds"),
        why=["converted document matched by pathless stem"] if converted_doc_needs_review else None,
    )
    report_text = json.dumps(normalized_report, indent=2, sort_keys=True)
    report_path.write_text(report_text + "\n")
    return {
        "output": resolved_dst,
        "report_json": report_abs,
        "jsx_path": jsx_abs,
        "report": report_text,
        "dry_run": False,
        "use_open_doc": use_open_doc,
    }
