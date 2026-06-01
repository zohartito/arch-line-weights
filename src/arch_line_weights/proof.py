"""Pure proof-manifest and visual-regression helpers."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - exercised only in minimal installs
    yaml = None


VALID_FIXTURE_STATUSES = {"pass", "expected_fail", "unsupported", "needs_manual_review"}
VALID_REPORT_STATUSES = VALID_FIXTURE_STATUSES | {"fail"}
_LOCAL_PATH_RE = re.compile(
    r"(?i)(?:file://)?(?:/Users/|/private/|/var/folders/|/tmp/|/Volumes/|[A-Z]:\\|\\\\)"
)


class ManifestValidationError(ValueError):
    """Raised when a proof manifest does not match the compact fixture schema."""


@dataclass(frozen=True)
class ExpectedReport:
    status: str
    counts: dict[str, int]


@dataclass(frozen=True)
class VisualArtifacts:
    before: Path
    after: Path
    diff: Path


@dataclass(frozen=True)
class GeometryArtifacts:
    cut_dump: Path
    layer_audit: Path


@dataclass(frozen=True)
class ReviewRegion:
    id: str
    kind: str
    rect: tuple[int, int, int, int]


@dataclass(frozen=True)
class ProofFixture:
    id: str
    source_path: Path
    commands: list[str]
    expected_report: ExpectedReport
    visual_artifacts: VisualArtifacts
    geometry_artifacts: GeometryArtifacts
    review_regions: list[ReviewRegion]
    caveats: list[str]
    status: str


@dataclass(frozen=True)
class ProofManifest:
    path: Path
    fixtures: list[ProofFixture]


@dataclass(frozen=True)
class CommandPlan:
    index: int
    command: str


@dataclass(frozen=True)
class ProofPacketPlan:
    fixture_id: str
    output_dir: Path
    report_path: Path
    before_path: Path
    after_path: Path
    diff_path: Path
    cut_geometry_path: Path
    layer_audit_path: Path
    commands: list[CommandPlan]


@dataclass(frozen=True)
class ProofPacketValidation:
    fixture_id: str
    status: str
    public_summary: dict[str, Any]
    missing_artifacts: tuple[str, ...]
    unsafe_references: tuple[str, ...]
    reasons: tuple[str, ...]


def load_manifest(path: str | Path) -> ProofManifest:
    """Load and validate a compact Make2D proof manifest."""

    manifest_path = Path(path)
    raw = _load_yaml_mapping(manifest_path)
    fixtures_raw = _required_list(raw, "fixtures", "manifest")
    fixtures = [_parse_fixture(item, manifest_path.parent, index) for index, item in enumerate(fixtures_raw)]
    return ProofManifest(path=manifest_path, fixtures=fixtures)


def build_proof_packet_plan(
    *,
    fixture_id: str,
    output_dir: str | Path,
    commands: list[str] | tuple[str, ...],
) -> ProofPacketPlan:
    """Build deterministic output paths and command metadata for a fixture proof packet."""

    if not isinstance(fixture_id, str) or not fixture_id:
        raise ValueError("fixture_id must be a non-empty string")
    command_list = _validate_string_list(commands, "commands")
    fixture_output_dir = Path(output_dir) / fixture_id
    return ProofPacketPlan(
        fixture_id=fixture_id,
        output_dir=fixture_output_dir,
        report_path=fixture_output_dir / "report.json",
        before_path=fixture_output_dir / "before.png",
        after_path=fixture_output_dir / "after.png",
        diff_path=fixture_output_dir / "diff.png",
        cut_geometry_path=fixture_output_dir / "cut-geometry.json",
        layer_audit_path=fixture_output_dir / "layer-audit.json",
        commands=[CommandPlan(index=index, command=command) for index, command in enumerate(command_list)],
    )


def validate_proof_packet(plan: ProofPacketPlan) -> ProofPacketValidation:
    """Validate a local proof packet and build a path-free public summary.

    Raw run reports are allowed to exist locally, but public proof status must
    never pass when required artifacts are absent, the report carries failed or
    no-go state, or local/private path references leak into the raw report.
    """

    artifacts = _proof_packet_artifacts(plan)
    missing_artifacts = tuple(
        label for label, path in artifacts.items() if not path.exists() or path.is_dir() or path.stat().st_size <= 0
    )

    report: dict[str, Any] = {}
    failed_reasons: list[str] = []
    no_go_reasons: list[str] = []
    review_reasons: list[str] = []

    if missing_artifacts:
        failed_reasons.append(f"missing proof artifacts: {', '.join(missing_artifacts)}")

    if "report.json" not in missing_artifacts:
        try:
            report = _load_json_mapping(plan.report_path)
        except ManifestValidationError as exc:
            failed_reasons.append(str(exc))
    else:
        failed_reasons.append("raw report is missing")

    raw_status = _normalized_status(report.get("status")) if report else ""
    if raw_status == "no_go":
        no_go_reasons.append("raw report status is no_go")
    elif raw_status in {"fail", "failed"}:
        failed_reasons.append("raw report status is failed")
    elif raw_status in {"needs_review", "needs_manual_review"}:
        review_reasons.append("raw report status needs review")

    unsafe_references = _find_unsafe_report_references(report)
    if unsafe_references:
        no_go_reasons.append(
            "raw report contains local/private path references: " + ", ".join(unsafe_references)
        )

    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    layer_failure_count = _int_count(summary, "layers_failed")
    if layer_failure_count:
        failed_reasons.append(_plural(layer_failure_count, "layer failed", "layers failed"))

    layers = report.get("layers") if isinstance(report.get("layers"), list) else []
    no_go_layers = 0
    failed_layers = 0
    review_layers = 0
    missing_payload_layers = 0
    for layer in layers:
        if not isinstance(layer, dict):
            continue
        layer_status = _normalized_status(layer.get("status"))
        review = layer.get("review") if isinstance(layer.get("review"), dict) else {}
        if layer_status == "no_go":
            no_go_layers += 1
        elif layer_status in {"fail", "failed"}:
            failed_layers += 1
        elif layer_status == "missing_payload":
            missing_payload_layers += 1
        elif layer_status in {"needs_review", "low_confidence"} or review.get("needs_review") is True:
            review_layers += 1

    if no_go_layers:
        no_go_reasons.append(_plural(no_go_layers, "layer is no_go", "layers are no_go"))
    if failed_layers:
        failed_reasons.append(_plural(failed_layers, "layer failed", "layers failed"))
    if missing_payload_layers:
        failed_reasons.append(
            _plural(missing_payload_layers, "layer missing payload", "layers missing payload")
        )
    summary_review_layers = _int_count(summary, "layers_needs_review")
    review_count = max(review_layers, summary_review_layers)
    if review_count:
        review_reasons.append(_plural(review_count, "layer needs review", "layers need review"))

    if no_go_reasons:
        status = "no_go"
    elif failed_reasons:
        status = "failed"
    elif review_reasons:
        status = "needs_review"
    else:
        status = "passed"

    reasons = tuple(dict.fromkeys([*no_go_reasons, *failed_reasons, *review_reasons]))
    return ProofPacketValidation(
        fixture_id=plan.fixture_id,
        status=status,
        public_summary=_build_public_summary(
            fixture_id=plan.fixture_id,
            status=status,
            report_summary=summary,
            reasons=reasons,
            missing_artifacts=missing_artifacts,
        ),
        missing_artifacts=missing_artifacts,
        unsafe_references=unsafe_references,
        reasons=reasons,
    )


def images_effectively_unchanged(
    before: Image.Image | np.ndarray,
    after: Image.Image | np.ndarray,
    *,
    max_changed_ratio: float = 0.001,
    per_channel_tolerance: int = 2,
) -> bool:
    """Return true when two raster images differ in no more than a tiny pixel ratio."""

    before_array = _as_image_array(before)
    after_array = _as_image_array(after)
    if before_array.shape != after_array.shape:
        return False
    if before_array.size == 0:
        return True

    changed = np.any(
        np.abs(before_array.astype(np.int16) - after_array.astype(np.int16)) > per_channel_tolerance, axis=-1
    )
    changed_ratio = float(np.count_nonzero(changed)) / float(changed.size)
    return changed_ratio <= max_changed_ratio


def has_dark_pixels_in_region(
    image: Image.Image | np.ndarray,
    *,
    rect: tuple[int, int, int, int] | list[int],
    min_dark_ratio: float = 0.05,
    threshold: int = 48,
) -> bool:
    """Return true when a rectangular region contains enough dark pixels for poché."""

    x0, y0, x1, y1 = _validate_rect(rect, "rect")
    array = _as_image_array(image)
    height, width = array.shape[:2]
    x0 = max(0, min(x0, width))
    x1 = max(0, min(x1, width))
    y0 = max(0, min(y0, height))
    y1 = max(0, min(y1, height))
    if x1 <= x0 or y1 <= y0:
        return False

    region = array[y0:y1, x0:x1, :3].astype(np.float32)
    luminance = (0.2126 * region[..., 0]) + (0.7152 * region[..., 1]) + (0.0722 * region[..., 2])
    dark_ratio = float(np.count_nonzero(luminance <= threshold)) / float(luminance.size)
    return dark_ratio >= min_dark_ratio


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    if yaml is None:
        raise ManifestValidationError("PyYAML is required to load proof manifests")
    with path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    if not isinstance(raw, dict):
        raise ManifestValidationError("manifest must be a mapping")
    return raw


def _load_json_mapping(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ManifestValidationError(f"raw report is not valid JSON: {exc.msg}") from exc
    if not isinstance(raw, dict):
        raise ManifestValidationError("raw report must be a mapping")
    return raw


def _proof_packet_artifacts(plan: ProofPacketPlan) -> dict[str, Path]:
    return {
        "report.json": plan.report_path,
        "before.png": plan.before_path,
        "after.png": plan.after_path,
        "diff.png": plan.diff_path,
        "cut-geometry.json": plan.cut_geometry_path,
        "layer-audit.json": plan.layer_audit_path,
    }


def _build_public_summary(
    *,
    fixture_id: str,
    status: str,
    report_summary: dict[str, Any],
    reasons: tuple[str, ...],
    missing_artifacts: tuple[str, ...],
) -> dict[str, Any]:
    changed = _changed_messages(report_summary)
    skipped = _skipped_messages(report_summary)
    failed = _failed_messages(report_summary, missing_artifacts)
    if not failed and status == "no_go":
        failed = ["raw report status is no_go"]

    return {
        "fixture_id": fixture_id,
        "status": status,
        "public_safe": status == "passed",
        "what_changed": changed,
        "what_skipped": skipped,
        "what_failed": failed,
        "why": list(reasons),
        "next_step": _next_step(status, reasons),
    }


def _changed_messages(summary: dict[str, Any]) -> list[str]:
    messages: list[str] = []
    for key, singular, plural in (
        ("layers_filled", "layer filled", "layers filled"),
        ("layers_inferred", "layer inferred", "layers inferred"),
        ("polygons_filled", "polygon filled", "polygons filled"),
        ("bytes_injected", "byte injected", "bytes injected"),
    ):
        count = _int_count(summary, key)
        if count:
            messages.append(_plural(count, singular, plural))
    return messages


def _skipped_messages(summary: dict[str, Any]) -> list[str]:
    skipped = _int_count(summary, "layers_skipped")
    return [_plural(skipped, "layer skipped", "layers skipped")] if skipped else []


def _failed_messages(summary: dict[str, Any], missing_artifacts: tuple[str, ...]) -> list[str]:
    messages: list[str] = []
    if missing_artifacts:
        messages.append(f"missing proof artifacts: {', '.join(missing_artifacts)}")
    failed = _int_count(summary, "layers_failed")
    if failed:
        messages.append(_plural(failed, "layer failed", "layers failed"))
    return messages


def _next_step(status: str, reasons: tuple[str, ...]) -> str:
    if status == "no_go" and any("local/private path references" in reason for reason in reasons):
        return (
            "Remove local/private references from raw proof, regenerate a public-safe summary, "
            "and keep private USC evidence local."
        )
    if status == "no_go":
        return "Fix the no-go proof condition before treating this packet as evidence."
    if status == "failed" and any("missing proof artifacts" in reason for reason in reasons):
        return "Regenerate the proof packet artifacts before treating this as evidence."
    if status == "failed":
        return "Fix failed proof stages, then rerun the proof packet."
    if status == "needs_review":
        return "Review flagged layers or regions before accepting the packet."
    return "Attach the public summary only; keep raw local reports out of committed/public proof."


def _find_unsafe_report_references(report: dict[str, Any]) -> tuple[str, ...]:
    references: set[str] = set()

    def walk(value: Any, label: str) -> None:
        if isinstance(value, str):
            if _LOCAL_PATH_RE.search(value):
                references.add(label)
        elif isinstance(value, dict):
            for key, child in value.items():
                child_label = f"{label}.{key}" if label else str(key)
                walk(child, child_label)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{label}[{index}]")

    walk(report, "")
    return tuple(sorted(references))


def _normalized_status(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip().lower().replace("-", "_")


def _int_count(summary: dict[str, Any], key: str) -> int:
    value = summary.get(key)
    return value if isinstance(value, int) and value > 0 else 0


def _plural(count: int, singular: str, plural: str) -> str:
    noun = singular if count == 1 else plural
    return f"{count} {noun}"


def _parse_fixture(raw: Any, manifest_dir: Path, index: int) -> ProofFixture:
    label = f"fixtures[{index}]"
    if not isinstance(raw, dict):
        raise ManifestValidationError(f"{label} must be a mapping")

    fixture_id = _required_str(raw, "id", label)
    source_value = raw.get("source_path", raw.get("fixture_path"))
    if not isinstance(source_value, str) or not source_value:
        raise ManifestValidationError(f"{fixture_id}.source_path or {fixture_id}.fixture_path is required")
    source_path = Path(source_value)
    if not source_path.is_absolute():
        source_path = manifest_dir / source_path

    status = _required_status(raw, "status", fixture_id, VALID_FIXTURE_STATUSES)
    expected_report = _parse_expected_report(raw.get("expected_report"), fixture_id)
    visual_artifacts = _parse_visual_artifacts(raw.get("visual_artifacts"), fixture_id)
    geometry_artifacts = _parse_geometry_artifacts(raw.get("geometry_artifacts"), fixture_id)
    review_regions = _parse_review_regions(raw.get("review_regions", []), fixture_id)

    return ProofFixture(
        id=fixture_id,
        source_path=source_path,
        commands=_validate_string_list(raw.get("commands"), f"{fixture_id}.commands"),
        expected_report=expected_report,
        visual_artifacts=visual_artifacts,
        geometry_artifacts=geometry_artifacts,
        review_regions=review_regions,
        caveats=_validate_string_list(raw.get("caveats", []), f"{fixture_id}.caveats"),
        status=status,
    )


def _parse_expected_report(raw: Any, fixture_id: str) -> ExpectedReport:
    if not isinstance(raw, dict):
        raise ManifestValidationError(f"{fixture_id}.expected_report must be a mapping")
    status = _required_status(raw, "status", f"{fixture_id}.expected_report", VALID_REPORT_STATUSES)
    counts = raw.get("counts")
    if not isinstance(counts, dict):
        raise ManifestValidationError(f"{fixture_id}.expected_report.counts must be a mapping")
    validated_counts: dict[str, int] = {}
    for key, value in counts.items():
        if not isinstance(key, str) or not isinstance(value, int) or value < 0:
            raise ManifestValidationError(
                f"{fixture_id}.expected_report.counts must map strings to non-negative ints"
            )
        validated_counts[key] = value
    return ExpectedReport(status=status, counts=validated_counts)


def _parse_visual_artifacts(raw: Any, fixture_id: str) -> VisualArtifacts:
    if not isinstance(raw, dict):
        raise ManifestValidationError(f"{fixture_id}.visual_artifacts must be a mapping")
    return VisualArtifacts(
        before=Path(_required_str(raw, "before", f"{fixture_id}.visual_artifacts")),
        after=Path(_required_str(raw, "after", f"{fixture_id}.visual_artifacts")),
        diff=Path(_required_str(raw, "diff", f"{fixture_id}.visual_artifacts")),
    )


def _parse_geometry_artifacts(raw: Any, fixture_id: str) -> GeometryArtifacts:
    if not isinstance(raw, dict):
        raise ManifestValidationError(f"{fixture_id}.geometry_artifacts must be a mapping")
    return GeometryArtifacts(
        cut_dump=Path(_required_str(raw, "cut_dump", f"{fixture_id}.geometry_artifacts")),
        layer_audit=Path(_required_str(raw, "layer_audit", f"{fixture_id}.geometry_artifacts")),
    )


def _parse_review_regions(raw: Any, fixture_id: str) -> list[ReviewRegion]:
    if not isinstance(raw, list):
        raise ManifestValidationError(f"{fixture_id}.review_regions must be a list")
    regions: list[ReviewRegion] = []
    for index, item in enumerate(raw):
        label = f"{fixture_id}.review_regions[{index}]"
        if not isinstance(item, dict):
            raise ManifestValidationError(f"{label} must be a mapping")
        regions.append(
            ReviewRegion(
                id=_required_str(item, "id", label),
                kind=_required_str(item, "kind", label),
                rect=_validate_rect(item.get("rect"), f"{label}.rect"),
            )
        )
    return regions


def _required_list(raw: dict[str, Any], key: str, label: str) -> list[Any]:
    value = raw.get(key)
    if not isinstance(value, list):
        raise ManifestValidationError(f"{label}.{key} must be a list")
    return value


def _required_str(raw: dict[str, Any], key: str, label: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value:
        raise ManifestValidationError(f"{label}.{key} must be a non-empty string")
    return value


def _required_status(raw: dict[str, Any], key: str, label: str, valid_statuses: set[str]) -> str:
    status = _required_str(raw, key, label)
    if status not in valid_statuses:
        expected = ", ".join(sorted(valid_statuses))
        raise ManifestValidationError(f"{label}.{key} must be one of: {expected}")
    return status


def _validate_string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, (list, tuple)) or any(not isinstance(item, str) for item in value):
        raise ManifestValidationError(f"{label} must be a list of strings")
    return list(value)


def _validate_rect(value: Any, label: str) -> tuple[int, int, int, int]:
    if (
        not isinstance(value, (list, tuple))
        or len(value) != 4
        or any(not isinstance(coordinate, int) for coordinate in value)
    ):
        raise ManifestValidationError(f"{label} must be four integer coordinates")
    x0, y0, x1, y1 = value
    if x1 <= x0 or y1 <= y0:
        raise ManifestValidationError(f"{label} must be ordered as [x0, y0, x1, y1]")
    return x0, y0, x1, y1


def _as_image_array(image: Image.Image | np.ndarray) -> np.ndarray:
    array = np.asarray(image.convert("RGBA")) if isinstance(image, Image.Image) else np.asarray(image)

    if array.ndim == 2:
        array = np.repeat(array[..., np.newaxis], 4, axis=-1)
    elif array.ndim == 3 and array.shape[-1] == 3:
        alpha = np.full((*array.shape[:2], 1), 255, dtype=array.dtype)
        array = np.concatenate([array, alpha], axis=-1)
    elif array.ndim != 3 or array.shape[-1] < 4:
        raise ValueError("image arrays must be grayscale, RGB, or RGBA")

    return array[..., :4].astype(np.uint8, copy=False)
