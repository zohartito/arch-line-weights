"""The retired designer console has one stable HTTP 410 contract."""

from __future__ import annotations

import pytest


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/api/console"),
        ("post", "/api/console/runs"),
        ("get", "/api/console/runs/run-1"),
        ("post", "/api/console/runs/run-1/stages/run_layout"),
        ("delete", "/api/console/runs/run-1"),
    ],
)
def test_console_routes_are_tombstoned(app_client, method: str, path: str) -> None:
    client, app = app_client
    response = client.request(method.upper(), path, content=b"untrusted input")
    assert response.status_code == 410
    assert response.json() == {"detail": "web processing is permanently disabled"}
    assert not hasattr(app.state, "console_store")
