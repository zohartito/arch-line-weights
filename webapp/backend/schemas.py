"""Pydantic schemas — request/response shapes for the REST API.

Kept deliberately small. The compute side (apply_saas / poche_saas) returns
dataclasses; we map those into these models inside ``compute.py`` so the
schemas stay decoupled from the pipeline internals.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Lifecycle states. PENDING -> RUNNING -> (DONE | FAILED)."""

    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class JobOptions(BaseModel):
    """Per-request pipeline knobs. Mirror the ``arch-lw apply-saas`` flags."""

    preset: str = "section"
    scale: str = "1/4"
    for_print: bool = False
    with_poche: bool = True
    default_width: float = 0.25


class FillSummary(BaseModel):
    """One row of the poché report (per cut layer).

    Mirrors :class:`arch_line_weights.poche.FillResult` but flat for JSON.
    Frontend renders these as a small table on the job-detail page.
    """

    layer: str
    strategy: str
    confidence: float
    polygon_count: int
    segment_count: int


class ApplySummary(BaseModel):
    """Counters from the stroke-width rewrite (B6) pipeline."""

    xa_seen: int
    widths_rewritten: int
    payload_size_in: int
    payload_size_out: int
    chunks_in: int
    chunks_out: int
    output_size: int
    input_size: int


class PocheSummary(BaseModel):
    """Counters from the poché injection (B7) pipeline."""

    layers_targeted: int
    layers_injected: int
    polygons_injected: int
    bytes_injected: int
    layers_missing: list[str] = Field(default_factory=list)


class JobCreated(BaseModel):
    """Returned by ``POST /api/jobs`` so the client can redirect to the job page."""

    job_id: str
    status: JobStatus


class JobDetail(BaseModel):
    """Returned by ``GET /api/jobs/{id}``. Polled by the frontend until DONE."""

    job_id: str
    status: JobStatus
    created_at: datetime
    finished_at: datetime | None = None
    original_filename: str
    options: JobOptions
    apply_summary: ApplySummary | None = None
    poche_summary: PocheSummary | None = None
    fills: list[FillSummary] = Field(default_factory=list)
    download_url: str | None = None
    error: str | None = None
