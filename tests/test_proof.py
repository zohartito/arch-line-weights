import copy
import json
import zipfile
from pathlib import Path

import pytest
from PIL import Image

from arch_line_weights.poche import FillResult, PocheReport
from arch_line_weights.proof import (
    W5_W7_HANDOFF_JSON_NAME,
    W5_W7_HANDOFF_MD_NAME,
    ManifestValidationError,
    ReviewRegion,
    assert_handoff_is_public_safe,
    build_proof_packet_plan,
    build_w5_w7_acceptance_handoff,
    find_handoff_public_safety_violations,
    has_dark_pixels_in_region,
    images_effectively_unchanged,
    load_manifest,
    validate_proof_packet,
    write_w5_w7_acceptance_handoff_to_zip,
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
        min_dark_ratio: 0.20
        min_dark_delta: 0.12
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
    assert manifest.fixtures[0].review_regions[0].min_dark_ratio == 0.20
    assert manifest.fixtures[0].review_regions[0].min_dark_delta == 0.12
    assert manifest.fixtures[0].caveats == ["synthetic fixture only"]
    assert manifest.fixtures[0].status == "pass"


def test_committed_make2d_manifest_tracks_public_and_private_review_lanes() -> None:
    manifest = load_manifest(Path("tests/fixtures/make2d/manifest.yml"))
    fixtures = {fixture.id: fixture for fixture in manifest.fixtures}
    fixture = fixtures["public_foundation_window_section_synthetic"]

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
    assert fixture.review_regions[0].min_dark_ratio == 0.20
    assert fixture.review_regions[0].min_dark_delta == 0.12
    assert any("does not close issue #30" in caveat for caveat in fixture.caveats)
    assert any("Private USC regression stays private" in caveat for caveat in fixture.caveats)

    private_fixture = fixtures["private_usc_wall_section_regression"]
    assert private_fixture.status == "needs_manual_review"
    assert not private_fixture.source_path.is_absolute()
    assert private_fixture.expected_report.status == "needs_manual_review"
    assert private_fixture.expected_report.counts["cut_layers_considered"] == 8
    assert private_fixture.expected_report.counts["visual_acceptance_gated_layers"] == 2
    assert {view.kind for view in private_fixture.visual_artifacts.rendered_views} == {
        "full_board",
        "cut_mass_closeup",
    }
    assert private_fixture.review_regions[0].kind == "poche_presence"
    assert any("source drawings and rendered artifacts stay out of git" in caveat for caveat in private_fixture.caveats)
    assert any("W5/W7 visual acceptance" in caveat for caveat in private_fixture.caveats)


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


def test_validate_proof_packet_accepts_w5_w7_visual_layer_gate(
    tmp_path: Path,
) -> None:
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
            "review_acceptance": {
                "visual_layer_gates": [
                    {
                        "layer": "TEC_CONCRETE_BASE",
                        "accepted": True,
                        "accepted_by": ["W7"],
                        "date": "2026-06-01",
                        "scope": "C2/C3 foundation-concrete crop visual review",
                    }
                ]
            },
        },
    )

    validation = validate_proof_packet(plan)

    assert validation.status == "passed"
    assert validation.public_summary["public_safe"] is False
    assert "W5/W7 public proof acceptance is not recorded" in validation.public_summary["why"]
    assert validation.public_summary["visual_acceptance"] == {
        "accepted_layer_count": 1,
        "accepted_by": ["W7"],
    }


def test_validate_proof_packet_visual_acceptance_does_not_clear_non_visual_review(
    tmp_path: Path,
) -> None:
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
                "layers_failed": 0,
                "layers_needs_review": 1,
                "polygons_filled": 2,
            },
            "layers": [
                {
                    "layer": "LayerB",
                    "status": "low_confidence",
                    "review": {
                        "needs_review": True,
                        "visual_acceptance_required": True,
                    },
                },
            ],
            "review_acceptance": {
                "visual_layer_gates": [
                    {
                        "layer": "LayerB",
                        "accepted": True,
                        "accepted_by": "W5",
                        "scope": "visual acceptance cannot override low-confidence status",
                    }
                ]
            },
        },
    )

    validation = validate_proof_packet(plan)

    assert validation.status == "needs_review"
    assert any("layer needs review" in reason for reason in validation.public_summary["why"])


