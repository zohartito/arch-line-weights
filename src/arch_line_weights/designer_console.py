"""Local designer-console prototype for arch-line-weights.

The console is intentionally local-first: files stay in a temp workspace, raw
engine reports stay local, and the browser only receives public-safe summaries.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
import threading
import uuid
import webbrowser
import zipfile
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, BinaryIO

from .apply_jsx import apply_via_jsx, validate_apply_jsx_result
from .inspect import inspect_file
from .layout_jsx import layout_via_jsx
from .poche import PocheReport, apply_poche
from .run_report import build_poche_report

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
    def from_dict(cls, data: dict[str, Any]) -> ConsoleRun:
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
    """Small file-backed run store for the local designer console."""

    def __init__(self, root: str | os.PathLike[str] | None = None) -> None:
        self.root = Path(root or default_console_root()).expanduser()
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
        temp_root = self.root / "_incoming"
        temp_root.mkdir(parents=True, exist_ok=True)
        temp_path = temp_root / f"{uuid.uuid4().hex}{Path(filename).suffix.lower()}"
        with temp_path.open("wb") as f:
            shutil.copyfileobj(stream, f, length=1024 * 1024)
        try:
            return self.create_run(temp_path, workflow=workflow, original_filename=filename)
        finally:
            temp_path.unlink(missing_ok=True)

    def create_synthetic_demo_run(self) -> ConsoleRun:
        from .poche_saas import write_synthetic_test_ai

        temp_root = self.root / "_incoming"
        temp_root.mkdir(parents=True, exist_ok=True)
        temp_path = temp_root / f"synthetic-demo-{uuid.uuid4().hex}.ai"
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
        except Exception as exc:
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
            result = layout_via_jsx(
                run.input_path,
                dst=str(output),
                report_json=str(raw_report_path),
                jsx_path=str(jsx_path),
            )
            report_data = _load_json_report(raw_report_path, result.get("report"))
            status = _report_status(report_data, default="passed")
            _require_stage_output(
                status=status,
                output_path=Path(result["output"]),
                report_label="layout-jsx",
            )
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
        except Exception as exc:
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
            )
            validate_apply_jsx_result(result, expected_output=str(output))
            run.artifacts["hierarchy_output"] = str(output)
            stage.finish(
                status="passed",
                what_changed=[
                    f"Applied {WORKFLOW_LABELS.get(run.workflow, run.workflow)} line weights "
                    f"to {output.name}."
                ],
                what_skipped=["Poché and proof packet stages have not run yet."],
                why=["apply-jsx output and report validation passed."],
                next_step="Generate Poché or export a proof packet.",
                output_path=str(output),
                raw_report_path=str(result.get("report_path")) if result.get("report_path") else None,
            )
        except Exception as exc:
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
        geometry_report_path = self._raw_path(run, "geometry-report.json")
        try:
            report = apply_poche(
                hierarchy_output,
                str(output),
                geometry_report_path=str(geometry_report_path),
            )
            report_data = build_poche_report(
                input_path=hierarchy_output,
                output_path=output,
                source={
                    "style": "solid",
                    "scale": 0.02,
                    "layer_source": "rhino",
                    "bridge_strategy": "best",
                    "min_inject_confidence": 0.85,
                },
                poche_report=report if isinstance(report, PocheReport) else None,
            )
            raw_report_path.write_text(
                json.dumps(report_data, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            status = _report_status(report_data, default="passed")
            _require_stage_output(status=status, output_path=output, report_label="poche")
            run.artifacts["poche_output"] = str(output)
            summary = report_data.get("summary", {})
            stage.finish(
                status=status,
                what_changed=[
                    f"Generated {summary.get('polygons_injected', 0)} injected poché polygon(s) "
                    f"in {output.name}."
                ],
                what_skipped=[],
                why=_report_why(report_data, fallback=["Poché report contract completed."]),
                next_step=(
                    "Export Proof Packet."
                    if status == "passed"
                    else "Review low-confidence or no-go poché layers before proof use."
                ),
                output_path=str(output),
                raw_report_path=str(raw_report_path),
            )
        except Exception as exc:
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
            {key: stage for key, stage in run.stages.items() if key != "export_proof_packet"}
        )
        has_outputs = any(
            key in run.artifacts
            for key in ("layout_output", "hierarchy_output", "poche_output")
        )
        status = prior_status if prior_status in TERMINAL_BAD_STATUSES else "passed"
        if not has_outputs and status == "passed":
            status = "needs_review"

        stage.finish(
            status=status,
            what_changed=[f"Created local proof packet {packet_path.name}."],
            what_skipped=[
                "Raw local reports and source drawings were not included in the public-safe packet.",
            ],
            why=[
                "Public-safe summary contains no local path patterns.",
                "Posting/public proof still requires W5/W7 acceptance.",
            ],
            next_step=(
                "Review the packet with W5/W7 before any public proof claim."
                if status == "passed"
                else "Resolve failed, no-go, or missing stages before using this packet."
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


def default_console_root() -> Path:
    return Path(tempfile.gettempdir()) / "arch-lw-designer-console"


def create_designer_console_app(
    *,
    storage_root: str | os.PathLike[str] | None = None,
):
    """Build the local FastAPI app for ``arch-lw designer-console``."""
    try:
        from fastapi import FastAPI, File, Form, HTTPException, UploadFile
        from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
    except ImportError as exc:  # pragma: no cover - exercised by CLI message
        raise RuntimeError(
            "designer-console requires FastAPI and Uvicorn. Install with "
            "`python -m pip install -e '.[console]'` from the repo root."
        ) from exc

    store = DesignerConsoleStore(storage_root)
    app = FastAPI(
        title="arch-line-weights designer console",
        version="0.1.0",
        description="Local-only designer console prototype.",
    )

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return DESIGNER_CONSOLE_HTML

    @app.get("/api/console/guardrails")
    def guardrails() -> dict[str, Any]:
        return {"guardrails": CONSOLE_GUARDRAILS, "workflows": WORKFLOW_LABELS}

    @app.post("/api/console/runs")
    async def create_run(
        file: UploadFile | None = File(None),  # noqa: B008 - FastAPI dependency marker
        workflow: str = Form("section"),
    ) -> JSONResponse:
        try:
            if file is None or not file.filename:
                if workflow == "synthetic_proof_demo":
                    run = store.create_synthetic_demo_run()
                else:
                    raise HTTPException(status_code=400, detail="choose a .ai or .pdf input file")
            else:
                run = store.create_run_from_upload(
                    file.file,
                    filename=file.filename,
                    workflow=workflow,
                )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return JSONResponse(run.public_summary())

    @app.get("/api/console/runs/{run_id}")
    def get_run(run_id: str) -> dict[str, Any]:
        try:
            return store.load(run_id).public_summary()
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="unknown console run") from exc

    @app.post("/api/console/runs/{run_id}/{action}")
    def run_action(run_id: str, action: str) -> dict[str, Any]:
        actions = {
            "inspect-file": store.inspect_file,
            "run-layout": store.run_layout,
            "apply-line-weights": store.apply_line_weights,
            "generate-poche": store.generate_poche,
            "export-proof-packet": store.export_proof_packet,
        }
        fn = actions.get(action)
        if fn is None:
            raise HTTPException(status_code=404, detail="unknown console action")
        try:
            return fn(run_id).public_summary()
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="unknown console run") from exc

    @app.get("/api/console/runs/{run_id}/proof-packet")
    def download_proof_packet(run_id: str) -> FileResponse:
        try:
            run = store.load(run_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="unknown console run") from exc
        packet = run.artifacts.get("proof_packet")
        if not packet or not Path(packet).exists():
            raise HTTPException(status_code=404, detail="proof packet has not been exported")
        return FileResponse(
            packet,
            filename=f"arch-lw-proof-packet-{run_id[:8]}.zip",
            media_type="application/zip",
        )

    return app


def run_designer_console_server(
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    storage_root: str | os.PathLike[str] | None = None,
    open_browser: bool = True,
) -> None:
    try:
        import uvicorn
    except ImportError as exc:  # pragma: no cover - dependency messaging
        raise RuntimeError(
            "designer-console requires Uvicorn. Install with "
            "`python -m pip install -e '.[console]'` from the repo root."
        ) from exc

    app = create_designer_console_app(storage_root=storage_root)
    url = f"http://{host}:{port}"
    if open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    uvicorn.run(app, host=host, port=port, log_level="info")


def _normalize_workflow(workflow: str) -> str:
    value = workflow.strip().lower().replace("-", "_")
    aliases = {
        "synthetic": "synthetic_proof_demo",
        "demo": "synthetic_proof_demo",
        "synthetic_proof": "synthetic_proof_demo",
    }
    value = aliases.get(value, value)
    if value not in WORKFLOW_LABELS:
        raise ValueError(
            f"unknown workflow {workflow!r}; expected one of {', '.join(WORKFLOW_LABELS)}"
        )
    return value


def _validate_input_suffix(filename: str) -> None:
    suffix = Path(filename).suffix.lower()
    if suffix not in {".ai", ".pdf"}:
        raise ValueError(f"unsupported file type {suffix!r}; expected .ai or .pdf")


def _preset_for_workflow(workflow: str) -> str:
    if workflow in {"section", "plan", "detail"}:
        return workflow
    return "section"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _filename(path: str | None) -> str | None:
    if not path:
        return None
    return Path(path).name


def _redact_text(text: str) -> str:
    return _LOCAL_PATH_RE.sub("[local path]", text)


def _redact_list(items: list[str]) -> list[str]:
    return [_redact_text(str(item)) for item in items]


def _contains_private_path(obj: Any) -> bool:
    return bool(_LOCAL_PATH_RE.search(json.dumps(obj, sort_keys=True)))


def _exception_message(exc: Exception) -> str:
    return _redact_text(f"{type(exc).__name__}: {exc}")


def _status_from_exception(exc: Exception) -> str:
    msg = str(exc).lower().replace("-", "_")
    if "no_go" in msg:
        return "no_go"
    return "failed"


def _load_json_report(path: Path, fallback_text: str | None = None) -> dict[str, Any]:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    if fallback_text:
        return json.loads(fallback_text)
    return {}


def _report_status(report: dict[str, Any], *, default: str) -> str:
    summary = report.get("summary")
    raw = summary.get("status") if isinstance(summary, dict) else report.get("status")
    status = str(raw or default).lower().replace("-", "_")
    if status not in STAGE_STATUSES:
        return default
    return status


def _report_why(report: dict[str, Any], *, fallback: list[str]) -> list[str]:
    summary = report.get("summary")
    why = summary.get("why") if isinstance(summary, dict) else report.get("why")
    if isinstance(why, list):
        return [str(item) for item in why]
    if why:
        return [str(why)]
    return fallback


def _require_stage_output(*, status: str, output_path: Path, report_label: str) -> None:
    if status in {"failed", "no_go"}:
        raise RuntimeError(f"{report_label} report status is {status}")
    if not output_path.exists():
        raise RuntimeError(f"{report_label} did not write expected output: {output_path}")


def _overall_status(stages: dict[str, ConsoleStage]) -> str:
    statuses = [stage.status for stage in stages.values()]
    if statuses and all(status == "not_run" for status in statuses):
        return "not_run"
    if "running" in statuses:
        return "running"
    if "no_go" in statuses:
        return "no_go"
    if "failed" in statuses:
        return "failed"
    if "needs_review" in statuses:
        return "needs_review"
    if statuses and all(status == "passed" for status in statuses):
        return "passed"
    return "needs_review"


def _rollup_report(stages: list[dict[str, Any]]) -> dict[str, list[str] | str]:
    changed: list[str] = []
    skipped: list[str] = []
    failed: list[str] = []
    why: list[str] = []
    next_steps: list[str] = []
    for stage in stages:
        changed.extend(stage["what_changed"])
        skipped.extend(stage["what_skipped"])
        failed.extend(stage["what_failed"])
        why.extend(stage["why"])
        if stage["next_step"]:
            next_steps.append(f"{stage['label']}: {stage['next_step']}")
    return {
        "what_changed": changed,
        "what_skipped": skipped,
        "what_failed": failed,
        "why": why,
        "next_step": next_steps[-1] if next_steps else "Choose an input file.",
    }


def _write_proof_packet(packet_path: Path, public_summary: dict[str, Any]) -> None:
    packet_path.parent.mkdir(parents=True, exist_ok=True)
    report_txt = _proof_report_text(public_summary)
    with zipfile.ZipFile(packet_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "public-summary.json",
            json.dumps(public_summary, indent=2, sort_keys=True) + "\n",
        )
        zf.writestr("designer-console-report.txt", report_txt)
        zf.writestr(
            "README-NOT-PUBLIC-CLEARANCE.txt",
            "\n".join(CONSOLE_GUARDRAILS)
            + "\n\nThis packet is a local design-review aid, not posting clearance.\n",
        )


def _proof_report_text(summary: dict[str, Any]) -> str:
    report = summary["report"]
    lines = [
        "arch-line-weights designer console proof packet",
        f"Run: {summary['run_id']}",
        f"Workflow: {summary['workflow_label']}",
        f"Overall status: {summary['overall_status']}",
        "",
        "Guardrails:",
        *[f"- {item}" for item in summary["guardrails"]],
        "",
        "What changed:",
        *[f"- {item}" for item in report["what_changed"]],
        "",
        "What skipped:",
        *[f"- {item}" for item in report["what_skipped"]],
        "",
        "What failed:",
        *[f"- {item}" for item in report["what_failed"]],
        "",
        "Why:",
        *[f"- {item}" for item in report["why"]],
        "",
        f"Next step: {report['next_step']}",
        "",
    ]
    return "\n".join(lines)


DESIGNER_CONSOLE_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>arch-lw designer console</title>
  <style>
    :root {
      color-scheme: light;
      --ink: #202124;
      --muted: #626a73;
      --line: #ccd3db;
      --paper: #f7f8f9;
      --panel: #ffffff;
      --green: #1f7a4d;
      --amber: #9a6700;
      --red: #b3261e;
      --blue: #255fa8;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--paper);
      color: var(--ink);
    }
    main {
      max-width: 1180px;
      margin: 0 auto;
      padding: 24px;
    }
    h1, h2, h3, p { margin: 0; }
    h1 { font-size: 22px; line-height: 1.2; font-weight: 650; }
    h2 { font-size: 15px; line-height: 1.2; font-weight: 650; }
    h3 { font-size: 13px; line-height: 1.2; font-weight: 650; color: var(--muted); }
    button, select, input { font: inherit; }
    button {
      min-height: 38px;
      border: 1px solid var(--line);
      background: var(--panel);
      color: var(--ink);
      border-radius: 6px;
      padding: 8px 12px;
      cursor: pointer;
    }
    button.primary { background: var(--ink); color: white; border-color: var(--ink); }
    button:disabled { opacity: 0.5; cursor: not-allowed; }
    select {
      width: 100%;
      min-height: 38px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--panel);
      padding: 8px 10px;
    }
    .topbar {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 18px;
    }
    .statusline { color: var(--muted); font-size: 13px; margin-top: 5px; }
    .guardrails {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
      margin-bottom: 16px;
    }
    .guardrail {
      border: 1px solid #e1c4c1;
      background: #fff7f6;
      color: #6f1d18;
      border-radius: 6px;
      padding: 10px 12px;
      font-size: 13px;
      font-weight: 600;
    }
    .workspace {
      display: grid;
      grid-template-columns: 330px minmax(0, 1fr);
      gap: 16px;
      align-items: start;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
    }
    .stack { display: grid; gap: 12px; }
    .dropzone {
      border: 2px dashed var(--line);
      border-radius: 8px;
      min-height: 132px;
      display: grid;
      place-items: center;
      padding: 18px;
      text-align: center;
      background: #fbfcfd;
    }
    .dropzone.dragover { border-color: var(--blue); background: #f1f6ff; }
    .dropzone strong { display: block; font-size: 14px; margin-bottom: 4px; }
    .dropzone span { color: var(--muted); font-size: 12px; overflow-wrap: anywhere; }
    .actions {
      display: grid;
      grid-template-columns: repeat(5, minmax(120px, 1fr));
      gap: 8px;
      margin-bottom: 16px;
    }
    .stages {
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 8px;
    }
    .stage {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px;
      min-height: 86px;
      background: #fbfcfd;
    }
    .stage-title { font-size: 12px; font-weight: 650; margin-bottom: 8px; }
    .badge {
      display: inline-flex;
      align-items: center;
      min-height: 22px;
      border-radius: 999px;
      padding: 2px 8px;
      font-size: 12px;
      font-weight: 650;
      background: #e9edf2;
      color: #414852;
    }
    .badge.running { background: #e8f0fe; color: var(--blue); }
    .badge.passed { background: #e6f4ea; color: var(--green); }
    .badge.needs_review { background: #fff4d6; color: var(--amber); }
    .badge.failed, .badge.no_go { background: #fce8e6; color: var(--red); }
    .report-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
      margin-top: 16px;
    }
    .report-list {
      margin: 8px 0 0;
      padding-left: 18px;
      color: var(--ink);
      font-size: 13px;
      line-height: 1.45;
    }
    .report-list:empty::after {
      content: "None yet.";
      color: var(--muted);
    }
    .next-step {
      margin-top: 12px;
      border-left: 3px solid var(--blue);
      padding: 10px 12px;
      background: #f4f8ff;
      font-size: 13px;
    }
    .error {
      color: var(--red);
      font-size: 13px;
      margin-top: 10px;
    }
    .download { display: none; margin-top: 12px; }
    .download.visible {
      display: inline-flex;
      min-height: 38px;
      align-items: center;
      border-radius: 6px;
      background: var(--ink);
      color: white;
      padding: 8px 12px;
      text-decoration: none;
    }
    @media (max-width: 900px) {
      main { padding: 16px; }
      .guardrails, .workspace, .actions, .stages, .report-grid {
        grid-template-columns: 1fr;
      }
      .topbar { display: block; }
    }
  </style>
</head>
<body>
  <main>
    <div class="topbar">
      <div>
        <h1>arch-line-weights designer console</h1>
        <p class="statusline" id="runStatus">Local run not started.</p>
      </div>
      <button type="button" id="resetButton">New Run</button>
    </div>

    <section class="guardrails" aria-label="Proof guardrails">
      <div class="guardrail">Posting/public proof is NO-GO unless W5/W7 explicitly accepts it.</div>
      <div class="guardrail">Synthetic proof does not close #30.</div>
      <div class="guardrail">Private USC regression stays private.</div>
    </section>

    <section class="workspace">
      <div class="panel stack">
        <div>
          <h2>Input</h2>
          <label class="dropzone" id="dropzone">
            <input id="fileInput" type="file" accept=".ai,.pdf" hidden />
            <span>
              <strong id="fileName">Choose or drag a Rhino / Illustrator / PDF export</strong>
              <span id="fileMeta">.ai and .pdf accepted</span>
            </span>
          </label>
        </div>
        <label class="stack">
          <h2>Workflow</h2>
          <select id="workflow">
            <option value="section">Section</option>
            <option value="plan">Plan</option>
            <option value="detail">Detail</option>
            <option value="synthetic_proof_demo">Synthetic proof / demo</option>
          </select>
        </label>
      </div>

      <div>
        <section class="actions" aria-label="Pipeline actions">
          <button type="button" data-action="inspect-file">Inspect File</button>
          <button type="button" data-action="run-layout">Run Layout</button>
          <button type="button" data-action="apply-line-weights">Apply Line Weights</button>
          <button type="button" data-action="generate-poche">Generate Poché</button>
          <button type="button" class="primary" data-action="export-proof-packet">Export Proof Packet</button>
        </section>

        <section class="stages" id="stages" aria-label="Stage status"></section>

        <section class="report-grid" aria-label="Run report">
          <div class="panel">
            <h3>What changed</h3>
            <ul class="report-list" id="changed"></ul>
          </div>
          <div class="panel">
            <h3>What skipped</h3>
            <ul class="report-list" id="skipped"></ul>
          </div>
          <div class="panel">
            <h3>What failed</h3>
            <ul class="report-list" id="failed"></ul>
          </div>
          <div class="panel">
            <h3>Why</h3>
            <ul class="report-list" id="why"></ul>
          </div>
        </section>

        <div class="next-step" id="nextStep">Next step: choose an input file.</div>
        <a class="download button primary" id="downloadProof" href="#">Download proof packet</a>
        <div class="error" id="errorBox"></div>
      </div>
    </section>
  </main>

  <script>
    const stageLabels = {
      inspect_file: "Inspect File",
      run_layout: "Run Layout",
      apply_line_weights: "Apply Line Weights",
      generate_poche: "Generate Poché",
      export_proof_packet: "Export Proof Packet"
    };
    const actionStage = {
      "inspect-file": "inspect_file",
      "run-layout": "run_layout",
      "apply-line-weights": "apply_line_weights",
      "generate-poche": "generate_poche",
      "export-proof-packet": "export_proof_packet"
    };
    let selectedFile = null;
    let currentRun = null;

    const fileInput = document.getElementById("fileInput");
    const dropzone = document.getElementById("dropzone");
    const fileName = document.getElementById("fileName");
    const fileMeta = document.getElementById("fileMeta");
    const workflow = document.getElementById("workflow");
    const runStatus = document.getElementById("runStatus");
    const errorBox = document.getElementById("errorBox");
    const downloadProof = document.getElementById("downloadProof");

    function setError(message) {
      errorBox.textContent = message || "";
    }

    function selectFile(file) {
      selectedFile = file;
      fileName.textContent = file ? file.name : "Choose or drag a Rhino / Illustrator / PDF export";
      fileMeta.textContent = file ? `${(file.size / 1048576).toFixed(2)} MB` : ".ai and .pdf accepted";
    }

    fileInput.addEventListener("change", () => selectFile(fileInput.files[0] || null));
    dropzone.addEventListener("dragover", (event) => {
      event.preventDefault();
      dropzone.classList.add("dragover");
    });
    dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
    dropzone.addEventListener("drop", (event) => {
      event.preventDefault();
      dropzone.classList.remove("dragover");
      selectFile(event.dataTransfer.files[0] || null);
    });

    document.getElementById("resetButton").addEventListener("click", () => {
      selectedFile = null;
      currentRun = null;
      fileInput.value = "";
      selectFile(null);
      render(null);
      setError("");
    });

    document.querySelectorAll("[data-action]").forEach((button) => {
      button.addEventListener("click", () => runAction(button.dataset.action));
    });

    async function ensureRun() {
      if (currentRun) return currentRun;
      if (!selectedFile && workflow.value !== "synthetic_proof_demo") {
        throw new Error("Choose a .ai or .pdf input file first.");
      }
      const form = new FormData();
      form.append("workflow", workflow.value);
      if (selectedFile) form.append("file", selectedFile);
      const response = await fetch("/api/console/runs", { method: "POST", body: form });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || `HTTP ${response.status}`);
      currentRun = body;
      render(currentRun);
      return currentRun;
    }

    async function runAction(action) {
      setError("");
      try {
        const run = await ensureRun();
        markRunning(actionStage[action]);
        const response = await fetch(`/api/console/runs/${run.run_id}/${action}`, { method: "POST" });
        const body = await response.json();
        if (!response.ok) throw new Error(body.detail || `HTTP ${response.status}`);
        currentRun = body;
        render(currentRun);
      } catch (error) {
        setError(error instanceof Error ? error.message : String(error));
        render(currentRun);
      }
    }

    function markRunning(stageKey) {
      if (!currentRun) return;
      currentRun = {
        ...currentRun,
        stages: currentRun.stages.map((stage) =>
          stage.key === stageKey ? { ...stage, status: "running" } : stage
        )
      };
      render(currentRun);
    }

    function render(run) {
      const stages = run?.stages || Object.entries(stageLabels).map(([key, label]) => ({
        key, label, status: "not_run", next_step: ""
      }));
      document.getElementById("stages").innerHTML = stages.map((stage) => `
        <div class="stage">
          <div class="stage-title">${stage.label}</div>
          <span class="badge ${stage.status}">${stage.status.replace("_", "-")}</span>
          ${stage.output_file ? `<div class="statusline">${stage.output_file}</div>` : ""}
        </div>
      `).join("");

      runStatus.textContent = run
        ? `${run.workflow_label} · ${run.original_filename} · ${run.overall_status.replace("_", "-")}`
        : "Local run not started.";
      fillList("changed", run?.report?.what_changed || []);
      fillList("skipped", run?.report?.what_skipped || []);
      fillList("failed", run?.report?.what_failed || []);
      fillList("why", run?.report?.why || []);
      document.getElementById("nextStep").textContent =
        `Next step: ${run?.report?.next_step || "choose an input file."}`;

      const proof = run?.artifacts?.find((artifact) => artifact.key === "proof_packet" && artifact.available);
      if (proof) {
        downloadProof.href = `/api/console/runs/${run.run_id}/proof-packet`;
        downloadProof.classList.add("visible");
      } else {
        downloadProof.classList.remove("visible");
      }
    }

    function fillList(id, items) {
      document.getElementById(id).innerHTML = items.map((item) => `<li>${escapeHtml(item)}</li>`).join("");
    }

    function escapeHtml(value) {
      return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
    }

    render(null);
  </script>
</body>
</html>
"""
