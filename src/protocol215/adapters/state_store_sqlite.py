"""SQLite-backed state store for local development."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from protocol215.domain.models import (
    ActionExecution,
    AmendmentReleaseManifest,
    ApprovalDecision,
    ApprovalRequest,
    AuditEvent,
    ParticipantState,
    ProtocolArtifactRecord,
    ProtocolIR,
    RehearsalFinding,
    SemanticChange,
    SessionMetadata,
    SiteState,
    WorkflowRun,
)

T = TypeVar("T", bound=BaseModel)

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
  run_id TEXT PRIMARY KEY,
  payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS protocol_artifacts (
  run_id TEXT NOT NULL,
  version TEXT NOT NULL,
  payload TEXT NOT NULL,
  PRIMARY KEY (run_id, version)
);
CREATE TABLE IF NOT EXISTS protocol_irs (
  run_id TEXT NOT NULL,
  version TEXT NOT NULL,
  payload TEXT NOT NULL,
  PRIMARY KEY (run_id, version)
);
CREATE TABLE IF NOT EXISTS semantic_changes (
  run_id TEXT NOT NULL,
  change_id TEXT NOT NULL,
  payload TEXT NOT NULL,
  PRIMARY KEY (run_id, change_id)
);
CREATE TABLE IF NOT EXISTS sites (
  run_id TEXT NOT NULL,
  site_id TEXT NOT NULL,
  payload TEXT NOT NULL,
  PRIMARY KEY (run_id, site_id)
);
CREATE TABLE IF NOT EXISTS participants (
  run_id TEXT NOT NULL,
  participant_id TEXT NOT NULL,
  payload TEXT NOT NULL,
  PRIMARY KEY (run_id, participant_id)
);
CREATE TABLE IF NOT EXISTS findings (
  run_id TEXT NOT NULL,
  finding_id TEXT NOT NULL,
  payload TEXT NOT NULL,
  PRIMARY KEY (run_id, finding_id)
);
CREATE TABLE IF NOT EXISTS actions (
  run_id TEXT NOT NULL,
  execution_id TEXT NOT NULL,
  idempotency_key TEXT NOT NULL UNIQUE,
  payload TEXT NOT NULL,
  PRIMARY KEY (run_id, execution_id)
);
CREATE TABLE IF NOT EXISTS approvals (
  approval_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL,
  payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS approval_decisions (
  approval_id TEXT PRIMARY KEY,
  payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_events (
  run_id TEXT NOT NULL,
  sequence_number INTEGER NOT NULL,
  event_id TEXT NOT NULL UNIQUE,
  payload TEXT NOT NULL,
  PRIMARY KEY (run_id, sequence_number)
);
CREATE TABLE IF NOT EXISTS manifests (
  run_id TEXT PRIMARY KEY,
  payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS session_metadata (
  run_id TEXT PRIMARY KEY,
  payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS processed_events (
  idempotency_key TEXT PRIMARY KEY,
  event_id TEXT NOT NULL
);
"""


