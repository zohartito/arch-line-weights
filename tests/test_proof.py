import json
from pathlib import Path

from PIL import Image

from arch_line_weights.poche import FillResult, PocheReport
from arch_line_weights.proof import (
    ManifestValidationError,
    build_proof_packet_plan,
    has_dark_pixels_in_region,
    images_effectively_unchanged,
    load_manifest,
    validate_proof_packet,
)
from arch_line_weights.run_report import build_poche_report


def test_load_manifest_validates_compact_make2d_fixture_schema(tmp_path: Path) -> None:
    source = tmp_path / "fixtures" / "section.pdf"
    source.parent.mkdir()
    source.write_bytes(b"%PDF synthetic placeholder")
    manifest_path = tmp_path / "manifest.yml"
    manifest_path.write_text(
        """
fixtures:
  - id: stair_section
    fixture_path: fixtures/section.pdf
    commands:
      - arch-lw apply fixtures/section.pdf --poche
      - arch-lw run-report out/stair_section.json
    expected_report:
      status: pass
      counts:
        layers: 4
        poche_regions: 1
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
        - id: stair_core
          kind: cut_mass_closeup
          before: stair-core-before.png
          after: stair-core-after.png
          diff: stair-core-diff.png
    geometry_artifacts:
      cut_dump: cut-geometry.json
      layer_audit: layer-audit.json
    review_regions:
      - id: stair_core
        kind: poche
        rect: [10, 20, 30, 40]
    caveats:
      - synthetic fixture only
    status: pass
""",
        encoding="utf-8",
    )

    manifest = load_manifest(manifest_path)

    assert manifest.fixtures[0].id == "stair_section"
    assert manifest.fixtures[0].source_path == source
    assert manifest.fixtures[0].commands == [
        "arch-lw apply fixtures/section.pdf --poche",
        "arch-lw run-report out/stair_section.json",
    ]
    assert manifest.fixtures[0].expected_report.status == "pass"
    assert manifest.fixtures[0].expected_report.counts == {"layers": 4, "poche_regions": 1}
    assert manifest.fixtures[0].visual_artifacts.after == Path("after.png")
    assert manifest.fixtures[0].visual_artifacts.rendered_views[0].kind == "full_board"
    assert manifest.fixtures[0].visual_artifacts.rendered_views[1].kind == "cut_mass_closeup"
    assert manifest.fixtures[0].geometry_artifacts.cut_dump == Path("cut-geometry.json")
    assert manifest.fixtures[0].geometry_artifacts.layer_audit == Path("layer-audit.json")
    assert manifest.fixtures[0].review_regions[0].rect == (10, 20, 30, 40)
    assert manifest.fixtures[0].caveats == ["synthetic fixture only"]
    assert manifest.fixtures[0].status == "pass"


def test_committed_make2d_manifest_is_repo_safe_synthetic_fixture() -> None:
    manifest = load_manifest(Path("tests/fixtures/make2d/manifest.yml"))
    fixture = manifest.fixtures[0]

    assert fixture.id == "public_foundation_window_section_synthetic"
    assert fixture.status == "pass"
    assert not fixture.source_path.is_absolute()
    assert fixture.expected_report.counts["cut_layers_considered"] == 3
    assert fixture.expected_report.counts["polygons_filled"] == 4
    assert fixture.geometry_artifacts.cut_dump == Path(
        "proof/public-foundation-window-section/cut-geometry.json"
    )
    assert {view.kind for view in fixture.visual_artifacts.rendered_views} == {
        "full_board",
        "cut_mass_closeup",
    }
    assert fixture.review_regions[0].kind == "poche_presence"
    assert any("does not close issue #30" in caveat for caveat in fixture.caveats)
    assert any("Private USC regression stays private" in caveat for caveat in fixture.caveats)


