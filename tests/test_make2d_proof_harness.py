from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

import pytest
from PIL import Image, ImageChops

from arch_line_weights.inspect import inspect_file
from arch_line_weights.poche import FillResult, PocheReport
from arch_line_weights.poche_saas import PocheSaasResult
from arch_line_weights.run_report import (
    build_apply_saas_report,
    build_poche_geometry_report,
    build_poche_report,
)

MANIFEST_PATH = Path(__file__).with_name("fixtures") / "make2d_day1_manifest.json"
PRIVATE_FIXTURE_ROOT_ENV = "ARCH_LW_PRIVATE_FIXTURE_ROOT"
FORBIDDEN_PUBLIC_MANIFEST_PATTERNS = (
    "/" + "Users" + r"/[^/\s]+",
    "Synology" + "Drive",
    "USC" + "_1",
    r"Spring \d{4}",
    r"ARCH \d{3}",
    "WALL" + r"\s+" + "SECTION",
    "Desk" + "top/",
    "arch-lw-day1" + "-qa-section-jsx",
    "section-" + "HIERARCHY",
)


def _load_case() -> dict[str, Any]:
    manifest = json.loads(MANIFEST_PATH.read_text())
    return manifest["cases"][0]


def _private_fixture_root() -> Path:
    raw = os.environ.get(PRIVATE_FIXTURE_ROOT_ENV)
    if not raw:
        pytest.skip(f"{PRIVATE_FIXTURE_ROOT_ENV} not set; private Make2D proof assets unavailable")
    root = Path(raw)
    if not root.exists():
        pytest.skip(f"{PRIVATE_FIXTURE_ROOT_ENV} points to missing path: {root}")
    return root


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _iter_assets(case: dict[str, Any]):
    for group_name in ("sources", "screenshots", "exports", "logs"):
        for asset_name, asset in case[group_name].items():
            yield group_name, asset_name, asset


def _resolve_asset(asset: dict[str, Any]) -> Path:
    return _private_fixture_root() / asset["relative_path"]


def _assert_asset_identity(asset: dict[str, Any]) -> Path:
    path = _resolve_asset(asset)
    assert path.exists(), f"missing proof asset: {path}"
    assert path.stat().st_size == asset["size_bytes"]
    assert _sha256(path) == asset["sha256"]
    if "width" in asset or "height" in asset:
        with Image.open(path) as image:
            assert image.size == (asset["width"], asset["height"])
    return path


def _changed_pixels(a: Path, b: Path) -> tuple[int, float]:
    with Image.open(a).convert("RGB") as before, Image.open(b).convert("RGB") as after:
        assert before.size == after.size
        diff = ImageChops.difference(before, after).convert("L")
        changed = sum(v for i, v in enumerate(diff.point(lambda px: 255 if px else 0).histogram()) if i)
        total = before.width * before.height
    return changed, changed / total


def _black_ratio(path: Path, roi: list[int]) -> float:
    with Image.open(path).convert("L") as image:
        crop = image.crop(tuple(roi))
        total = crop.width * crop.height
        black = sum(count for value, count in enumerate(crop.histogram()) if value <= 64)
    return black / total


def _parse_poche_log(log_text: str) -> tuple[dict[str, int], list[dict[str, Any]]]:
    summary_patterns = {
        "polygons_created": r"polygons created:\s+(\d+)",
        "clean_layers": r"clean \(linemerge\):\s+(\d+) layers",
        "imperfect_layers": r"imperfect \(concave\):\s+(\d+) layers",
        "failed_layers": r"failed:\s+(\d+) layers",
    }
    summary = {}
    for name, pattern in summary_patterns.items():
        match = re.search(pattern, log_text)
        assert match is not None, f"missing poche log summary field: {name}"
        summary[name] = int(match.group(1))
    layer_re = re.compile(
        r"^\s*(?P<mark>\S)\s+"
        r"(?P<layer>.+?)\s{2,}"
        r"(?P<strategy>\S+)\s+polys=\s*(?P<polygons>\d+)\s+"
        r"conf=(?P<confidence>[0-9.]+)(?:\s+bridge=(?P<bridge>\S+))?",
        re.MULTILINE,
    )
    layers = []
    for match in layer_re.finditer(log_text):
        data = match.groupdict()
        layers.append({
            "strategy": data["strategy"],
            "polygons": int(data["polygons"]),
            "confidence": float(data["confidence"]),
            "bridge_strategy_name": data["bridge"],
            "mark": data["mark"],
        })
    return summary, layers


def test_public_manifest_contains_no_local_private_paths():
    text = MANIFEST_PATH.read_text()

    for pattern in FORBIDDEN_PUBLIC_MANIFEST_PATTERNS:
        assert re.search(pattern, text) is None


