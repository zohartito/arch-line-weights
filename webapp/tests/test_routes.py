"""HTTP-level tests for the FastAPI routes — uses TestClient + the
synthetic .ai fixture. Verifies the upload-process-poll-download flow
end-to-end without any external services.
"""

from __future__ import annotations

from pathlib import Path

from backend.config import Settings, local_vite_cors_origins


def test_health_returns_200(app_client) -> None:
    """Health endpoint is the only route that must always be up."""
    client, _app = app_client
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "arch-line-weights-webapp"


def test_default_cors_allows_local_vite_fallback_ports(monkeypatch) -> None:
    monkeypatch.delenv("ARCHLW_CORS_ORIGINS", raising=False)

    origins = Settings().cors_origins

    assert local_vite_cors_origins() == origins
    assert "http://localhost:5173" in origins
    assert "http://127.0.0.1:5173" in origins
    assert "http://localhost:5175" in origins
    assert "http://127.0.0.1:5175" in origins


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


# --------------------------------------------------------------------------- #
# v0.5+ / v0.6.x flag plumbing — verify each new field round-trips through
# the API and the server echoes it back via ``flags_applied``. Tests use the
# synthetic .ai fixture so every combination actually runs the pipeline.
# --------------------------------------------------------------------------- #


def _post_synthetic(client, synthetic_ai: Path, **form: object):
    """Helper: POST the synthetic .ai with a form-data overlay and return the response."""
    with synthetic_ai.open("rb") as f:
        return client.post(
            "/api/jobs",
            files={"file": (synthetic_ai.name, f, "application/postscript")},
            data={k: ("true" if v is True else "false" if v is False else str(v)) for k, v in form.items()},
        )


def test_default_post_round_trips_default_flags(app_client, synthetic_ai: Path) -> None:
    """A bare upload should report the documented CLI defaults via flags_applied."""
    client, _app = app_client
    resp = _post_synthetic(client, synthetic_ai)
    assert resp.status_code == 200, resp.text
    detail = client.get(f"/api/jobs/{resp.json()['job_id']}").json()
    flags = detail["flags_applied"]
    # Defaults must match the schema (and the CLI). Frontend reads this dict
    # to render the "ran with: ..." chip on the job page.
    assert flags["preset"] == "section"
    assert flags["scale"] == "1/4"
    assert flags["for_print"] is False
    assert flags["with_poche"] is True
    assert flags["bridge_strategy"] == "best"
    assert flags["alpha_shape"] is True
    assert flags["llm_fallback"] is False
    assert flags["source"] == "auto"


def test_preset_round_trip(app_client, synthetic_ai: Path) -> None:
    client, _app = app_client
    resp = _post_synthetic(client, synthetic_ai, preset="plan")
    assert resp.status_code == 200, resp.text
    detail = client.get(f"/api/jobs/{resp.json()['job_id']}").json()
    assert detail["status"] == "done", detail
    assert detail["options"]["preset"] == "plan"
    assert detail["flags_applied"]["preset"] == "plan"


def test_scale_round_trip(app_client, synthetic_ai: Path) -> None:
    client, _app = app_client
    resp = _post_synthetic(client, synthetic_ai, scale="1/8")
    assert resp.status_code == 200, resp.text
    detail = client.get(f"/api/jobs/{resp.json()['job_id']}").json()
    assert detail["options"]["scale"] == "1/8"
    assert detail["flags_applied"]["scale"] == "1/8"


def test_for_print_round_trip(app_client, synthetic_ai: Path) -> None:
    client, _app = app_client
    resp = _post_synthetic(client, synthetic_ai, for_print=True)
    assert resp.status_code == 200, resp.text
    detail = client.get(f"/api/jobs/{resp.json()['job_id']}").json()
    assert detail["options"]["for_print"] is True
    assert detail["flags_applied"]["for_print"] is True


def test_bridge_strategy_round_trip(app_client, synthetic_ai: Path) -> None:
    client, _app = app_client
    resp = _post_synthetic(client, synthetic_ai, bridge_strategy="greedy")
    assert resp.status_code == 200, resp.text
    detail = client.get(f"/api/jobs/{resp.json()['job_id']}").json()
    assert detail["options"]["bridge_strategy"] == "greedy"
    assert detail["flags_applied"]["bridge_strategy"] == "greedy"


