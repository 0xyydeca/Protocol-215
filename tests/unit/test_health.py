"""Unit tests for settings and health probes."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from protocol215.adapters import (
    FakeGeminiProbe,
    GcsObjectStoreProbe,
    LocalObjectStoreProbe,
    MemoryStateStoreProbe,
)
from protocol215.config import (
    AppEnv,
    GeminiBackend,
    ObjectStoreBackend,
    Settings,
    StateStoreBackend,
    clear_settings_cache,
)
from protocol215.health import liveness, readiness


def test_liveness_reports_ok() -> None:
    settings = Settings(app_env=AppEnv.TEST)
    body = liveness(settings)
    assert body["status"] == "ok"
    assert body["service"] == "protocol-215-api"


def test_readiness_ok_for_local_backends(tmp_path: Path) -> None:
    settings = Settings(
        app_env=AppEnv.TEST,
        object_store_backend=ObjectStoreBackend.LOCAL,
        state_store_backend=StateStoreBackend.MEMORY,
        gemini_backend=GeminiBackend.FAKE,
        local_object_store_path=tmp_path / "objects",
    )
    body = readiness(settings)
    assert body["status"] == "ok"
    assert body["checks"]["object_store"]["ok"] is True
    assert body["checks"]["state_store"]["ok"] is True
    assert body["checks"]["gemini"]["ok"] is True


def test_readiness_fails_when_gcs_selected_without_project() -> None:
    settings = Settings(
        app_env=AppEnv.TEST,
        object_store_backend=ObjectStoreBackend.GCS,
        google_cloud_project=None,
        state_store_backend=StateStoreBackend.MEMORY,
        gemini_backend=GeminiBackend.FAKE,
    )
    body = readiness(settings)
    assert body["status"] == "unavailable"
    assert body["checks"]["object_store"]["ok"] is False


def test_local_object_store_probe_writes(tmp_path: Path) -> None:
    ok, detail = LocalObjectStoreProbe(tmp_path).check()
    assert ok is True
    assert "writable" in detail


def test_gcs_probe_requires_project() -> None:
    ok, _ = GcsObjectStoreProbe(None).check()
    assert ok is False


def test_memory_and_fake_gemini_probes() -> None:
    assert MemoryStateStoreProbe().check()[0] is True
    assert FakeGeminiProbe("gemini-3.5-flash").check()[0] is True


def test_api_health_endpoints(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    clear_settings_cache()
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("OBJECT_STORE_BACKEND", "local")
    monkeypatch.setenv("STATE_STORE_BACKEND", "memory")
    monkeypatch.setenv("EVENT_BUS_BACKEND", "inprocess")
    monkeypatch.setenv("GEMINI_BACKEND", "fake")
    monkeypatch.setenv("LOCAL_OBJECT_STORE_PATH", str(tmp_path / "objects"))
    clear_settings_cache()

    from apps.api.main import app

    client = TestClient(app)
    hz = client.get("/healthz")
    assert hz.status_code == 200
    assert hz.json()["status"] == "ok"

    rz = client.get("/readyz")
    assert rz.status_code == 200
    assert rz.json()["status"] == "ok"
    clear_settings_cache()