def test_validate_proof_packet_visual_acceptance_requires_allowed_reviewer_and_exact_layer(
    tmp_path: Path,
) -> None:
    plan = build_proof_packet_plan(
        fixture_id="stair_section",
        output_dir=tmp_path / "proof",
        commands=["arch-lw apply-jsx in.pdf", "arch-lw poche out.ai"],
    )
    report = _safe_pass_report()
    report["summary"]["layers_needs_review"] = 1
    report["layers"] = [
        {
            "layer": "TEC_CONCRETE_BASE",
            "status": "inferred",
            "review": {
                "needs_review": True,
                "visual_acceptance_required": True,
            },
        },
    ]
    report["review_acceptance"] = {
        "visual_layer_gates": [
            {
                "layer": "TEC_FOUNDATION",
                "accepted": True,
                "accepted_by": "W7",
            },
            {
                "layer": "TEC_CONCRETE_BASE",
                "accepted": True,
                "accepted_by": "W4",
            },
        ]
    }
    _write_packet_artifacts(plan, report=report)

    validation = validate_proof_packet(plan)

    assert validation.status == "needs_review"
    assert validation.public_summary["visual_acceptance"] == {
        "accepted_layer_count": 0,
        "accepted_by": [],
    }


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
            structural_helper_counts={layer: 2},
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
    assert report["layers"][0]["evidence"]["used_structural_helpers"] is True
    assert report["layers"][0]["evidence"]["structural_helper_count"] == 2
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


def test_validate_proof_packet_rejects_effectively_unchanged_rendered_views_when_enabled(
    tmp_path: Path,
) -> None:
    plan = build_proof_packet_plan(
        fixture_id="stair_section",
        output_dir=tmp_path / "proof",
        commands=["arch-lw apply-jsx in.pdf", "arch-lw poche out.ai"],
    )
    _write_packet_artifacts(plan, report=_safe_pass_report())
    before = Image.new("RGB", (20, 20), "white")
    before.save(plan.output_dir / "before.png")
    before.save(plan.output_dir / "after.png")
    before.save(plan.output_dir / "cut-mass-before.png")
    before.save(plan.output_dir / "cut-mass-after.png")

    validation = validate_proof_packet(plan, fail_on_unchanged=True)

    assert validation.status == "failed"
    assert any("rendered view full_board is effectively unchanged" in reason for reason in validation.reasons)
    assert any("rendered view cut_mass_detail is effectively unchanged" in reason for reason in validation.reasons)


def test_has_dark_pixels_in_region_detects_expected_poche_presence() -> None:
    image = Image.new("RGB", (20, 20), "white")
    for x in range(5, 10):
        for y in range(5, 10):
            image.putpixel((x, y), (5, 5, 5))

    assert has_dark_pixels_in_region(image, rect=(4, 4, 12, 12), min_dark_ratio=0.25, threshold=32)
    assert not has_dark_pixels_in_region(image, rect=(12, 12, 19, 19), min_dark_ratio=0.25, threshold=32)


def test_validate_proof_packet_checks_dark_pixels_in_matching_review_region(
    tmp_path: Path,
) -> None:
    plan = build_proof_packet_plan(
        fixture_id="stair_section",
        output_dir=tmp_path / "proof",
        commands=["arch-lw apply-jsx in.pdf", "arch-lw poche out.ai"],
    )
    _write_packet_artifacts(plan, report=_safe_pass_report())
    after = Image.new("RGB", (20, 20), "white")
    for x in range(6, 12):
        for y in range(6, 12):
            after.putpixel((x, y), (0, 0, 0))
    after.save(plan.output_dir / "cut-mass-after.png")

    validation = validate_proof_packet(
        plan,
        review_regions=[
            ReviewRegion(
                id="cut_mass_detail",
                kind="poche_presence",
                rect=(5, 5, 13, 13),
            )
        ],
        min_dark_ratio=0.25,
        threshold=32,
    )

    assert validation.status == "passed"
    assert validation.public_summary["public_safe"] is False


