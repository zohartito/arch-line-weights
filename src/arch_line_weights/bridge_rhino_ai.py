"""Orchestrate Rhino Make2D exports through Illustrator layout and proof stages."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .apply_jsx import apply_via_jsx, validate_apply_jsx_result
from .apply_jsx import default_output_path as apply_jsx_default_output_path
from .layout_jsx import default_output_path as layout_jsx_default_output_path
from .layout_jsx import layout_via_jsx
from .poche import PocheReport, apply_poche
from .run_report import build_poche_report


def _default_report_dir(src: str | os.PathLike[str]) -> Path:
    p = Path(src)
    return p.with_name(f"{p.stem} arch-lw-bridge")


def _default_poche_output_path(src: str | os.PathLike[str]) -> str:
    p = Path(src)
    stem = p.stem
    for suffix in (" HIERARCHY-jsx", " HIERARCHY-saas", " HIERARCHY"):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
            break
    return str(p.with_name(f"{stem} POCHE{p.suffix}"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def _stage(name: str, status: str, **fields: Any) -> dict[str, Any]:
    return {"name": name, "status": status, **fields}


def _summary_status(stages: list[dict[str, Any]]) -> str:
    statuses = {stage["status"] for stage in stages}
    if "failed" in statuses:
        return "failed"
    if "no_go" in statuses:
        return "no_go"
    if "needs_review" in statuses:
        return "needs_review"
    if "dry_run" in statuses or "planned" in statuses:
        return "dry_run"
    return "passed"


def _next_action(*, status: str, dry_run: bool) -> str:
    if status == "failed":
        return "Fix the failed stage, then rerun bridge-rhino-ai."
    if dry_run:
        return "Inspect planned stages, then rerun without --dry-run."
    return "Review stage reports before proof recapture or posting decisions."


def _build_result(
    *,
    src_abs: str,
    source: str,
    stages: list[dict[str, Any]],
    bridge_report: Path,
    dry_run: bool,
) -> dict[str, Any]:
    status = _summary_status(stages)
    return {
        "schema_version": 1,
        "source": {
            "input": src_abs,
            "command": "bridge-rhino-ai",
            "stage": "bridge",
            "layer_source": source,
        },
        "summary": {
            "status": status,
            "next_action": _next_action(status=status, dry_run=dry_run),
        },
        "stages": stages,
        "report_json": str(bridge_report),
    }


def _write_bridge_result(
    *,
    src_abs: str,
    source: str,
    stages: list[dict[str, Any]],
    bridge_report: Path,
    dry_run: bool,
) -> dict[str, Any]:
    result = _build_result(
        src_abs=src_abs,
        source=source,
        stages=stages,
        bridge_report=bridge_report,
        dry_run=dry_run,
    )
    _write_json(bridge_report, result)
    return result


def _raise_stage_failure(*, stage_name: str, bridge_report: Path, exc: Exception) -> None:
    raise RuntimeError(f"bridge-rhino-ai failed during {stage_name}; see {bridge_report}: {exc}") from exc


def bridge_rhino_ai(
    src: str,
    *,
    layout_output: str | None = None,
    artboard: str = "24x36in",
    fit_mode: str = "center",
    margin: str = "0.5in",
    allow_enlarge: bool = False,
    preset: str = "section",
    source: str = "rhino",
    scale: str = "1/4",
    for_print: bool = False,
    run_apply_jsx: bool = False,
    run_poche: bool = False,
    report_dir: str | None = None,
    timeout_min: int | None = None,
    bridge_strategy: str = "best",
    poche_style: str = "solid",
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run the narrow Rhino-export bridge.

    The first stage always normalizes the exported file with ``layout-jsx``.
    Hierarchy and poché are optional so the command can be used as a safe
    framing step before proof recapture.
    """
    if run_poche and not run_apply_jsx:
        raise ValueError("--poche requires --apply-jsx so poché runs on hierarchy output")

    src_abs = os.path.abspath(src)
    report_root = Path(report_dir) if report_dir else _default_report_dir(src_abs)
    report_root.mkdir(parents=True, exist_ok=True)

    layout_report = report_root / "layout-report.json"
    layout_jsx = report_root / "layout.jsx"
    bridge_report = report_root / "bridge-report.json"
    poche_report_path = report_root / "poche-report.json"
    geometry_report = report_root / "geometry-report.json"
    planned_layout_output = os.path.abspath(layout_output or layout_jsx_default_output_path(src_abs))

    stages: list[dict[str, Any]] = []
    try:
        layout_result = layout_via_jsx(
            src_abs,
            dst=layout_output,
            artboard=artboard,
            fit_mode=fit_mode,
            margin=margin,
            allow_enlarge=allow_enlarge,
            report_json=str(layout_report),
            jsx_path=str(layout_jsx),
            timeout_min=timeout_min,
            dry_run=dry_run,
        )
    except Exception as exc:
        stages.append(
            _stage(
                "layout",
                "failed",
                input=src_abs,
                output=planned_layout_output,
                report_json=str(layout_report),
                jsx_path=str(layout_jsx),
                error=str(exc),
            )
        )
        _write_bridge_result(
            src_abs=src_abs,
            source=source,
            stages=stages,
            bridge_report=bridge_report,
            dry_run=dry_run,
        )
        _raise_stage_failure(stage_name="layout", bridge_report=bridge_report, exc=exc)
    layout_status = "dry_run" if dry_run else "passed"
    try:
        layout_data = json.loads(layout_result.get("report") or "{}")
        layout_status = layout_data.get("summary", {}).get("status", layout_status)
    except json.JSONDecodeError:
        pass
    stages.append(
        _stage(
            "layout",
            layout_status,
            input=src_abs,
            output=layout_result["output"],
            report_json=layout_result["report_json"],
            jsx_path=layout_result.get("jsx_path", str(layout_jsx)),
        )
    )

    hierarchy_output = None
    if run_apply_jsx:
        if dry_run:
            hierarchy_output = apply_jsx_default_output_path(layout_result["output"])
            stages.append(
                _stage(
                    "apply-jsx",
                    "planned",
                    input=layout_result["output"],
                    output=hierarchy_output,
                    preset=preset,
                    source=source,
                    scale=scale,
                    for_print=for_print,
                )
            )
        else:
            effective_preset = None if preset == "section" and not for_print else preset
            planned_hierarchy_output = apply_jsx_default_output_path(layout_result["output"])
            try:
                apply_result = apply_via_jsx(
                    layout_result["output"],
                    None,
                    timeout_min=timeout_min,
                    preset=effective_preset,
                    scale=scale,
                    for_print=for_print,
                    printer=lambda _line: None,
                )
            except Exception as exc:
                stages.append(
                    _stage(
                        "apply-jsx",
                        "failed",
                        input=layout_result["output"],
                        output=planned_hierarchy_output,
                        preset=preset,
                        source=source,
                        scale=scale,
                        for_print=for_print,
                        error=str(exc),
                    )
                )
                _write_bridge_result(
                    src_abs=src_abs,
                    source=source,
                    stages=stages,
                    bridge_report=bridge_report,
                    dry_run=dry_run,
                )
                _raise_stage_failure(stage_name="apply-jsx", bridge_report=bridge_report, exc=exc)
            try:
                validate_apply_jsx_result(apply_result, expected_output=planned_hierarchy_output)
            except Exception as exc:
                stages.append(
                    _stage(
                        "apply-jsx",
                        "failed",
                        input=layout_result["output"],
                        output=planned_hierarchy_output,
                        report_path=apply_result.get("report_path"),
                        preset=preset,
                        source=source,
                        scale=scale,
                        for_print=for_print,
                        error=str(exc),
                    )
                )
                _write_bridge_result(
                    src_abs=src_abs,
                    source=source,
                    stages=stages,
                    bridge_report=bridge_report,
                    dry_run=dry_run,
                )
                _raise_stage_failure(stage_name="apply-jsx", bridge_report=bridge_report, exc=exc)
            hierarchy_output = apply_result["output"]
            stages.append(
                _stage(
                    "apply-jsx",
                    "passed",
                    input=layout_result["output"],
                    output=hierarchy_output,
                    report_path=apply_result.get("report_path"),
                    preset=preset,
                    source=source,
                    scale=scale,
                    for_print=for_print,
                )
            )

    if run_poche:
        assert hierarchy_output is not None
        planned_poche_output = _default_poche_output_path(hierarchy_output)
        if dry_run:
            stages.append(
                _stage(
                    "poche",
                    "planned",
                    input=hierarchy_output,
                    output=planned_poche_output,
                    report_json=str(poche_report_path),
                    geometry_json=str(geometry_report),
                    style=poche_style,
                    bridge_strategy=bridge_strategy,
                )
            )
        else:
            try:
                report = apply_poche(
                    hierarchy_output,
                    planned_poche_output,
                    style=poche_style,
                    bridge_strategy=bridge_strategy,
                    geometry_report_path=str(geometry_report),
                )
            except Exception as exc:
                stages.append(
                    _stage(
                        "poche",
                        "failed",
                        input=hierarchy_output,
                        output=planned_poche_output,
                        report_json=str(poche_report_path),
                        geometry_json=str(geometry_report),
                        style=poche_style,
                        bridge_strategy=bridge_strategy,
                        error=str(exc),
                    )
                )
                _write_bridge_result(
                    src_abs=src_abs,
                    source=source,
                    stages=stages,
                    bridge_report=bridge_report,
                    dry_run=dry_run,
                )
                _raise_stage_failure(stage_name="poche", bridge_report=bridge_report, exc=exc)
            status = "passed"
            if isinstance(report, PocheReport):
                run_report = build_poche_report(
                    input_path=hierarchy_output,
                    output_path=planned_poche_output,
                    source={
                        "style": poche_style,
                        "scale": 1 / 50,
                        "layer_source": source,
                        "bridge_strategy": bridge_strategy,
                        "min_inject_confidence": 0.85,
                    },
                    poche_report=report,
                )
                _write_json(poche_report_path, run_report)
                status = run_report["summary"]["status"]
            stages.append(
                _stage(
                    "poche",
                    status,
                    input=hierarchy_output,
                    output=planned_poche_output,
                    report_json=str(poche_report_path),
                    geometry_json=str(geometry_report),
                    style=poche_style,
                    bridge_strategy=bridge_strategy,
                )
            )

    return _write_bridge_result(
        src_abs=src_abs,
        source=source,
        stages=stages,
        bridge_report=bridge_report,
        dry_run=dry_run,
    )
