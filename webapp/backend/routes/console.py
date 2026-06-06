"""Designer-console API routes.

These routes are local-prototype-only and live beside the older all-in-one
``/api/jobs`` scaffold. The browser gets public-safe summaries; raw reports
stay under the local storage root.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

from ..config import get_settings
from ..console import CONSOLE_GUARDRAILS, DesignerConsoleStore, default_console_root

router = APIRouter(prefix="/api/console", tags=["designer-console"])


def get_console_store(request: Request) -> DesignerConsoleStore:
    store = getattr(request.app.state, "console_store", None)
    if store is not None:
        return store
    settings = get_settings()
    store = DesignerConsoleStore(default_console_root(settings.storage_root))
    request.app.state.console_store = store
    return store


@router.get("/guardrails")
def guardrails() -> dict[str, object]:
    return {"guardrails": list(CONSOLE_GUARDRAILS)}


@router.post("/runs")
async def create_run(
    file: UploadFile | None = File(None),
    workflow: str = Form("section"),
    store: DesignerConsoleStore = Depends(get_console_store),
) -> dict[str, object]:
    try:
        if workflow == "synthetic_proof_demo" and file is None:
            run = await run_in_threadpool(store.create_synthetic_demo_run)
        else:
            if file is None or not file.filename:
                raise HTTPException(status_code=400, detail="choose a .ai or .pdf file")
            run = await run_in_threadpool(
                store.create_run_from_upload,
                file.file,
                filename=file.filename,
                workflow=workflow,
            )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return run.public_summary()


@router.get("/runs/{run_id}")
def get_run(
    run_id: str,
    store: DesignerConsoleStore = Depends(get_console_store),
) -> dict[str, object]:
    try:
        run = store.load(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="unknown run_id") from exc
    return run.public_summary()


@router.post("/runs/{run_id}/stages/{stage_key}")
async def run_stage(
    run_id: str,
    stage_key: str,
    store: DesignerConsoleStore = Depends(get_console_store),
) -> dict[str, object]:
    try:
        run = await run_in_threadpool(store.run_stage, run_id, stage_key)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="unknown run_id or stage") from exc
    return run.public_summary()


@router.get("/runs/{run_id}/artifacts/{artifact_key}")
def download_artifact(
    run_id: str,
    artifact_key: str,
    store: DesignerConsoleStore = Depends(get_console_store),
) -> FileResponse:
    try:
        path = store.artifact_path(run_id, artifact_key)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="unknown run_id or artifact") from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="artifact missing on disk") from exc

    media_type = "application/zip" if path.suffix == ".zip" else "application/octet-stream"
    return FileResponse(path=path, filename=path.name, media_type=media_type)
