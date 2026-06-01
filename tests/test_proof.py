from pathlib import Path

from PIL import Image

from arch_line_weights.proof import (
    ManifestValidationError,
    build_proof_packet_plan,
    has_dark_pixels_in_region,
    images_effectively_unchanged,
    load_manifest,
)


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
