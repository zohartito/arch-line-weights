"""Geometry-only role inference for low-semantic linework."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from itertools import pairwise
from statistics import median

from .role_ladder import Role

Point = tuple[float, float]


@dataclass(frozen=True)
class GeometryPath:
    path_id: str
    points: list[Point]


@dataclass(frozen=True)
class GeometryRoleAssignment:
    path_id: str
    role: Role
    confidence: float
    explanation: str
    needs_review: bool
    metrics: dict[str, float | int | bool] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "path_id": self.path_id,
            "role": self.role.value,
            "confidence": round(float(self.confidence), 3),
            "explanation": self.explanation,
            "needs_review": self.needs_review,
            "metrics": dict(self.metrics),
        }


@dataclass(frozen=True)
class _PathMetrics:
    length: float
    closed: bool
    area: float
    bbox_width: float
    bbox_height: float
    angle_change_count: int


def _distance(a: Point, b: Point) -> float:
    return math.hypot(b[0] - a[0], b[1] - a[1])


def _path_length(points: list[Point]) -> float:
    return sum(_distance(a, b) for a, b in pairwise(points))


def _polygon_area(points: list[Point]) -> float:
    if len(points) < 4:
        return 0.0
    total = 0.0
    for a, b in pairwise(points):
        total += a[0] * b[1] - b[0] * a[1]
    return abs(total) / 2.0


def _angle_change_count(points: list[Point]) -> int:
    count = 0
    for a, b, c in zip(points, points[1:], points[2:], strict=False):
        v1 = (b[0] - a[0], b[1] - a[1])
        v2 = (c[0] - b[0], c[1] - b[1])
        len1 = math.hypot(*v1)
        len2 = math.hypot(*v2)
        if len1 == 0 or len2 == 0:
            continue
        dot = (v1[0] * v2[0] + v1[1] * v2[1]) / (len1 * len2)
        dot = max(-1.0, min(1.0, dot))
        angle = math.degrees(math.acos(dot))
        if 45 <= angle <= 135:
            count += 1
    return count


def _metrics(points: list[Point]) -> _PathMetrics:
    if not points:
        return _PathMetrics(0.0, False, 0.0, 0.0, 0.0, 0)
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    closed = len(points) >= 4 and _distance(points[0], points[-1]) <= 1e-6
    return _PathMetrics(
        length=_path_length(points),
        closed=closed,
        area=_polygon_area(points) if closed else 0.0,
        bbox_width=max(xs) - min(xs),
        bbox_height=max(ys) - min(ys),
        angle_change_count=_angle_change_count(points),
    )


def _assignment(
    path: GeometryPath,
    role: Role,
    confidence: float,
    explanation: str,
    metrics: _PathMetrics,
) -> GeometryRoleAssignment:
    return GeometryRoleAssignment(
        path_id=path.path_id,
        role=role,
        confidence=round(confidence, 3),
        explanation=explanation,
        needs_review=confidence < 0.65,
        metrics={
            "length": round(metrics.length, 3),
            "closed": metrics.closed,
            "area": round(metrics.area, 3),
            "bbox_width": round(metrics.bbox_width, 3),
            "bbox_height": round(metrics.bbox_height, 3),
            "angle_change_count": metrics.angle_change_count,
        },
    )


def infer_geometric_roles(paths: list[GeometryPath]) -> list[GeometryRoleAssignment]:
    """Infer semantic roles from geometry when color/layer hierarchy is absent.

    This is intentionally conservative. Dominant closed loops can become cut
    profiles, dominant open profiles can become silhouettes, right-angle bends
    become planar corners, mid-length simple linework becomes surface/material,
    and tiny strokes become layout/reference. If the corpus has no dominant
    geometry, assignments are review-flagged rather than overconfident.
    """

    metrics_by_id = {path.path_id: _metrics(path.points) for path in paths}
    lengths = [m.length for m in metrics_by_id.values() if m.length > 0]
    if not lengths:
        return [
            _assignment(path, Role.LAYOUT, 0.2, "empty or zero-length geometry", metrics_by_id[path.path_id])
            for path in paths
        ]

    max_length = max(lengths)
    open_lengths = [m.length for m in metrics_by_id.values() if m.length > 0 and not m.closed]
    max_open_length = max(open_lengths) if open_lengths else max_length
    median_length = median(lengths)
    dominant_ratio = max_length / max(median_length, 1e-6)
    has_dominant = dominant_ratio >= 1.5

    out: list[GeometryRoleAssignment] = []
    for path in paths:
        m = metrics_by_id[path.path_id]
        relative = m.length / max(max_length, 1e-6)
        if m.closed and m.area > 0 and relative >= 0.45:
            conf = 0.88 if has_dominant else 0.72
            out.append(
                _assignment(path, Role.CUT_PROFILE, conf, "closed dominant loop suggests cut profile", m)
            )
        elif m.length <= max(4.0, max_length * 0.05):
            conf = 0.70 if has_dominant else 0.55
            out.append(
                _assignment(path, Role.LAYOUT, conf, "tiny isolated stroke suggests layout/reference", m)
            )
        elif m.angle_change_count > 0 and relative >= 0.15:
            conf = 0.76 if has_dominant else 0.58
            out.append(
                _assignment(path, Role.PLANAR_CORNER, conf, "right-angle bend suggests planar corner", m)
            )
        elif has_dominant and not m.closed and m.length >= max_open_length * 0.70:
            out.append(
                _assignment(path, Role.SPATIAL_EDGE, 0.78, "dominant open profile suggests silhouette", m)
            )
        elif has_dominant and relative >= 0.12:
            out.append(
                _assignment(path, Role.SURFACE, 0.70, "mid-length linework suggests surface/material", m)
            )
        else:
            out.append(
                _assignment(
                    path,
                    Role.SURFACE,
                    0.45,
                    "ambiguous geometry without dominant role signal; manual review required",
                    m,
                )
            )
    return out


__all__ = ["GeometryPath", "GeometryRoleAssignment", "infer_geometric_roles"]
