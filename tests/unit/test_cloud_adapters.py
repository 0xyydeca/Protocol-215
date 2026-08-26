"""Cloud adapter unit tests — mocked / in-memory fakes (not live GCP)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from tests.unit.fakes_firestore import FakeFirestore, FakeFirestoreModule

from protocol215.adapters.event_bus_pubsub import (
    PubSubEventBus,
    encode_push_body,
    parse_pubsub_push_envelope,
)
from protocol215.adapters.object_store_gcs import GCSObjectStore, GCSObjectStoreError
from protocol215.adapters.state_store_firestore import FirestoreStateStore
from protocol215.application.hashing import sha256_hex
from protocol215.cloud.errors import RetryableWorkerError, TerminalWorkerError
from protocol215.cloud.events import AmendmentEventType, EventEnvelope
from protocol215.cloud.logging import emit_cloud_log
from protocol215.cloud.paths import manifest_html_key, manifest_json_key, protocol_pdf_key
from protocol215.cloud.worker import AmendmentWorkerHandler
from protocol215.domain.enums import ActionStatus, ApprovalStatus, RiskTier, WorkflowStatus
from protocol215.domain.models import (
    ActionExecution,
    AmendmentReleaseManifest,
    ApprovalDecision,
    ApprovalRequest,
    AuditEvent,
    WorkflowRun,
)


def _run(run_id: str = "run-1") -> WorkflowRun:
    return WorkflowRun(
        run_id=run_id,
        study_id="AURORA-101",
        from_version="1.0",
        to_version="2.0",
        status=WorkflowStatus.CREATED,
        state_version=3,
        created_at=datetime(2026, 8, 21, tzinfo=UTC),
    )


def _firestore_store() -> FirestoreStateStore:
    client = FakeFirestore()
    store = FirestoreStateStore(client=client, use_server_timestamps=True)
    store._firestore_module = FakeFirestoreModule
    return store


# --- GCS (mocked client) ---


def test_gcs_metadata_and_size_bound() -> None:
    blob = MagicMock()
    blob.exists.return_value = True
    blob.metadata = {}
    blob.content_type = "application/pdf"
    bucket = MagicMock()
    bucket.blob.return_value = blob
    client = MagicMock()
    client.bucket.return_value = bucket

    store = GCSObjectStore(
        bucket_name="protocol-215-artifacts",
        max_upload_bytes=100,
        client=client,
    )
    data = b"%PDF-1.4 tiny"
    key = store.put_protocol_pdf("run-1", "1.0", data)
    assert key == protocol_pdf_key("run-1", "1.0")
    assert blob.upload_from_string.called
    assert blob.metadata["sha256"] == sha256_hex(data)
    assert blob.metadata["access"] == "private"
    assert blob.metadata["content_type"] == "application/pdf"

    with pytest.raises(GCSObjectStoreError):
        store.put_bytes("too-big", b"x" * 200)

    store.put_manifest_json("run-1", b"{}")
    assert bucket.blob.call_args_list[-1].args[0] == manifest_json_key("run-1")
    store.put_manifest_html("run-1", b"<html></html>")
    assert bucket.blob.call_args_list[-1].args[0] == manifest_html_key("run-1")


# --- Firestore transactions (fake client) ---


def test_firestore_action_idempotency_across_restarts() -> None:
    store = _firestore_store()
    action = ActionExecution(
        execution_id="ex-1",
        proposal_id="p1",
        tool_name="create_courier_exception_task",
        status=ActionStatus.EXECUTED,
        authorized_tier=RiskTier.GREEN,
        idempotency_key="idem-courier-1",
        executed=True,
    )
    first = store.save_action_idempotent("run-1", action)
    assert first.execution_id == "ex-1"
    # Simulate adapter restart with new store instance on same fake client
    store2 = FirestoreStateStore(client=store._db, use_server_timestamps=False)
    store2._firestore_module = FakeFirestoreModule
    replay = store2.save_action_idempotent(
        "run-1",
        action.model_copy(update={"execution_id": "ex-2"}),
    )
    assert replay.execution_id == "ex-1"
    assert replay.replayed is True
    assert store2.get_action_by_idempotency_key("idem-courier-1") is not None


def test_firestore_approval_consumption_and_stale_version() -> None:
    store = _firestore_store()
    store.save_run(_run())
    store.save_approval_request(
        ApprovalRequest(
            approval_id="apr-1",
            run_id="run-1",
            action_ids=["a1"],
            status=ApprovalStatus.PENDING,
            state_hash="h",
            expected_state_version=3,
        )
    )
    decision = ApprovalDecision(
        approval_id="apr-1",
        decision=ApprovalStatus.APPROVED,
        decided_at=datetime(2026, 8, 21, tzinfo=UTC),
    )
    updated = store.consume_approval(
        approval_id="apr-1",
        decision=decision,
        expected_state_version=3,
        run_id="run-1",
    )
    assert updated.status == ApprovalStatus.APPROVED

    with pytest.raises(ValueError, match="already consumed"):
        store.consume_approval(
            approval_id="apr-1",
            decision=decision,
            expected_state_version=3,
            run_id="run-1",
        )


def test_firestore_manifest_finalization_state_version() -> None:
    store = _firestore_store()
    store.save_run(_run())
    manifest = AmendmentReleaseManifest(
        run_id="run-1",
        study_id="AURORA-101",
        from_version="1.0",
        to_version="2.0",
    )
    saved = store.finalize_manifest(manifest, expected_state_version=3)
    assert saved.run_id == "run-1"
    again = store.finalize_manifest(manifest, expected_state_version=3)
    assert again.run_id == "run-1"
    with pytest.raises(ValueError, match="state version"):
        store.finalize_manifest(manifest, expected_state_version=99)


def test_firestore_audit_persistence() -> None:
    store = _firestore_store()
    event = AuditEvent(
        event_id="audit-1",
        run_id="run-1",
        sequence_number=1,
        event_type="tool.executed",
        actor="system",
        timestamp=datetime(2026, 8, 21, tzinfo=UTC),
        input_hash="a",
        output_hash="b",
        previous_event_hash="0" * 64,
        current_event_hash="c" * 64,
        decision_summary="ok",
    )
    store.append_audit_event(event)
    events = store.list_audit_events("run-1")
    assert len(events) == 1
    assert events[0].event_type == "tool.executed"


# --- Pub/Sub envelope ---


def test_malformed_pubsub_envelope() -> None:
    with pytest.raises(TerminalWorkerError, match="malformed"):
        parse_pubsub_push_envelope({})
    with pytest.raises(TerminalWorkerError, match="malformed"):
        parse_pubsub_push_envelope({"message": {"data": "!!!"}})


def test_duplicate_pubsub_event() -> None:
    store = _firestore_store()
    store.save_run(_run())

    class Runner:
        def __init__(self) -> None:
            self.starts = 0

        def start(self, envelope: EventEnvelope) -> WorkflowStatus:
            self.starts += 1
            return WorkflowStatus.AWAITING_APPROVAL

        def resume(self, envelope: EventEnvelope) -> WorkflowStatus:
            return WorkflowStatus.COMPLETED

    runner = Runner()
    handler = AmendmentWorkerHandler(state=store, runner=runner)
    env = EventEnvelope(
        event_id="evt-1",
        event_type=AmendmentEventType.RECEIVED,
        run_id="run-1",
        correlation_id="corr-1",
    )
    r1 = handler.handle(env)
    r2 = handler.handle(env)
    assert r1.duplicate is False
    assert r2.duplicate is True
    assert runner.starts == 1


def test_start_and_resume_events() -> None:
    store = _firestore_store()
    store.save_run(_run())

    class Runner:
        def start(self, envelope: EventEnvelope) -> WorkflowStatus:
            assert envelope.event_type == AmendmentEventType.RECEIVED
            return WorkflowStatus.AWAITING_APPROVAL

        def resume(self, envelope: EventEnvelope) -> WorkflowStatus:
            assert envelope.approval_id == "apr-9"
            return WorkflowStatus.COMPLETED

    handler = AmendmentWorkerHandler(state=store, runner=Runner())
    start = handler.handle(
        EventEnvelope(
            event_id="e-start",
            event_type=AmendmentEventType.RECEIVED,
            run_id="run-1",
            correlation_id="c1",
        )
    )
    assert start.status == WorkflowStatus.AWAITING_APPROVAL
    resume = handler.handle(
        EventEnvelope(
            event_id="e-resume",
            event_type=AmendmentEventType.RESUME,
            run_id="run-1",
            approval_id="apr-9",
            correlation_id="c2",
        )
    )
    assert resume.status == WorkflowStatus.COMPLETED


def test_retryable_and_terminal_worker_errors() -> None:
    store = _firestore_store()
    store.save_run(_run())

    class RetryRunner:
        def start(self, envelope: EventEnvelope) -> WorkflowStatus:
            return WorkflowStatus.FAILED_RETRYABLE

        def resume(self, envelope: EventEnvelope) -> WorkflowStatus:
            return WorkflowStatus.COMPLETED

    handler = AmendmentWorkerHandler(state=store, runner=RetryRunner())
    with pytest.raises(RetryableWorkerError):
        handler.handle(
            EventEnvelope(
                event_id="e-r",
                event_type=AmendmentEventType.RECEIVED,
                run_id="run-1",
                correlation_id="c",
            )
        )

    with pytest.raises(TerminalWorkerError, match="run not found"):
        handler.handle(
            EventEnvelope(
                event_id="e-x",
                event_type=AmendmentEventType.RECEIVED,
                run_id="missing",
                correlation_id="c",
            )
        )


def test_worker_http_push_endpoint() -> None:
    store = _firestore_store()
    store.save_run(_run())

    class Runner:
        def start(self, envelope: EventEnvelope) -> WorkflowStatus:
            return WorkflowStatus.AWAITING_APPROVAL

        def resume(self, envelope: EventEnvelope) -> WorkflowStatus:
            return WorkflowStatus.COMPLETED

    from apps.worker.main import create_worker_app

    app = create_worker_app(
        handler=AmendmentWorkerHandler(state=store, runner=Runner()),
        require_oidc=False,
    )
    client = TestClient(app)
    assert client.get("/healthz").status_code == 200

    env = EventEnvelope(
        event_id="evt-http",
        event_type=AmendmentEventType.RECEIVED,
        run_id="run-1",
        correlation_id="corr-http",
    )
    resp = client.post("/pubsub/push", json=encode_push_body(env))
    assert resp.status_code == 200
    assert resp.json()["workflow_status"] == "AWAITING_APPROVAL"

    bad = client.post("/pubsub/push", json={"nope": True})
    assert bad.status_code == 200
    assert bad.json()["retryable"] is False


def test_pubsub_publisher_attributes() -> None:
    publisher = MagicMock()
    future = MagicMock()
    future.result.return_value = "msg-id"
    publisher.publish.return_value = future
    bus = PubSubEventBus(
        project="demo-proj",
        topic_received="amendment-received",
        topic_resume="amendment-resume",
        publisher=publisher,
    )
    from protocol215.domain.models import DomainEvent

    bus.publish(
        DomainEvent(
            event_id="evt-p",
            event_type="amendment.received",
            run_id="run-1",
            payload={"correlation_id": "corr-p"},
        )
    )
    assert publisher.publish.called
    args, kwargs = publisher.publish.call_args
    assert "amendment-received" in args[0]
    assert kwargs["event_type"] == "amendment.received"
    assert kwargs["correlation_id"] == "corr-p"


def test_cloud_log_redacts_sensitive_fields(capsys: pytest.CaptureFixture[str]) -> None:
    emit_cloud_log(
        severity="INFO",
        message="safe",
        run_id="run-1",
        pdf_bytes=b"secret-pdf",
        credentials={"token": "x"},
        correlation_id="c",
        outcome="ok",
    )
    out = capsys.readouterr().out
    assert "secret-pdf" not in out
    assert "[REDACTED]" in out or "bytes:" in out
