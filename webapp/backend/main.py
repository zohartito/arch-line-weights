"""FastAPI application entry point.

Run locally:

    cd webapp/backend
    uvicorn main:app --reload

Production runs the same module with ``uvicorn`` behind a Fly.io proxy.
The app stays purely sync at the request level (no async I/O against
external services yet); all CPU-heavy work is dispatched via
``run_in_threadpool`` inside the routes.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routes.health import router as health_router

logger = logging.getLogger("archlw.webapp")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Wire singletons (storage backend, in-memory job store) onto app.state.

    Using lifespan instead of module-level globals lets tests build their own
    app via ``create_app(...)`` with isolated state per run.
    """
    settings = get_settings()
    app.state.settings = settings
    logger.info("archlw webapp ready: processing routes tombstoned")
    try:
        yield
    finally:
        # Nothing to flush in the scaffold. Production drains the queue +
        # closes the DB pool here.
        pass


def create_app() -> FastAPI:
    """Factory used by both ``uvicorn main:app`` and tests.

    Tests can replace state in two ways:
       1. ``app.state.storage = LocalStorage(tmp_path)`` after construction
       2. ``app.dependency_overrides[get_settings] = lambda: TestSettings(...)``
    """
    settings = get_settings()
    app = FastAPI(
        title="arch-line-weights webapp",
        version="0.0.1",
        description="Apply architectural line-weight hierarchy + poché to .ai / .pdf",
        lifespan=lifespan,
    )

    # Browser dev (SvelteKit starts on :5173 and may shift upward when that
    # port is occupied) talks to FastAPI on :8000 — same host but different
    # ports => CORS preflight. We trust only the configured origin list;
    # ``allow_credentials=True`` because magic-link cookies are coming in a
    # later phase.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router, prefix="/api")

    # Upload and designer-console processing are intentionally not mounted.
    # This check runs before FastAPI can parse multipart bodies or allocate
    # per-run storage. Re-enable only with a reviewed authenticated service.
    @app.api_route("/api/jobs/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    @app.api_route("/api/jobs", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    @app.api_route("/api/console/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    @app.api_route("/api/console", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    async def processing_tombstone(path: str = "") -> None:
        from fastapi import HTTPException

        raise HTTPException(status_code=410, detail="web processing is permanently disabled")

    return app


# Module-level instance for ``uvicorn main:app``.
app = create_app()
