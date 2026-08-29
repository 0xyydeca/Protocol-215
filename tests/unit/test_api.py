"""API unit tests: uploads, approvals, OpenAPI snapshot."""

from __future__ import annotations

import io
import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from protocol215.api.app import create_app
from protocol215.api.container import build_container
from protocol215.config import AppEnv, Settings, clear_settings_cache
from protocol215.domain.enums import ApprovalStatus, WorkflowStatus

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "protocols"
V1_PDF = FIXTURES / "AURORA-101_Protocol_v1.0.pdf"
V2_PDF = FIXTURES / "AURORA-101_Protocol_v2.0.pdf"
SNAPSHOT = Path(__file__).resolve().parent / "snapshots" / "openapi.json"


def _minimal_pdf(pages: int = 1) -> bytes:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _encrypted_pdf() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.encrypt("secret")
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


@pytest.fixture()
def api_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Settings:
    clear_settings_cache()
    settings = Settings(
        app_env=AppEnv.TEST,
        local_object_store_path=tmp_path / "objects",
        sqlite_path=tmp_path / "db.sqlite",
        max_pdf_bytes=50_000,
        max_pdf_pages=20,
        execution_mode="local",
    )
    monkeypatch.setenv("APP_ENV", "test")
    clear_settings_cache()
    return settings


@pytest.fixture()
def client(api_env: Settings) -> TestClient:
    container = build_container(api_env)
    app = create_app(settings=api_env, container=container)
    with TestClient(app) as tc:
        yield tc


def test_health_endpoints(client: TestClient) -> None:
    assert client.get("/healthz").status_code == 200
    assert client.get("/readyz").status_code == 200


def test_multipart_create_run_returns_immediately(client: TestClient) -> None:
    assert V1_PDF.exists() and V2_PDF.exists()
    files = {
        "old_protocol": ("v1.pdf", V1_PDF.read_bytes(), "application/pdf"),
        "new_protocol": ("v2.pdf", V2_PDF.read_bytes(), "application/pdf"),
    }
    t0 = time.perf_counter()
    resp = client.post("/api/runs", files=files)
    elapsed = time.perf_counter() - t0
    assert resp.status_code == 202, resp.text
    body = resp.json()
    assert "run_id" in body
    assert body["status"] == WorkflowStatus.CREATED.value
    # Must return before full workflow completion (even with fakes, keep budget tight)
    assert elapsed < 2.0

    status = client.get(f"/api/runs/{body['run_id']}")
    assert status.status_code == 200
    st = status.json()
    assert st["run_id"] == body["run_id"]
    assert "current_stage" in st
    assert "progress" in st
    assert "execution_mode" in st
    assert st["execution_mode"] == "local"


def test_malformed_pdf_rejected(client: TestClient) -> None:
    files = {
        "old_protocol": ("bad.pdf", b"not-a-pdf", "application/pdf"),
        "new_protocol": ("v2.pdf", _minimal_pdf(), "application/pdf"),
    }
    resp = client.post("/api/runs", files=files)
    assert resp.status_code == 400
    err = resp.json()
    assert err["error_code"] == "invalid_pdf"
    assert "correlation_id" in err
    assert "retryable" in err
    assert "traceback" not in err
    assert "stack" not in json.dumps(err).lower()


def test_wrong_extension_rejected(client: TestClient) -> None:
    files = {
        "old_protocol": ("v1.txt", _minimal_pdf(), "application/pdf"),
        "new_protocol": ("v2.pdf", _minimal_pdf(), "application/pdf"),
    }
    resp = client.post("/api/runs", files=files)
    assert resp.status_code == 400
    assert resp.json()["error_code"] == "invalid_pdf"


def test_oversized_file_rejected(client: TestClient) -> None:
    big = b"%PDF-1.4\n" + (b"x" * 60_000)
    files = {
        "old_protocol": ("big.pdf", big, "application/pdf"),
        "new_protocol": ("v2.pdf", _minimal_pdf(), "application/pdf"),
    }
    resp = client.post("/api/runs", files=files)
    assert resp.status_code == 413
    assert resp.json()["error_code"] == "file_too_large"


def test_too_many_pages_rejected(api_env: Settings, tmp_path: Path) -> None:
    # Lower page limit only for this case
    tight = api_env.model_copy(update={"max_pdf_pages": 5})
    container = build_container(tight)
    app = create_app(settings=tight, container=container)
    with TestClient(app) as client:
        files = {
            "old_protocol": ("many.pdf", _minimal_pdf(pages=10), "application/pdf"),
            "new_protocol": ("v2.pdf", _minimal_pdf(), "application/pdf"),
        }
        resp = client.post("/api/runs", files=files)
        assert resp.status_code == 400
        assert resp.json()["error_code"] == "too_many_pages"


def test_encrypted_pdf_rejected(client: TestClient) -> None:
    files = {
        "old_protocol": ("enc.pdf", _encrypted_pdf(), "application/pdf"),
        "new_protocol": ("v2.pdf", _minimal_pdf(), "application/pdf"),
    }
    resp = client.post("/api/runs", files=files)
    assert resp.status_code == 400
    assert resp.json()["error_code"] == "encrypted_pdf"