def test_load_manifest_rejects_invalid_fixture_status(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.yml"
    manifest_path.write_text(
        """
fixtures:
  - id: bad_status
    fixture_path: bad.pdf
    commands: []
    expected_report:
      status: pass
      counts: {}
    visual_artifacts:
      before: before.png
      after: after.png
      diff: diff.png
    review_regions: []
    status: maybe
""",
        encoding="utf-8",
    )

    try:
        load_manifest(manifest_path)
    except ManifestValidationError as exc:
        assert "bad_status.status" in str(exc)
    else:
        raise AssertionError("expected manifest validation to reject unknown status")


def test_build_proof_packet_plan_uses_stable_artifact_paths(tmp_path: Path) -> None:
    plan = build_proof_packet_plan(
        fixture_id="stair_section",
        output_dir=tmp_path / "proof",
        commands=["arch-lw apply in.pdf", "arch-lw run-report out.json"],
    )

    assert plan.fixture_id == "stair_section"
    assert plan.report_path == tmp_path / "proof" / "stair_section" / "report.json"
    assert plan.before_path == tmp_path / "proof" / "stair_section" / "before.png"
    assert plan.after_path == tmp_path / "proof" / "stair_section" / "after.png"
    assert plan.diff_path == tmp_path / "proof" / "stair_section" / "diff.png"
    assert plan.cut_geometry_path == tmp_path / "proof" / "stair_section" / "cut-geometry.json"
    assert plan.layer_audit_path == tmp_path / "proof" / "stair_section" / "layer-audit.json"
    assert [command.index for command in plan.commands] == [0, 1]
    assert [command.command for command in plan.commands] == [
        "arch-lw apply in.pdf",
        "arch-lw run-report out.json",
    ]


def test_validate_proof_packet_rejects_missing_artifacts(tmp_path: Path) -> None:
    plan = build_proof_packet_plan(
        fixture_id="stair_section",
        output_dir=tmp_path / "proof",
        commands=["arch-lw apply-jsx in.pdf", "arch-lw poche out.ai"],
    )
    _write_packet_artifacts(
        plan,
        report={
            "schema_version": 2,
            "summary": {"layers_filled": 1, "layers_failed": 0, "layers_needs_review": 0},
            "layers": [],
        },
        missing={plan.after_path},
    )

    validation = validate_proof_packet(plan)

    assert validation.status == "failed"
    assert "after.png" in validation.public_summary["what_failed"][0]
    assert "Regenerate the proof packet artifacts" in validation.public_summary["next_step"]


def test_validate_proof_packet_rejects_no_go_report(tmp_path: Path) -> None:
    plan = build_proof_packet_plan(
        fixture_id="stair_section",
        output_dir=tmp_path / "proof",
        commands=["arch-lw apply-jsx in.pdf", "arch-lw poche out.ai"],
    )
    _write_packet_artifacts(
        plan,
        report={
            "schema_version": 2,
            "status": "no_go",
            "summary": {"layers_filled": 0, "layers_failed": 1, "layers_needs_review": 0},
            "layers": [{"layer": "LayerA", "status": "failed", "review": {"needs_review": True}}],
        },
    )

    validation = validate_proof_packet(plan)

    assert validation.status == "no_go"
    assert any("raw report status is no_go" in reason for reason in validation.reasons)
    assert "Fix the no-go proof condition" in validation.public_summary["next_step"]


def test_validate_proof_packet_rejects_local_paths_and_sanitizes_public_summary(tmp_path: Path) -> None:
    plan = build_proof_packet_plan(
        fixture_id="stair_section",
        output_dir=tmp_path / "proof",
        commands=["arch-lw apply-jsx in.pdf", "arch-lw poche out.ai"],
    )
    local_input = "/" + "/".join(("Users", "example", "private", "client-section.ai"))
    _write_packet_artifacts(
        plan,
        report={
            "schema_version": 2,
            "source": {
                "input": local_input,
                "command": f"arch-lw apply-jsx {local_input}",
            },
            "summary": {"layers_filled": 1, "layers_failed": 0, "layers_needs_review": 0},
            "layers": [{"layer": "LayerA", "status": "filled", "review": {"needs_review": False}}],
        },
    )

    validation = validate_proof_packet(plan)

    assert validation.status == "no_go"
    assert validation.unsafe_references == ("source.command", "source.input")
    public_payload = json.dumps(validation.public_summary, sort_keys=True)
    assert local_input.rsplit("/", 1)[0] not in public_payload
    assert "client-section" not in public_payload
    assert "raw report contains local/private path references" in validation.public_summary["why"][0]


def test_validate_proof_packet_requires_report_identity_and_rendered_views(tmp_path: Path) -> None:
    plan = build_proof_packet_plan(
        fixture_id="stair_section",
        output_dir=tmp_path / "proof",
        commands=["arch-lw apply-jsx in.pdf", "arch-lw poche out.ai"],
    )
    _write_packet_artifacts(
        plan,
        report={
            "schema_version": 2,
            "summary": {"layers_filled": 1, "layers_failed": 0, "layers_needs_review": 0},
            "layers": [{"layer": "LayerA", "status": "filled", "review": {"needs_review": False}}],
        },
    )

    validation = validate_proof_packet(plan)

    assert validation.status == "failed"
    assert any("report source.input is required" in reason for reason in validation.reasons)
    assert any("visual artifacts missing rendered view checklist" in reason for reason in validation.reasons)


def test_validate_proof_packet_requires_full_board_and_closeup_views(tmp_path: Path) -> None:
    plan = build_proof_packet_plan(
        fixture_id="stair_section",
        output_dir=tmp_path / "proof",
        commands=["arch-lw apply-jsx in.pdf", "arch-lw poche out.ai"],
    )
    _write_packet_artifacts(
        plan,
        report=_safe_pass_report(
            visual_artifacts={
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
                    }
                ],
            }
        ),
    )

    validation = validate_proof_packet(plan)

    assert validation.status == "failed"
    assert any("visual artifacts missing close-up rendered view" in reason for reason in validation.reasons)


