"""Pydantic schemas — request/response shapes for the REST API.

Kept deliberately small. The compute side (apply_saas / poche_saas) returns
dataclasses; we map those into these models inside ``compute.py`` so the
schemas stay decoupled from the pipeline internals.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Lifecycle states. PENDING -> RUNNING -> (DONE | FAILED)."""

    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


# Literal aliases mirror the CLI's ``click.Choice`` vocabularies so the API
# rejects unknown values up-front (FastAPI returns 422 for any value outside
# the Literal). Update these if the CLI grows new options.
PresetName = Literal["section", "plan", "elevation", "detail"]
ScaleName = Literal["1/16", "1/8", "1/4", "1/2", "1", "3", "full"]
BridgeStrategy = Literal["greedy", "best"]
SourceName = Literal["auto", "rhino", "autocad"]


class JobOptions(BaseModel):
    """Per-request pipeline knobs. Mirror the ``arch-lw apply-saas`` flags.

    Field defaults match the CLI defaults so a bare ``POST /api/jobs``
    behaves identically to ``arch-lw apply-saas <file> --auto``.
    """

    preset: PresetName = "section"
    scale: ScaleName = "1/4"
    for_print: bool = False
    with_poche: bool = True
    default_width: float = 0.25
    # v0.5.x + v0.6.x flags surfaced through the API. Keep names symmetrical
    # with the CLI (``poche_saas.apply_saas_with_poche`` kwargs and
    # ``cli.apply_saas_cmd`` click options) so the docs map 1-to-1.
    bridge_strategy: BridgeStrategy = "best"
    alpha_shape: bool = True
    llm_fallback: bool = False
    source: SourceName = "auto"


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
    """Returned by ``GET /api/jobs/{id}``. Polled by the frontend until DONE.

    ``flags_applied`` echoes back the resolved options so a debugging client
    can confirm exactly which knobs the pipeline ran with — useful when an
    upload comes from a form that left some fields empty / used defaults.
    """

    job_id: str
    status: JobStatus
    created_at: datetime
    finished_at: datetime | None = None
    original_filename: str
    options: JobOptions
    apply_summary: ApplySummary | None = None
    poche_summary: PocheSummary | None = None
    fills: list[FillSummary] = Field(default_factory=list)
    flags_applied: dict[str, Any] = Field(default_factory=dict)
    download_url: str | None = None
    error: str | None = None