def test_duplicate_submission_rejected(client: TestClient) -> None:
    files = {
        "old_protocol": ("v1.pdf", _minimal_pdf(), "application/pdf"),
        "new_protocol": ("v2.pdf", _minimal_pdf(pages=2), "application/pdf"),
    }
    first = client.post("/api/runs", files=files)
    assert first.status_code == 202
    second = client.post("/api/runs", files=files)
    assert second.status_code == 409
    assert second.json()["error_code"] == "duplicate"
    assert second.json()["details"]["run_id"] == first.json()["run_id"]


def test_resubmit_allowed_after_failed_run(client: TestClient) -> None:
    from protocol215.domain.enums import WorkflowStatus

    files = {
        "old_protocol": ("v1.pdf", _minimal_pdf(), "application/pdf"),
        "new_protocol": ("v2.pdf", _minimal_pdf(pages=2), "application/pdf"),
    }
    first = client.post("/api/runs", files=files)
    assert first.status_code == 202
    run_id = first.json()["run_id"]
    container = client.app.state.container
    run = container.state.get_run(run_id)
    assert run is not None
    container.state.save_run(run.model_copy(update={"status": WorkflowStatus.FAILED_RETRYABLE}))
    second = client.post("/api/runs", files=files)
    assert second.status_code == 202
    assert second.json()["run_id"] != run_id


def test_list_runs_and_demo_reset(client: TestClient) -> None:
    files = {
        "old_protocol": ("v1.pdf", _minimal_pdf(), "application/pdf"),
        "new_protocol": ("v2.pdf", _minimal_pdf(), "application/pdf"),
    }
    client.post("/api/runs", files=files)
    listed = client.get("/api/runs")
    assert listed.status_code == 200
    assert len(listed.json()) >= 1
    reset = client.post("/api/demo/reset")
    assert reset.status_code == 200
    assert client.get("/api/runs").json() == []


def test_approval_and_stale_approval(client: TestClient) -> None:
    # Use fixture PDFs so FakeCompiler + FakePlanner produce AMBER pause
    files = {
        "old_protocol": ("v1.pdf", V1_PDF.read_bytes(), "application/pdf"),
        "new_protocol": ("v2.pdf", V2_PDF.read_bytes(), "application/pdf"),
    }
    created = client.post("/api/runs", files=files)
    run_id = created.json()["run_id"]

    # Wait for background pipeline to reach AWAITING_APPROVAL
    pending = None
    for _ in range(50):
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
    assert pending is not None, client.get(f"/api/runs/{run_id}").json()

    # Stale version
    bad = client.post(
        f"/api/runs/{run_id}/approvals/{pending['approval_id']}",
        json={
            "decision": ApprovalStatus.APPROVED.value,
            "expected_state_version": pending["expected_state_version"] + 99,
        },
    )
    assert bad.status_code == 409
    assert bad.json()["error_code"] == "stale_approval"

    good = client.post(
        f"/api/runs/{run_id}/approvals/{pending['approval_id']}",
        json={
            "decision": ApprovalStatus.APPROVED.value,
            "expected_state_version": pending["expected_state_version"],
        },
    )
    assert good.status_code == 202
    assert good.json()["event_published"] is True

    # Nested resources exist
    assert client.get(f"/api/runs/{run_id}/changes").status_code == 200
    assert client.get(f"/api/runs/{run_id}/impact").status_code == 200
    assert client.get(f"/api/runs/{run_id}/findings").status_code == 200
    assert client.get(f"/api/runs/{run_id}/actions").status_code == 200
    assert client.get(f"/api/runs/{run_id}/approvals").status_code == 200
    assert client.get(f"/api/runs/{run_id}/audit").status_code == 200


def test_openapi_generation_and_snapshot(client: TestClient) -> None:
    schema = client.app.openapi()
    assert schema["info"]["title"] == "Protocol 215 API"
    paths = schema["paths"]
    for path in (
        "/healthz",
        "/readyz",
        "/api/runs",
        "/api/runs/{run_id}",
        "/api/runs/{run_id}/changes",
        "/api/runs/{run_id}/impact",
        "/api/runs/{run_id}/findings",
        "/api/runs/{run_id}/actions",
        "/api/runs/{run_id}/approvals",
        "/api/runs/{run_id}/approvals/{approval_id}",
        "/api/runs/{run_id}/audit",
        "/api/runs/{run_id}/audit/verify",
        "/api/runs/{run_id}/manifest",
        "/api/demo/reset",
        "/api/demo/recording-readiness",
    ):
        assert path in paths, path

    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    # Normalize volatile fields
    normalized = json.loads(json.dumps(schema))
    if SNAPSHOT.exists():
        expected = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        assert normalized == expected
    else:
        SNAPSHOT.write_text(
            json.dumps(normalized, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    assert "/api/demo/recording-readiness" in normalized["paths"]
    assert "/api/runs" in normalized["paths"]
