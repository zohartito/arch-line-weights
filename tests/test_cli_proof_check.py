from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner
from PIL import Image

from arch_line_weights.cli import cli


def test_proof_check_plan_only_reads_make2d_manifest_and_emits_packet_plan(tmp_path: Path) -> None:
    manifest = Path("tests/fixtures/make2d/manifest.yml")
    output_dir = tmp_path / "proof"

    result = CliRunner().invoke(
        cli,
        [
            "proof-check",
            str(manifest),
            "--output-dir",
            str(output_dir),
            "--plan-only",
            "--no-pretty",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    fixtures = {fixture["id"]: fixture for fixture in payload["fixtures"]}

    assert payload["schema_version"] == 1
    assert payload["status"] == "planned"
    assert payload["summary"]["fixtures"] == 4
    assert payload["summary"]["needs_manual_review"] == 1
    assert "Posting/public proof is NO-GO" in payload["guardrails"][0]
    assert fixtures["public_foundation_window_section_synthetic"]["proof_packet"]["report"].endswith(
        "public_foundation_window_section_synthetic/report.json"
    )
    assert fixtures["public_foundation_window_section_synthetic"]["visual_artifacts"]["after"] == (
        "proof/public-foundation-window-section/after.png"
    )
    assert fixtures["private_usc_wall_section_regression"]["manifest_status"] == "needs_manual_review"
    assert fixtures["private_usc_wall_section_regression"]["validation"]["status"] == "not_run"
    assert fixtures["public_false_fill_void_expected_fail_synthetic"]["manifest_status"] == "expected_fail"
    assert fixtures["public_unsupported_payload_synthetic"]["manifest_status"] == "unsupported"


def test_proof_check_can_materialize_public_synthetic_packet(tmp_path: Path) -> None:
    manifest = Path("tests/fixtures/make2d/manifest.yml")
    output_dir = tmp_path / "proof"
    output_report = tmp_path / "proof-check.json"

    result = CliRunner().invoke(
        cli,
        [
            "proof-check",
            str(manifest),
            "--output-dir",
            str(output_dir),
            "--fixture",
            "public_foundation_window_section_synthetic",
            "--materialize-synthetic",
            "--write",
            str(output_report),
            "--no-pretty",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    fixture = payload["fixtures"][0]
    packet_dir = output_dir / "public_foundation_window_section_synthetic"

    assert payload["status"] == "passed"
    assert payload["summary"] == {
        "expectations_satisfied": 1,
        "expected_fail": 0,
        "failed": 0,
        "fixtures": 1,
        "needs_manual_review": 0,
        "needs_review": 0,
        "no_go": 0,
        "passed": 1,
        "unexpected_fail": 0,
        "unexpected_pass": 0,
        "unsupported": 0,
    }
    assert fixture["validation"]["status"] == "passed"
    assert fixture["validation"]["observed_status"] == "passed"
    assert fixture["validation"]["expected_status"] == "pass"
    assert fixture["validation"]["expectation_status"] == "satisfied"
    assert fixture["validation"]["public_summary"]["public_safe"] is False
    assert "W5/W7 public proof acceptance is not recorded" in fixture["validation"]["public_summary"]["why"]
    for name in [
        "report.json",
        "before.png",
        "after.png",
        "diff.png",
        "cut-geometry.json",
        "layer-audit.json",
        "foundation_window_cut_mass-before.png",
        "foundation_window_cut_mass-after.png",
        "foundation_window_cut_mass-diff.png",
    ]:
        assert (packet_dir / name).is_file(), name
    assert json.loads(output_report.read_text(encoding="utf-8")) == payload


def test_proof_check_materializes_public_synthetic_sentinels(tmp_path: Path) -> None:
    manifest = Path("tests/fixtures/make2d/manifest.yml")

    result = CliRunner().invoke(
        cli,
        [
            "proof-check",
            str(manifest),
            "--output-dir",
            str(tmp_path / "proof"),
            "--fixture",
            "public_foundation_window_section_synthetic",
            "--fixture",
            "public_false_fill_void_expected_fail_synthetic",
            "--fixture",
            "public_unsupported_payload_synthetic",
            "--materialize-synthetic",
            "--no-pretty",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    fixtures = {fixture["id"]: fixture for fixture in payload["fixtures"]}

    assert payload["status"] == "passed"
    assert payload["summary"] == {
        "expectations_satisfied": 3,
        "expected_fail": 1,
        "failed": 0,
        "fixtures": 3,
        "needs_manual_review": 0,
        "needs_review": 0,
        "no_go": 0,
        "passed": 1,
        "unexpected_fail": 0,
        "unexpected_pass": 0,
        "unsupported": 1,
    }
    assert fixtures["public_foundation_window_section_synthetic"]["validation"]["status"] == "passed"
    expected_fail = fixtures["public_false_fill_void_expected_fail_synthetic"]["validation"]
    assert expected_fail["status"] == "expected_fail"
    assert expected_fail["observed_status"] == "failed"
    assert expected_fail["expected_status"] == "expected_fail"
    assert expected_fail["expectation_status"] == "satisfied"
    assert any("protected void" in reason for reason in expected_fail["reasons"])
    unsupported = fixtures["public_unsupported_payload_synthetic"]["validation"]
    assert unsupported["status"] == "unsupported"
    assert unsupported["observed_status"] == "failed"
    assert unsupported["expected_status"] == "unsupported"
    assert unsupported["expectation_status"] == "satisfied"
    assert any("missing payload" in reason for reason in unsupported["reasons"])


def test_proof_check_expected_fail_unexpected_pass_is_failed(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.yml"
    manifest_path.write_text(
        """
fixtures:
  - id: expected_fail_unexpected_pass
    fixture_path: synthetic.pdf
    commands:
      - arch-lw poche synthetic.ai --report report.json
    expected_report:
      status: expected_fail
      counts:
        polygons_filled: 1
    visual_artifacts:
      before: before.png
      after: after.png
      diff: diff.png
      rendered_views:
        - id: full_board
          kind: full_board
          before: before.png
          after: after.png
          diff: diff.png
        - id: cut_mass
          kind: cut_mass_closeup
          before: cut-mass-before.png
          after: cut-mass-after.png
          diff: cut-mass-diff.png
    geometry_artifacts:
      cut_dump: cut-geometry.json
      layer_audit: layer-audit.json
    review_regions: []
    status: expected_fail
""",
        encoding="utf-8",
    )
    packet_dir = tmp_path / "proof" / "expected_fail_unexpected_pass"
    packet_dir.mkdir(parents=True)
    report = {
        "schema_version": 2,
        "source": {
            "input": "synthetic.pdf",
            "output": "synthetic POCHE.pdf",
            "command": "arch-lw poche synthetic.ai --report report.json",
        },
        "summary": {
            "layers_filled": 1,
            "layers_failed": 0,
            "layers_needs_review": 0,
            "polygons_filled": 1,
        },
        "layers": [{"layer": "SYN::CUT", "status": "filled", "review": {"needs_review": False}}],
        "visual_artifacts": _safe_visual_artifacts(),
    }
    (packet_dir / "report.json").write_text(json.dumps(report), encoding="utf-8")
    for name in ["cut-geometry.json", "layer-audit.json"]:
        (packet_dir / name).write_bytes(b"proof artifact")
    _write_changed_rendered_images(packet_dir)

    result = CliRunner().invoke(
        cli,
        [
            "proof-check",
            str(manifest_path),
            "--output-dir",
            str(tmp_path / "proof"),
            "--no-pretty",
        ],
    )

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    validation = payload["fixtures"][0]["validation"]
    assert payload["status"] == "failed"
    assert validation["status"] == "failed"
    assert validation["observed_status"] == "passed"
    assert validation["expectation_status"] == "unexpected_pass"
    assert any("expected_fail fixture validated as passed" in reason for reason in validation["reasons"])


def test_proof_check_expected_fail_does_not_mask_no_go(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.yml"
    manifest_path.write_text(
        """
fixtures:
  - id: expected_fail_no_go
    fixture_path: synthetic.pdf
    commands:
      - arch-lw poche synthetic.ai --report report.json
    expected_report:
      status: expected_fail
      counts:
        polygons_filled: 1
    visual_artifacts:
      before: before.png
      after: after.png
      diff: diff.png
      rendered_views:
        - id: full_board
          kind: full_board
          before: before.png
          after: after.png
          diff: diff.png
        - id: cut_mass
          kind: cut_mass_closeup
          before: cut-mass-before.png
          after: cut-mass-after.png
          diff: cut-mass-diff.png
    geometry_artifacts:
      cut_dump: cut-geometry.json
      layer_audit: layer-audit.json
    review_regions: []
    status: expected_fail
""",
        encoding="utf-8",
    )
    packet_dir = tmp_path / "proof" / "expected_fail_no_go"
    packet_dir.mkdir(parents=True)
    report = {
        "schema_version": 2,
        "source": {
            "input": "/private/tmp/synthetic.pdf",
            "output": "synthetic POCHE.pdf",
            "command": "arch-lw poche synthetic.ai --report report.json",
        },
        "summary": {
            "layers_filled": 1,
            "layers_failed": 0,
            "layers_needs_review": 0,
            "polygons_filled": 1,
        },
        "layers": [{"layer": "SYN::CUT", "status": "filled", "review": {"needs_review": False}}],
        "visual_artifacts": _safe_visual_artifacts(),
    }
    (packet_dir / "report.json").write_text(json.dumps(report), encoding="utf-8")
    for name in ["cut-geometry.json", "layer-audit.json"]:
        (packet_dir / name).write_bytes(b"proof artifact")
    _write_changed_rendered_images(packet_dir)

    result = CliRunner().invoke(
        cli,
        [
            "proof-check",
            str(manifest_path),
            "--output-dir",
            str(tmp_path / "proof"),
            "--no-pretty",
        ],
    )

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    validation = payload["fixtures"][0]["validation"]
    assert payload["status"] == "no_go"
    assert validation["status"] == "no_go"
    assert validation["observed_status"] == "no_go"
    assert validation["expectation_status"] == "unexpected_fail"


def test_proof_check_unsupported_requires_explicit_evidence(tmp_path: Path) -> None:
    manifest = Path("tests/fixtures/make2d/manifest.yml")

    result = CliRunner().invoke(
        cli,
        [
            "proof-check",
            str(manifest),
            "--output-dir",
            str(tmp_path / "proof"),
            "--fixture",
            "public_unsupported_payload_synthetic",
            "--no-pretty",
        ],
    )

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    validation = payload["fixtures"][0]["validation"]
    assert payload["status"] == "failed"
    assert validation["status"] == "failed"
    assert validation["observed_status"] == "failed"
    assert validation["expectation_status"] == "unexpected_fail"
    assert any("unsupported fixture validated as failed" in reason for reason in validation["reasons"])


def test_proof_check_materialize_synthetic_does_not_clear_private_manual_review(tmp_path: Path) -> None:
    manifest = Path("tests/fixtures/make2d/manifest.yml")

    result = CliRunner().invoke(
        cli,
        [
            "proof-check",
            str(manifest),
            "--output-dir",
            str(tmp_path / "proof"),
            "--materialize-synthetic",
            "--no-pretty",
        ],
    )

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    fixtures = {fixture["id"]: fixture for fixture in payload["fixtures"]}

    assert payload["status"] == "failed"
    assert payload["summary"]["passed"] == 1
    assert payload["summary"]["expected_fail"] == 1
    assert payload["summary"]["unsupported"] == 1
    assert payload["summary"]["failed"] == 1
    assert payload["summary"]["expectations_satisfied"] == 3
    assert payload["summary"]["unexpected_fail"] == 0
    assert fixtures["public_foundation_window_section_synthetic"]["validation"]["status"] == "passed"
    assert (
        fixtures["public_false_fill_void_expected_fail_synthetic"]["validation"]["status"] == "expected_fail"
    )
    assert fixtures["public_unsupported_payload_synthetic"]["validation"]["status"] == "unsupported"
    assert fixtures["private_usc_wall_section_regression"]["validation"]["status"] == "failed"
    assert "report.json" in " ".join(
        fixtures["private_usc_wall_section_regression"]["validation"]["missing_artifacts"]
    )


def test_proof_check_validates_existing_packet_and_writes_json(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.yml"
    manifest_path.write_text(
        """
fixtures:
  - id: synthetic_pass
    fixture_path: synthetic.pdf
    commands:
      - arch-lw poche synthetic.ai --report report.json
    expected_report:
      status: pass
      counts:
        polygons_filled: 1
    visual_artifacts:
      before: before.png
      after: after.png
      diff: diff.png
      rendered_views:
        - id: full_board
          kind: full_board
          before: before.png
          after: after.png
          diff: diff.png
        - id: cut_mass
          kind: cut_mass_closeup
          before: cut-mass-before.png
          after: cut-mass-after.png
          diff: cut-mass-diff.png
    geometry_artifacts:
      cut_dump: cut-geometry.json
      layer_audit: layer-audit.json
    review_regions: []
    status: pass
""",
        encoding="utf-8",
    )
    packet_dir = tmp_path / "proof" / "synthetic_pass"
    packet_dir.mkdir(parents=True)
    report = {
        "schema_version": 2,
        "source": {
            "input": "synthetic.pdf",
            "output": "synthetic POCHE.pdf",
            "command": "arch-lw poche synthetic.ai --report report.json",
        },
        "summary": {
            "layers_filled": 1,
            "layers_inferred": 0,
            "layers_skipped": 0,
            "layers_failed": 0,
            "layers_needs_review": 0,
            "polygons_filled": 1,
        },
        "layers": [{"layer": "SYN::CUT", "status": "filled", "review": {"needs_review": False}}],
        "visual_artifacts": {
            "before": "before.png",
            "after": "after.png",
            "diff": "diff.png",
            "rendered_views": [
                {
                    "id": "full_board",
                    "kind": "full_board",
                    "before": "before.png",
                    "after": "after.png",
                    "diff": "diff.png",
                },
                {
                    "id": "cut_mass",
                    "kind": "cut_mass_closeup",
                    "before": "cut-mass-before.png",
                    "after": "cut-mass-after.png",
                    "diff": "cut-mass-diff.png",
                },
            ],
        },
    }
    (packet_dir / "report.json").write_text(json.dumps(report), encoding="utf-8")
    for name in [
        "cut-geometry.json",
        "layer-audit.json",
    ]:
        (packet_dir / name).write_bytes(b"proof artifact")
    _write_changed_rendered_images(packet_dir)

    output_report = tmp_path / "proof-check.json"
    result = CliRunner().invoke(
        cli,
        [
            "proof-check",
            str(manifest_path),
            "--output-dir",
            str(tmp_path / "proof"),
            "--write",
            str(output_report),
            "--no-pretty",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    written = json.loads(output_report.read_text(encoding="utf-8"))

    assert payload == written
    assert payload["status"] == "passed"
    assert payload["summary"]["passed"] == 1
    assert payload["fixtures"][0]["validation"]["status"] == "passed"
    assert payload["fixtures"][0]["validation"]["public_summary"]["public_safe"] is False


def test_proof_check_fails_when_manifest_expected_counts_do_not_match_report(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.yml"
    manifest_path.write_text(
        """
fixtures:
  - id: synthetic_mismatch
    fixture_path: synthetic.pdf
    commands:
      - arch-lw poche synthetic.ai --report report.json
    expected_report:
      status: pass
      counts:
        polygons_filled: 2
    visual_artifacts:
      before: before.png
      after: after.png
      diff: diff.png
      rendered_views:
        - id: full_board
          kind: full_board
          before: before.png
          after: after.png
          diff: diff.png
        - id: cut_mass
          kind: cut_mass_closeup
          before: cut-mass-before.png
          after: cut-mass-after.png
          diff: cut-mass-diff.png
    geometry_artifacts:
      cut_dump: cut-geometry.json
      layer_audit: layer-audit.json
    review_regions: []
    status: pass
""",
        encoding="utf-8",
    )
    packet_dir = tmp_path / "proof" / "synthetic_mismatch"
    packet_dir.mkdir(parents=True)
    report = {
        "schema_version": 2,
        "source": {
            "input": "synthetic.pdf",
            "output": "synthetic POCHE.pdf",
            "command": "arch-lw poche synthetic.ai --report report.json",
        },
        "summary": {
            "layers_filled": 1,
            "layers_failed": 0,
            "layers_needs_review": 0,
            "polygons_filled": 1,
        },
        "layers": [{"layer": "SYN::CUT", "status": "filled", "review": {"needs_review": False}}],
        "visual_artifacts": {
            "before": "before.png",
            "after": "after.png",
            "diff": "diff.png",
            "rendered_views": [
                {
                    "id": "full_board",
                    "kind": "full_board",
                    "before": "before.png",
                    "after": "after.png",
                    "diff": "diff.png",
                },
                {
                    "id": "cut_mass",
                    "kind": "cut_mass_closeup",
                    "before": "cut-mass-before.png",
                    "after": "cut-mass-after.png",
                    "diff": "cut-mass-diff.png",
                },
            ],
        },
    }
    (packet_dir / "report.json").write_text(json.dumps(report), encoding="utf-8")
    for name in [
        "cut-geometry.json",
        "layer-audit.json",
    ]:
        (packet_dir / name).write_bytes(b"proof artifact")
    _write_changed_rendered_images(packet_dir)

    result = CliRunner().invoke(
        cli,
        [
            "proof-check",
            str(manifest_path),
            "--output-dir",
            str(tmp_path / "proof"),
            "--no-pretty",
        ],
    )

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "failed"
    assert payload["fixtures"][0]["validation"]["status"] == "failed"
    assert (
        "expected_report.counts.polygons_filled expected 2, found 1"
        in payload["fixtures"][0]["validation"]["reasons"]
    )


def test_proof_check_fails_when_report_json_is_missing(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.yml"
    manifest_path.write_text(
        """
fixtures:
  - id: missing_report
    fixture_path: synthetic.pdf
    commands:
      - arch-lw poche synthetic.ai --report report.json
    expected_report:
      status: pass
      counts:
        polygons_filled: 1
    visual_artifacts:
      before: before.png
      after: after.png
      diff: diff.png
      rendered_views:
        - id: full_board
          kind: full_board
          before: before.png
          after: after.png
          diff: diff.png
        - id: cut_mass
          kind: cut_mass_closeup
          before: cut-mass-before.png
          after: cut-mass-after.png
          diff: cut-mass-diff.png
    geometry_artifacts:
      cut_dump: cut-geometry.json
      layer_audit: layer-audit.json
    review_regions: []
    status: pass
""",
        encoding="utf-8",
    )
    packet_dir = tmp_path / "proof" / "missing_report"
    packet_dir.mkdir(parents=True)
    for name in [
        "cut-geometry.json",
        "layer-audit.json",
    ]:
        (packet_dir / name).write_bytes(b"proof artifact")
    _write_changed_rendered_images(packet_dir)

    result = CliRunner().invoke(
        cli,
        [
            "proof-check",
            str(manifest_path),
            "--output-dir",
            str(tmp_path / "proof"),
            "--no-pretty",
        ],
    )

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "failed"
    validation = payload["fixtures"][0]["validation"]
    assert validation["status"] == "failed"
    assert "report.json" in " ".join(validation.get("missing_artifacts", []))


def test_proof_check_fails_when_rendered_views_are_effectively_unchanged(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.yml"
    manifest_path.write_text(
        """
fixtures:
  - id: unchanged_packet
    fixture_path: synthetic.pdf
    commands:
      - arch-lw poche synthetic.ai --report report.json
    expected_report:
      status: pass
      counts:
        polygons_filled: 1
    visual_artifacts:
      before: before.png
      after: after.png
      diff: diff.png
      rendered_views:
        - id: full_board
          kind: full_board
          before: before.png
          after: after.png
          diff: diff.png
        - id: cut_mass
          kind: cut_mass_closeup
          before: cut-mass-before.png
          after: cut-mass-after.png
          diff: cut-mass-diff.png
    geometry_artifacts:
      cut_dump: cut-geometry.json
      layer_audit: layer-audit.json
    review_regions: []
    status: pass
""",
        encoding="utf-8",
    )
    packet_dir = tmp_path / "proof" / "unchanged_packet"
    packet_dir.mkdir(parents=True)
    report = {
        "schema_version": 2,
        "source": {
            "input": "synthetic.pdf",
            "output": "synthetic POCHE.pdf",
            "command": "arch-lw poche synthetic.ai --report report.json",
        },
        "summary": {
            "layers_filled": 1,
            "layers_failed": 0,
            "layers_needs_review": 0,
            "polygons_filled": 1,
        },
        "layers": [{"layer": "SYN::CUT", "status": "filled", "review": {"needs_review": False}}],
        "visual_artifacts": {
            "before": "before.png",
            "after": "after.png",
            "diff": "diff.png",
            "rendered_views": [
                {
                    "id": "full_board",
                    "kind": "full_board",
                    "before": "before.png",
                    "after": "after.png",
                    "diff": "diff.png",
                },
                {
                    "id": "cut_mass",
                    "kind": "cut_mass_closeup",
                    "before": "cut-mass-before.png",
                    "after": "cut-mass-after.png",
                    "diff": "cut-mass-diff.png",
                },
            ],
        },
    }
    (packet_dir / "report.json").write_text(json.dumps(report), encoding="utf-8")
    for name in ["cut-geometry.json", "layer-audit.json", "diff.png", "cut-mass-diff.png"]:
        (packet_dir / name).write_bytes(b"proof artifact")
    unchanged = Image.new("RGB", (20, 20), "white")
    for name in ["before.png", "after.png", "cut-mass-before.png", "cut-mass-after.png"]:
        unchanged.save(packet_dir / name)

    result = CliRunner().invoke(
        cli,
        [
            "proof-check",
            str(manifest_path),
            "--output-dir",
            str(tmp_path / "proof"),
            "--no-pretty",
        ],
    )

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "failed"
    assert any(
        "effectively unchanged" in reason for reason in payload["fixtures"][0]["validation"]["reasons"]
    )


def _write_changed_rendered_images(packet_dir: Path) -> None:
    before = Image.new("RGB", (20, 20), "white")
    after = Image.new("RGB", (20, 20), "white")
    for x in range(5, 15):
        for y in range(5, 15):
            after.putpixel((x, y), (0, 0, 0))
    before.save(packet_dir / "before.png")
    after.save(packet_dir / "after.png")
    before.save(packet_dir / "cut-mass-before.png")
    after.save(packet_dir / "cut-mass-after.png")
    after.save(packet_dir / "diff.png")
    after.save(packet_dir / "cut-mass-diff.png")


def _safe_visual_artifacts() -> dict:
    return {
        "before": "before.png",
        "after": "after.png",
        "diff": "diff.png",
        "rendered_views": [
            {
                "id": "full_board",
                "kind": "full_board",
                "before": "before.png",
                "after": "after.png",
                "diff": "diff.png",
            },
            {
                "id": "cut_mass",
                "kind": "cut_mass_closeup",
                "before": "cut-mass-before.png",
                "after": "cut-mass-after.png",
                "diff": "cut-mass-diff.png",
            },
        ],
    }