def test_validate_proof_packet_passes_clean_report_but_is_not_public_safe_without_acceptance(
    tmp_path: Path,
) -> None:
    plan = build_proof_packet_plan(
        fixture_id="stair_section",
        output_dir=tmp_path / "proof",
        commands=["arch-lw apply-jsx in.pdf", "arch-lw poche out.ai"],
    )
    _write_packet_artifacts(
        plan,
        report=_safe_pass_report(),
    )

    validation = validate_proof_packet(plan)

    assert validation.status == "passed"
    assert validation.public_summary["public_safe"] is False
    assert "W5/W7 public proof acceptance is not recorded" in validation.public_summary["why"]
    assert "1 layer filled" in validation.public_summary["what_changed"]
    assert "4 polygons filled" in validation.public_summary["what_changed"]
    assert validation.public_summary["what_failed"] == []
    assert validation.public_summary["proof_identity"]["command"] == "arch-lw poche stair-section.ai"
    assert validation.public_summary["rendered_views"] == [
        {
            "id": "full_board",
            "kind": "full_board",
            "before": "before.png",
            "after": "after.png",
            "diff": "diff.png",
        },
        {
            "id": "cut_mass_detail",
            "kind": "cut_mass_closeup",
            "before": "cut-mass-before.png",
            "after": "cut-mass-after.png",
            "diff": "cut-mass-diff.png",
        },
    ]
    assert validation.public_summary["public_acceptance"] == {
        "accepted": False,
        "accepted_by": [],
    }
    assert "Get explicit W5/W7 acceptance" in validation.public_summary["next_step"]


def test_validate_proof_packet_is_public_safe_only_with_w5_w7_acceptance(tmp_path: Path) -> None:
    plan = build_proof_packet_plan(
        fixture_id="stair_section",
        output_dir=tmp_path / "proof",
        commands=["arch-lw apply-jsx in.pdf", "arch-lw poche out.ai"],
    )
    _write_packet_artifacts(
        plan,
        report=_safe_pass_report(
            review_acceptance={
                "public_proof": {
                    "accepted": True,
                    "accepted_by": "W5",
                    "date": "2026-06-01",
                    "scope": "synthetic proof only",
                }
            }
        ),
    )

    validation = validate_proof_packet(plan)

    assert validation.status == "passed"
    assert validation.public_summary["public_safe"] is True
    assert validation.public_summary["public_acceptance"] == {
        "accepted": True,
        "accepted_by": ["W5"],
        "date": "2026-06-01",
        "scope": "synthetic proof only",
    }
    assert "Attach the public summary only" in validation.public_summary["next_step"]


def test_validate_proof_packet_needs_review_for_visual_acceptance_gate(tmp_path: Path) -> None:
    plan = build_proof_packet_plan(
        fixture_id="stair_section",
        output_dir=tmp_path / "proof",
        commands=["arch-lw apply-jsx in.pdf", "arch-lw poche out.ai"],
    )
    _write_packet_artifacts(
        plan,
        report={
            "schema_version": 2,
            "source": {
                "input": "stair-section.ai",
                "output": "stair-section-poche.ai",
                "command": "arch-lw poche stair-section.ai",
            },
            "visual_artifacts": _safe_visual_artifacts(),
            "summary": {
                "layers_filled": 1,
                "layers_inferred": 1,
                "layers_failed": 0,
                "layers_needs_review": 1,
                "polygons_filled": 2,
            },
            "layers": [
                {"layer": "LayerA", "status": "filled", "review": {"needs_review": False}},
                {
                    "layer": "TEC_CONCRETE_BASE",
                    "status": "inferred",
                    "review": {
                        "needs_review": True,
                        "visual_acceptance_required": True,
                        "reasons": [
                            "inferred concrete/foundation fill requires W5/W7 visual acceptance"
                        ],
                    },
                },
            ],
        },
    )

    validation = validate_proof_packet(plan)

    assert validation.status == "needs_review"
    assert "layer needs review" in validation.public_summary["why"][0]


