"""Pure proof-manifest and visual-regression helpers."""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
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
VALID_RENDERED_VIEW_KINDS = {"full_board", "cut_mass_closeup", "openings_closeup", "detail_closeup"}
_CLOSEUP_RENDERED_VIEW_KINDS = {"cut_mass_closeup", "openings_closeup", "detail_closeup"}
_LOCAL_PATH_RE = re.compile(
    r"(?i)(?:file://)?(?:/Users/|/private/|/var/folders/|/tmp/|/Volumes/|[A-Z]:\\|\\\\)"
)
_PUBLIC_ACCEPTANCE_REVIEWERS = {"W5", "W7"}


class ManifestValidationError(ValueError):
    """Raised when a proof manifest does not match the compact fixture schema."""


@dataclass(frozen=True)
class ExpectedReport:
    status: str
    counts: dict[str, int]


@dataclass(frozen=True)
class RenderedView:
    id: str
    kind: str
    before: Path
    after: Path
    diff: Path


@dataclass(frozen=True)
class VisualArtifacts:
    before: Path
    after: Path
    diff: Path
    rendered_views: list[RenderedView]


@dataclass(frozen=True)
class GeometryArtifacts:
    cut_dump: Path
    layer_audit: Path


@dataclass(frozen=True)
class ReviewRegion:
    id: str
    kind: str
    rect: tuple[int, int, int, int]
    min_dark_ratio: float | None = None
    min_dark_delta: float | None = None


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