class SQLiteStateStore:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        try:
            yield self._conn
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise

    def _upsert(self, sql: str, params: tuple[Any, ...]) -> None:
        with self.transaction():
            self._conn.execute(sql, params)

    def _fetchone_model(self, sql: str, params: tuple[Any, ...], model: type[T]) -> T | None:
        row = self._conn.execute(sql, params).fetchone()
        if row is None:
            return None
        return model.model_validate_json(row["payload"])

    def _fetchall_model(self, sql: str, params: tuple[Any, ...], model: type[T]) -> list[T]:
        rows = self._conn.execute(sql, params).fetchall()
        return [model.model_validate_json(r["payload"]) for r in rows]

    def save_run(self, run: WorkflowRun) -> None:
        self._upsert(
            "INSERT INTO runs(run_id, payload) VALUES(?, ?) "
            "ON CONFLICT(run_id) DO UPDATE SET payload=excluded.payload",
            (run.run_id, run.model_dump_json()),
        )

    def get_run(self, run_id: str) -> WorkflowRun | None:
        return self._fetchone_model(
            "SELECT payload FROM runs WHERE run_id=?", (run_id,), WorkflowRun
        )

    def list_runs(self) -> list[WorkflowRun]:
        return self._fetchall_model("SELECT payload FROM runs ORDER BY run_id", (), WorkflowRun)

    def save_protocol_artifact(self, artifact: ProtocolArtifactRecord) -> None:
        self._upsert(
            "INSERT INTO protocol_artifacts(run_id, version, payload) VALUES(?, ?, ?) "
            "ON CONFLICT(run_id, version) DO UPDATE SET payload=excluded.payload",
            (artifact.run_id, artifact.version, artifact.model_dump_json()),
        )

    def list_protocol_artifacts(self, run_id: str) -> list[ProtocolArtifactRecord]:
        return self._fetchall_model(
            "SELECT payload FROM protocol_artifacts WHERE run_id=? ORDER BY version",
            (run_id,),
            ProtocolArtifactRecord,
        )

    def save_protocol_ir(self, run_id: str, version: str, ir: ProtocolIR) -> None:
        self._upsert(
            "INSERT INTO protocol_irs(run_id, version, payload) VALUES(?, ?, ?) "
            "ON CONFLICT(run_id, version) DO UPDATE SET payload=excluded.payload",
            (run_id, version, ir.model_dump_json()),
        )

    def get_protocol_ir(self, run_id: str, version: str) -> ProtocolIR | None:
        return self._fetchone_model(
            "SELECT payload FROM protocol_irs WHERE run_id=? AND version=?",
            (run_id, version),
            ProtocolIR,
        )

    def save_changes(self, run_id: str, changes: list[SemanticChange]) -> None:
        with self.transaction():
            self._conn.execute("DELETE FROM semantic_changes WHERE run_id=?", (run_id,))
            for change in changes:
                self._conn.execute(
                    "INSERT INTO semantic_changes(run_id, change_id, payload) VALUES(?, ?, ?)",
                    (run_id, change.change_id, change.model_dump_json()),
                )

    def list_changes(self, run_id: str) -> list[SemanticChange]:
        return self._fetchall_model(
            "SELECT payload FROM semantic_changes WHERE run_id=? ORDER BY change_id",
            (run_id,),
            SemanticChange,
        )

    def save_sites(self, run_id: str, sites: list[SiteState]) -> None:
        with self.transaction():
            self._conn.execute("DELETE FROM sites WHERE run_id=?", (run_id,))
            for site in sites:
                self._conn.execute(
                    "INSERT INTO sites(run_id, site_id, payload) VALUES(?, ?, ?)",
                    (run_id, site.site_id, site.model_dump_json()),
                )

    def list_sites(self, run_id: str) -> list[SiteState]:
        return self._fetchall_model(
            "SELECT payload FROM sites WHERE run_id=? ORDER BY site_id",
            (run_id,),
            SiteState,
        )

    def save_participants(self, run_id: str, participants: list[ParticipantState]) -> None:
        with self.transaction():
            self._conn.execute("DELETE FROM participants WHERE run_id=?", (run_id,))
            for participant in participants:
                self._conn.execute(
                    "INSERT INTO participants(run_id, participant_id, payload) VALUES(?, ?, ?)",
                    (run_id, participant.participant_id, participant.model_dump_json()),
                )

    def list_participants(self, run_id: str) -> list[ParticipantState]:
        return self._fetchall_model(
            "SELECT payload FROM participants WHERE run_id=? ORDER BY participant_id",
            (run_id,),
            ParticipantState,
        )

    def save_findings(self, run_id: str, findings: list[RehearsalFinding]) -> None:
        with self.transaction():
            self._conn.execute("DELETE FROM findings WHERE run_id=?", (run_id,))
            for finding in findings:
                self._conn.execute(
                    "INSERT INTO findings(run_id, finding_id, payload) VALUES(?, ?, ?)",
                    (run_id, finding.finding_id, finding.model_dump_json()),
                )

    def list_findings(self, run_id: str) -> list[RehearsalFinding]:
        return self._fetchall_model(
            "SELECT payload FROM findings WHERE run_id=? ORDER BY finding_id",
            (run_id,),
            RehearsalFinding,
        )

    def save_action(self, run_id: str, action: ActionExecution) -> None:
        self._upsert(
            "INSERT INTO actions(run_id, execution_id, idempotency_key, payload) "
            "VALUES(?, ?, ?, ?) "
            "ON CONFLICT(idempotency_key) DO UPDATE SET "
            "payload=excluded.payload, execution_id=excluded.execution_id, run_id=excluded.run_id",
            (run_id, action.execution_id, action.idempotency_key, action.model_dump_json()),
        )

    def get_action_by_idempotency_key(self, idempotency_key: str) -> ActionExecution | None:
        return self._fetchone_model(
            "SELECT payload FROM actions WHERE idempotency_key=?",
            (idempotency_key,),
            ActionExecution,
        )

    def list_actions(self, run_id: str) -> list[ActionExecution]:
        return self._fetchall_model(
            "SELECT payload FROM actions WHERE run_id=? ORDER BY execution_id",
            (run_id,),
            ActionExecution,
        )

    def save_approval_request(self, request: ApprovalRequest) -> None:
        self._upsert(
            "INSERT INTO approvals(approval_id, run_id, payload) VALUES(?, ?, ?) "
            "ON CONFLICT(approval_id) DO UPDATE SET "
            "payload=excluded.payload, run_id=excluded.run_id",
            (request.approval_id, request.run_id, request.model_dump_json()),
        )

    def get_approval_request(self, approval_id: str) -> ApprovalRequest | None:
        return self._fetchone_model(
            "SELECT payload FROM approvals WHERE approval_id=?",
            (approval_id,),
            ApprovalRequest,
        )

    def list_approval_requests(self, run_id: str) -> list[ApprovalRequest]:
        return self._fetchall_model(
            "SELECT payload FROM approvals WHERE run_id=?",
            (run_id,),
            ApprovalRequest,
        )

    def save_approval_decision(self, decision: ApprovalDecision) -> None:
        self._upsert(
            "INSERT INTO approval_decisions(approval_id, payload) VALUES(?, ?) "
            "ON CONFLICT(approval_id) DO UPDATE SET payload=excluded.payload",
            (decision.approval_id, decision.model_dump_json()),
        )

    def get_approval_decision(self, approval_id: str) -> ApprovalDecision | None:
        return self._fetchone_model(
            "SELECT payload FROM approval_decisions WHERE approval_id=?",
            (approval_id,),
            ApprovalDecision,
        )

    def append_audit_event(self, event: AuditEvent) -> None:
        self._upsert(
            "INSERT INTO audit_events(run_id, sequence_number, event_id, payload) "
            "VALUES(?, ?, ?, ?)",
            (event.run_id, event.sequence_number, event.event_id, event.model_dump_json()),
        )

    def list_audit_events(self, run_id: str) -> list[AuditEvent]:
        return self._fetchall_model(
            "SELECT payload FROM audit_events WHERE run_id=? ORDER BY sequence_number",
            (run_id,),
            AuditEvent,
        )

    def save_manifest(self, manifest: AmendmentReleaseManifest) -> None:
        self._upsert(
            "INSERT INTO manifests(run_id, payload) VALUES(?, ?) "
            "ON CONFLICT(run_id) DO UPDATE SET payload=excluded.payload",
            (manifest.run_id, manifest.model_dump_json()),
        )

    def get_manifest(self, run_id: str) -> AmendmentReleaseManifest | None:
        return self._fetchone_model(
            "SELECT payload FROM manifests WHERE run_id=?",
            (run_id,),
            AmendmentReleaseManifest,
        )

    def save_session_metadata(self, meta: SessionMetadata) -> None:
        self._upsert(
            "INSERT INTO session_metadata(run_id, payload) VALUES(?, ?) "
            "ON CONFLICT(run_id) DO UPDATE SET payload=excluded.payload",
            (meta.run_id, meta.model_dump_json()),
        )

    def get_session_metadata(self, run_id: str) -> SessionMetadata | None:
        return self._fetchone_model(
            "SELECT payload FROM session_metadata WHERE run_id=?",
            (run_id,),
            SessionMetadata,
        )

    def record_processed_event(self, idempotency_key: str, event_id: str) -> bool:
        try:
            with self.transaction():
                self._conn.execute(
                    "INSERT INTO processed_events(idempotency_key, event_id) VALUES(?, ?)",
                    (idempotency_key, event_id),
                )
            return True
        except sqlite3.IntegrityError:
            return False

    def clear_processed_event(self, idempotency_key: str) -> None:
        with self.transaction():
            self._conn.execute(
                "DELETE FROM processed_events WHERE idempotency_key = ?",
                (idempotency_key,),
            )

    def execute_action_transaction(
        self,
        *,
        run_id: str,
        action: ActionExecution,
        audit_event: AuditEvent | None = None,
        fail_after_action: bool = False,
    ) -> None:
        """Persist action (+ optional audit) atomically; used to test rollback."""
        with self.transaction():
            self._conn.execute(
                "INSERT INTO actions(run_id, execution_id, idempotency_key, payload) "
                "VALUES(?, ?, ?, ?) "
                "ON CONFLICT(idempotency_key) DO UPDATE SET payload=excluded.payload, "
                "execution_id=excluded.execution_id, run_id=excluded.run_id",
                (run_id, action.execution_id, action.idempotency_key, action.model_dump_json()),
            )
            if fail_after_action:
                raise RuntimeError("simulated write failure")
            if audit_event is not None:
                self._conn.execute(
                    "INSERT INTO audit_events(run_id, sequence_number, event_id, payload) "
                    "VALUES(?, ?, ?, ?)",
                    (
                        audit_event.run_id,
                        audit_event.sequence_number,
                        audit_event.event_id,
                        audit_event.model_dump_json(),
                    ),
                )
