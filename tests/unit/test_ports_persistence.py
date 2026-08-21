"""Unit and integration tests for ports, persistence, idempotency, and audit."""

from __future__ import annotations

from pathlib import Path

import pytest

from protocol215.adapters.audit_log import HashChainedAuditLog, verify_audit_chain
from protocol215.adapters.clock import DeterministicClock
from protocol215.adapters.event_bus_inprocess import InProcessEventBus
from protocol215.adapters.fakes import FakeActionPlanner, FakeProtocolCompiler
from protocol215.adapters.identifiers import DeterministicIdentifierGenerator
from protocol215.adapters.object_store_local import LocalFileObjectStore
from protocol215.adapters.state_store_memory import InMemoryStateStore
from protocol215.adapters.state_store_sqlite import SQLiteStateStore
from protocol215.application.hashing import build_idempotency_key
from protocol215.application.services import AmendmentAppService
from protocol215.domain.enums import ApprovalStatus
from protocol215.domain.models import ActionProposal, EvidenceReference


def _build_service(
    tmp_path: Path,
    *,
    use_sqlite: bool = False,
    db_path: Path | None = None,
) -> tuple[AmendmentAppService, DeterministicClock, StateStoreLike]:
    clock = DeterministicClock()
    ids = DeterministicIdentifierGenerator()
    state: InMemoryStateStore | SQLiteStateStore
    if use_sqlite:
        state = SQLiteStateStore(db_path or (tmp_path / "state.db"))
    else:
        state = InMemoryStateStore()
    objects = LocalFileObjectStore(tmp_path / "objects")
    events = InProcessEventBus()
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
    return service, clock, state


# Typing helper for tests
StateStoreLike = InMemoryStateStore | SQLiteStateStore


@pytest.fixture
def mem_service(
    tmp_path: Path,
) -> tuple[AmendmentAppService, DeterministicClock, InMemoryStateStore]:
    service, clock, state = _build_service(tmp_path, use_sqlite=False)
    assert isinstance(state, InMemoryStateStore)
    return service, clock, state


def test_sqlite_state_survives_process_restart(tmp_path: Path) -> None:
    db = tmp_path / "persist.db"
    service, _, state = _build_service(tmp_path, use_sqlite=True, db_path=db)
    assert isinstance(state, SQLiteStateStore)
    run = service.create_run(study_id="AURORA-101", from_version="1.0", to_version="2.0")
    service.register_protocol_artifact(
        run_id=run.run_id,
        version="1.0",
        pdf_bytes=b"%PDF-1.4 Protocol Version: 1.0 synthetic",
    )
    service.load_synthetic_study_state(run.run_id)
    state.close()

    reopened = SQLiteStateStore(db)
    loaded = reopened.get_run(run.run_id)
    assert loaded is not None
    assert loaded.study_id == "AURORA-101"
    assert reopened.get_protocol_ir(run.run_id, "1.0") is not None
    assert len(reopened.list_sites(run.run_id)) == 3
    assert reopened.get_session_metadata(run.run_id) is not None
    reopened.close()


def test_duplicate_action_execution_is_idempotent(
    mem_service: tuple[AmendmentAppService, DeterministicClock, InMemoryStateStore],
) -> None:
    service, _, state = mem_service
    run = service.create_run(study_id="AURORA-101", from_version="1.0", to_version="2.0")
    proposal = ActionProposal(
        proposal_id="prop-1",
        tool_name="update_contact_directory",
        rationale="update lab",
        evidence=[EvidenceReference(page=10, section_id="SEC-LAB-CONTACT")],
        args={"email": "lab-v2@example.test", "role": "central_lab", "run_id": run.run_id},
    )
    first = service.execute_idempotent_action(
        run_id=run.run_id,
        proposal=proposal,
        protocol_version="2.0",
        target_id="central_lab",
        mutation={"email": "lab-v2@example.test"},
    )
    second = service.execute_idempotent_action(
        run_id=run.run_id,
        proposal=proposal,
        protocol_version="2.0",
        target_id="central_lab",
        mutation={"email": "SHOULD-NOT-APPLY"},
    )
    assert second.execution_id == first.execution_id
    assert second.replayed is True
    assert second.executed_at == first.executed_at
    assert second.after.get("email") == "lab-v2@example.test"
    assert len(state.list_actions(run.run_id)) == 1
    key = build_idempotency_key(
        run_id=run.run_id,
        action_type="update_contact_directory",
        target_id="central_lab",
        protocol_version="2.0",
    )
    assert first.idempotency_key == key
    replay_events = [
        e
        for e in state.list_audit_events(run.run_id)
        if e.event_type in {"action.replay_observed", "tool.replay_observed"}
    ]
    assert len(replay_events) == 1


