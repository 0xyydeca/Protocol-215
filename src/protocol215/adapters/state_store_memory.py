"""In-memory state store for tests."""

from __future__ import annotations

from copy import deepcopy

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


class InMemoryStateStore:
    def __init__(self) -> None:
        self.runs: dict[str, WorkflowRun] = {}
        self.artifacts: dict[str, list[ProtocolArtifactRecord]] = {}
        self.irs: dict[tuple[str, str], ProtocolIR] = {}
        self.changes: dict[str, list[SemanticChange]] = {}
        self.sites: dict[str, list[SiteState]] = {}
        self.participants: dict[str, list[ParticipantState]] = {}
        self.findings: dict[str, list[RehearsalFinding]] = {}
        self.actions: dict[str, list[ActionExecution]] = {}
        self.actions_by_key: dict[str, ActionExecution] = {}
        self.approvals: dict[str, ApprovalRequest] = {}
        self.approval_decisions: dict[str, ApprovalDecision] = {}
        self.audit: dict[str, list[AuditEvent]] = {}
        self.manifests: dict[str, AmendmentReleaseManifest] = {}
        self.sessions: dict[str, SessionMetadata] = {}
        self.processed_events: dict[str, str] = {}

    def save_run(self, run: WorkflowRun) -> None:
        self.runs[run.run_id] = run.model_copy(deep=True)

    def get_run(self, run_id: str) -> WorkflowRun | None:
        run = self.runs.get(run_id)
        return run.model_copy(deep=True) if run else None

    def list_runs(self) -> list[WorkflowRun]:
        return [
            r.model_copy(deep=True) for r in sorted(self.runs.values(), key=lambda x: x.created_at)
        ]

    def save_protocol_artifact(self, artifact: ProtocolArtifactRecord) -> None:
        self.artifacts.setdefault(artifact.run_id, []).append(artifact.model_copy(deep=True))

    def list_protocol_artifacts(self, run_id: str) -> list[ProtocolArtifactRecord]:
        return [a.model_copy(deep=True) for a in self.artifacts.get(run_id, [])]

    def save_protocol_ir(self, run_id: str, version: str, ir: ProtocolIR) -> None:
        self.irs[(run_id, version)] = ir.model_copy(deep=True)

    def get_protocol_ir(self, run_id: str, version: str) -> ProtocolIR | None:
        ir = self.irs.get((run_id, version))
        return ir.model_copy(deep=True) if ir else None

    def save_changes(self, run_id: str, changes: list[SemanticChange]) -> None:
        self.changes[run_id] = [c.model_copy(deep=True) for c in changes]

    def list_changes(self, run_id: str) -> list[SemanticChange]:
        return [c.model_copy(deep=True) for c in self.changes.get(run_id, [])]

    def save_sites(self, run_id: str, sites: list[SiteState]) -> None:
        self.sites[run_id] = [s.model_copy(deep=True) for s in sites]

    def list_sites(self, run_id: str) -> list[SiteState]:
        return [s.model_copy(deep=True) for s in self.sites.get(run_id, [])]

    def save_participants(self, run_id: str, participants: list[ParticipantState]) -> None:
        self.participants[run_id] = [p.model_copy(deep=True) for p in participants]

    def list_participants(self, run_id: str) -> list[ParticipantState]:
        return [p.model_copy(deep=True) for p in self.participants.get(run_id, [])]

    def save_findings(self, run_id: str, findings: list[RehearsalFinding]) -> None:
        self.findings[run_id] = [f.model_copy(deep=True) for f in findings]

    def list_findings(self, run_id: str) -> list[RehearsalFinding]:
        return [f.model_copy(deep=True) for f in self.findings.get(run_id, [])]

    def save_action(self, run_id: str, action: ActionExecution) -> None:
        bucket = self.actions.setdefault(run_id, [])
        existing_idx = next(
            (i for i, a in enumerate(bucket) if a.idempotency_key == action.idempotency_key),
            None,
        )
        copy = action.model_copy(deep=True)
        if existing_idx is None:
            bucket.append(copy)
        else:
            bucket[existing_idx] = copy
        self.actions_by_key[action.idempotency_key] = copy

    def get_action_by_idempotency_key(self, idempotency_key: str) -> ActionExecution | None:
        action = self.actions_by_key.get(idempotency_key)
        return action.model_copy(deep=True) if action else None

    def list_actions(self, run_id: str) -> list[ActionExecution]:
        return [a.model_copy(deep=True) for a in self.actions.get(run_id, [])]

    def save_approval_request(self, request: ApprovalRequest) -> None:
        self.approvals[request.approval_id] = request.model_copy(deep=True)

    def get_approval_request(self, approval_id: str) -> ApprovalRequest | None:
        req = self.approvals.get(approval_id)
        return req.model_copy(deep=True) if req else None

    def list_approval_requests(self, run_id: str) -> list[ApprovalRequest]:
        return [r.model_copy(deep=True) for r in self.approvals.values() if r.run_id == run_id]

    def save_approval_decision(self, decision: ApprovalDecision) -> None:
        self.approval_decisions[decision.approval_id] = decision.model_copy(deep=True)

    def get_approval_decision(self, approval_id: str) -> ApprovalDecision | None:
        dec = self.approval_decisions.get(approval_id)
        return dec.model_copy(deep=True) if dec else None

    def append_audit_event(self, event: AuditEvent) -> None:
        self.audit.setdefault(event.run_id, []).append(event.model_copy(deep=True))

    def list_audit_events(self, run_id: str) -> list[AuditEvent]:
        return [e.model_copy(deep=True) for e in self.audit.get(run_id, [])]

    def save_manifest(self, manifest: AmendmentReleaseManifest) -> None:
        self.manifests[manifest.run_id] = manifest.model_copy(deep=True)

    def get_manifest(self, run_id: str) -> AmendmentReleaseManifest | None:
        man = self.manifests.get(run_id)
        return man.model_copy(deep=True) if man else None

    def save_session_metadata(self, meta: SessionMetadata) -> None:
        self.sessions[meta.run_id] = meta.model_copy(deep=True)

    def get_session_metadata(self, run_id: str) -> SessionMetadata | None:
        meta = self.sessions.get(run_id)
        return meta.model_copy(deep=True) if meta else None

    def record_processed_event(self, idempotency_key: str, event_id: str) -> bool:
        if idempotency_key in self.processed_events:
            return False
        self.processed_events[idempotency_key] = event_id
        return True

    def clear_processed_event(self, idempotency_key: str) -> None:
        self.processed_events.pop(idempotency_key, None)

    def snapshot(self) -> dict[str, object]:
        return deepcopy(
            {
                "runs": self.runs,
                "actions_by_key": self.actions_by_key,
                "processed_events": self.processed_events,
            }
        )