def test_day1_make2d_proof_assets_match_manifest_identity():
    case = _load_case()

    for _group_name, _asset_name, asset in _iter_assets(case):
        _assert_asset_identity(asset)


def test_day1_manifest_records_missing_structured_truth_sources():
    case = _load_case()

    missing = {item["kind"]: item["relative_path"] for item in case["missing_source_files"]}
    assert missing == {}
    assert "structured_poche_report_json" not in missing
    assert case["generated_outputs"]["structured_poche_report_json"]["filename"] == (
        "arch_lw_poche_report.json"
    )
    assert case["generated_outputs"]["cut_geometry_dump_json"]["filename"] == (
        "arch_lw_cut_geometry.json"
    )


def test_day1_raw_capture_provenance_points_to_expected_make2d_source():
    case = _load_case()
    capture_script = _resolve_asset(case["logs"]["capture_script"]).read_text()
    capture_log = _resolve_asset(case["logs"]["capture_log"]).read_text()

    assert case["sources"]["raw_ai"]["relative_path"] in capture_script
    assert case["screenshots"]["raw"]["relative_path"] in capture_script
    assert case["screenshots"]["raw"]["relative_path"] in capture_log


def test_day1_hierarchy_vector_changes_are_measurable_and_bounded():
    case = _load_case()
    raw = inspect_file(str(_resolve_asset(case["sources"]["raw_ai"])))
    hierarchy = inspect_file(str(_resolve_asset(case["sources"]["hierarchy_ai"])))
    expected = case["expected_inspect"]

    assert raw.total_stroked == expected["total_stroked"]
    assert hierarchy.total_stroked == expected["total_stroked"]
    assert raw.stroke_colors == expected["stroke_colors"]
    assert hierarchy.stroke_colors == expected["stroke_colors"]
    assert raw.stroke_widths == expected["raw_stroke_widths"]
    assert hierarchy.stroke_widths == expected["hierarchy_stroke_widths"]
    assert raw.stroke_widths != hierarchy.stroke_widths
    assert min(float(width) for width in hierarchy.stroke_widths) >= 0.5
    assert max(float(width) for width in hierarchy.stroke_widths) <= 2.0


def test_day1_screenshot_deltas_are_measurable_and_bounded():
    case = _load_case()
    screenshots = case["screenshots"]

    changed, ratio = _changed_pixels(_resolve_asset(screenshots["raw"]), _resolve_asset(screenshots["hierarchy"]))
    bounds = case["expected_image_deltas"]["raw_to_hierarchy"]
    assert bounds["changed_pixels_min"] <= changed <= bounds["changed_pixels_max"]
    assert bounds["ratio_min"] <= ratio <= bounds["ratio_max"]

    changed, ratio = _changed_pixels(_resolve_asset(screenshots["hierarchy"]), _resolve_asset(screenshots["poche"]))
    bounds = case["expected_image_deltas"]["hierarchy_to_poche"]
    assert bounds["changed_pixels_min"] <= changed <= bounds["changed_pixels_max"]
    assert bounds["ratio_min"] <= ratio <= bounds["ratio_max"]


def test_day1_poche_log_exposes_real_filled_and_review_layers():
    case = _load_case()
    log_text = _resolve_asset(case["logs"]["poche_log"]).read_text()
    summary, layers = _parse_poche_log(log_text)

    assert summary == case["poche"]["expected_summary"]
    assert len(layers) == len(case["poche"]["expected_fills"])
    for expected, layer in zip(case["poche"]["expected_fills"], layers, strict=True):
        assert layer["strategy"] == expected["strategy"]
        assert layer["polygons"] == expected["polygons"]
        assert layer["confidence"] == pytest.approx(expected["confidence"], abs=0.01)
        if "bridge_strategy_name" in expected:
            assert layer["bridge_strategy_name"] == expected["bridge_strategy_name"]


def test_make2d_report_contract_separates_filled_skipped_and_low_confidence_layers():
    filled = "fixture::cut::cut_layer_001"
    skipped = "fixture::cut::cut_layer_002"
    low_confidence = "fixture::cut::cut_layer_003"
    data = build_apply_saas_report(
        input_path="section.ai",
        output_path="section-POCHE.ai",
        source={"mode": "poche", "fixture": "day1_section_jsx"},
        poche_report=PocheReport(
            fills=[
                FillResult(filled, "linemerge_bare", 1.0, 1, 22),
                FillResult(skipped, "skipped", 0.0, 0, 12),
                FillResult(low_confidence, "auto_bridge", 0.69, 1, 18),
            ],
            polygons={filled: [[[0, 0], [10, 0], [10, 10], [0, 10]]]},
        ),
        poche_result=PocheSaasResult(polygons_injected=1),
    )

    by_short_name = {layer["short_name"]: layer for layer in data["layers"]}
    assert data["summary"]["layers_filled"] == 1
    assert data["summary"]["layers_skipped"] == 1
    assert data["summary"]["layers_low_confidence"] == 1
    assert by_short_name["cut_layer_001"]["status"] == "filled"
    assert by_short_name["cut_layer_002"]["status"] == "skipped"
    assert by_short_name["cut_layer_003"]["status"] == "low_confidence"


