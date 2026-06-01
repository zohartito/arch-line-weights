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

from .compute import JobStore
from .config import get_settings
from .console import DesignerConsoleStore, default_console_root
from .routes.console import router as console_router
from .routes.health import router as health_router
from .routes.jobs import router as jobs_router
from .storage import LocalStorage

logger = logging.getLogger("archlw.webapp")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Wire singletons (storage backend, in-memory job store) onto app.state.

    Using lifespan instead of module-level globals lets tests build their own
    app via ``create_app(...)`` with isolated state per run.
    """
    settings = get_settings()
    settings.storage_root.mkdir(parents=True, exist_ok=True)
    app.state.settings = settings
    app.state.storage = LocalStorage(settings.storage_root)
    app.state.job_store = JobStore()
    app.state.console_store = DesignerConsoleStore(default_console_root(settings.storage_root))
    logger.info(
        "archlw webapp ready: storage_root=%s job_runner=%s",
        settings.storage_root,
        settings.job_runner,
    )
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

    # Browser dev (SvelteKit on :5173) talks to FastAPI on :8000 — same host
    # but different ports => CORS preflight. We trust only the configured
    # origin list; ``allow_credentials=True`` because magic-link cookies
    # are coming in a later phase.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router, prefix="/api")
    app.include_router(jobs_router)
    app.include_router(console_router)

    return app


# Module-level instance for ``uvicorn main:app``.
app = create_app()
