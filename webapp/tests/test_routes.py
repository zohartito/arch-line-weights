"""HTTP contract tests for the health route and retired processing routes."""

from __future__ import annotations

import pytest

from backend.config import Settings, local_vite_cors_origins


def test_health_returns_200(app_client) -> None:
    client, _app = app_client
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "arch-line-weights-webapp"


def test_default_cors_allows_local_vite_fallback_ports(monkeypatch) -> None:
    monkeypatch.delenv("ARCHLW_CORS_ORIGINS", raising=False)
    assert local_vite_cors_origins() == Settings().cors_origins


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/api/jobs"),
        ("post", "/api/jobs"),
        ("get", "/api/jobs/any-id"),
        ("post", "/api/jobs/any-id/retry"),
        ("get", "/api/console"),
        ("post", "/api/console/runs"),
        ("get", "/api/console/runs/any-id"),
        ("post", "/api/console/runs/any-id/stages/inspect_file"),
    ],
)
def test_processing_routes_are_permanently_gone(app_client, method: str, path: str) -> None:
    """The mount-level tombstone responds before body parsing or storage setup."""
    client, app = app_client
    response = client.request(method.upper(), path, content=b"not a multipart upload")
    assert response.status_code == 410
    assert response.json() == {"detail": "web processing is permanently disabled"}
    assert not hasattr(app.state, "job_store")
    assert not hasattr(app.state, "storage")
