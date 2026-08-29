"""CORS preflight and run-status diagnostic fields."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from protocol215.api.app import create_app
from protocol215.api.container import build_container
from protocol215.config import Settings, clear_settings_cache

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "protocols"
V1_PDF = FIXTURES / "AURORA-101_Protocol_v1.0.pdf"
V2_PDF = FIXTURES / "AURORA-101_Protocol_v2.0.pdf"


def test_cors_preflight_allows_configured_origin(tmp_path) -> None:
    clear_settings_cache()
    settings = Settings(
        app_env="local",
        cors_origins="https://protocol-215.vercel.app,http://127.0.0.1:5173",
        local_object_store_path=tmp_path / "obj",
        sqlite_path=tmp_path / "db.sqlite",
    )
    app = create_app(settings=settings, container=build_container(settings))
    client = TestClient(app)
    resp = client.options(
        "/api/runs",
        headers={
            "Origin": "https://protocol-215.vercel.app",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,idempotency-key",
        },
    )
    assert resp.status_code in {200, 204}
    assert resp.headers.get("access-control-allow-origin") == "https://protocol-215.vercel.app"
    allow_methods = resp.headers.get("access-control-allow-methods", "")
    assert "POST" in allow_methods
    assert "GET" in allow_methods
    assert "OPTIONS" in allow_methods
    allow_headers = resp.headers.get("access-control-allow-headers", "").lower()
    assert "content-type" in allow_headers
    assert "idempotency-key" in allow_headers
    assert resp.headers.get("access-control-allow-credentials") in {None, "false"}


def test_cors_rejects_unknown_origin(tmp_path) -> None:
    clear_settings_cache()
    settings = Settings(
        app_env="local",
        cors_origins="https://protocol-215.vercel.app",
        local_object_store_path=tmp_path / "obj",
        sqlite_path=tmp_path / "db.sqlite",
    )
    app = create_app(settings=settings, container=build_container(settings))
    client = TestClient(app)
    resp = client.options(
        "/api/runs",
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.headers.get("access-control-allow-origin") != "https://evil.example"


def test_run_status_includes_diagnostic_fields(tmp_path) -> None:
    clear_settings_cache()
    settings = Settings(
        app_env="local",
        gemini_backend="fake",
        local_object_store_path=tmp_path / "obj",
        sqlite_path=tmp_path / "db.sqlite",
    )
    container = build_container(settings)
    app = create_app(settings=settings, container=container)
    client = TestClient(app)

    files = {
        "old_protocol": ("v1.pdf", V1_PDF.read_bytes(), "application/pdf"),
        "new_protocol": ("v2.pdf", V2_PDF.read_bytes(), "application/pdf"),
    }
    created = client.post("/api/runs", files=files, data={"study_id": "AURORA-101"})
    assert created.status_code == 202, created.text
    run_id = created.json()["run_id"]
    status = client.get(f"/api/runs/{run_id}")
    assert status.status_code == 200
    body = status.json()
    for key in (
        "updated_at",
        "last_checkpoint_at",
        "last_worker_event_id",
        "last_error_code",
        "last_error_detail_safe",
        "correlation_id",
        "web_revision",
        "worker_revision",
        "actual_adapters",
        "compiler_model",
    ):
        assert key in body, key
    assert body["correlation_id"] == run_id
    assert body["compiler_model"]
    assert isinstance(body["actual_adapters"], dict)
    assert body["actual_adapters"].get("event_bus")
