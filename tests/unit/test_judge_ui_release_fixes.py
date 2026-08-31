"""Judge-facing release fixes: resume proof IDs and Trial Twin roster counts."""

from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from protocol215.api.app import create_app
from protocol215.api.container import build_container
from protocol215.api.status import build_run_status
from protocol215.config import Settings, clear_settings_cache
from protocol215.domain.enums import WorkflowStatus
from protocol215.domain.models import SessionMetadata, WorkflowRun

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "protocols"
V1_PDF = FIXTURES / "AURORA-101_Protocol_v1.0.pdf"
V2_PDF = FIXTURES / "AURORA-101_Protocol_v2.0.pdf"


def _client(tmp_path) -> TestClient:
    clear_settings_cache()
    settings = Settings(
        app_env="local",
        gemini_backend="fake",
        local_object_store_path=tmp_path / "obj",
        sqlite_path=tmp_path / "db.sqlite",
    )
    container = build_container(settings)
    app = create_app(settings=settings, container=container)
    return TestClient(app)


def test_completed_run_status_exposes_persisted_session_and_invocation(tmp_path) -> None:
    client = _client(tmp_path)
    container = client.app.state.container
    run = WorkflowRun(
        run_id="run-resume-1",
        study_id="AURORA-101",
        from_version="1.0",
        to_version="2.0",
        status=WorkflowStatus.COMPLETED,
        checkpoint="CompleteRun",
        state_version=12,
    )
    container.state.save_run(run)
    container.state.save_session_metadata(
        SessionMetadata(
            run_id="run-resume-1",
            session_id="sess-persisted-abc",
            invocation_id="inv-persisted-xyz",
            expected_state_version=12,
        )
    )

    body = client.get("/api/runs/run-resume-1").json()
    assert body["status"] == "COMPLETED"
    assert body["session_id"] == "sess-persisted-abc"
    assert body["invocation_id"] == "inv-persisted-xyz"

    typed = build_run_status(
        container.service, container.settings, "run-resume-1", container=container
    )
    assert typed.session_id == "sess-persisted-abc"
    assert typed.invocation_id == "inv-persisted-xyz"


def test_awaiting_approval_status_includes_session_ids_from_workflow_session(tmp_path) -> None:
    client = _client(tmp_path)
    files = {
        "old_protocol": ("v1.pdf", V1_PDF.read_bytes(), "application/pdf"),
        "new_protocol": ("v2.pdf", V2_PDF.read_bytes(), "application/pdf"),
    }
    created = client.post("/api/runs", files=files, data={"study_id": "AURORA-101"})
    assert created.status_code == 202, created.text
    run_id = created.json()["run_id"]

    pending = None
    last = None
    for _ in range(80):
        last = client.get(f"/api/runs/{run_id}").json()
        if last["status"] == WorkflowStatus.AWAITING_APPROVAL.value:
            pending = last.get("pending_approval")
            break
        if last["status"] in {
            WorkflowStatus.FAILED_RETRYABLE.value,
            WorkflowStatus.FAILED_TERMINAL.value,
            WorkflowStatus.COMPLETED.value,
        }:
            break
        time.sleep(0.05)

    assert pending is not None, last
    assert last["session_id"], last
    # Local background pause may not yet have an ADK invocation_id — do not invent one.
    assert "invocation_id" in last
    meta = client.app.state.container.state.get_session_metadata(run_id)
    assert meta is not None
    assert last["session_id"] == meta.session_id
    assert pending.get("session_id") in {None, last["session_id"]}

    # When ADK/session state later persists an invocation_id, status must surface it.
    client.app.state.container.state.save_session_metadata(
        meta.model_copy(update={"invocation_id": "inv-from-adk"})
    )
    refreshed = client.get(f"/api/runs/{run_id}").json()
    assert refreshed["session_id"] == meta.session_id
    assert refreshed["invocation_id"] == "inv-from-adk"


def test_manifest_roster_counts_come_from_trial_twin(tmp_path) -> None:
    client = _client(tmp_path)
    files = {
        "old_protocol": ("v1.pdf", V1_PDF.read_bytes(), "application/pdf"),
        "new_protocol": ("v2.pdf", V2_PDF.read_bytes(), "application/pdf"),
    }
    created = client.post("/api/runs", files=files, data={"study_id": "AURORA-101"})
    run_id = created.json()["run_id"]

    pending = None
    for _ in range(80):
        st = client.get(f"/api/runs/{run_id}").json()
        if st["status"] == WorkflowStatus.AWAITING_APPROVAL.value:
            pending = st.get("pending_approval")
            break
        if st["status"] in {
            WorkflowStatus.FAILED_RETRYABLE.value,
            WorkflowStatus.FAILED_TERMINAL.value,
            WorkflowStatus.COMPLETED.value,
        }:
            break
        time.sleep(0.05)
    assert pending is not None

    good = client.post(
        f"/api/runs/{run_id}/approvals/{pending['approval_id']}",
        json={
            "decision": "approved",
            "expected_state_version": pending["expected_state_version"],
        },
    )
    assert good.status_code == 202, good.text

    manifest = None
    for _ in range(80):
        resp = client.get(f"/api/runs/{run_id}/manifest")
        if resp.status_code == 200:
            manifest = resp.json()
            break
        time.sleep(0.05)
    assert manifest is not None, client.get(f"/api/runs/{run_id}").json()

    sites = client.app.state.container.state.list_sites(run_id)
    participants = client.app.state.container.state.list_participants(run_id)
    assert len(sites) == 3
    assert len(participants) == 5
    assert manifest["sites_evaluated_count"] == len(sites)
    assert manifest["participants_evaluated_count"] == len(participants)
    assert manifest["participants_evaluated_count"] == 5

    # Affected refs in findings/actions can be a subset — roster counts must still be twin size.
    affected_participants = {
        *(f.get("participant_id") for f in manifest.get("findings", []) if f.get("participant_id")),
        *(a.get("participant_id") for a in manifest.get("actions", []) if a.get("participant_id")),
    }
    assert len(affected_participants) <= 5
    assert manifest["participants_evaluated_count"] >= len(affected_participants)
