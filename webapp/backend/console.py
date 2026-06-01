"""Local designer-console run model for the webapp prototype.

This module is intentionally webapp-scoped. It wraps existing arch-lw engine
entry points, stores raw local reports under the local storage root, and only
returns public-safe summaries to the browser.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import uuid
import zipfile
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, BinaryIO

from arch_line_weights.apply_jsx import apply_via_jsx
from arch_line_weights.inspect import inspect_file
from arch_line_weights.poche import PocheReport, apply_poche

try:  # PR #36 branches provide these; older branches honestly degrade.
    from arch_line_weights.apply_jsx import validate_apply_jsx_result
except ImportError:  # pragma: no cover - depends on branch composition
    validate_apply_jsx_result = None

try:  # PR #36 branches provide layout-jsx; older branches keep this absent.
    from arch_line_weights.layout_jsx import layout_via_jsx
except ImportError:  # pragma: no cover - depends on branch composition
    layout_via_jsx = None


CONSOLE_GUARDRAILS = [
    "Posting/public proof is NO-GO unless W5/W7 explicitly accepts it.",
    "Synthetic proof does not close #30.",
    "Private USC regression stays private.",
]

WORKFLOW_LABELS = {
    "section": "Section",
    "plan": "Plan",
    "detail": "Detail",
    "synthetic_proof_demo": "Synthetic proof / demo",
}

STAGE_DEFINITIONS = [
    ("inspect_file", "Inspect File"),
    ("run_layout", "Run Layout"),
    ("apply_line_weights", "Apply Line Weights"),
    ("generate_poche", "Generate Poché"),
    ("export_proof_packet", "Export Proof Packet"),
]

STAGE_STATUSES = {"not_run", "running", "passed", "needs_review", "failed", "no_go"}
TERMINAL_BAD_STATUSES = {"failed", "no_go"}

_LOCAL_PATH_RE = re.compile(
    r"(/Users/|/private/|/var/folders/|/tmp/|[A-Za-z]:\\|\\\\|file://)",
    re.IGNORECASE,
)


@dataclass
class ConsoleStage:
    key: str
    label: str
    status: str = "not_run"
    what_changed: list[str] = field(default_factory=list)
    what_skipped: list[str] = field(default_factory=list)
    what_failed: list[str] = field(default_factory=list)
    why: list[str] = field(default_factory=list)
    next_step: str = "Choose an input file, then run this stage."
    output_path: str | None = None
    raw_report_path: str | None = None
    updated_at: str | None = None

    def start(self) -> None:
        self.status = "running"
        self.what_failed = []
        self.updated_at = _now_iso()

    def finish(
        self,
        *,
        status: str,
        what_changed: list[str] | None = None,
        what_skipped: list[str] | None = None,
        what_failed: list[str] | None = None,
        why: list[str] | None = None,
        next_step: str,
        output_path: str | None = None,
        raw_report_path: str | None = None,
    ) -> None:
        if status not in STAGE_STATUSES:
            raise ValueError(f"unknown console stage status: {status}")
        self.status = status
        self.what_changed = list(what_changed or [])
        self.what_skipped = list(what_skipped or [])
        self.what_failed = list(what_failed or [])
        self.why = list(why or [])
        self.next_step = next_step
        self.output_path = output_path
        self.raw_report_path = raw_report_path
        self.updated_at = _now_iso()

    def to_public_dict(self, *, redact: bool = True) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "status": self.status,
            "what_changed": _redact_list(self.what_changed) if redact else list(self.what_changed),
            "what_skipped": _redact_list(self.what_skipped) if redact else list(self.what_skipped),
            "what_failed": _redact_list(self.what_failed) if redact else list(self.what_failed),
            "why": _redact_list(self.why) if redact else list(self.why),
            "next_step": _redact_text(self.next_step) if redact else self.next_step,
            "output_file": _filename(self.output_path),
            "raw_report_available": bool(self.raw_report_path),
            "updated_at": self.updated_at,
        }


@dataclass
class ConsoleRun:
    run_id: str
    workflow: str
    original_filename: str
    input_path: str
    root: str
    created_at: str
    guardrails: list[str] = field(default_factory=lambda: list(CONSOLE_GUARDRAILS))
    stages: dict[str, ConsoleStage] = field(default_factory=dict)
    artifacts: dict[str, str] = field(default_factory=dict)

    def public_summary(self, *, redact: bool = True) -> dict[str, Any]:
        stage_rows = [
            self.stages[key].to_public_dict(redact=redact)
            for key, _label in STAGE_DEFINITIONS
            if key in self.stages
        ]
        return {
            "schema_version": 1,
            "run_id": self.run_id,
            "workflow": self.workflow,
            "workflow_label": WORKFLOW_LABELS.get(self.workflow, self.workflow),
            "original_filename": self.original_filename,
            "created_at": self.created_at,
            "overall_status": _overall_status(self.stages),
            "guardrails": list(self.guardrails),
            "stages": stage_rows,
            "report": _rollup_report(stage_rows),
            "artifacts": [
                {
                    "key": key,
                    "filename": Path(path).name,
                    "available": Path(path).exists(),
                    "download_url": f"/api/console/runs/{self.run_id}/artifacts/{key}",
                }
                for key, path in sorted(self.artifacts.items())
            ],
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "workflow": self.workflow,
            "original_filename": self.original_filename,
            "input_path": self.input_path,
            "root": self.root,
            "created_at": self.created_at,
            "guardrails": list(self.guardrails),
            "stages": {key: asdict(stage) for key, stage in self.stages.items()},
            "artifacts": dict(self.artifacts),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConsoleRun":
        stages = {
            key: ConsoleStage(**stage_data)
            for key, stage_data in data.get("stages", {}).items()
        }
        return cls(
            run_id=str(data["run_id"]),
            workflow=str(data["workflow"]),
            original_filename=str(data["original_filename"]),
            input_path=str(data["input_path"]),
            root=str(data["root"]),
            created_at=str(data["created_at"]),
            guardrails=list(data.get("guardrails") or CONSOLE_GUARDRAILS),
            stages=stages,
            artifacts=dict(data.get("artifacts") or {}),
        )


class DesignerConsoleStore:
    """Small file-backed store for local designer-console runs."""

    def __init__(self, root: str | os.PathLike[str]) -> None:
        self.root = Path(root).expanduser()
        self.root.mkdir(parents=True, exist_ok=True)

    def create_run(
        self,
        input_path: str | os.PathLike[str],
        *,
        workflow: str,
        original_filename: str | None = None,
    ) -> ConsoleRun:
        workflow = _normalize_workflow(workflow)
        src = Path(input_path)
        _validate_input_suffix(src.name)

        run_id = uuid.uuid4().hex
        run_root = self.root / run_id
        raw_root = run_root / "raw"
        raw_root.mkdir(parents=True, exist_ok=True)

        display_name = original_filename or src.name
        suffix = Path(display_name).suffix.lower() or src.suffix.lower() or ".ai"
        stored_input = run_root / f"input{suffix}"
        shutil.copy2(src, stored_input)

        run = ConsoleRun(
            run_id=run_id,
            workflow=workflow,
            original_filename=display_name,
            input_path=str(stored_input),
            root=str(run_root),
            created_at=_now_iso(),
            stages={
                key: ConsoleStage(key=key, label=label)
                for key, label in STAGE_DEFINITIONS
            },
        )
        self.save(run)
        return run

    def create_run_from_upload(
        self,
        stream: BinaryIO,
        *,
        filename: str,
        workflow: str,
    ) -> ConsoleRun:
        _validate_input_suffix(filename)
        incoming = self.root / "_incoming"
        incoming.mkdir(parents=True, exist_ok=True)
        temp_path = incoming / f"{uuid.uuid4().hex}{Path(filename).suffix.lower()}"
        with temp_path.open("wb") as f:
            shutil.copyfileobj(stream, f, length=1024 * 1024)
        try:
            return self.create_run(temp_path, workflow=workflow, original_filename=filename)
        finally:
            temp_path.unlink(missing_ok=True)

    def create_synthetic_demo_run(self) -> ConsoleRun:
        from arch_line_weights.poche_saas import write_synthetic_test_ai

        incoming = self.root / "_incoming"
        incoming.mkdir(parents=True, exist_ok=True)
        temp_path = incoming / f"synthetic-demo-{uuid.uuid4().hex}.ai"
        write_synthetic_test_ai(
            temp_path,
            layer_name="WALL::ClippingPlaneIntersections::Default",
        )
        try:
            return self.create_run(
                temp_path,
                workflow="synthetic_proof_demo",
                original_filename="synthetic-proof-demo.ai",
            )
        finally:
            temp_path.unlink(missing_ok=True)

    def load(self, run_id: str) -> ConsoleRun:
        path = self._state_path(run_id)
        if not path.exists():
            raise KeyError(run_id)
        return ConsoleRun.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def save(self, run: ConsoleRun) -> None:
        self._state_path(run.run_id).write_text(
            json.dumps(run.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def run_stage(self, run_id: str, stage_key: str) -> ConsoleRun:
        if stage_key not in {key for key, _label in STAGE_DEFINITIONS}:
            raise KeyError(stage_key)
        method = getattr(self, stage_key)
        return method(run_id)

    def inspect_file(self, run_id: str) -> ConsoleRun:
        run = self._start(run_id, "inspect_file")
        stage = run.stages["inspect_file"]
        try:
            report = inspect_file(run.input_path)
            report_data = report.to_dict()
            raw_report_path = self._raw_path(run, "inspect-report.json")
            raw_report_path.write_text(
                json.dumps(report_data, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            total_stroked = int(report_data.get("total_stroked") or 0)
            layer_count = len(report_data.get("layer_names") or [])
            color_count = len(report_data.get("stroke_colors") or {})
            status = "passed" if total_stroked else "needs_review"
            stage.finish(
                status=status,
                what_changed=[
                    f"Inspected {report_data.get('pages', 0)} page(s), "
                    f"{report_data.get('total_drawings', 0)} drawing object(s), "
                    f"and {total_stroked} stroked path(s)."
                ],
                what_skipped=[
                    "No artwork was modified during inspection.",
                    "Layout, line weights, poché, and proof packet stages have not run yet.",
                ],
                why=[
                    f"{layer_count} layer name(s) detected.",
                    f"{color_count} stroke color bucket(s) detected.",
                ],
                next_step=(
                    "Run Layout before applying line weights."
                    if status == "passed"
                    else "Review the export: no stroked paths were detected."
                ),
                raw_report_path=str(raw_report_path),
            )
        except Exception as exc:  # noqa: BLE001 - surfaced in stage report
            stage.finish(
                status="failed",
                what_failed=[_exception_message(exc)],
                why=["The existing inspect engine could not read this file."],
                next_step="Re-export from Rhino or Illustrator, then inspect again.",
            )
        self.save(run)
        return run

    def run_layout(self, run_id: str) -> ConsoleRun:
        run = self._start(run_id, "run_layout")
        stage = run.stages["run_layout"]
        output = self._output_path(run, "LAYOUT-jsx")
        raw_report_path = self._raw_path(run, "layout-report.json")
        jsx_path = self._raw_path(run, "layout.jsx")
        try:
            if layout_via_jsx is None:
                shutil.copy2(run.input_path, output)
                run.artifacts["layout_output"] = str(output)
                stage.finish(
                    status="needs_review",
                    what_changed=[f"Prepared layout working copy {output.name}."],
                    what_skipped=[
                        "layout-jsx is not available in this worktree; no layout normalization ran."
                    ],
                    why=[
                        "This console can render and advance the local workflow, "
                        "but the layout validator arrives with the verification-core branch."
                    ],
                    next_step="Apply Line Weights, then review layout manually.",
                    output_path=str(output),
                )
                self.save(run)
                return run

            result = layout_via_jsx(
                run.input_path,
                dst=str(output),
                report_json=str(raw_report_path),
                jsx_path=str(jsx_path),
            )
            report_data = _load_json_report(raw_report_path, result.get("report"))
            status = _report_status(report_data, default="passed")
            _require_stage_output(status=status, output_path=Path(result["output"]), report_label="layout-jsx")
            run.artifacts["layout_output"] = str(output)
            stage.finish(
                status=status,
                what_changed=[f"Created layout-normalized file {output.name}."],
                what_skipped=["Line weights, poché, and proof packet stages have not run yet."],
                why=_report_why(report_data, fallback=["layout-jsx completed its report contract."]),
                next_step=(
                    "Apply Line Weights."
                    if status == "passed"
                    else "Review the layout output before applying line weights."
                ),
                output_path=str(output),
                raw_report_path=str(raw_report_path),
            )
        except Exception as exc:  # noqa: BLE001 - surfaced in stage report
            stage.finish(
                status=_status_from_exception(exc),
                what_failed=[_exception_message(exc)],
                why=["layout-jsx did not produce a trustworthy layout output."],
                next_step="Fix the layout/export issue, then run layout again.",
                output_path=str(output),
                raw_report_path=str(raw_report_path) if raw_report_path.exists() else None,
            )
        self.save(run)
        return run

    def apply_line_weights(self, run_id: str) -> ConsoleRun:
        run = self._start(run_id, "apply_line_weights")
        stage = run.stages["apply_line_weights"]
        layout_output = run.artifacts.get("layout_output")
        if not layout_output or not Path(layout_output).exists():
            stage.finish(
                status="failed",
                what_failed=["Layout output is missing."],
                why=["Apply Line Weights depends on the Run Layout stage."],
                next_step="Run Layout, then apply line weights.",
            )
            self.save(run)
            return run

        output = self._derived_output_path(Path(layout_output), "HIERARCHY-jsx")
        jsx_path = self._raw_path(run, "apply-line-weights.jsx")
        preset = _preset_for_workflow(run.workflow)
        effective_preset = None if preset == "section" else preset
        try:
            result = apply_via_jsx(
                layout_output,
                str(output),
                jsx_path=str(jsx_path),
                preset=effective_preset,
                printer=lambda _line: None,
            )
            _validate_apply_result(result, expected_output=output)
            run.artifacts["hierarchy_output"] = str(output)
            report_text = str(result.get("report") or "")
            status = _text_report_status(report_text)
            stage.finish(
                status=status,
                what_changed=[
                    f"Applied {WORKFLOW_LABELS.get(run.workflow, run.workflow)} line weights "
                    f"to {output.name}."
                ],
                what_skipped=["Poché and proof packet stages have not run yet."],
                why=["apply-jsx output/report validation completed."],
                next_step=(
                    "Generate Poché or export a proof packet."
                    if status == "passed"
                    else "Review the apply-jsx report before proof use."
                ),
                output_path=str(output),
                raw_report_path=str(result.get("report_path")) if result.get("report_path") else None,
            )
        except Exception as exc:  # noqa: BLE001 - surfaced in stage report
            stage.finish(
                status=_status_from_exception(exc),
                what_failed=[_exception_message(exc)],
                why=["apply-jsx validation rejected the hierarchy output/report."],
                next_step="Fix the apply-jsx issue, then run line weights again.",
                output_path=str(output),
            )
        self.save(run)
        return run

    def generate_poche(self, run_id: str) -> ConsoleRun:
        run = self._start(run_id, "generate_poche")
        stage = run.stages["generate_poche"]
        hierarchy_output = run.artifacts.get("hierarchy_output")
        if not hierarchy_output or not Path(hierarchy_output).exists():
            stage.finish(
                status="failed",
                what_failed=["Hierarchy output is missing."],
                why=["Generate Poché depends on Apply Line Weights."],
                next_step="Apply Line Weights, then generate poché.",
            )
            self.save(run)
            return run

        output = self._poche_output_path(Path(hierarchy_output))
        raw_report_path = self._raw_path(run, "poche-report.json")
        raw_dir = raw_report_path.parent
        try:
            report = apply_poche(
                hierarchy_output,
                str(output),
                workdir=str(raw_dir),
                bridge_strategy="best",
            )
            report_data = _poche_report_dict(
                report if isinstance(report, PocheReport) else PocheReport(),
                input_name=Path(hierarchy_output).name,
                output_name=output.name,
            )
            raw_report_path.write_text(
                json.dumps(report_data, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            status = _poche_status(report_data)
            _require_stage_output(status=status, output_path=output, report_label="poche")
            run.artifacts["poche_output"] = str(output)
            summary = report_data["summary"]
            stage.finish(
                status=status,
                what_changed=[
                    f"Generated {summary['polygons_injected']} injected poché polygon(s) "
                    f"in {output.name}."
                ],
                what_skipped=[],
                why=_poche_why(report_data),
                next_step=(
                    "Export Proof Packet."
                    if status == "passed"
                    else "Review low-confidence or failed poché layers before proof use."
                ),
                output_path=str(output),
                raw_report_path=str(raw_report_path),
            )
        except Exception as exc:  # noqa: BLE001 - surfaced in stage report
            stage.finish(
                status=_status_from_exception(exc),
                what_failed=[_exception_message(exc)],
                why=["Poché did not produce a trustworthy output/report."],
                next_step="Fix cut-layer closure or poché settings, then generate poché again.",
                output_path=str(output),
                raw_report_path=str(raw_report_path) if raw_report_path.exists() else None,
            )
        self.save(run)
        return run

    def export_proof_packet(self, run_id: str) -> ConsoleRun:
        run = self._start(run_id, "export_proof_packet")
        stage = run.stages["export_proof_packet"]

        raw_summary = run.public_summary(redact=False)
        if _contains_private_path(raw_summary):
            stage.finish(
                status="no_go",
                what_failed=["Public proof summary contains a private/local path."],
                why=["Proof packets must be public-safe summaries separated from raw local reports."],
                next_step="Remove private/local paths from the summary source, then export again.",
            )
            self.save(run)
            return run

        packet_path = Path(run.root) / "proof-packet.zip"
        prior_status = _overall_status(
            {key: prior for key, prior in run.stages.items() if key != "export_proof_packet"}
        )
        status = prior_status if prior_status in TERMINAL_BAD_STATUSES else "passed"
        if prior_status == "needs_review":
            status = "needs_review"
        if not any(key in run.artifacts for key in ("layout_output", "hierarchy_output", "poche_output")):
            status = "needs_review"

        stage.finish(
            status=status,
            what_changed=[f"Created local proof packet {packet_path.name}."],
            what_skipped=[
                "Raw local reports and source drawings were not included in the public-safe packet."
            ],
            why=[
                "Public-safe summary contains no local path patterns.",
                "Posting/public proof still requires W5/W7 acceptance.",
            ],
            next_step=(
                "Review the packet with W5/W7 before any public proof claim."
                if status == "passed"
                else "Resolve failed, no-go, missing, or review stages before using this packet."
            ),
            output_path=str(packet_path),
        )
        run.artifacts["proof_packet"] = str(packet_path)

        final_raw_summary = run.public_summary(redact=False)
        if _contains_private_path(final_raw_summary):
            run.artifacts.pop("proof_packet", None)
            stage.finish(
                status="no_go",
                what_failed=["Proof packet contents would contain a private/local path."],
                why=["The packet was blocked before writing public-safe artifacts."],
                next_step="Remove private/local paths from stage summaries, then export again.",
            )
            self.save(run)
            return run

        _write_proof_packet(packet_path, run.public_summary(redact=True))
        self.save(run)
        return run

    def artifact_path(self, run_id: str, artifact_key: str) -> Path:
        run = self.load(run_id)
        if artifact_key not in run.artifacts:
            raise KeyError(artifact_key)
        path = Path(run.artifacts[artifact_key])
        if not path.exists():
            raise FileNotFoundError(path)
        return path

    def _start(self, run_id: str, stage_key: str) -> ConsoleRun:
        run = self.load(run_id)
        run.stages[stage_key].start()
        self.save(run)
        return run

    def _state_path(self, run_id: str) -> Path:
        return self.root / run_id / "state.json"

    @staticmethod
    def _raw_path(run: ConsoleRun, name: str) -> Path:
        path = Path(run.root) / "raw" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def _output_path(run: ConsoleRun, suffix: str) -> Path:
        src = Path(run.input_path)
        return Path(run.root) / f"{Path(run.original_filename).stem} {suffix}{src.suffix}"

    @staticmethod
    def _derived_output_path(src: Path, suffix: str) -> Path:
        return src.with_name(f"{src.stem} {suffix}{src.suffix}")

    @staticmethod
    def _poche_output_path(src: Path) -> Path:
        stem = src.stem
        for suffix in (" HIERARCHY-jsx", " HIERARCHY-saas", " HIERARCHY"):
            if stem.endswith(suffix):
                stem = stem[: -len(suffix)]
                break
        return src.with_name(f"{stem} POCHE{src.suffix}")


def default_console_root(storage_root: Path) -> Path:
    return storage_root / "designer-console"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _normalize_workflow(value: str) -> str:
    normalized = value.strip().lower().replace("-", "_")
    if normalized == "synthetic":
        normalized = "synthetic_proof_demo"
    if normalized not in WORKFLOW_LABELS:
        raise ValueError(f"unknown workflow {value!r}")
    return normalized


def _validate_input_suffix(filename: str) -> None:
    suffix = Path(filename).suffix.lower()
    if suffix not in {".ai", ".pdf"}:
        raise ValueError(f"unsupported file type {suffix!r}; expected .ai or .pdf")


def _preset_for_workflow(workflow: str) -> str:
    if workflow == "synthetic_proof_demo":
        return "section"
    return workflow


def _filename(path: str | None) -> str | None:
    return Path(path).name if path else None


def _redact_text(text: str) -> str:
    return _LOCAL_PATH_RE.sub("[local path]", text)


def _redact_list(values: list[str]) -> list[str]:
    return [_redact_text(str(value)) for value in values]


def _contains_private_path(value: object) -> bool:
    return bool(_LOCAL_PATH_RE.search(json.dumps(value, sort_keys=True, default=str)))


def _overall_status(stages: dict[str, ConsoleStage]) -> str:
    statuses = [stage.status for stage in stages.values()]
    if "running" in statuses:
        return "running"
    if "no_go" in statuses:
        return "no_go"
    if "failed" in statuses:
        return "failed"
    if any(status in {"not_run", "needs_review"} for status in statuses):
        return "needs_review"
    return "passed"


def _rollup_report(stage_rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "what_changed": _flatten_stage_list(stage_rows, "what_changed"),
        "what_skipped": _flatten_stage_list(stage_rows, "what_skipped"),
        "what_failed": _flatten_stage_list(stage_rows, "what_failed"),
        "why": _flatten_stage_list(stage_rows, "why"),
        "next_step": _next_step(stage_rows),
    }


def _flatten_stage_list(stage_rows: list[dict[str, Any]], key: str) -> list[str]:
    items: list[str] = []
    for stage in stage_rows:
        for value in stage.get(key) or []:
            if value not in items:
                items.append(str(value))
    return items


def _next_step(stage_rows: list[dict[str, Any]]) -> str:
    for stage in stage_rows:
        if stage["status"] in {"failed", "no_go", "needs_review", "not_run"}:
            return str(stage["next_step"])
    return "Review the packet with W5/W7 before any public proof claim."


def _exception_message(exc: Exception) -> str:
    return f"{type(exc).__name__}: {exc}"


def _status_from_exception(exc: Exception) -> str:
    message = _exception_message(exc).lower()
    if "no_go" in message or "no-go" in message:
        return "no_go"
    return "failed"


def _load_json_report(path: Path, fallback: Any = None) -> dict[str, Any]:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    if isinstance(fallback, dict):
        return fallback
    if isinstance(fallback, str) and fallback.strip():
        return json.loads(fallback)
    return {}


def _report_status(report: dict[str, Any], *, default: str) -> str:
    raw = (
        report.get("status")
        or report.get("summary", {}).get("status")
        or report.get("result", {}).get("status")
        or default
    )
    status = str(raw).lower().replace("-", "_")
    if status in {"ok", "done", "pass", "passed"}:
        return "passed"
    if status in {"review", "needs_review"}:
        return "needs_review"
    if status in {"fail", "failed", "error"}:
        return "failed"
    if status in {"no_go", "nogo", "blocked"}:
        return "no_go"
    if _contains_no_go(report):
        return "no_go"
    return default


def _report_why(report: dict[str, Any], *, fallback: list[str]) -> list[str]:
    for key in ("why", "reasons", "review_reasons"):
        value = report.get(key)
        if isinstance(value, list) and value:
            return [str(item) for item in value]
    summary = report.get("summary")
    if isinstance(summary, dict):
        for key in ("why", "reasons", "review_reasons"):
            value = summary.get(key)
            if isinstance(value, list) and value:
                return [str(item) for item in value]
    return fallback


def _contains_no_go(report: Any) -> bool:
    return "no_go" in json.dumps(report, sort_keys=True, default=str).lower()


def _require_stage_output(*, status: str, output_path: Path, report_label: str) -> None:
    if status in TERMINAL_BAD_STATUSES:
        raise RuntimeError(f"{report_label} report status is {status}")
    if not output_path.exists():
        raise RuntimeError(f"{report_label} output is missing: {output_path.name}")


def _validate_apply_result(result: dict[str, Any], *, expected_output: Path) -> None:
    if validate_apply_jsx_result is not None:
        validate_apply_jsx_result(result, expected_output=str(expected_output))
    report = str(result.get("report") or "")
    status = _text_report_status(report)
    if status in TERMINAL_BAD_STATUSES:
        raise RuntimeError(f"apply-jsx report status is {status}")
    output = Path(str(result.get("output") or expected_output))
    if output != expected_output:
        raise RuntimeError("apply-jsx wrote an unexpected output path")
    if not output.exists():
        raise RuntimeError(f"apply-jsx output is missing: {output.name}")


def _text_report_status(report: str) -> str:
    lower = report.lower()
    if "no_go" in lower or "no-go" in lower:
        return "no_go"
    if "failed" in lower or "traceback" in lower:
        return "failed"
    errors = re.search(r"errors:\s*(\d+)", lower)
    if errors and int(errors.group(1)) > 0:
        return "needs_review"
    return "passed"


def _poche_report_dict(report: PocheReport, *, input_name: str, output_name: str) -> dict[str, Any]:
    layers = [
        {
            "layer": fill.layer,
            "status": _fill_status(fill.confidence, fill.polygon_count),
            "strategy": fill.strategy,
            "confidence": round(float(fill.confidence), 4),
            "polygon_count": int(fill.polygon_count),
            "segment_count": int(fill.segment_count),
        }
        for fill in report.fills
    ]
    return {
        "schema_version": 1,
        "source": {"input_file": input_name, "output_file": output_name},
        "summary": {
            "layers_considered": len(report.fills),
            "layers_passed": sum(1 for layer in layers if layer["status"] == "passed"),
            "layers_needs_review": sum(1 for layer in layers if layer["status"] == "needs_review"),
            "layers_failed": sum(1 for layer in layers if layer["status"] == "failed"),
            "polygons_injected": int(report.injected_polygons),
        },
        "layers": layers,
    }


def _fill_status(confidence: float, polygon_count: int) -> str:
    if polygon_count <= 0 or confidence <= 0:
        return "failed"
    if confidence < 0.85:
        return "needs_review"
    return "passed"


def _poche_status(report: dict[str, Any]) -> str:
    summary = report["summary"]
    if summary["layers_failed"]:
        return "needs_review"
    if summary["layers_needs_review"]:
        return "needs_review"
    if summary["polygons_injected"] <= 0:
        return "needs_review"
    return "passed"


def _poche_why(report: dict[str, Any]) -> list[str]:
    summary = report["summary"]
    if summary["layers_failed"] or summary["layers_needs_review"]:
        return [
            f"{summary['layers_failed']} failed layer(s).",
            f"{summary['layers_needs_review']} layer(s) need review.",
        ]
    return ["Poché report indicates injectable cut geometry."]


def _write_proof_packet(packet_path: Path, summary: dict[str, Any]) -> None:
    packet_path.parent.mkdir(parents=True, exist_ok=True)
    text_lines = [
        "arch-line-weights designer console proof packet",
        "",
        *CONSOLE_GUARDRAILS,
        "",
        f"Run ID: {summary['run_id']}",
        f"Workflow: {summary['workflow_label']}",
        f"Overall status: {summary['overall_status']}",
        "",
        "Next step:",
        summary["report"]["next_step"],
        "",
    ]
    with zipfile.ZipFile(packet_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "public-summary.json",
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
        )
        zf.writestr("designer-console-report.txt", "\n".join(text_lines))
        zf.writestr(
            "README-NOT-PUBLIC-CLEARANCE.txt",
            "\n".join(CONSOLE_GUARDRAILS)
            + "\n\nThis packet is local review material only. It is not posting clearance.\n",
        )
