"""Recording readiness endpoint — real checks, no state mutation."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from protocol215.api.app import create_app
from protocol215.api.container import build_container
from protocol215.application.recording_readiness import (
    evaluate_recording_readiness,
    is_gemini_3_5_plus,
)
from protocol215.config import (
    AppEnv,
    EventBusBackend,
    GeminiBackend,
    ObjectStoreBackend,
    Settings,
    StateStoreBackend,
    clear_settings_cache,
)


def test_is_gemini_3_5_plus() -> None:
    assert is_gemini_3_5_plus("gemini-3.5-flash") is True
    assert is_gemini_3_5_plus("publishers/google/models/gemini-3.5-flash") is True
    assert is_gemini_3_5_plus("gemini-2.5-flash") is False
    assert is_gemini_3_5_plus("gemini-1.5-flash") is False
    assert is_gemini_3_5_plus("") is False


def test_recording_readiness_fails_when_live_deps_unavailable(tmp_path: Path) -> None:
    settings = Settings(
        app_env=AppEnv.TEST,
        execution_mode="local",
        gemini_backend=GeminiBackend.FAKE,
        gemini_model="gemini-2.5-flash",
        object_store_backend=ObjectStoreBackend.LOCAL,
        state_store_backend=StateStoreBackend.MEMORY,
        event_bus_backend=EventBusBackend.INPROCESS,
        local_object_store_path=tmp_path / "objects",
    )
    container = build_container(settings)
    report = evaluate_recording_readiness(settings, state=container.state)
    assert report["overall"] == "FAIL"
    by_name = {c["name"]: c for c in report["checks"]}
    assert by_name["cloud_execution_mode"]["status"] == "FAIL"
    assert by_name["live_gemini_backend"]["status"] == "FAIL"
    assert by_name["model_is_gemini_3_5_plus"]["status"] == "FAIL"
    assert by_name["gcs_reachable"]["status"] == "FAIL"
    assert by_name["firestore_reachable"]["status"] == "FAIL"
    assert by_name["pubsub_topic_reachable"]["status"] == "FAIL"
    assert by_name["fixture_pdfs_available"]["status"] == "PASS"
    assert by_name["audit_verifier_operational"]["status"] == "PASS"
    # No mutation: still zero runs
    assert container.state.list_runs() == []


def test_recording_readiness_endpoint(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    clear_settings_cache()
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("GEMINI_BACKEND", "fake")
    monkeypatch.setenv("EXECUTION_MODE", "local")
    monkeypatch.setenv("OBJECT_STORE_BACKEND", "local")
    monkeypatch.setenv("STATE_STORE_BACKEND", "memory")
    monkeypatch.setenv("EVENT_BUS_BACKEND", "inprocess")
    monkeypatch.setenv("LOCAL_OBJECT_STORE_PATH", str(tmp_path / "objects"))
    clear_settings_cache()
    settings = Settings(
        app_env=AppEnv.TEST,
        execution_mode="local",
        gemini_backend=GeminiBackend.FAKE,
        local_object_store_path=tmp_path / "objects",
    )
    app = create_app(settings=settings, container=build_container(settings))
    client = TestClient(app)
    resp = client.get("/api/demo/recording-readiness")
    assert resp.status_code == 503
    body = resp.json()
    assert body["overall"] == "FAIL"
    assert body["failed_count"] >= 1
    assert "checks" in body
    # Never leak secret-like keys
    dumped = resp.text.lower()
    assert "private_key" not in dumped
    assert "begin rsa" not in dumped
    clear_settings_cache()