def validate_proof_packet(
    plan: ProofPacketPlan,
    *,
    review_regions: Sequence[ReviewRegion] | None = None,
    min_dark_ratio: float = 0.05,
    min_dark_delta: float = 0.0,
    threshold: int = 48,
) -> ProofPacketValidation:
    """Validate a local proof packet and build a path-free public summary.

    Raw run reports are allowed to exist locally, but public proof status must
    never pass when required artifacts are absent, the report carries failed or
    no-go state, or local/private path references leak into the raw report.
    """
    artifacts = _proof_packet_artifacts(plan)
    missing_artifacts = [
        label for label, path in artifacts.items() if not path.exists() or path.is_dir() or path.stat().st_size <= 0
    ]

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

    if report:
        failed_reasons.extend(_report_identity_errors(report))
        visual_errors, visual_missing = _report_visual_errors(report, plan)
        failed_reasons.extend(visual_errors)
        missing_artifacts.extend(visual_missing)

    if report and review_regions:
        failed_reasons.extend(
            _review_region_pixel_errors(
                report,
                plan,
                review_regions,
                min_dark_ratio=min_dark_ratio,
                min_dark_delta=min_dark_delta,
                threshold=threshold,
            )
        )

    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    layer_failure_count = _int_count(summary, "layers_failed")
    if layer_failure_count:
        failed_reasons.append(_plural(layer_failure_count, "layer failed", "layers failed"))

    layers = report.get("layers") if isinstance(report.get("layers"), list) else []
    visual_acceptance_by_layer = _visual_layer_acceptance_by_layer(report)
    no_go_layers = 0
    failed_layers = 0
    review_layers = 0
    missing_payload_layers = 0
    accepted_visual_review_layers = 0
    for layer in layers:
        if not isinstance(layer, dict):
            continue
        layer_name = layer.get("layer")
        layer_status = _normalized_status(layer.get("status"))
        review = layer.get("review") if isinstance(layer.get("review"), dict) else {}
        if layer_status == "no_go":
            no_go_layers += 1
        elif layer_status in {"fail", "failed"}:
            failed_layers += 1
        elif layer_status == "missing_payload":
            missing_payload_layers += 1
        elif layer_status in {"needs_review", "low_confidence"}:
            review_layers += 1
        elif review.get("needs_review") is True:
            if (
                review.get("visual_acceptance_required") is True
                and isinstance(layer_name, str)
                and layer_name in visual_acceptance_by_layer
            ):
                accepted_visual_review_layers += 1
            else:
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
    if layers and accepted_visual_review_layers:
        summary_review_layers = max(0, summary_review_layers - accepted_visual_review_layers)
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
    missing_artifact_tuple = tuple(dict.fromkeys(missing_artifacts))
    return ProofPacketValidation(
        fixture_id=plan.fixture_id,
        status=status,
        public_summary=_build_public_summary(
            fixture_id=plan.fixture_id,
            status=status,
            report=report,
            report_summary=summary,
            reasons=reasons,
            missing_artifacts=missing_artifact_tuple,
        ),
        missing_artifacts=missing_artifact_tuple,
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

    return (
        _dark_pixel_ratio_in_region(
            image,
            rect=rect,
            threshold=threshold,
        )
        >= min_dark_ratio
    )


def _dark_pixel_ratio_in_region(
    image: Image.Image | np.ndarray,
    *,
    rect: tuple[int, int, int, int] | list[int],
    threshold: int = 48,
) -> float:
    """Return the share of dark pixels in a clipped rectangular region."""

    x0, y0, x1, y1 = _validate_rect(rect, "rect")
    array = _as_image_array(image)
    height, width = array.shape[:2]
    x0 = max(0, min(x0, width))
    x1 = max(0, min(x1, width))
    y0 = max(0, min(y0, height))
    y1 = max(0, min(y1, height))
    if x1 <= x0 or y1 <= y0:
        return 0.0

    region = array[y0:y1, x0:x1, :3].astype(np.float32)
    luminance = (0.2126 * region[..., 0]) + (0.7152 * region[..., 1]) + (0.0722 * region[..., 2])
    return float(np.count_nonzero(luminance <= threshold)) / float(luminance.size)


def review_region_pixel_errors(
    image: Image.Image | np.ndarray,
    regions: Sequence[ReviewRegion],
    *,
    before_image: Image.Image | np.ndarray | None = None,
    min_dark_ratio: float = 0.05,
    min_dark_delta: float = 0.0,
    threshold: int = 48,
) -> list[str]:
    """Return visual failure reasons for known review-region expectations."""

    errors: list[str] = []
    for region in regions:
        explicit_min_dark_ratio = region.min_dark_ratio
        required_min_dark_ratio = (
            explicit_min_dark_ratio if explicit_min_dark_ratio is not None else min_dark_ratio
        )
        required_min_dark_delta = region.min_dark_delta if region.min_dark_delta is not None else min_dark_delta
        after_dark_ratio = _dark_pixel_ratio_in_region(
            image,
            rect=region.rect,
            threshold=threshold,
        )
        has_poche = after_dark_ratio >= required_min_dark_ratio
        if region.kind == "poche_presence" and not has_poche:
            if explicit_min_dark_ratio is None:
                errors.append(f"review region {region.id} ({region.kind}) expected dark poché pixels")
            else:
                errors.append(
                    f"review region {region.id} ({region.kind}) expected solid poché dark ratio "
                    f">= {required_min_dark_ratio:.3f}; found {after_dark_ratio:.3f}"
                )
        if region.kind == "poche_presence" and required_min_dark_delta > 0:
            if before_image is None:
                errors.append(
                    f"review region {region.id} ({region.kind}) expected new dark poché delta "
                    f">= {required_min_dark_delta:.3f}; before image unavailable"
                )
                continue
            before_dark_ratio = _dark_pixel_ratio_in_region(
                before_image,
                rect=region.rect,
                threshold=threshold,
            )
            dark_delta = after_dark_ratio - before_dark_ratio
            if dark_delta < required_min_dark_delta:
                errors.append(
                    f"review region {region.id} ({region.kind}) expected new dark poché delta "
                    f">= {required_min_dark_delta:.3f}; before {before_dark_ratio:.3f}, "
                    f"after {after_dark_ratio:.3f}, delta {dark_delta:.3f}"
                )
        elif region.kind == "protected_void" and has_poche:
            errors.append(f"review region {region.id} ({region.kind}) expected light protected void")
    return errors


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
    report: dict[str, Any],
    report_summary: dict[str, Any],
    reasons: tuple[str, ...],
    missing_artifacts: tuple[str, ...],
) -> dict[str, Any]:
    changed = _changed_messages(report_summary)
    skipped = _skipped_messages(report_summary)
    failed = _failed_messages(report_summary, missing_artifacts)
    if not failed and status in {"failed", "no_go"}:
        failed = list(reasons) or [f"raw report status is {status}"]
    public_acceptance = _public_acceptance(report)
    visual_acceptance = _public_visual_acceptance(report)
    public_safe = status == "passed" and bool(public_acceptance["accepted"])
    public_reasons = list(reasons)
    if status == "passed" and not public_safe:
        public_reasons.append("W5/W7 public proof acceptance is not recorded")

    return {
        "fixture_id": fixture_id,
        "status": status,
        "public_safe": public_safe,
        "what_changed": changed,
        "what_skipped": skipped,
        "what_failed": failed,
        "why": public_reasons,
        "next_step": _next_step(status, reasons, public_safe=public_safe),
        "proof_identity": _public_proof_identity(report),
        "rendered_views": _public_rendered_views(report),
        "public_acceptance": public_acceptance,
        "visual_acceptance": visual_acceptance,
    }


