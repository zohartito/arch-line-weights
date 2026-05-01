"""Health check — used by Fly.io's HTTP health probe and the frontend's
sanity ping. Returns 200 + a small JSON blob; never reads storage or DB.
"""

from __future__ import annotations

from fastapi import APIRouter

from .. import __version__

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness probe. Always 200 unless the worker is fully wedged."""
    return {"status": "ok", "version": __version__, "service": "arch-line-weights-webapp"}
