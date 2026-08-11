"""Shared fixtures for the health and permanently-disabled web routes."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

# We import the factory rather than the module-level ``app`` so each test
# gets a fresh instance with its own state.
from backend.config import Settings, get_settings
from backend.main import create_app


@pytest.fixture
def settings(tmp_path) -> Settings:
    """Settings for an app with no mounted processing storage."""
    return Settings(
        storage_root=tmp_path / "archlw-test",
        max_upload_bytes=5 * 1024 * 1024,
        cors_origins=["http://localhost:5173"],
        local_api_capability="test-capability",
        job_runner="sync",
    )


@pytest.fixture
def app_client(settings: Settings):
    """FastAPI TestClient for health and tombstone contract checks."""
    app = create_app()
    app.state.settings = settings
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(
        app,
        client=("127.0.0.1", 50000),
        headers={
            "Origin": "http://localhost:5173",
            "X-Archlw-Capability": settings.local_api_capability or "",
        },
    ) as client:
        yield client, app
    app.dependency_overrides.clear()