def test_day1_harness_can_generate_structured_poche_report_json(tmp_path):
    case = _load_case()
    fills = []
    polygons = {}
    for expected in case["poche"]["expected_fills"]:
        layer = expected["layer_id"]
        fill = FillResult(
            layer,
            expected["strategy"],
            expected["confidence"],
            expected["polygons"],
            segment_count=0,
            bridge_strategy_name=expected.get("bridge_strategy_name"),
        )
        fills.append(fill)
        if expected.get("expected_status") != "low_confidence":
            polygons[layer] = [[[0, 0], [10, 0], [10, 10], [0, 10]]]

    report_path = tmp_path / case["generated_outputs"]["structured_poche_report_json"]["filename"]
    data = build_poche_report(
        input_path=case["sources"]["hierarchy_ai"]["relative_path"],
        output_path=case["sources"]["poche_ai"]["relative_path"],
        source={"fixture": case["id"], "style": "solid", "bridge_strategy": "best"},
        poche_report=PocheReport(fills=fills, polygons=polygons),
        known_limitations=case["known_misses"],
    )
    report_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")

    reloaded = json.loads(report_path.read_text())
    assert reloaded["summary"]["status"] == "no_go"
    assert reloaded["summary"]["layers_filled"] == 1
    assert reloaded["summary"]["layers_inferred"] == 5
    assert reloaded["summary"]["layers_low_confidence"] == 2
    assert reloaded["summary"]["no_go_limitations"] == 1
    assert "cut_layer_007" in reloaded["layers_by_status"]["low_confidence"]
    assert "cut_layer_008" in reloaded["layers_by_status"]["low_confidence"]
    assert reloaded["limitations"][0]["id"] == "foundation_concrete_under_wood_column_left_footing"
    assert reloaded["limitations"][0]["status"] == "no_go"
    assert reloaded["limitations"][0]["scope"] == "foundation_concrete"


def test_day1_harness_can_generate_cut_geometry_summary_json(tmp_path):
    case = _load_case()
    fills = []
    polygons = {}
    paths_by_layer = {}
    for idx, expected in enumerate(case["poche"]["expected_fills"], start=1):
        layer = expected["layer_id"]
        paths_by_layer[layer] = [
            [[0, idx], [10, idx], [10, idx + 1], [0, idx + 1], [0, idx]]
        ]
        fill = FillResult(
            layer,
            expected["strategy"],
            expected["confidence"],
            expected["polygons"],
            segment_count=4,
            bridge_strategy_name=expected.get("bridge_strategy_name"),
        )
        fills.append(fill)
        if expected.get("expected_status") != "low_confidence":
            polygons[layer] = [[[0, idx], [10, idx], [10, idx + 1], [0, idx + 1], [0, idx]]]

    geometry_path = tmp_path / case["generated_outputs"]["cut_geometry_dump_json"]["filename"]
    data = build_poche_geometry_report(
        source={"fixture": case["id"], "style": "solid", "bridge_strategy": "best"},
        paths_by_layer=paths_by_layer,
        poche_report=PocheReport(fills=fills, polygons=polygons),
        known_limitations=case["known_misses"],
        redact_layer_names=False,
    )
    geometry_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")

    reloaded = json.loads(geometry_path.read_text())
    assert reloaded["source"]["stage"] == "cut_geometry"
    assert reloaded["summary"]["status"] == "no_go"
    assert reloaded["summary"]["layers_considered"] == 8
    assert reloaded["summary"]["source_cut_contours_total"] == 8
    assert reloaded["summary"]["ambiguous_regions_total"] == 2
    assert reloaded["summary"]["no_go_limitations"] == 1
    assert reloaded["limitations"][0]["code"] == "known_visual_proof_miss"
    assert reloaded["layers"][0]["layer_name"] == "cut_layer_001"
    assert reloaded["layers"][0]["source_cut_contours_count"] == 1


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Known Day-1 proof miss: screenshot 05 shows the left foundation/concrete "
        "mass under the wood column as outline-only."
    ),
)
def test_day1_known_foundation_concrete_under_wood_column_is_filled():
    case = _load_case()
    miss = case["known_misses"][0]

    assert miss["current_black_ratio_observed"] >= miss["expected_min_black_ratio"]
