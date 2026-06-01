"""Settings — env-var-driven config for the webapp scaffold.

Everything that would change per-environment (storage root, max upload size,
default poché on/off, allowed CORS origins) lives here. Production deploy
swaps these via env vars without touching code. Pydantic-settings v2 picks up
``ARCHLW_*`` env vars automatically.
"""

from __future__ import annotations

import os
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. All fields overridable via ARCHLW_* env vars."""

    model_config = SettingsConfigDict(
        env_prefix="ARCHLW_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Storage root for uploads + outputs. In production this becomes a Tigris
    # bucket prefix; locally we fall back to a tempdir so tests don't pollute
    # the developer's home directory.
    storage_root: Path = Field(
        default_factory=lambda: Path(
            os.environ.get("ARCHLW_STORAGE_ROOT")
            or str(Path(tempfile.gettempdir()) / "archlw-webapp")
        )
    )

    # Maximum upload size in bytes. 50 MB matches the Phase D research note
    # which capped real-world Rhino-export sizes around 30 MB.
    max_upload_bytes: int = 50 * 1024 * 1024

    # CORS — broad in dev, narrow in prod. Comma-separated origin list.
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    # Default pipeline knobs. The frontend can override per-request.
    default_preset: str = "section"
    default_scale: str = "1/4"
    default_for_print: bool = False
    default_with_poche: bool = True

    # Whether the upload route runs the pipeline synchronously (current
    # scaffold) or hands off to a queue. Set to "queue" once Redis+RQ is wired.
    job_runner: str = "sync"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor. FastAPI deps and tests both go through this."""
    return Settings()
