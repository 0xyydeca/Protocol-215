"""Tests for cloud execution-path repair (factories, routes, worker, durability)."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from tests.unit.fakes_firestore import FakeFirestore, FakeFirestoreModule

from protocol215.adapters.event_bus_inprocess import InProcessEventBus
from protocol215.adapters.event_bus_pubsub import PubSubEventBus
from protocol215.adapters.object_store_gcs import GCSObjectStore
from protocol215.adapters.object_store_local import LocalFileObjectStore
from protocol215.adapters.state_store_firestore import FirestoreStateStore
from protocol215.adapters.state_store_memory import InMemoryStateStore
from protocol215.api.app import create_app
from protocol215.api.container import build_container
from protocol215.api.factories import (
    build_event_bus,
    build_object_store,
    build_state_store,
)
from protocol215.cloud.events import AmendmentEventType, EventEnvelope
from protocol215.cloud.http_worker import create_worker_app
from protocol215.cloud.worker import AmendmentWorkerHandler
from protocol215.config import (
    AdkSessionBackend,
    EventBusBackend,
    ObjectStoreBackend,
    Settings,
    StateStoreBackend,
    clear_settings_cache,
)
from protocol215.domain.enums import WorkflowStatus
from protocol215.domain.models import WorkflowRun
from protocol215.fixtures import PDF_V1, PDF_V2
from protocol215.health import readiness
from protocol215.simulator.twin import load_participants, load_sites


def test_factory_selects_local_adapters(tmp_path: Path) -> None:
    settings = Settings(
        object_store_backend=ObjectStoreBackend.LOCAL,
        state_store_backend=StateStoreBackend.MEMORY,
        event_bus_backend=EventBusBackend.INPROCESS,
        local_object_store_path=tmp_path / "obj",
    )
    assert isinstance(build_object_store(settings), LocalFileObjectStore)
    assert isinstance(build_state_store(settings), InMemoryStateStore)
    assert isinstance(build_event_bus(settings), InProcessEventBus)


def test_factory_selects_cloud_adapters() -> None:
    gcs = GCSObjectStore(bucket_name="demo-bucket", project="demo-project", client=MagicMock())
    assert isinstance(gcs, GCSObjectStore)
    fs = FirestoreStateStore(client=FakeFirestore())
    fs._firestore_module = FakeFirestoreModule  # type: ignore[attr-defined]
    assert isinstance(fs, FirestoreStateStore)
    bus = PubSubEventBus(
        project="demo-project",
        topic_received="t",
        topic_resume="t",
        publisher=MagicMock(),
    )
    assert isinstance(bus, PubSubEventBus)


def test_build_container_actual_adapters(tmp_path: Path) -> None:
    settings = Settings(
        object_store_backend=ObjectStoreBackend.LOCAL,
        state_store_backend=StateStoreBackend.MEMORY,
        event_bus_backend=EventBusBackend.INPROCESS,
        gemini_backend="fake",  # type: ignore[arg-type]
        local_object_store_path=tmp_path / "obj",
    )
    container = build_container(settings)
    assert container.actual_adapters["object_store"] == "LocalFileObjectStore"
    assert container.actual_adapters["state_store"] == "InMemoryStateStore"
    assert container.actual_adapters["event_bus"] == "InProcessEventBus"
    payload = readiness(settings, container=container)
    assert payload["actual_adapters"]["event_bus"] == "InProcessEventBus"


def test_cloud_readyz_fails_with_local_adapters(tmp_path: Path) -> None:
    settings = Settings(
        object_store_backend=ObjectStoreBackend.GCS,
        state_store_backend=StateStoreBackend.FIRESTORE,
        event_bus_backend=EventBusBackend.PUBSUB,
        gcs_bucket="b",
        google_cloud_project="p",
        gemini_backend="fake",  # type: ignore[arg-type]
        local_object_store_path=tmp_path / "obj",
    )
    from protocol215.adapters.audit_log import HashChainedAuditLog
    from protocol215.adapters.clock import SystemClock
    from protocol215.adapters.fakes import FakeActionPlanner, FakeProtocolCompiler
    from protocol215.adapters.identifiers import UUIDIdentifierGenerator
    from protocol215.api.container import AppContainer
    from protocol215.application.services import AmendmentAppService

    state = InMemoryStateStore()
    objects = LocalFileObjectStore(tmp_path / "obj")
    events = InProcessEventBus()
    clock = SystemClock()
    ids = UUIDIdentifierGenerator()
    audit = HashChainedAuditLog(state, clock, ids)
    service = AmendmentAppService(
        state=state,
        objects=objects,
        events=events,
        audit=audit,
        compiler=FakeProtocolCompiler(),
        planner=FakeActionPlanner(),
        clock=clock,
        ids=ids,
    )
    container = AppContainer(
        settings=settings, state=state, objects=objects, events=events, service=service
    )
    payload = readiness(settings, container=container)
    assert payload["status"] == "unavailable"
    assert payload["checks"]["actual_object_store"]["ok"] is False


def test_pubsub_routes_do_not_call_local_kick(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    clear_settings_cache()
    settings = Settings(
        app_env="test",  # type: ignore[arg-type]
        object_store_backend=ObjectStoreBackend.LOCAL,
        state_store_backend=StateStoreBackend.MEMORY,
        event_bus_backend=EventBusBackend.PUBSUB,
        google_cloud_project="demo",
        pubsub_topic_received="events",
        pubsub_topic_resume="events",
        gemini_backend="fake",  # type: ignore[arg-type]
        local_object_store_path=tmp_path / "obj",
    )
    published: list[str] = []

    class CapturingBus(InProcessEventBus):
        def publish(self, event: Any) -> None:  # type: ignore[override]
            published.append(event.event_type)
            super().publish(event)

    monkeypatch.setattr(
        "protocol215.api.container.build_event_bus",
        lambda _s: CapturingBus(),
    )
    container = build_container(settings)

    kicked: list[str] = []

    def fake_kick(*_a: Any, **_k: Any) -> None:
        kicked.append("received")

    def fake_resume(*_a: Any, **_k: Any) -> None:
        kicked.append("resume")

    monkeypatch.setattr("protocol215.api.routes.kick_amendment_received", fake_kick)
    monkeypatch.setattr("protocol215.api.routes.kick_amendment_resume", fake_resume)

    app = create_app(settings=settings, container=container)
    client = TestClient(app)
    files = {
        "old_protocol": ("v1.pdf", PDF_V1.read_bytes(), "application/pdf"),
        "new_protocol": ("v2.pdf", PDF_V2.read_bytes(), "application/pdf"),
    }
    resp = client.post("/api/runs", files=files)
    assert resp.status_code == 202, resp.text
    assert kicked == []
    assert "amendment.received" in published


def test_worker_app_without_handler_readyz_fails() -> None:
    app = create_worker_app(handler=None)
    assert app.state.handler is None
    client = TestClient(app)
    r = client.post(
        "/pubsub/push",
        json={
            "message": {
                "data": (
                    "eyJldmVudF90eXBlIjoiYW1lbmRtZW50LnJlY2VpdmVkIiwicnVuX2lkIjoi"
                    "cnVuLXgiLCJldmVudF9pZCI6ImUifQ=="
                ),
                "messageId": "1",
            }
        },
    )
    assert r.status_code == 503
    assert r.json()["error"] == "handler_not_configured"


def test_worker_app_with_handler_acks() -> None:
    store = FirestoreStateStore(client=FakeFirestore())
    store._firestore_module = FakeFirestoreModule  # type: ignore[attr-defined]
    run = WorkflowRun(
        run_id="run-1",
        study_id="AURORA-101",
        from_version="1.0",
        to_version="2.0",
        status=WorkflowStatus.CREATED,
    )
    store.save_run(run)

    class Runner:
        def start(self, envelope: EventEnvelope) -> WorkflowStatus:
            return WorkflowStatus.AWAITING_APPROVAL

        def resume(self, envelope: EventEnvelope) -> WorkflowStatus:
            return WorkflowStatus.COMPLETED

    handler = AmendmentWorkerHandler(state=store, runner=Runner())
    app = create_worker_app(handler=handler)
    assert app.state.handler is not None
    client = TestClient(app)
    from protocol215.adapters.event_bus_pubsub import encode_push_body

    body = encode_push_body(
        EventEnvelope(
            event_id="e1",
            event_type=AmendmentEventType.RECEIVED,
            run_id="run-1",
            correlation_id="c1",
        )
    )
    r = client.post("/pubsub/push", json=body)
    assert r.status_code == 200
    assert r.json()["workflow_status"] == "AWAITING_APPROVAL"


def test_fixtures_loadable() -> None:
    assert PDF_V1.is_file() and PDF_V2.is_file()
    sites = load_sites()
    parts = load_participants()
    assert len(sites) >= 1
    assert len(parts) >= 1


def test_cloud_driver_start_reads_gcs_and_updates_state(tmp_path: Path) -> None:
    """Fake GCS + memory + sqlite ADK sessions → AWAITING_APPROVAL; resume on new driver."""
    from google.adk.sessions.sqlite_session_service import SqliteSessionService

    from protocol215.adapters.fakes import FakeActionPlanner, FakeProtocolCompiler
    from protocol215.config import GeminiBackend
    from protocol215.workflow.cloud_driver import CloudWorkflowDriver

    settings = Settings(
        gemini_backend=GeminiBackend.FAKE,
        adk_session_backend=AdkSessionBackend.SQLITE,
        adk_session_sqlite_path=tmp_path / "adk.sqlite3",
        local_object_store_path=tmp_path / "obj",
    )
    state = InMemoryStateStore()
    objects = LocalFileObjectStore(tmp_path / "obj")
    events = InProcessEventBus()
    run = WorkflowRun(
        run_id="run-cloud-1",
        study_id="AURORA-101",
        from_version="1.0",
        to_version="2.0",
        status=WorkflowStatus.CREATED,
        object_keys={
            "1.0": "runs/run-cloud-1/protocols/v1.0.pdf",
            "2.0": "runs/run-cloud-1/protocols/v2.0.pdf",
        },
    )
    state.save_run(run)
    objects.put_bytes(run.object_keys["1.0"], PDF_V1.read_bytes(), content_type="application/pdf")
    objects.put_bytes(run.object_keys["2.0"], PDF_V2.read_bytes(), content_type="application/pdf")

    session_path = str(tmp_path / "adk.sqlite3")
    driver1 = CloudWorkflowDriver(
        settings=settings,
        state=state,
        objects=objects,
        events=events,
        session_service=SqliteSessionService(session_path),
        compiler=FakeProtocolCompiler(),
        planner=FakeActionPlanner(include_amber=True),
    )
    status = driver1.start(
        EventEnvelope(
            event_id="evt-start",
            event_type=AmendmentEventType.RECEIVED,
            run_id="run-cloud-1",
            correlation_id="c1",
        )
    )
    assert status == WorkflowStatus.AWAITING_APPROVAL
    meta = state.get_session_metadata("run-cloud-1")
    assert meta is not None
    assert meta.session_id
    assert meta.invocation_id
    green_before = {
        a.execution_id: a.status
        for a in state.list_actions("run-cloud-1")
        if a.authorized_tier == "GREEN" or getattr(a, "authorized_tier", None) == "GREEN"
    }
    # Destroy in-memory driver / pause cache.
    driver1.shutdown()
    del driver1

    # New worker/driver instance sharing durable stores + sqlite sessions.
    driver2 = CloudWorkflowDriver(
        settings=settings,
        state=state,
        objects=objects,
        events=events,
        session_service=SqliteSessionService(session_path),
        compiler=FakeProtocolCompiler(),
        planner=FakeActionPlanner(include_amber=True),
    )
    apr = state.list_approval_requests("run-cloud-1")
    assert apr
    status2 = driver2.resume(
        EventEnvelope(
            event_id="evt-resume",
            event_type=AmendmentEventType.RESUME,
            run_id="run-cloud-1",
            correlation_id="c2",
            approval_id=apr[0].approval_id,
            payload={"decision": "approved"},
        )
    )
    assert status2 in {
        WorkflowStatus.COMPLETED,
        WorkflowStatus.COMPLETED_WITH_BLOCKS,
        WorkflowStatus.MANIFEST_READY,
    }
    green_after = {
        a.execution_id: a.status
        for a in state.list_actions("run-cloud-1")
        if str(getattr(a, "authorized_tier", "")) == "GREEN"
    }
    # GREEN executions must not duplicate across resume.
    for eid, st in green_before.items():
        assert green_after.get(eid) == st


def test_missing_pdf_is_terminal(tmp_path: Path) -> None:
    from google.adk.sessions.sqlite_session_service import SqliteSessionService

    from protocol215.adapters.fakes import FakeProtocolCompiler
    from protocol215.config import GeminiBackend
    from protocol215.workflow.cloud_driver import CloudWorkflowDriver

    settings = Settings(
        gemini_backend=GeminiBackend.FAKE,
        adk_session_backend=AdkSessionBackend.SQLITE,
        adk_session_sqlite_path=tmp_path / "adk2.sqlite3",
        local_object_store_path=tmp_path / "obj2",
    )
    state = InMemoryStateStore()
    objects = LocalFileObjectStore(tmp_path / "obj2")
    events = InProcessEventBus()
    run = WorkflowRun(
        run_id="run-missing",
        study_id="AURORA-101",
        from_version="1.0",
        to_version="2.0",
        status=WorkflowStatus.CREATED,
        object_keys={"1.0": "runs/x/v1.pdf", "2.0": "runs/x/v2.pdf"},
    )
    state.save_run(run)
    driver = CloudWorkflowDriver(
        settings=settings,
        state=state,
        objects=objects,
        events=events,
        session_service=SqliteSessionService(str(tmp_path / "adk2.sqlite3")),
        compiler=FakeProtocolCompiler(),
    )
    status = driver.start(
        EventEnvelope(
            event_id="e",
            event_type=AmendmentEventType.RECEIVED,
            run_id="run-missing",
            correlation_id="c",
        )
    )
    assert status == WorkflowStatus.FAILED_TERMINAL
    saved = state.get_run("run-missing")
    assert saved is not None
    assert saved.failure_class == "missing_protocol_pdfs"