def test_validate_proof_packet_rejects_sparse_outline_when_region_requires_solid_poche(
    tmp_path: Path,
) -> None:
    plan = build_proof_packet_plan(
        fixture_id="stair_section",
        output_dir=tmp_path / "proof",
        commands=["arch-lw apply-jsx in.pdf", "arch-lw poche out.ai"],
    )
    _write_packet_artifacts(plan, report=_safe_pass_report())
    rect = (10, 10, 40, 40)
    before = Image.new("RGB", (50, 50), "white")
    after = Image.new("RGB", (50, 50), "white")
    for x in range(rect[0], rect[2]):
        after.putpixel((x, rect[1]), (0, 0, 0))
        after.putpixel((x, rect[3] - 1), (0, 0, 0))
    for y in range(rect[1], rect[3]):
        after.putpixel((rect[0], y), (0, 0, 0))
        after.putpixel((rect[2] - 1, y), (0, 0, 0))
    for x, y in ((16, 16), (22, 21), (28, 18), (32, 30), (18, 34), (35, 23)):
        after.putpixel((x, y), (0, 0, 0))
    before.save(plan.output_dir / "cut-mass-before.png")
    after.save(plan.output_dir / "cut-mass-after.png")

    validation = validate_proof_packet(
        plan,
        review_regions=[
            _strict_review_region(
                id="cut_mass_detail",
                kind="poche_presence",
                rect=rect,
                min_dark_ratio=0.20,
                min_dark_delta=0.12,
            )
        ],
        min_dark_ratio=0.05,
        threshold=32,
    )

    assert validation.status == "failed"
    assert any("expected solid poché dark ratio >= 0.200" in reason for reason in validation.reasons)


def test_validate_proof_packet_requires_dark_delta_from_before_view(
    tmp_path: Path,
) -> None:
    plan = build_proof_packet_plan(
        fixture_id="stair_section",
        output_dir=tmp_path / "proof",
        commands=["arch-lw apply-jsx in.pdf", "arch-lw poche out.ai"],
    )
    _write_packet_artifacts(plan, report=_safe_pass_report())
    rect = (10, 10, 40, 40)
    before = Image.new("RGB", (50, 50), "white")
    after = Image.new("RGB", (50, 50), "white")
    _fill_rect(before, rect, (0, 0, 0))
    _fill_rect(after, rect, (0, 0, 0))
    before.save(plan.output_dir / "cut-mass-before.png")
    after.save(plan.output_dir / "cut-mass-after.png")

    validation = validate_proof_packet(
        plan,
        review_regions=[
            _strict_review_region(
                id="cut_mass_detail",
                kind="poche_presence",
                rect=rect,
                min_dark_ratio=0.20,
                min_dark_delta=0.12,
            )
        ],
        min_dark_ratio=0.05,
        threshold=32,
    )

    assert validation.status == "failed"
    assert any("expected new dark poché delta >= 0.120" in reason for reason in validation.reasons)


def test_validate_proof_packet_accepts_solid_region_with_strict_ratio_and_delta(
    tmp_path: Path,
) -> None:
    plan = build_proof_packet_plan(
        fixture_id="stair_section",
        output_dir=tmp_path / "proof",
        commands=["arch-lw apply-jsx in.pdf", "arch-lw poche out.ai"],
    )
    _write_packet_artifacts(plan, report=_safe_pass_report())
    rect = (10, 10, 40, 40)
    before = Image.new("RGB", (50, 50), "white")
    after = Image.new("RGB", (50, 50), "white")
    _fill_rect(after, rect, (0, 0, 0))
    before.save(plan.output_dir / "cut-mass-before.png")
    after.save(plan.output_dir / "cut-mass-after.png")

    validation = validate_proof_packet(
        plan,
        review_regions=[
            _strict_review_region(
                id="cut_mass_detail",
                kind="poche_presence",
                rect=rect,
                min_dark_ratio=0.20,
                min_dark_delta=0.12,
            )
        ],
        min_dark_ratio=0.05,
        threshold=32,
    )

    assert validation.status == "passed"


def test_validate_proof_packet_fails_when_matching_review_region_stays_light(
    tmp_path: Path,
) -> None:
    plan = build_proof_packet_plan(
        fixture_id="stair_section",
        output_dir=tmp_path / "proof",
        commands=["arch-lw apply-jsx in.pdf", "arch-lw poche out.ai"],
    )
    _write_packet_artifacts(plan, report=_safe_pass_report())
    Image.new("RGB", (20, 20), "white").save(plan.output_dir / "cut-mass-after.png")

    validation = validate_proof_packet(
        plan,
        review_regions=[
            ReviewRegion(
                id="cut_mass_detail",
                kind="poche_presence",
                rect=(5, 5, 13, 13),
            )
        ],
        min_dark_ratio=0.25,
        threshold=32,
    )

    assert validation.status == "failed"
    assert "review region cut_mass_detail (poche_presence) expected dark poché pixels" in validation.reasons
    assert validation.public_summary["what_failed"] == [
        "review region cut_mass_detail (poche_presence) expected dark poché pixels"
    ]
    assert validation.public_summary["why"] == [
        "review region cut_mass_detail (poche_presence) expected dark poché pixels"
    ]


