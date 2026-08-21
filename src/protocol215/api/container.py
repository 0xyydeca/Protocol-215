"""Shared application container for the API process."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from protocol215.adapters.audit_log import HashChainedAuditLog
from protocol215.adapters.clock import SystemClock
from protocol215.adapters.event_bus_inprocess import InProcessEventBus
from protocol215.adapters.fakes import FakeActionPlanner, FakeProtocolCompiler
from protocol215.adapters.identifiers import UUIDIdentifierGenerator
from protocol215.adapters.object_store_local import LocalFileObjectStore
from protocol215.adapters.state_store_firestore import FirestoreStateStore
from protocol215.adapters.state_store_memory import InMemoryStateStore
from protocol215.adapters.state_store_sqlite import SQLiteStateStore
from protocol215.application.demo_reset import (
    DemoResetResult,
    clear_firestore_demo_collections,
    clear_local_object_runs,
    fixture_inventory_paths,
    require_cloud_confirmation,
    twin_baseline_snapshot,
)
from protocol215.application.services import AmendmentAppService
from protocol215.config import Settings, StateStoreBackend
from protocol215.ports import EventBus, ObjectStore, StateStore


@dataclass
class AppContainer:
    settings: Settings
    state: StateStore
    objects: ObjectStore
    events: EventBus
    service: AmendmentAppService
    # Content-hash → run_id for duplicate submission detection
    submission_index: dict[str, str] = field(default_factory=dict)
    # Last twin baseline after reset (for demo UI / reset response)
    last_twin_snapshot: dict = field(default_factory=dict)

    def reset(self, *, confirmed: bool = False) -> DemoResetResult:
        """
        Clear Protocol 215 synthetic demo state only.

        Preserves: GCP infra, fixtures/ source PDFs & twin JSON.
        Restores: twin baseline counts from fixtures (sites, participants, logistics).
        """
        require_cloud_confirmation(self.settings, confirmed=confirmed)

        fixtures_short: list[str] = []
        root = Path(__file__).resolve().parents[3]
        for p in fixture_inventory_paths():
            try:
                fixtures_short.append(str(p.relative_to(root)))
            except ValueError:
                fixtures_short.append(str(p))

        runs_before = 0
        try:
            runs_before = len(self.state.list_runs())
        except Exception:  # noqa: BLE001
            runs_before = 0

        objects_cleared = 0

        if isinstance(self.state, InMemoryStateStore):
            self.state.runs.clear()
            self.state.artifacts.clear()
            self.state.irs.clear()
            self.state.changes.clear()
            self.state.sites.clear()
            self.state.participants.clear()
            self.state.findings.clear()
            self.state.actions.clear()
            self.state.actions_by_key.clear()
            self.state.approvals.clear()
            self.state.approval_decisions.clear()
            self.state.audit.clear()
            self.state.manifests.clear()
            self.state.sessions.clear()
            self.state.processed_events.clear()
        elif isinstance(self.state, SQLiteStateStore):
            path = Path(self.settings.sqlite_path)
            self.state.close()
            if path.exists():
                path.unlink()
            self.state = SQLiteStateStore(path)
            self._rebind_service_state()
        elif isinstance(self.state, FirestoreStateStore):
            deleted = clear_firestore_demo_collections(self.state._db)  # noqa: SLF001
            objects_cleared += deleted

        if isinstance(self.objects, LocalFileObjectStore):
            objects_cleared += clear_local_object_runs(
                Path(self.settings.local_object_store_path)
            )
            Path(self.settings.local_object_store_path).mkdir(parents=True, exist_ok=True)

        self.submission_index.clear()
        twin = twin_baseline_snapshot()
        self.last_twin_snapshot = twin

        return DemoResetResult(
            ok=True,
            message=(
                "Demo state cleared. Twin baseline restored from fixtures "
                f"({twin['site_count']} sites, {twin['participant_count']} participants). "
                "Source protocol PDFs preserved."
            ),
            sites_restored=int(twin["site_count"]),
            participants_restored=int(twin["participant_count"]),
            runs_cleared=runs_before,
            objects_cleared=objects_cleared,
            fixtures_preserved=fixtures_short[:40],
            twin_snapshot=twin,
            details={"execution_mode": self.settings.execution_mode},
        )

    def _rebind_service_state(self) -> None:
        self.service.state = self.state
        self.service.audit = HashChainedAuditLog(
            self.state, self.service.clock, self.service.ids
        )
        self.service.tools.state = self.state  # type: ignore[attr-defined]
        self.service.tools.audit = self.service.audit  # type: ignore[attr-defined]


def build_container(settings: Settings) -> AppContainer:
    settings.local_object_store_path.mkdir(parents=True, exist_ok=True)
    objects: ObjectStore = LocalFileObjectStore(settings.local_object_store_path)
    if settings.state_store_backend == StateStoreBackend.SQLITE:
        settings.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        state: StateStore = SQLiteStateStore(settings.sqlite_path)
    else:
        state = InMemoryStateStore()
    events: EventBus = InProcessEventBus()
    clock = SystemClock()
    ids = UUIDIdentifierGenerator()
    audit = HashChainedAuditLog(state, clock, ids)
    service = AmendmentAppService(
        state=state,
        objects=objects,
        events=events,
        audit=audit,
        compiler=FakeProtocolCompiler(),
        planner=FakeActionPlanner(include_amber=True),
        clock=clock,
        ids=ids,
    )
    return AppContainer(
        settings=settings,
        state=state,
        objects=objects,
        events=events,
        service=service,
    )


def submission_fingerprint(old_sha: str, new_sha: str, study_id: str) -> str:
    return f"{study_id}:{old_sha}:{new_sha}"