def _report_identity_errors(report: dict[str, Any]) -> list[str]:
    source = report.get("source")
    if not isinstance(source, dict):
        return [
            "report source.input is required",
            "report source.output is required",
            "report source.command is required",
        ]

    errors: list[str] = []
    for key in ("input", "output", "command"):
        value = source.get(key)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"report source.{key} is required")
    return errors


def _report_visual_errors(report: dict[str, Any], plan: ProofPacketPlan) -> tuple[list[str], list[str]]:
    visual_artifacts = report.get("visual_artifacts")
    if not isinstance(visual_artifacts, dict):
        return ["visual artifacts mapping is required", "visual artifacts missing rendered view checklist"], []

    errors: list[str] = []
    missing: list[str] = []
    for key in ("before", "after", "diff"):
        value = visual_artifacts.get(key)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"visual_artifacts.{key} is required")
            continue
        if not _artifact_reference_exists(plan, value):
            missing.append(f"visual_artifacts.{key}")

    rendered_views = visual_artifacts.get("rendered_views")
    if not isinstance(rendered_views, list) or not rendered_views:
        errors.append("visual artifacts missing rendered view checklist")
        return errors, missing

    kinds: set[str] = set()
    for index, raw_view in enumerate(rendered_views):
        label = f"visual_artifacts.rendered_views[{index}]"
        if not isinstance(raw_view, dict):
            errors.append(f"{label} must be a mapping")
            continue
        view_id = raw_view.get("id")
        if not isinstance(view_id, str) or not view_id.strip():
            errors.append(f"{label}.id is required")
        kind = raw_view.get("kind")
        if not isinstance(kind, str) or kind not in VALID_RENDERED_VIEW_KINDS:
            expected = ", ".join(sorted(VALID_RENDERED_VIEW_KINDS))
            errors.append(f"{label}.kind must be one of: {expected}")
        else:
            kinds.add(kind)
        for key in ("before", "after", "diff"):
            value = raw_view.get(key)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{label}.{key} is required")
                continue
            if not _artifact_reference_exists(plan, value):
                missing.append(f"{label}.{key}")

    if "full_board" not in kinds:
        errors.append("visual artifacts missing full-board rendered view")
    if not (kinds & _CLOSEUP_RENDERED_VIEW_KINDS):
        errors.append("visual artifacts missing close-up rendered view")
    return errors, missing


def _artifact_reference_exists(plan: ProofPacketPlan, value: str) -> bool:
    if _LOCAL_PATH_RE.search(value):
        return True
    path = _artifact_reference_path(plan, value)
    return path.exists() and path.is_file() and path.stat().st_size > 0