def test_validate_proof_packet_fails_when_review_region_has_no_matching_rendered_view(
    tmp_path: Path,
) -> None:
    plan = build_proof_packet_plan(
        fixture_id="stair_section",
        output_dir=tmp_path / "proof",
        commands=["arch-lw apply-jsx in.pdf", "arch-lw poche out.ai"],
    )
    _write_packet_artifacts(plan, report=_safe_pass_report())

    validation = validate_proof_packet(
        plan,
        review_regions=[
            ReviewRegion(
                id="missing_region",
                kind="poche_presence",
                rect=(5, 5, 13, 13),
            )
        ],
    )

    assert validation.status == "failed"
    assert "review region missing_region has no matching rendered view after image" in validation.reasons


def test_committed_manifest_review_region_can_fail_synthetic_packet(
    tmp_path: Path,
) -> None:
    fixture = load_manifest(Path("tests/fixtures/make2d/manifest.yml")).fixtures[0]
    plan = build_proof_packet_plan(
        fixture_id=fixture.id,
        output_dir=tmp_path / "proof",
        commands=fixture.commands,
    )
    visual_artifacts = {
        "before": fixture.visual_artifacts.before.as_posix(),
        "after": fixture.visual_artifacts.after.as_posix(),
        "diff": fixture.visual_artifacts.diff.as_posix(),
        "rendered_views": [
            {
                "id": view.id,
                "kind": view.kind,
                "before": view.before.as_posix(),
                "after": view.after.as_posix(),
                "diff": view.diff.as_posix(),
            }
            for view in fixture.visual_artifacts.rendered_views
        ],
    }
    _write_packet_artifacts(plan, report=_safe_pass_report(visual_artifacts=visual_artifacts))
    closeup = next(view for view in fixture.visual_artifacts.rendered_views if view.kind == "cut_mass_closeup")
    Image.new("RGB", (800, 600), "white").save(plan.output_dir / closeup.before)
    Image.new("RGB", (800, 600), "white").save(plan.output_dir / closeup.after)

    validation = validate_proof_packet(
        plan,
        review_regions=fixture.review_regions,
        min_dark_ratio=0.05,
        threshold=32,
    )

    assert validation.status == "failed"
    assert any(
        "review region foundation_window_cut_mass (poche_presence) expected solid poché dark ratio >= 0.200"
        in reason
        for reason in validation.reasons
    )


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


