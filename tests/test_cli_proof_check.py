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
    assert payload["summary"]["fixtures"] == 2
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