def _artifact_reference_path(plan: ProofPacketPlan, value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = plan.output_dir / path
    return path


def _review_region_pixel_errors(
    report: dict[str, Any],
    plan: ProofPacketPlan,
    review_regions: Sequence[ReviewRegion],
    *,
    min_dark_ratio: float,
    min_dark_delta: float,
    threshold: int,
) -> list[str]:
    rendered_before_paths = _rendered_view_artifact_paths(report, plan, "before")
    rendered_after_paths = _rendered_view_artifact_paths(report, plan, "after")
    errors: list[str] = []
    for region in review_regions:
        after_path = rendered_after_paths.get(region.id)
        if after_path is None:
            errors.append(f"review region {region.id} has no matching rendered view after image")
            continue
        if not after_path.exists() or not after_path.is_file() or after_path.stat().st_size <= 0:
            errors.append(f"review region {region.id} after image is missing")
            continue
        before_path = rendered_before_paths.get(region.id)
        before_image = None
        required_min_dark_delta = region.min_dark_delta if region.min_dark_delta is not None else min_dark_delta
        needs_before_image = region.kind == "poche_presence" and required_min_dark_delta > 0
        try:
            with Image.open(after_path) as after_image:
                if (
                    needs_before_image
                    and before_path is not None
                    and before_path.exists()
                    and before_path.is_file()
                ):
                    with Image.open(before_path) as opened_before_image:
                        before_image = opened_before_image.copy()
                errors.extend(
                    review_region_pixel_errors(
                        after_image,
                        [region],
                        before_image=before_image,
                        min_dark_ratio=min_dark_ratio,
                        min_dark_delta=min_dark_delta,
                        threshold=threshold,
                    )
                )
        except OSError as exc:
            errors.append(f"review region {region.id} after image could not be opened: {exc}")
    return errors


def _rendered_view_artifact_paths(
    report: dict[str, Any],
    plan: ProofPacketPlan,
    artifact_key: str,
) -> dict[str, Path]:
    visual_artifacts = report.get("visual_artifacts") if isinstance(report.get("visual_artifacts"), dict) else {}
    rendered_views = (
        visual_artifacts.get("rendered_views") if isinstance(visual_artifacts.get("rendered_views"), list) else []
    )
    paths: dict[str, Path] = {}
    for raw_view in rendered_views:
        if not isinstance(raw_view, dict):
            continue
        view_id = raw_view.get("id")
        artifact = raw_view.get(artifact_key)
        if not isinstance(view_id, str) or not view_id.strip():
            continue
        if not isinstance(artifact, str) or not artifact.strip() or _LOCAL_PATH_RE.search(artifact):
            continue
        paths[view_id] = _artifact_reference_path(plan, artifact)
    return paths


def _public_proof_identity(report: dict[str, Any]) -> dict[str, str]:
    source = report.get("source") if isinstance(report.get("source"), dict) else {}
    identity: dict[str, str] = {}
    for key in ("input", "output", "command"):
        value = source.get(key)
        if isinstance(value, str) and value.strip() and not _LOCAL_PATH_RE.search(value):
            identity[key] = value
    return identity


def _public_rendered_views(report: dict[str, Any]) -> list[dict[str, str]]:
    visual_artifacts = report.get("visual_artifacts") if isinstance(report.get("visual_artifacts"), dict) else {}
    rendered_views = (
        visual_artifacts.get("rendered_views") if isinstance(visual_artifacts.get("rendered_views"), list) else []
    )
    public_views: list[dict[str, str]] = []
    for raw_view in rendered_views:
        if not isinstance(raw_view, dict):
            continue
        public_view: dict[str, str] = {}
        for key in ("id", "kind", "before", "after", "diff"):
            value = raw_view.get(key)
            if isinstance(value, str) and value.strip() and not _LOCAL_PATH_RE.search(value):
                public_view[key] = value
        if {"id", "kind", "before", "after", "diff"}.issubset(public_view):
            public_views.append(public_view)
    return public_views


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


def _public_acceptance(report: dict[str, Any]) -> dict[str, Any]:
    raw = report.get("review_acceptance")
    if not isinstance(raw, dict):
        return {"accepted": False, "accepted_by": []}

    public_proof = raw.get("public_proof") if isinstance(raw.get("public_proof"), dict) else raw
    accepted_by = _accepted_reviewers(public_proof.get("accepted_by"))
    accepted = public_proof.get("accepted") is True and bool(
        set(accepted_by) & _PUBLIC_ACCEPTANCE_REVIEWERS
    )
    acceptance: dict[str, Any] = {
        "accepted": accepted,
        "accepted_by": accepted_by,
    }
    for key in ("date", "scope"):
        value = public_proof.get(key)
        if isinstance(value, str) and value.strip() and not _LOCAL_PATH_RE.search(value):
            acceptance[key] = value
    return acceptance


def _public_visual_acceptance(report: dict[str, Any]) -> dict[str, Any]:
    accepted = _visual_layer_acceptance_by_layer(report)
    accepted_by = sorted(
        {
            reviewer
            for acceptance in accepted.values()
            for reviewer in acceptance.get("accepted_by", [])
            if isinstance(reviewer, str)
        }
    )
    return {
        "accepted_layer_count": len(accepted),
        "accepted_by": accepted_by,
    }


def _visual_layer_acceptance_by_layer(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw = report.get("review_acceptance")
    if not isinstance(raw, dict):
        return {}

    visual_layer_gates = raw.get("visual_layer_gates")
    if not isinstance(visual_layer_gates, list):
        return {}

    eligible_layers = _visual_acceptance_eligible_layers(report)
    if not eligible_layers:
        return {}

    accepted: dict[str, dict[str, Any]] = {}
    for entry in visual_layer_gates:
        if not isinstance(entry, dict):
            continue
        layer = entry.get("layer")
        if not isinstance(layer, str) or not layer.strip() or _LOCAL_PATH_RE.search(layer):
            continue
        if layer not in eligible_layers:
            continue
        if entry.get("accepted") is not True:
            continue
        accepted_by = _accepted_reviewers(entry.get("accepted_by"))
        if not accepted_by:
            continue
        existing = accepted.setdefault(layer, {"accepted_by": []})
        for reviewer in accepted_by:
            if reviewer not in existing["accepted_by"]:
                existing["accepted_by"].append(reviewer)
    return accepted


def _visual_acceptance_eligible_layers(report: dict[str, Any]) -> set[str]:
    layers = report.get("layers") if isinstance(report.get("layers"), list) else []
    eligible_layers: set[str] = set()
    for layer in layers:
        if not isinstance(layer, dict):
            continue
        layer_name = layer.get("layer")
        if not isinstance(layer_name, str) or not layer_name.strip() or _LOCAL_PATH_RE.search(layer_name):
            continue
        layer_status = _normalized_status(layer.get("status"))
        if layer_status in {"no_go", "fail", "failed", "missing_payload", "needs_review", "low_confidence"}:
            continue
        review = layer.get("review") if isinstance(layer.get("review"), dict) else {}
        if review.get("needs_review") is True and review.get("visual_acceptance_required") is True:
            eligible_layers.add(layer_name)
    return eligible_layers


def _accepted_reviewers(value: Any) -> list[str]:
    raw_reviewers = value if isinstance(value, list) else [value]
    reviewers: list[str] = []
    for reviewer in raw_reviewers:
        if not isinstance(reviewer, str):
            continue
        normalized = reviewer.strip().upper()
        if normalized in _PUBLIC_ACCEPTANCE_REVIEWERS and normalized not in reviewers:
            reviewers.append(normalized)
    return reviewers


def _next_step(status: str, reasons: tuple[str, ...], *, public_safe: bool = False) -> str:
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
    if status == "passed" and not public_safe:
        return "Get explicit W5/W7 acceptance before treating this packet as public proof."
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
    rendered_views = _parse_rendered_views(raw.get("rendered_views"), fixture_id)
    return VisualArtifacts(
        before=Path(_required_str(raw, "before", f"{fixture_id}.visual_artifacts")),
        after=Path(_required_str(raw, "after", f"{fixture_id}.visual_artifacts")),
        diff=Path(_required_str(raw, "diff", f"{fixture_id}.visual_artifacts")),
        rendered_views=rendered_views,
    )


def _parse_rendered_views(raw: Any, fixture_id: str) -> list[RenderedView]:
    label = f"{fixture_id}.visual_artifacts.rendered_views"
    if not isinstance(raw, list) or not raw:
        raise ManifestValidationError(f"{label} must include full_board and close-up rendered views")

    views: list[RenderedView] = []
    kinds: set[str] = set()
    for index, item in enumerate(raw):
        item_label = f"{label}[{index}]"
        if not isinstance(item, dict):
            raise ManifestValidationError(f"{item_label} must be a mapping")
        kind = _required_status(item, "kind", item_label, VALID_RENDERED_VIEW_KINDS)
        kinds.add(kind)
        views.append(
            RenderedView(
                id=_required_str(item, "id", item_label),
                kind=kind,
                before=Path(_required_str(item, "before", item_label)),
                after=Path(_required_str(item, "after", item_label)),
                diff=Path(_required_str(item, "diff", item_label)),
            )
        )

    if "full_board" not in kinds:
        raise ManifestValidationError(f"{label} must include a full_board rendered view")
    if not (kinds & _CLOSEUP_RENDERED_VIEW_KINDS):
        raise ManifestValidationError(f"{label} must include at least one close-up rendered view")
    return views


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
                min_dark_ratio=_optional_ratio(item.get("min_dark_ratio"), f"{label}.min_dark_ratio"),
                min_dark_delta=_optional_ratio(item.get("min_dark_delta"), f"{label}.min_dark_delta"),
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


def _optional_ratio(value: Any, label: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ManifestValidationError(f"{label} must be a number between 0 and 1")
    ratio = float(value)
    if ratio < 0 or ratio > 1:
        raise ManifestValidationError(f"{label} must be a number between 0 and 1")
    return ratio


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
