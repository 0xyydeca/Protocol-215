"""Demo reset restores twin baseline and clears runs."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from protocol215.api.app import create_app
from protocol215.api.container import build_container
from protocol215.config import AppEnv, Settings, clear_settings_cache
from protocol215.fixtures import PDF_V1, PDF_V2


def test_demo_reset_clears_runs_and_restores_twin(tmp_path: Path) -> None:
    clear_settings_cache()
    settings = Settings(
        app_env=AppEnv.TEST,
        local_object_store_path=tmp_path / "objects",
        sqlite_path=tmp_path / "db.sqlite",
        execution_mode="local",
    )
    app = create_app(settings=settings, container=build_container(settings))
    with TestClient(app) as client:
        files = {
            "old_protocol": ("v1.pdf", PDF_V1.read_bytes(), "application/pdf"),
            "new_protocol": ("v2.pdf", PDF_V2.read_bytes(), "application/pdf"),
        }
        assert client.post("/api/runs", files=files).status_code == 202
        assert len(client.get("/api/runs").json()) >= 1

        reset = client.post("/api/demo/reset")
        assert reset.status_code == 200
        body = reset.json()
        assert body["ok"] is True
        assert body["sites_restored"] == 3
        assert body["participants_restored"] == 5
        assert body["runs_cleared"] >= 1
        assert client.get("/api/runs").json() == []
        twin = body["twin_snapshot"]
        assert set(twin["site_ids"]) == {"SITE-001", "SITE-002", "SITE-003"}
        assert "P001" in twin["participant_ids"]
        assert "P002" in twin["participant_ids"]
