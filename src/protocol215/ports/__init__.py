"""Application port protocols — no Google Cloud SDK imports."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from protocol215.domain.models import (
    ActionExecution,
    ActionProposal,
    AmendmentReleaseManifest,
    ApprovalDecision,
    ApprovalRequest,
    AuditEvent,
    DomainEvent,
    ParticipantState,
    ProtocolArtifactRecord,
    ProtocolIR,
    RehearsalFinding,
    SemanticChange,
    SessionMetadata,
    SiteState,
    WorkflowRun,
)


@runtime_checkable
class HealthProbe(Protocol):
    name: str

    def check(self) -> tuple[bool, str]: ...


@runtime_checkable
class ObjectStore(Protocol):
    def put_bytes(
        self, key: str, data: bytes, *, content_type: str = "application/octet-stream"
    ) -> str: ...

    def get_bytes(self, key: str) -> bytes: ...

    def exists(self, key: str) -> bool: ...


@runtime_checkable
class StateStore(Protocol):
    def save_run(self, run: WorkflowRun) -> None: ...

    def get_run(self, run_id: str) -> WorkflowRun | None: ...

    def list_runs(self) -> list[WorkflowRun]: ...

    def save_protocol_artifact(self, artifact: ProtocolArtifactRecord) -> None: ...

    def list_protocol_artifacts(self, run_id: str) -> list[ProtocolArtifactRecord]: ...

    def save_protocol_ir(self, run_id: str, version: str, ir: ProtocolIR) -> None: ...

    def get_protocol_ir(self, run_id: str, version: str) -> ProtocolIR | None: ...

    def save_changes(self, run_id: str, changes: list[SemanticChange]) -> None: ...

    def list_changes(self, run_id: str) -> list[SemanticChange]: ...

    def save_sites(self, run_id: str, sites: list[SiteState]) -> None: ...

    def list_sites(self, run_id: str) -> list[SiteState]: ...

    def save_participants(self, run_id: str, participants: list[ParticipantState]) -> None: ...

    def list_participants(self, run_id: str) -> list[ParticipantState]: ...

    def save_findings(self, run_id: str, findings: list[RehearsalFinding]) -> None: ...

    def list_findings(self, run_id: str) -> list[RehearsalFinding]: ...

    def save_action(self, run_id: str, action: ActionExecution) -> None: ...

    def get_action_by_idempotency_key(self, idempotency_key: str) -> ActionExecution | None: ...

    def list_actions(self, run_id: str) -> list[ActionExecution]: ...

    def save_approval_request(self, request: ApprovalRequest) -> None: ...

    def get_approval_request(self, approval_id: str) -> ApprovalRequest | None: ...

    def list_approval_requests(self, run_id: str) -> list[ApprovalRequest]: ...

    def save_approval_decision(self, decision: ApprovalDecision) -> None: ...

    def get_approval_decision(self, approval_id: str) -> ApprovalDecision | None: ...

    def append_audit_event(self, event: AuditEvent) -> None: ...

    def list_audit_events(self, run_id: str) -> list[AuditEvent]: ...

    def save_manifest(self, manifest: AmendmentReleaseManifest) -> None: ...

    def get_manifest(self, run_id: str) -> AmendmentReleaseManifest | None: ...

    def save_session_metadata(self, meta: SessionMetadata) -> None: ...

    def get_session_metadata(self, run_id: str) -> SessionMetadata | None: ...

    def record_processed_event(self, idempotency_key: str, event_id: str) -> bool:
        """Return True if newly recorded, False if already processed."""
        ...


@runtime_checkable
class EventBus(Protocol):
    def publish(self, event: DomainEvent) -> None: ...

    def subscribe(self, event_type: str, handler: Any) -> None: ...


@runtime_checkable
class ProtocolCompiler(Protocol):
    def compile(
        self,
        *,
        pdf_bytes: bytes | None = None,
        pdf_path: str | None = None,
        gcs_uri: str | None = None,
        version_hint: str | None = None,
    ) -> ProtocolIR: ...


@runtime_checkable
class ChangeExplainer(Protocol):
    """Gemini (or fake) explanations only — never mutates deterministic changes."""

    def explain_changes(
        self,
        *,
        changes: list[SemanticChange],
        old_ir: ProtocolIR,
        new_ir: ProtocolIR,
    ) -> dict[str, str]:
        """Return mapping change_id → concise explanation text."""
        ...


@runtime_checkable
class ActionPlanner(Protocol):
    def propose(
        self,
        *,
        run: WorkflowRun,
        changes: list[SemanticChange],
        findings: list[RehearsalFinding],
    ) -> list[ActionProposal]: ...


@runtime_checkable
class AuditLog(Protocol):
    def append(
        self,
        *,
        run_id: str,
        event_type: str,
        actor: str,
        decision_summary: str,
        evidence: list[Any] | None = None,
        input_payload: dict[str, Any] | None = None,
        output_payload: dict[str, Any] | None = None,
        action_id: str | None = None,
        tool_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> AuditEvent: ...

    def list_events(self, run_id: str) -> list[AuditEvent]: ...

    def verify(self, run_id: str) -> tuple[bool, list[str]]: ...


@runtime_checkable
class Clock(Protocol):
    def now(self) -> datetime: ...


@runtime_checkable
class IdentifierGenerator(Protocol):
    def new_id(self, prefix: str = "") -> str: ...
