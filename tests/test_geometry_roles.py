from __future__ import annotations

from arch_line_weights.geometry_roles import GeometryPath, infer_geometric_roles
from arch_line_weights.role_ladder import Role


def test_geometry_role_inference_covers_small_no_color_fixture_corpus() -> None:
    assignments = infer_geometric_roles(
        [
            GeometryPath("closed-cut", [(0, 0), (100, 0), (100, 60), (0, 60), (0, 0)]),
            GeometryPath("silhouette", [(0, -10), (120, -10)]),
            GeometryPath("corner", [(10, 10), (35, 10), (35, 35)]),
            GeometryPath("surface-joint", [(0, 20), (70, 20)]),
            GeometryPath("reference", [(0, 0), (3, 0)]),
        ]
    )
    by_name = {assignment.path_id: assignment for assignment in assignments}

    assert by_name["closed-cut"].role is Role.CUT_PROFILE
    assert by_name["closed-cut"].confidence >= 0.8
    assert "closed" in by_name["closed-cut"].explanation

    assert by_name["silhouette"].role is Role.SPATIAL_EDGE
    assert by_name["silhouette"].confidence >= 0.7

    assert by_name["corner"].role is Role.PLANAR_CORNER
    assert "corner" in by_name["corner"].explanation

    assert by_name["surface-joint"].role is Role.SURFACE
    assert by_name["reference"].role is Role.LAYOUT


def test_ambiguous_geometry_is_flagged_for_review_instead_of_confident_guess() -> None:
    assignments = infer_geometric_roles(
        [
            GeometryPath("a", [(0, 0), (20, 0)]),
            GeometryPath("b", [(0, 10), (20, 10)]),
            GeometryPath("c", [(0, 20), (20, 20)]),
        ]
    )

    assert all(assignment.needs_review for assignment in assignments)
    assert all(assignment.confidence < 0.65 for assignment in assignments)
    assert {assignment.role for assignment in assignments} == {Role.SURFACE}
