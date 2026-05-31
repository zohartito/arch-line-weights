from __future__ import annotations

import json
from pathlib import Path

import pytest

from arch_line_weights import designer_console as dc


class FakeInspectionReport:
    def __init__(self, path: str) -> None:
        self.file = path
        self.pages = 1
        self.width_pt = 1728.0
        self.height_pt = 2592.0
        self.total_drawings = 42
        self.total_stroked = 37
        self.stroke_widths = {"0.25": 37}
        self.stroke_colors = {"RGB(0,0,0)": 37}
        self.fill_colors = {}
        self.width_by_color = {"RGB(0,0,0)": {"0.25": 37}}
        self.pdf_metadata = {"/Creator": "Rhino"}
        self.layer_names = ["Visible::ClippingPlaneIntersections::WALL", "Visible::WINDOW"]

    def to_dict(self) -> dict:
        return {
            "file": self.file,
            "pages": self.pages,
            "width_pt": self.width_pt,
            "height_pt": self.height_pt,
            "total_drawings": self.total_drawings,
            "total_stroked": self.total_stroked,
            "stroke_widths": self.stroke_widths,
            "stroke_colors": self.stroke_colors,
            "fill_colors": self.fill_colors,
            "width_by_color": self.width_by_color,
            "pdf_metadata": self.pdf_metadata,
            "layer_names": self.layer_names,
        }


def test_create_run_has_required_guardrails_and_not_run_stages(tmp_path: Path) -> None:
    src = tmp_path / "usc-private-section.ai"
    src.write_text("%AI\n")

    store = dc.DesignerConsoleStore(tmp_path / "console")
    run = store.create_run(src, workflow="section")

    assert run.workflow == "section"
    assert run.original_filename == src.name
    assert [stage.status for stage in run.stages.values()] == ["not_run"] * 5
    assert "Posting/public proof is NO-GO unless W5/W7 explicitly accepts it." in run.guardrails
    assert "Synthetic proof does not close #30." in run.guardrails
    assert "Private USC regression stays private." in run.guardrails

    reloaded_summary = store.load(run.run_id).public_summary()
    assert [stage["key"] for stage in reloaded_summary["stages"]] == [
        "inspect_file",
        "run_layout",
        "apply_line_weights",
        "generate_poche",
        "export_proof_packet",
    ]


def test_inspect_file_builds_public_safe_summary_without_local_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    src = tmp_path / "private USC wall section.ai"
    src.write_text("%AI\n")
    store = dc.DesignerConsoleStore(tmp_path / "console")
    run = store.create_run(src, workflow="plan")

    monkeypatch.setattr(dc, "inspect_file", lambda path: FakeInspectionReport(path))

    updated = store.inspect_file(run.run_id)

    stage = updated.stages["inspect_file"]
    assert stage.status == "passed"
    assert any("37 stroked" in item for item in stage.what_changed)
    assert any("2 layer" in item for item in stage.why)

    public_summary = updated.public_summary()
    dumped = json.dumps(public_summary)
    assert public_summary["overall_status"] == "needs_review"
    assert str(tmp_path) not in dumped
    assert src.name in dumped


def test_apply_line_weights_rejects_failed_apply_jsx_report_even_when_output_exists(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    src = tmp_path / "section.ai"
    src.write_text("%AI\n")
    layout_output = tmp_path / "section LAYOUT-jsx.ai"
    layout_output.write_text("%AI layout\n")
    hierarchy_output = tmp_path / "section LAYOUT-jsx HIERARCHY-jsx.ai"
    hierarchy_output.write_text("%AI hierarchy\n")

    store = dc.DesignerConsoleStore(tmp_path / "console")
    run = store.create_run(src, workflow="section")
    run.artifacts["layout_output"] = str(layout_output)
    store.save(run)

    monkeypatch.setattr(
        dc,
        "apply_via_jsx",
        lambda *args, **kwargs: {
            "output": str(hierarchy_output),
            "report": '{"summary":{"status":"failed","why":["Illustrator reported failure"]}}',
            "report_path": str(tmp_path / "raw-apply-report.txt"),
        },
    )

    updated = store.apply_line_weights(run.run_id)

    stage = updated.stages["apply_line_weights"]
    assert stage.status == "failed"
    assert any("apply-jsx report status is failed" in item for item in stage.what_failed)
    assert updated.artifacts.get("hierarchy_output") is None


def test_export_proof_packet_fails_closed_when_public_summary_leaks_private_path(
    tmp_path: Path,
) -> None:
    src = tmp_path / "section.ai"
    src.write_text("%AI\n")
    store = dc.DesignerConsoleStore(tmp_path / "console")
    run = store.create_run(src, workflow="section")
    run.stages["run_layout"].what_changed.append(f"Leaked path: {tmp_path / 'private-output.ai'}")
    store.save(run)

    updated = store.export_proof_packet(run.run_id)

    stage = updated.stages["export_proof_packet"]
    assert stage.status == "no_go"
    assert any("private/local path" in item for item in stage.what_failed)
    assert updated.artifacts.get("proof_packet") is None


def test_designer_console_main_screen_serves_required_designer_actions(tmp_path: Path) -> None:
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    app = dc.create_designer_console_app(storage_root=tmp_path / "console")
    client = TestClient(app)

    resp = client.get("/")

    assert resp.status_code == 200
    text = resp.text
    assert "Inspect File" in text
    assert "Run Layout" in text
    assert "Apply Line Weights" in text
    assert "Generate Poché" in text
    assert "Export Proof Packet" in text
    assert "Posting/public proof is NO-GO unless W5/W7 explicitly accepts it." in text
    assert "Synthetic proof does not close #30." in text
    assert "Private USC regression stays private." in text
