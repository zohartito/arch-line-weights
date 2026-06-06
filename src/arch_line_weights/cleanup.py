"""Conservative path-level cleanup for low-semantic one-layer drawings."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import pikepdf

from .apply_saas import _read_payload, _write_payload

_NUM = rb"[0-9.eE\-+]+"
_LN_RE = re.compile(rb"\(([^)]+)\) Ln$")
_PATH_OPS = {b"m", b"L", b"l", b"C", b"c"}
_STROKE_OPS = {b"S", b"s", b"B", b"B*", b"b", b"b*"}


@dataclass(frozen=True)
class CleanupThresholds:
    debris_max_pt: float = 1.0
    detail_max_pt: float = 24.0
    profile_min_pt: float = 96.0
    detail_weight_pt: float = 0.18
    medium_weight_pt: float = 0.25
    profile_weight_pt: float = 0.5


@dataclass
class CleanupLayerReport:
    name: str
    stroked_paths: int = 0
    deleted: int = 0
    duplicates: int = 0
    lightened: int = 0
    medium: int = 0
    heavy: int = 0
    unchanged: int = 0
    uncertain: int = 0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "stroked_paths": self.stroked_paths,
            "deleted": self.deleted,
            "duplicates": self.duplicates,
            "lightened": self.lightened,
            "medium": self.medium,
            "heavy": self.heavy,
            "unchanged": self.unchanged,
            "uncertain": self.uncertain,
        }


@dataclass
class CleanupReport:
    layers: list[CleanupLayerReport] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        summary = {
            "layers": len(self.layers),
            "low_semantic": bool(self.warnings),
            "stroked_paths": sum(layer.stroked_paths for layer in self.layers),
            "deleted": sum(layer.deleted for layer in self.layers),
            "duplicates": sum(layer.duplicates for layer in self.layers),
            "lightened": sum(layer.lightened for layer in self.layers),
            "medium": sum(layer.medium for layer in self.layers),
            "heavy": sum(layer.heavy for layer in self.layers),
            "unchanged": sum(layer.unchanged for layer in self.layers),
            "uncertain": sum(layer.uncertain for layer in self.layers),
        }
        return {
            "summary": summary,
            "warnings": list(self.warnings),
            "layers": [layer.to_dict() for layer in self.layers],
        }


@dataclass
class CleanupPayloadResult:
    payload: bytes
    report: CleanupReport


@dataclass
class CleanupFileResult:
    output_size: int
    input_size: int
    report: CleanupReport


def default_output_path(src: str | os.PathLike[str]) -> str:
    path = Path(src)
    return str(path.with_name(f"{path.stem} CLEANUP{path.suffix}"))


def cleanup_payload(
    payload: bytes,
    *,
    thresholds: CleanupThresholds | None = None,
) -> CleanupPayloadResult:
    """Rewrite clear path strokes by path length and delete only tiny dust."""
    thresholds = thresholds or CleanupThresholds()
    lines = payload.split(b"\r")
    out: list[bytes] = []
    reports_by_layer: dict[str, CleanupLayerReport] = {}
    seen_paths_by_layer: dict[str, set[tuple[tuple[float, float], ...]]] = {}

    in_layer = False
    current_layer: str | None = None
    current_path: list[bytes] = []
    current_points: list[tuple[float, float]] = []

    def layer_report() -> CleanupLayerReport:
        nonlocal current_layer
        name = current_layer or "<unknown>"
        if name not in reports_by_layer:
            reports_by_layer[name] = CleanupLayerReport(name=name)
        return reports_by_layer[name]

    def layer_seen_paths() -> set[tuple[tuple[float, float], ...]]:
        name = current_layer or "<unknown>"
        return seen_paths_by_layer.setdefault(name, set())

    def flush_current_path() -> None:
        nonlocal current_path, current_points
        if current_path:
            out.extend(current_path)
            if in_layer:
                layer_report().uncertain += 1
        current_path = []
        current_points = []

    for line in lines:
        if line == b"%AI5_BeginLayer":
            flush_current_path()
            in_layer = True
            current_layer = None
            out.append(line)
            continue

        ln_match = _LN_RE.match(line)
        if in_layer and ln_match:
            flush_current_path()
            current_layer = ln_match.group(1).decode("utf-8", errors="replace")
            layer_report()
            out.append(line)
            continue

        if in_layer and line == b"LB":
            flush_current_path()
            out.append(line)
            in_layer = False
            current_layer = None
            continue

        if in_layer:
            parsed = _parse_path_point(line)
            if parsed is not None:
                op, point = parsed
                if op == b"m" and current_path:
                    flush_current_path()
                current_path.append(line)
                current_points.append(point)
                continue

            if line in _STROKE_OPS and current_path:
                _emit_classified_path(
                    out,
                    report=layer_report(),
                    path_lines=current_path,
                    points=current_points,
                    stroke_op=line,
                    thresholds=thresholds,
                    seen_paths=layer_seen_paths(),
                )
                current_path = []
                current_points = []
                continue

        flush_current_path()
        out.append(line)

    rewritten = b"\r".join(out)
    if payload.endswith(b"\r") and not rewritten.endswith(b"\r"):
        rewritten += b"\r"

    report = CleanupReport(layers=list(reports_by_layer.values()))
    if len(report.layers) <= 1 and report.layers:
        report.warnings.append(
            "single/low-semantic layer hierarchy detected; path-length cleanup was applied conservatively"
        )
    return CleanupPayloadResult(payload=rewritten, report=report)


def cleanup_file(
    src: str | os.PathLike[str],
    dst: str | os.PathLike[str],
    *,
    thresholds: CleanupThresholds | None = None,
    zstd_level: int = 19,
) -> CleanupFileResult:
    """Apply cleanup to an Illustrator-native .ai payload and save a new file."""
    src_path = os.fspath(src)
    dst_path = os.fspath(dst)
    if os.path.abspath(src_path) == os.path.abspath(dst_path):
        raise ValueError("dst must differ from src to keep the original safe")

    input_size = os.path.getsize(src_path)
    with pikepdf.open(src_path, allow_overwriting_input=False) as pdf:
        payload = _read_payload(pdf)
        cleaned = cleanup_payload(payload, thresholds=thresholds)
        _write_payload(pdf, cleaned.payload, level=zstd_level)
        pdf.save(dst_path)

    return CleanupFileResult(
        output_size=os.path.getsize(dst_path),
        input_size=input_size,
        report=cleaned.report,
    )


def _parse_path_point(line: bytes) -> tuple[bytes, tuple[float, float]] | None:
    parts = line.split()
    if not parts:
        return None
    op = parts[-1]
    if op not in _PATH_OPS:
        return None
    if op in {b"m", b"L", b"l"} and len(parts) >= 3:
        try:
            return op, (float(parts[-3]), float(parts[-2]))
        except ValueError:
            return None
    if op in {b"C", b"c"} and len(parts) >= 7:
        try:
            return op, (float(parts[-3]), float(parts[-2]))
        except ValueError:
            return None
    return None


def _path_length(points: list[tuple[float, float]]) -> float:
    if len(points) < 2:
        return 0.0
    total = 0.0
    last = points[0]
    for point in points[1:]:
        total += ((point[0] - last[0]) ** 2 + (point[1] - last[1]) ** 2) ** 0.5
        last = point
    return total


def _format_weight(weight: float) -> bytes:
    if weight == int(weight):
        return f"{int(weight)}".encode("ascii")
    return f"{weight:g}".encode("ascii")


def _canonical_path(points: list[tuple[float, float]]) -> tuple[tuple[float, float], ...]:
    rounded = tuple((round(x, 4), round(y, 4)) for x, y in points)
    reversed_path = tuple(reversed(rounded))
    return min(rounded, reversed_path)


def _emit_classified_path(
    out: list[bytes],
    *,
    report: CleanupLayerReport,
    path_lines: list[bytes],
    points: list[tuple[float, float]],
    stroke_op: bytes,
    thresholds: CleanupThresholds,
    seen_paths: set[tuple[tuple[float, float], ...]],
) -> None:
    length = _path_length(points)
    report.stroked_paths += 1
    canonical = _canonical_path(points)

    if canonical in seen_paths:
        report.deleted += 1
        report.duplicates += 1
        return
    seen_paths.add(canonical)

    if length <= thresholds.debris_max_pt:
        report.deleted += 1
        return
    if length < thresholds.detail_max_pt:
        report.lightened += 1
        out.append(_format_weight(thresholds.detail_weight_pt) + b" w")
    elif length < thresholds.profile_min_pt:
        report.medium += 1
        out.append(_format_weight(thresholds.medium_weight_pt) + b" w")
    else:
        report.heavy += 1
        out.append(_format_weight(thresholds.profile_weight_pt) + b" w")

    out.extend(path_lines)
    out.append(stroke_op)


__all__ = [
    "CleanupFileResult",
    "CleanupLayerReport",
    "CleanupPayloadResult",
    "CleanupReport",
    "CleanupThresholds",
    "cleanup_file",
    "cleanup_payload",
    "default_output_path",
]
