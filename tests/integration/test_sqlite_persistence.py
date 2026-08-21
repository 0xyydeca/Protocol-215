"""Integration tests for SQLite persistence across reopen."""

from __future__ import annotations

from pathlib import Path

from protocol215.adapters.audit_log import HashChainedAuditLog
from protocol215.adapters.clock import DeterministicClock
from protocol215.adapters.event_bus_inprocess import InProcessEventBus
from protocol215.adapters.fakes import FakeActionPlanner, FakeProtocolCompiler
from protocol215.adapters.identifiers import DeterministicIdentifierGenerator
from protocol215.adapters.object_store_local import LocalFileObjectStore
from protocol215.adapters.state_store_sqlite import SQLiteStateStore
from protocol215.application.services import AmendmentAppService
from protocol215.domain.models import ActionProposal, EvidenceReference


def test_sqlite_integration_restart_and_idempotency(tmp_path: Path) -> None:
    db = tmp_path / "integration.db"

    def make_service(store: SQLiteStateStore) -> AmendmentAppService:
        clock = DeterministicClock()
        ids = DeterministicIdentifierGenerator()
        return AmendmentAppService(
            state=store,
            objects=LocalFileObjectStore(tmp_path / "objects"),
            events=InProcessEventBus(),
            audit=HashChainedAuditLog(store, clock, ids),
            compiler=FakeProtocolCompiler(),
            planner=FakeActionPlanner(),
            clock=clock,
            ids=ids,
        )

    store1 = SQLiteStateStore(db)
    svc1 = make_service(store1)
    run = svc1.create_run(
        study_id="AURORA-101",
        from_version="1.0",
        to_version="2.0",
        run_id="run-int-1",
    )
    proposal = ActionProposal(
        proposal_id="p1",
        tool_name="update_contact_directory",
        rationale="lab",
        evidence=[EvidenceReference(page=10, section_id="SEC-LAB-CONTACT")],
        args={"email": "lab-v2@example.test", "role": "central_lab"},
    )
    first = svc1.execute_idempotent_action(
        run_id=run.run_id,
        proposal=proposal,
        protocol_version="2.0",
        target_id="central_lab",
        mutation={"email": "lab-v2@example.test"},
    )
    store1.close()

    store2 = SQLiteStateStore(db)
    svc2 = make_service(store2)
    second = svc2.execute_idempotent_action(
        run_id=run.run_id,
        proposal=proposal,
        protocol_version="2.0",
        target_id="central_lab",
        mutation={"email": "SHOULD-NOT-APPLY"},
    )
    assert second.execution_id == first.execution_id
    assert second.replayed is True
    assert second.after.get("email") == "lab-v2@example.test"
    assert second.executed_at == first.executed_at
    ok, errors = svc2.audit.verify(run.run_id)
    assert ok, errors
    store2.close()