def test_alpha_shape_round_trip(app_client, synthetic_ai: Path) -> None:
    """``--no-alpha-shape`` reverts to the v0.5.1 ladder; verify the boolean rides through."""
    client, _app = app_client
    resp = _post_synthetic(client, synthetic_ai, alpha_shape=False)
    assert resp.status_code == 200, resp.text
    detail = client.get(f"/api/jobs/{resp.json()['job_id']}").json()
    assert detail["options"]["alpha_shape"] is False
    assert detail["flags_applied"]["alpha_shape"] is False


def test_llm_fallback_round_trip_without_api_key(
    app_client, synthetic_ai: Path, monkeypatch
) -> None:
    """``llm_fallback=true`` must round-trip and *not* explode without ANTHROPIC_API_KEY.

    The synthetic fixture's single rectangle closes cleanly via ``linemerge_bare``,
    so the LLM rung never actually fires — meaning we can exercise the flag-
    plumbing path without paying for (or mocking) a real Anthropic call.
    Defensively we also ensure the env key is unset.
    """
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    client, _app = app_client
    resp = _post_synthetic(client, synthetic_ai, llm_fallback=True)
    assert resp.status_code == 200, resp.text
    detail = client.get(f"/api/jobs/{resp.json()['job_id']}").json()
    assert detail["status"] == "done", detail
    assert detail["options"]["llm_fallback"] is True
    assert detail["flags_applied"]["llm_fallback"] is True
    # The compute helper restores the env var on exit. Confirm it didn't leak.
    import os

    assert "ARCH_LW_LLM_FALLBACK" not in os.environ


def test_source_round_trip(app_client, synthetic_ai: Path) -> None:
    client, _app = app_client
    resp = _post_synthetic(client, synthetic_ai, source="rhino")
    assert resp.status_code == 200, resp.text
    detail = client.get(f"/api/jobs/{resp.json()['job_id']}").json()
    assert detail["options"]["source"] == "rhino"
    assert detail["flags_applied"]["source"] == "rhino"


def test_combined_non_default_flags(app_client, synthetic_ai: Path) -> None:
    """Sanity-check that several non-default flags work together end-to-end."""
    client, _app = app_client
    resp = _post_synthetic(
        client,
        synthetic_ai,
        preset="elevation",
        scale="1/2",
        for_print=True,
        bridge_strategy="greedy",
        alpha_shape=False,
        source="autocad",
    )
    assert resp.status_code == 200, resp.text
    detail = client.get(f"/api/jobs/{resp.json()['job_id']}").json()
    assert detail["status"] == "done", detail
    flags = detail["flags_applied"]
    assert flags["preset"] == "elevation"
    assert flags["scale"] == "1/2"
    assert flags["for_print"] is True
    assert flags["bridge_strategy"] == "greedy"
    assert flags["alpha_shape"] is False
    assert flags["source"] == "autocad"
    # Poché should have been applied (default=true); confirm the report rode through.
    assert detail["poche_summary"] is not None


def test_invalid_preset_returns_422(app_client, synthetic_ai: Path) -> None:
    client, _app = app_client
    resp = _post_synthetic(client, synthetic_ai, preset="bogus")
    assert resp.status_code == 422, resp.text


def test_invalid_scale_returns_422(app_client, synthetic_ai: Path) -> None:
    client, _app = app_client
    resp = _post_synthetic(client, synthetic_ai, scale="42")
    assert resp.status_code == 422, resp.text


def test_invalid_bridge_strategy_returns_422(app_client, synthetic_ai: Path) -> None:
    client, _app = app_client
    resp = _post_synthetic(client, synthetic_ai, bridge_strategy="random")
    assert resp.status_code == 422, resp.text


def test_invalid_source_returns_422(app_client, synthetic_ai: Path) -> None:
    client, _app = app_client
    resp = _post_synthetic(client, synthetic_ai, source="freecad")
    assert resp.status_code == 422, resp.text
