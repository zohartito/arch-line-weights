"""Shared test fixtures for the webapp backend.

Each test gets its own temp storage root so jobs don't leak across runs.
We use the synthetic .ai writer from ``poche_saas.write_synthetic_test_ai``
to exercise the full pipeline without needing a real Rhino export checked
in to the repo.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# We import the factory rather than the module-level ``app`` so each test
# gets a fresh instance with its own state.
from backend.compute import JobStore
from backend.config import Settings, get_settings
from backend.main import create_app
from backend.storage import LocalStorage


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """Per-test settings with an isolated storage root and small upload cap.

    The 5 MB cap keeps the 413-overflow test cheap while still letting the
    full synthetic .ai (~1 KB compressed) flow through unimpeded.
    """
    return Settings(
        storage_root=tmp_path / "archlw-test",
        max_upload_bytes=5 * 1024 * 1024,
        cors_origins=["http://localhost:5173"],
        job_runner="sync",
    )


@pytest.fixture
def app_client(settings: Settings):
    """FastAPI TestClient with isolated state.

    Overrides ``get_settings`` so the singleton cache from prior tests can't
    leak into this one. Yields ``(client, app)`` so individual tests can
    poke ``app.state`` if they want to swap storage mid-test.
    """
    app = create_app()
    # Replace state assembled by lifespan with our test-scoped versions.
    app.state.settings = settings
    app.state.storage = LocalStorage(settings.storage_root)
    app.state.job_store = JobStore()
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as client:
        yield client, app
    app.dependency_overrides.clear()


@pytest.fixture
def synthetic_ai(tmp_path: Path) -> Path:
    """Write a tiny .ai fixture and return its path.

    The fixture exercises the AI24 native payload path used by ``apply_saas``
    + ``poche_saas`` without requiring a real Rhino export. The cut-layer
    name matches the ``ClippingPlaneIntersections`` filter so the poché
    pipeline picks it up.
    """
    from arch_line_weights.poche_saas import write_synthetic_test_ai

    path = tmp_path / "synthetic.ai"
    write_synthetic_test_ai(
        path,
        layer_name="WALL::ClippingPlaneIntersections::Default",
    )
    return path
