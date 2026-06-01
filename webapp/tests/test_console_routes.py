from __future__ import annotations

import json
import zipfile
from pathlib import Path


class FakeInspectionReport:
    def __init__(self, path: str) -> None:
        self.path = path

    def to_dict(self) -> dict:
        return {
            "file": self.path,
            "pages": 1,
            "total_drawings": 42,
            "total_stroked": 37,
            "stroke_colors": {"RGB(0,0,0)": 37},
            "layer_names": [
                "Visible::ClippingPlaneIntersections::WALL",
                "Visible::WINDOW",
            ],
        }


def test_console_create_run_has_guardrails_and_required_stage_statuses(
    app_client,
    synthetic_ai: Path,
) -> None:
    client, _app = app_client

    with synthetic_ai.open("rb") as f:
        resp = client.post(
            "/api/console/runs",
            files={"file": (synthetic_ai.name, f, "application/postscript")},
            data={"workflow": "section"},
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["workflow"] == "section"
    assert body["workflow_label"] == "Section"
    assert body["original_filename"] == synthetic_ai.name
    assert body["overall_status"] == "needs_review"
    assert body["public_safe"] is False
    assert body["public_acceptance"] == {"accepted": False, "accepted_by": []}
    assert [stage["status"] for stage in body["stages"]] == ["not_run"] * 5
    assert [stage["key"] for stage in body["stages"]] == [
        "inspect_file",
        "run_layout",
        "apply_line_weights",
        "generate_poche",
        "export_proof_packet",
    ]
    assert "Posting/public proof is NO-GO unless W5/W7 explicitly accepts it." in body["guardrails"]
    assert "Synthetic proof does not close #30." in body["guardrails"]
    assert "Private USC regression stays private." in body["guardrails"]


def test_console_synthetic_demo_can_start_without_upload(app_client) -> None:
    client, _app = app_client

    resp = client.post(
        "/api/console/runs",
        data={"workflow": "synthetic_proof_demo"},
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["workflow"] == "synthetic_proof_demo"
    assert body["workflow_label"] == "Synthetic proof / demo"
    assert body["original_filename"] == "synthetic-proof-demo.ai"
    assert "Synthetic proof does not close #30." in body["guardrails"]


def test_console_inspect_stage_returns_public_safe_report(
    app_client,
    synthetic_ai: Path,
    monkeypatch,
) -> None:
    client, _app = app_client
    import backend.console as console

    monkeypatch.setattr(console, "inspect_file", lambda path: FakeInspectionReport(path))
    with synthetic_ai.open("rb") as f:
        created = client.post(
            "/api/console/runs",
            files={"file": (synthetic_ai.name, f, "application/postscript")},
            data={"workflow": "plan"},
        ).json()

    resp = client.post(f"/api/console/runs/{created['run_id']}/stages/inspect_file")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["workflow"] == "plan"
    assert body["stages"][0]["status"] == "passed"
    assert any("37 stroked" in item for item in body["stages"][0]["what_changed"])
    assert body["report"]["what_changed"]
    dumped = json.dumps(body)
    assert str(synthetic_ai.parent) not in dumped
    assert "raw_report_path" not in dumped


def test_console_apply_line_weights_requires_layout_output(
    app_client,
    synthetic_ai: Path,
) -> None:
    client, _app = app_client
    with synthetic_ai.open("rb") as f:
        created = client.post(
            "/api/console/runs",
            files={"file": (synthetic_ai.name, f, "application/postscript")},
            data={"workflow": "detail"},
        ).json()

    resp = client.post(f"/api/console/runs/{created['run_id']}/stages/apply_line_weights")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    stage = next(s for s in body["stages"] if s["key"] == "apply_line_weights")
    assert stage["status"] == "failed"
    assert "Layout output is missing." in stage["what_failed"]
    assert stage["next_step"] == "Run Layout, then apply line weights."


def test_console_export_packet_blocks_private_path_leak(
    app_client,
    synthetic_ai: Path,
    tmp_path: Path,
) -> None:
    client, app = app_client
    with synthetic_ai.open("rb") as f:
        created = client.post(
            "/api/console/runs",
            files={"file": (synthetic_ai.name, f, "application/postscript")},
            data={"workflow": "section"},
        ).json()

    run = app.state.console_store.load(created["run_id"])
    run.stages["run_layout"].what_changed.append(f"Leaked path: {tmp_path / 'private-output.ai'}")
    app.state.console_store.save(run)

    resp = client.post(f"/api/console/runs/{created['run_id']}/stages/export_proof_packet")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    stage = next(s for s in body["stages"] if s["key"] == "export_proof_packet")
    assert stage["status"] == "no_go"
    assert any("private/local path" in item for item in stage["what_failed"])
    assert not any(artifact["key"] == "proof_packet" for artifact in body["artifacts"])


def test_console_export_packet_is_review_gated_without_w5_w7_acceptance(
    app_client,
    synthetic_ai: Path,
) -> None:
    client, app = app_client
    with synthetic_ai.open("rb") as f:
        created = client.post(
            "/api/console/runs",
            files={"file": (synthetic_ai.name, f, "application/postscript")},
            data={"workflow": "section"},
        ).json()

    run = app.state.console_store.load(created["run_id"])
    output = Path(run.root) / "synthetic-output.ai"
    output.write_bytes(b"synthetic output")
    run.artifacts["hierarchy_output"] = str(output)
    for key, stage in run.stages.items():
        if key == "export_proof_packet":
            continue
        stage.finish(
            status="passed",
            what_changed=[f"{stage.label} passed."],
            next_step="Continue.",
            output_path=str(output),
        )
    app.state.console_store.save(run)

    resp = client.post(f"/api/console/runs/{created['run_id']}/stages/export_proof_packet")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    stage = next(s for s in body["stages"] if s["key"] == "export_proof_packet")
    assert stage["status"] == "needs_review"
    assert "W5/W7 public proof acceptance is not recorded." in stage["why"]
    assert "Get explicit W5/W7 acceptance" in stage["next_step"]
    assert body["overall_status"] == "needs_review"
    assert body["public_safe"] is False
    assert body["public_acceptance"] == {"accepted": False, "accepted_by": []}
    proof_artifact = next(artifact for artifact in body["artifacts"] if artifact["key"] == "proof_packet")

    run = app.state.console_store.load(created["run_id"])
    packet_path = Path(run.artifacts[proof_artifact["key"]])
    with zipfile.ZipFile(packet_path) as packet:
        packet_summary = json.loads(packet.read("public-summary.json"))
        readme = packet.read("README-NOT-PUBLIC-CLEARANCE.txt").decode("utf-8")

    assert packet_summary["public_safe"] is False
    assert packet_summary["public_acceptance"] == {"accepted": False, "accepted_by": []}
    assert packet_summary["overall_status"] == "needs_review"
    assert "W5/W7 public proof acceptance is not recorded." in readme