def test_duplicate_event_handling_is_idempotent(
    mem_service: tuple[AmendmentAppService, DeterministicClock, InMemoryStateStore],
) -> None:
    service, _, state = mem_service
    run = service.create_run(study_id="AURORA-101", from_version="1.0", to_version="2.0")
    bus = service.events
    assert isinstance(bus, InProcessEventBus)
    first = service.publish_run_event(
        run_id=run.run_id,
        event_type="amendment.received",
        idempotency_key=f"{run.run_id}:event:amendment.received:publish",
    )
    second = service.publish_run_event(
        run_id=run.run_id,
        event_type="amendment.received",
        idempotency_key=f"{run.run_id}:event:amendment.received:publish",
    )
    assert first is not None
    assert second is None
    assert len(bus.published) == 1
    assert any(e.event_type == "event.replay_observed" for e in state.list_audit_events(run.run_id))


def test_audit_tampering_is_detected(
    mem_service: tuple[AmendmentAppService, DeterministicClock, InMemoryStateStore],
) -> None:
    service, _, state = mem_service
    run = service.create_run(study_id="AURORA-101", from_version="1.0", to_version="2.0")
    service.load_synthetic_study_state(run.run_id)
    events = state.list_audit_events(run.run_id)
    ok, errors = verify_audit_chain(events)
    assert ok is True
    assert errors == []

    tampered = events[1].model_copy(update={"decision_summary": "TAMPERED SUMMARY"})
    bad_chain = [events[0], tampered, *events[2:]]
    ok2, errors2 = verify_audit_chain(bad_chain)
    assert ok2 is False
    assert any("invalid current hash" in e for e in errors2)

    broken_prev = events[1].model_copy(update={"previous_event_hash": "deadbeef" * 8})
    ok3, errors3 = verify_audit_chain([events[0], broken_prev])
    assert ok3 is False
    assert any("broken previous hash" in e for e in errors3)

    missing = (
        [events[0], events[2]]
        if len(events) > 2
        else [events[0].model_copy(update={"sequence_number": 3})]
    )
    ok4, errors4 = verify_audit_chain(missing)
    assert ok4 is False
    assert any("sequence" in e for e in errors4)


def test_deterministic_clock_produces_reproducible_audit_hashes(tmp_path: Path) -> None:
    def run_once(root: Path) -> list[str]:
        service, _, state = _build_service(root, use_sqlite=False)
        run = service.create_run(
            study_id="AURORA-101",
            from_version="1.0",
            to_version="2.0",
            run_id="run-fixed",
        )
        service.load_synthetic_study_state(run.run_id)
        return [e.current_event_hash for e in state.list_audit_events(run.run_id)]

    hashes_a = run_once(tmp_path / "a")
    hashes_b = run_once(tmp_path / "b")
    assert hashes_a == hashes_b
    assert len(hashes_a) >= 2


def test_failed_write_does_not_leave_partial_action_state(tmp_path: Path) -> None:
    db = tmp_path / "tx.db"
    store = SQLiteStateStore(db)
    clock = DeterministicClock()
    ids = DeterministicIdentifierGenerator()
    audit = HashChainedAuditLog(store, clock, ids)
    service = AmendmentAppService(
        state=store,
        objects=LocalFileObjectStore(tmp_path / "obj"),
        events=InProcessEventBus(),
        audit=audit,
        compiler=FakeProtocolCompiler(),
        planner=FakeActionPlanner(),
        clock=clock,
        ids=ids,
    )
    run = service.create_run(study_id="AURORA-101", from_version="1.0", to_version="2.0")
    proposal = ActionProposal(
        proposal_id="prop-tx",
        tool_name="update_contact_directory",
        rationale="tx test",
        evidence=[EvidenceReference(page=10, section_id="SEC-LAB-CONTACT")],
    )
    # First commit a real action via service
    action = service.execute_idempotent_action(
        run_id=run.run_id,
        proposal=proposal,
        protocol_version="2.0",
        target_id="central_lab",
    )
    assert store.get_action_by_idempotency_key(action.idempotency_key) is not None

    # Simulated transactional failure for a different key
    failing = action.model_copy(
        update={
            "execution_id": "act-fail",
            "idempotency_key": build_idempotency_key(
                run_id=run.run_id,
                action_type="reserve_sample_kits",
                target_id="SITE-001",
                protocol_version="2.0",
            ),
        }
    )
    with pytest.raises(RuntimeError, match="simulated write failure"):
        store.execute_action_transaction(
            run_id=run.run_id,
            action=failing,
            fail_after_action=True,
        )
    assert store.get_action_by_idempotency_key(failing.idempotency_key) is None
    # Original action intact
    assert store.get_action_by_idempotency_key(action.idempotency_key) is not None
    store.close()


