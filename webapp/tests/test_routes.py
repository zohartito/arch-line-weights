"""HTTP-level tests for the FastAPI routes — uses TestClient + the
synthetic .ai fixture. Verifies the upload-process-poll-download flow
end-to-end without any external services.
"""

from __future__ import annotations

from pathlib import Path


def test_health_returns_200(app_client) -> None:
    """Health endpoint is the only route that must always be up."""
    client, _app = app_client
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "arch-line-weights-webapp"


def test_get_unknown_job_returns_404(app_client) -> None:
    client, _app = app_client
    resp = client.get("/api/jobs/does-not-exist")
    assert resp.status_code == 404


def test_download_unknown_job_returns_404(app_client) -> None:
    client, _app = app_client
    resp = client.get("/api/jobs/does-not-exist/download")
    assert resp.status_code == 404


def test_upload_rejects_unsupported_extension(app_client, tmp_path: Path) -> None:
    """Any upload that isn't .ai or .pdf should bounce with a 415."""
    client, _app = app_client
    fake = tmp_path / "thing.txt"
    fake.write_text("not a drawing")
    with fake.open("rb") as f:
        resp = client.post(
            "/api/jobs",
            files={"file": ("thing.txt", f, "text/plain")},
        )
    assert resp.status_code == 415


def test_upload_rejects_missing_filename(app_client, synthetic_ai: Path) -> None:
    """Multipart without a filename should 400."""
    client, _app = app_client
    with synthetic_ai.open("rb") as f:
        # FastAPI/Starlette assigns "upload" by default if no filename is
        # set explicitly. We force the empty filename to cover the guard.
        resp = client.post(
            "/api/jobs",
            files={"file": ("", f, "application/postscript")},
        )
    # Some Starlette versions short-circuit before our handler with 422.
    # Either is fine — the upload absolutely must not succeed.
    assert resp.status_code in (400, 415, 422)


def test_full_upload_run_poll_download(app_client, synthetic_ai: Path) -> None:
    """End-to-end: upload synthetic .ai, poll status, download output."""
    client, _app = app_client

    # 1. Upload (sync runner -> done by the time the response returns)
    with synthetic_ai.open("rb") as f:
        resp = client.post(
            "/api/jobs",
            files={"file": (synthetic_ai.name, f, "application/postscript")},
            data={
                "preset": "section",
                "scale": "1/4",
                "for_print": "false",
                "with_poche": "true",
                "default_width": "0.25",
            },
        )
    assert resp.status_code == 200, resp.text
    created = resp.json()
    assert "job_id" in created
    job_id = created["job_id"]
    assert created["status"] in ("done", "pending", "running")

    # 2. Poll status
    detail = client.get(f"/api/jobs/{job_id}").json()
    assert detail["job_id"] == job_id
    # Sync runner means the job is already done.
    assert detail["status"] == "done", detail
    assert detail["original_filename"] == synthetic_ai.name
    assert detail["apply_summary"] is not None
    assert detail["poche_summary"] is not None
    assert detail["download_url"] is not None
    # The download URL is path-only (no scheme/host).
    assert detail["download_url"].startswith("/api/jobs/")

    # 3. Download
    dl = client.get(detail["download_url"])
    assert dl.status_code == 200
    assert len(dl.content) > 0
    assert "HIERARCHY" in dl.headers.get("content-disposition", "")


def test_upload_with_poche_false_skips_poche_summary(app_client, synthetic_ai: Path) -> None:
    """When ``with_poche=false`` the response has no poche_summary populated."""
    client, _app = app_client
    with synthetic_ai.open("rb") as f:
        resp = client.post(
            "/api/jobs",
            files={"file": (synthetic_ai.name, f, "application/postscript")},
            data={"with_poche": "false"},
        )
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]
    detail = client.get(f"/api/jobs/{job_id}").json()
    assert detail["status"] == "done", detail
    assert detail["apply_summary"] is not None
    assert detail["poche_summary"] is None
    assert detail["fills"] == []


def test_download_before_done_returns_409(app_client) -> None:
    """A job that exists but isn't DONE should 409 on download.

    Build the record manually (skipping the run) so we can hit the guard.
    """
    client, app = app_client
    from backend.schemas import JobOptions

    record = app.state.job_store.create(
        original_filename="never-ran.ai",
        options=JobOptions(),
    )
    resp = client.get(f"/api/jobs/{record.job_id}/download")
    assert resp.status_code == 409