def test_w5_w7_handoff_zip_contains_public_safe_files(tmp_path: Path) -> None:
    plan = build_proof_packet_plan(
        fixture_id="stair_section",
        output_dir=tmp_path / "proof",
        commands=["arch-lw apply-jsx in.pdf", "arch-lw poche out.ai"],
    )
    _write_packet_artifacts(plan, report=_safe_pass_report())
    validation = validate_proof_packet(plan)
    handoff_json, handoff_md = build_w5_w7_acceptance_handoff(
        fixture_id="stair_section",
        public_summary=validation.public_summary,
    )
    packet_path = tmp_path / "proof-packet.zip"
    with zipfile.ZipFile(packet_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        write_w5_w7_acceptance_handoff_to_zip(
            zf,
            handoff_json=handoff_json,
            handoff_md=handoff_md,
        )

    with zipfile.ZipFile(packet_path) as zf:
        names = set(zf.namelist())
        loaded = json.loads(zf.read(W5_W7_HANDOFF_JSON_NAME))
        md_text = zf.read(W5_W7_HANDOFF_MD_NAME).decode("utf-8")

    assert W5_W7_HANDOFF_JSON_NAME in names
    assert W5_W7_HANDOFF_MD_NAME in names
    assert loaded["public_clearance"] == "NO-GO"
    assert loaded["public_safe"] is False
    assert loaded["posting_ready"] is False
    assert loaded["acceptance_recorded"] is False
    assert "NO-GO" in md_text
    assert "acceptance has not occurred" in md_text.lower()
    gates = loaded["local_only_overlay_template"]["review_acceptance"]["visual_layer_gates"]
    assert gates[0]["accepted"] is False
    assert find_handoff_public_safety_violations(loaded) == []
    dumped = json.dumps(loaded) + md_text
    assert "/Users/" not in dumped
    assert "/private/" not in dumped
    assert "/var/folders/" not in dumped
    assert "macro_for_archlw" not in dumped.lower()
    assert "synologydrive" not in dumped.lower()


def test_w5_w7_handoff_stays_no_go_when_packet_passed_but_not_public_safe(tmp_path: Path) -> None:
    plan = build_proof_packet_plan(
        fixture_id="stair_section",
        output_dir=tmp_path / "proof",
        commands=["arch-lw apply-jsx in.pdf"],
    )
    _write_packet_artifacts(plan, report=_safe_pass_report())
    validation = validate_proof_packet(plan)
    assert validation.status == "passed"
    assert validation.public_summary["public_safe"] is False

    handoff_json, _handoff_md = build_w5_w7_acceptance_handoff(
        fixture_id="stair_section",
        public_summary=validation.public_summary,
    )
    assert handoff_json["public_clearance"] == "NO-GO"
    assert handoff_json["public_safe"] is False


def _baseline_safe_handoff() -> dict:
    plan = build_proof_packet_plan(
        fixture_id="stair_section",
        output_dir=Path("/tmp/synthetic-proof"),
        commands=["arch-lw apply-jsx in.pdf"],
    )
    validation = validate_proof_packet(plan)
    handoff_json, _ = build_w5_w7_acceptance_handoff(
        fixture_id="stair_section",
        public_summary=validation.public_summary,
    )
    return handoff_json


@pytest.mark.parametrize(
    ("mutator", "expected_substring"),
    [
        (lambda h: h.update({"public_clearance": "GO"}), "public_clearance must be NO-GO"),
        (lambda h: h.update({"public_safe": True}), "public_safe must be false"),
        (lambda h: h.update({"posting_ready": True}), "posting_ready must be false"),
        (lambda h: h.update({"acceptance_recorded": True}), "acceptance_recorded must be false"),
        (
            lambda h: h.update({"fixture_id": "/Users/reviewer/private-fixture"}),
            "local/private path references",
        ),
        (
            lambda h: h.update({"fixture_id": "macro_for_archlw_section"}),
            "private fixture tokens",
        ),
        (
            lambda h: h["local_only_overlay_template"]["review_acceptance"]["visual_layer_gates"][0].update(
                {"accepted": True}
            ),
            "overlay template must not claim visual acceptance",
        ),
    ],
)
def test_find_handoff_public_safety_violations_rejects_overclaims(
    mutator,
    expected_substring: str,
) -> None:
    handoff = copy.deepcopy(_baseline_safe_handoff())
    mutator(handoff)
    violations = find_handoff_public_safety_violations(handoff)
    assert violations
    assert any(expected_substring in item for item in violations)


def test_assert_handoff_is_public_safe_rejects_local_path_in_json() -> None:
    handoff = copy.deepcopy(_baseline_safe_handoff())
    handoff["next_steps"] = ["Review at /private/tmp/local-report.json"]
    with pytest.raises(ValueError, match="not public-safe"):
        assert_handoff_is_public_safe(handoff)


def test_write_w5_w7_handoff_to_zip_rejects_local_path_in_markdown(tmp_path: Path) -> None:
    handoff = copy.deepcopy(_baseline_safe_handoff())
    _, handoff_md = build_w5_w7_acceptance_handoff(
        fixture_id="stair_section",
        public_summary={"status": "needs_review", "public_safe": False},
    )
    packet_path = tmp_path / "proof-packet.zip"
    with (
        zipfile.ZipFile(packet_path, "w", compression=zipfile.ZIP_DEFLATED) as zf,
        pytest.raises(ValueError, match="handoff markdown is not public-safe"),
    ):
        write_w5_w7_acceptance_handoff_to_zip(
            zf,
            handoff_json=handoff,
            handoff_md=handoff_md + "\n/private/tmp/leaked-report.json\n",
        )


def _strict_review_region(
    *,
    id: str,
    kind: str,
    rect: tuple[int, int, int, int],
    min_dark_ratio: float,
    min_dark_delta: float,
) -> ReviewRegion:
    return ReviewRegion(
        id=id,
        kind=kind,
        rect=rect,
        min_dark_ratio=min_dark_ratio,
        min_dark_delta=min_dark_delta,
    )


def _fill_rect(
    image: Image.Image,
    rect: tuple[int, int, int, int],
    color: tuple[int, int, int],
) -> None:
    for x in range(rect[0], rect[2]):
        for y in range(rect[1], rect[3]):
            image.putpixel((x, y), color)