def test_transaction_rollback_works(tmp_path: Path) -> None:
    store = SQLiteStateStore(tmp_path / "rollback.db")
    from datetime import UTC, datetime

    from protocol215.domain.enums import ActionStatus, RiskTier
    from protocol215.domain.models import ActionExecution, AuditEvent

    action = ActionExecution(
        execution_id="e-roll",
        proposal_id="p",
        tool_name="update_contact_directory",
        status=ActionStatus.EXECUTED,
        authorized_tier=RiskTier.GREEN,
        evidence=[EvidenceReference(page=10, section_id="SEC-LAB-CONTACT")],
        idempotency_key="run:update_contact_directory:x:2.0",
        executed=True,
        executed_at=datetime(2026, 8, 21, tzinfo=UTC),
        after={"ok": True},
    )
    audit_event = AuditEvent(
        event_id="aud-1",
        run_id="run-1",
        sequence_number=1,
        event_type="action.executed",
        actor="system",
        timestamp=datetime(2026, 8, 21, tzinfo=UTC),
        evidence=[],
        input_hash="a" * 64,
        output_hash="b" * 64,
        previous_event_hash="0" * 64,
        current_event_hash="c" * 64,
        decision_summary="test",
        idempotency_key=action.idempotency_key,
    )
    with pytest.raises(RuntimeError):
        store.execute_action_transaction(
            run_id="run-1",
            action=action,
            audit_event=audit_event,
            fail_after_action=True,
        )
    assert store.get_action_by_idempotency_key(action.idempotency_key) is None
    assert store.list_audit_events("run-1") == []
    store.close()


def test_application_services_happy_path(tmp_path: Path) -> None:
    service, _, state = _build_service(tmp_path, use_sqlite=True)
    run = service.create_run(study_id="AURORA-101", from_version="1.0", to_version="2.0")
    service.register_protocol_artifact(
        run_id=run.run_id,
        version="1.0",
        pdf_bytes=b"%PDF-1.4 Protocol Version: 1.0",
    )
    service.register_protocol_artifact(
        run_id=run.run_id,
        version="2.0",
        pdf_bytes=b"%PDF-1.4 Protocol Version: 2.0",
    )
    service.publish_run_event(run_id=run.run_id, event_type="amendment.received")
    service.load_synthetic_study_state(run.run_id)
    from protocol215.application.semantic_diff import diff_protocol_irs

    v1 = service.get_protocol_ir(run.run_id, "1.0")
    v2 = service.get_protocol_ir(run.run_id, "2.0")
    assert v1 and v2
    changes = diff_protocol_irs(v1, v2)
    service.save_changes(run.run_id, changes)
    from protocol215.simulator.twin import rehearse_amendment

    findings = rehearse_amendment(
        changes=changes,
        sites=state.list_sites(run.run_id),
        participants=state.list_participants(run.run_id),
    )
    service.save_findings(run.run_id, findings)
    proposals = service.propose_actions(run.run_id)
    assert proposals
    for proposal in proposals:
        service.execute_idempotent_action(
            run_id=run.run_id,
            proposal=proposal,
            protocol_version="2.0",
            target_id=proposal.site_id or proposal.tool_name,
        )
    approval = service.create_approval_request(
        run_id=run.run_id,
        action_ids=[a.execution_id for a in state.list_actions(run.run_id)],
        state_hash="hash-1",
    )
    service.record_approval(approval_id=approval.approval_id, decision=ApprovalStatus.APPROVED)
    manifest = service.generate_manifest(
        run_id=run.run_id,
        study_id="AURORA-101",
        from_version="1.0",
        to_version="2.0",
    )
    assert manifest.run_id == run.run_id
    ok, errors = service.audit.verify(run.run_id)
    assert ok, errors
    if isinstance(state, SQLiteStateStore):
        state.close()


def test_no_google_cloud_imports_in_application_services() -> None:
    import inspect

    import protocol215.application.services as services_mod

    source = inspect.getsource(services_mod)
    assert "google.cloud" not in source
    assert "from google" not in source
