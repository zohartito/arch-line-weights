from __future__ import annotations

from unittest.mock import Mock

import pytest
from click.testing import CliRunner
from shapely.geometry import Polygon

from arch_line_weights.apply import apply_to_file
from arch_line_weights.apply_jsx import apply_via_jsx
from arch_line_weights.apply_saas import _read_payload
from arch_line_weights.bridge_rhino_ai import bridge_rhino_ai
from arch_line_weights.cli import cli
from arch_line_weights.hatch import hatch_polygon
from arch_line_weights.inspect import inspect_file
from arch_line_weights.layout_jsx import layout_via_jsx
from arch_line_weights.llm_topology import infer_closing_plan
from arch_line_weights.poche import polygonize_layer
from arch_line_weights.poche_saas import enumerate_layer_paths_from_payload
from arch_line_weights.preview import GhostscriptRenderer, PyMuPDFRenderer, side_by_side
from arch_line_weights.proof import build_proof_packet_plan, validate_proof_packet
from arch_line_weights.safety import ProcessingDisabledError


def test_pdf_roots_refuse_before_open(monkeypatch, tmp_path) -> None:
    opener = Mock(side_effect=AssertionError("must not open"))
    monkeypatch.setattr("arch_line_weights.inspect.pikepdf.open", opener)
    with pytest.raises(ProcessingDisabledError):
        inspect_file(str(tmp_path / "hostile.pdf"))
    with pytest.raises(ProcessingDisabledError):
        apply_to_file("hostile.pdf", "out.pdf", {})
    assert opener.call_count == 0


def test_native_and_geometry_roots_refuse_before_iteration() -> None:
    hostile_pdf = Mock()
    with pytest.raises(ProcessingDisabledError):
        _read_payload(hostile_pdf)
    hostile_payload = Mock(spec=bytes)
    with pytest.raises(ProcessingDisabledError):
        enumerate_layer_paths_from_payload(hostile_payload)
    with pytest.raises(ProcessingDisabledError):
        polygonize_layer("cut", [])
    assert hostile_pdf.mock_calls == []


def test_preview_hatch_and_proof_refuse_before_path_access(tmp_path) -> None:
    with pytest.raises(ProcessingDisabledError):
        side_by_side(tmp_path / "before.pdf", tmp_path / "after.pdf", tmp_path / "out.png")
    with pytest.raises(ProcessingDisabledError):
        hatch_polygon(Polygon(), "concrete", 0.02)
    plan = build_proof_packet_plan(fixture_id="safe", output_dir=tmp_path, commands=["proof-check"])
    with pytest.raises(ProcessingDisabledError):
        validate_proof_packet(plan)


def test_injected_llm_client_cannot_bypass_explicit_consent() -> None:
    client = Mock()
    assert infer_closing_plan("layer", [(0.0, 0.0)], [], client=client) is None
    assert client.mock_calls == []


def test_jsx_and_bridge_roots_refuse_before_creating_artifacts(tmp_path) -> None:
    output = tmp_path / "out.ai"
    report = tmp_path / "report.json"
    jsx = tmp_path / "rendered.jsx"
    bridge_dir = tmp_path / "bridge"

    with pytest.raises(ProcessingDisabledError):
        apply_via_jsx(str(tmp_path / "input.ai"), str(output), jsx_path=str(jsx))
    with pytest.raises(ProcessingDisabledError):
        layout_via_jsx(
            str(tmp_path / "input.ai"),
            dst=str(output),
            report_json=str(report),
            jsx_path=str(jsx),
            dry_run=True,
        )
    with pytest.raises(ProcessingDisabledError):
        bridge_rhino_ai(str(tmp_path / "input.ai"), report_dir=str(bridge_dir), dry_run=True)

    assert not output.exists()
    assert not report.exists()
    assert not jsx.exists()
    assert not bridge_dir.exists()


def test_preview_render_all_refuses_before_budget_validation(monkeypatch) -> None:
    budget = Mock(side_effect=AssertionError("must not inspect a PDF"))
    monkeypatch.setattr("arch_line_weights.preview._validate_render_budget", budget)
    ghostscript = object.__new__(GhostscriptRenderer)
    ghostscript.supersample = 4

    for renderer in (PyMuPDFRenderer(), ghostscript):
        with pytest.raises(ProcessingDisabledError):
            renderer.render_all("hostile.pdf", 300)

    assert budget.call_count == 0


@pytest.mark.parametrize(
    ("command", "surface"),
    [
        (["inspect", "does-not-exist.ai"], "PDF inspection"),
        (["apply", "does-not-exist.ai", "--auto"], "PDF content-stream rewrite"),
        (["apply", "does-not-exist.ai", "--mapping", "missing.json"], "PDF content-stream rewrite"),
        (["apply-saas", "does-not-exist.ai", "--auto"], "native-payload rewrite"),
        (
            [
                "apply-saas",
                "does-not-exist.ai",
                "--mapping",
                "missing.json",
                "--poche-overrides",
                "nope.json",
            ],
            "native-payload rewrite",
        ),
        (["poche", "does-not-exist.ai"], "poche geometry processing"),
        (["poche", "does-not-exist.ai", "--overrides", "missing.json"], "poche geometry processing"),
        (["apply-jsx", "does-not-exist.ai"], "native-document rewrite"),
        (["layout-jsx", "does-not-exist.ai"], "native-document layout"),
        (["bridge-rhino-ai", "--input", "does-not-exist.ai"], "native-document bridge"),
        (["bridge-rhino-ai"], "native-document bridge"),
        (["preview", "before.pdf", "after.pdf", "-o", "out.png"], "preview supersampled rendering"),
        (["preview", "before.pdf", "after.pdf"], "preview supersampled rendering"),
        (["proof-check", "does-not-exist.yml"], "proof packet validation"),
    ],
)
def test_disabled_cli_commands_refuse_before_path_validation(command, surface) -> None:
    result = CliRunner().invoke(cli, command)
    assert result.exit_code == 1
    assert surface in result.output
    assert "permanently disabled" in result.output