def test_helper_backed_concrete_poche_report_stays_review_gated_in_proof(
    tmp_path: Path,
) -> None:
    layer = "axon::Visible::ClippingPlaneIntersections::TEC_CONCRETE_BASE"
    report = build_poche_report(
        input_path="public-foundation-window-section.ai",
        output_path="public-foundation-window-section-poche.ai",
        source={"mode": "poche", "style": "solid", "fixture": "synthetic"},
        poche_report=PocheReport(
            fills=[FillResult(layer, "structural_open_loop", 0.88, 1, 8)],
            polygons={layer: [[[100, 0], [130, 0], [130, 160], [100, 160], [100, 0]]]},
        ),
        command="arch-lw poche public-foundation-window-section.ai --report report.json",
        visual_artifacts=_safe_visual_artifacts(),
    )
    plan = build_proof_packet_plan(
        fixture_id="public_foundation_window_section",
        output_dir=tmp_path / "proof",
        commands=["arch-lw poche public-foundation-window-section.ai --report report.json"],
    )
    _write_packet_artifacts(plan, report=report)

    validation = validate_proof_packet(plan)

    assert report["summary"]["layers_inferred"] == 1
    assert report["summary"]["layers_needs_review"] == 1
    assert report["layers"][0]["status"] == "inferred"
    assert report["layers"][0]["review"]["visual_acceptance_required"] is True
    assert validation.status == "needs_review"
    assert validation.public_summary["public_safe"] is False
    assert "1 layer needs review" in validation.public_summary["why"]
    assert "1 layer inferred" in validation.public_summary["what_changed"]
    assert validation.public_summary["what_failed"] == []


def test_images_effectively_unchanged_uses_pixel_ratio_threshold() -> None:
    before = Image.new("RGB", (10, 10), "white")
    almost_same = before.copy()
    almost_same.putpixel((0, 0), (250, 250, 250))
    changed = before.copy()
    for x in range(5):
        for y in range(5):
            changed.putpixel((x, y), (0, 0, 0))

    assert images_effectively_unchanged(before, almost_same, max_changed_ratio=0.02, per_channel_tolerance=8)
    assert not images_effectively_unchanged(before, changed, max_changed_ratio=0.02, per_channel_tolerance=8)


def test_has_dark_pixels_in_region_detects_expected_poche_presence() -> None:
    image = Image.new("RGB", (20, 20), "white")
    for x in range(5, 10):
        for y in range(5, 10):
            image.putpixel((x, y), (5, 5, 5))

    assert has_dark_pixels_in_region(image, rect=(4, 4, 12, 12), min_dark_ratio=0.25, threshold=32)
    assert not has_dark_pixels_in_region(image, rect=(12, 12, 19, 19), min_dark_ratio=0.25, threshold=32)


def _write_packet_artifacts(
    plan,
    *,
    report: dict,
    missing: set[Path] | None = None,
) -> None:
    missing = missing or set()
    for path in (
        plan.report_path,
        plan.before_path,
        plan.after_path,
        plan.diff_path,
        plan.cut_geometry_path,
        plan.layer_audit_path,
    ):
        if path in missing:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        if path == plan.report_path:
            path.write_text(json.dumps(report), encoding="utf-8")
        else:
            path.write_bytes(b"synthetic proof artifact")
    visual_artifacts = report.get("visual_artifacts") if isinstance(report.get("visual_artifacts"), dict) else {}
    views = visual_artifacts.get("rendered_views") if isinstance(visual_artifacts.get("rendered_views"), list) else []
    for view in views:
        if not isinstance(view, dict):
            continue
        for key in ("before", "after", "diff"):
            value = view.get(key)
            if isinstance(value, str):
                path = plan.output_dir / value
                if path in missing:
                    continue
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"synthetic rendered view")


def _safe_pass_report(
    *,
    visual_artifacts: dict | None = None,
    review_acceptance: dict | None = None,
) -> dict:
    return {
        "schema_version": 2,
        "source": {
            "input": "stair-section.ai",
            "output": "stair-section-poche.ai",
            "command": "arch-lw poche stair-section.ai",
        },
        "visual_artifacts": visual_artifacts or _safe_visual_artifacts(),
        "summary": {
            "layers_filled": 1,
            "layers_inferred": 1,
            "layers_skipped": 0,
            "layers_failed": 0,
            "layers_needs_review": 0,
            "polygons_filled": 4,
        },
        "layers": [
            {"layer": "LayerA", "status": "filled", "review": {"needs_review": False}},
            {"layer": "LayerB", "status": "inferred", "review": {"needs_review": False}},
        ],
        **({"review_acceptance": review_acceptance} if review_acceptance is not None else {}),
    }


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
                "id": "cut_mass_detail",
                "kind": "cut_mass_closeup",
                "before": "cut-mass-before.png",
                "after": "cut-mass-after.png",
                "diff": "cut-mass-diff.png",
            },
        ],
    }
