"""API response / request schemas for Protocol 215."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from protocol215.domain.enums import ApprovalStatus, WorkflowStatus


class CreateRunResponse(BaseModel):
    run_id: str
    status: WorkflowStatus
    study_id: str
    from_version: str
    to_version: str
    old_sha256: str
    new_sha256: str
    old_pages: int
    new_pages: int
    event_published: bool
    message: str = "Run accepted; workflow started asynchronously."
    event_id: str | None = None
    correlation_id: str | None = None


class PendingApprovalSummary(BaseModel):
    approval_id: str
    action_id: str | None = None
    tool_name: str | None = None
    affected_site_id: str | None = None
    affected_participant_id: str | None = None
    expected_state_version: int = 0
    reason_approval_required: str = ""
    interrupt_id: str | None = None
    invocation_id: str | None = None


class RunStatusResponse(BaseModel):
    run_id: str
    study_id: str
    from_version: str
    to_version: str
    status: WorkflowStatus
    current_stage: str
    progress: float = Field(ge=0.0, le=1.0)
    last_event: str | None = None
    pending_approval: PendingApprovalSummary | None = None
    completed_action_count: int = 0
    blocked_action_count: int = 0
    error_summary: str | None = None
    execution_mode: str
    state_version: int = 0
    checkpoint: str | None = None
    created_at: datetime
    event_sequence: list[str] = Field(default_factory=list)
    # Stalled-run / recording diagnostics (safe for UI; no secrets / CoT)
    updated_at: datetime | None = None
    last_checkpoint_at: datetime | None = None
    last_worker_event_id: str | None = None
    last_error_code: str | None = None
    last_error_detail_safe: str | None = None
    correlation_id: str | None = None
    web_revision: str | None = None
    worker_revision: str | None = None
    actual_adapters: dict[str, str] = Field(default_factory=dict)
    compiler_model: str | None = None


class RunListItem(BaseModel):
    run_id: str
    study_id: str
    status: WorkflowStatus
    from_version: str
    to_version: str
    created_at: datetime
    current_stage: str


class ApprovalDecisionRequest(BaseModel):
    decision: ApprovalStatus  # APPROVED | REJECTED
    expected_state_version: int
    comment: str = ""
    actor: str = "synthetic_operator"


class ApprovalDecisionResponse(BaseModel):
    approval_id: str
    run_id: str
    decision: ApprovalStatus
    event_published: bool
    message: str = "Approval recorded; resume event published."


class DemoResetResponse(BaseModel):
    ok: bool
    message: str
    sites_restored: int = 0
    participants_restored: int = 0
    runs_cleared: int = 0
    objects_cleared: int = 0
    fixtures_preserved: list[str] = Field(default_factory=list)
    twin_snapshot: dict[str, Any] = Field(default_factory=dict)


class RecordingReadinessCheck(BaseModel):
    name: str
    status: str  # PASS | FAIL
    detail: str


class RecordingReadinessResponse(BaseModel):
    overall: str  # PASS | FAIL
    checks: list[RecordingReadinessCheck]
    failed_count: int = 0
    passed_count: int = 0
    observed: dict[str, Any] = Field(default_factory=dict)


class ImpactGraphResponse(BaseModel):
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)
    node_count: int = 0
    edge_count: int = 0


STAGE_ORDER: list[str] = [
    "CREATED",
    "ARTIFACTS_REGISTERED",
    "COMPILING",
    "ANALYZING",
    "REHEARSING",
    "PLANNING",
    "EXECUTING_SAFE_ACTIONS",
    "AWAITING_APPROVAL",
    "RESUMING",
    "VERIFYING",
    "COMPLETED",
]


def progress_for_status(status: WorkflowStatus) -> float:
    mapping = {
        WorkflowStatus.CREATED: 0.05,
        WorkflowStatus.RECEIVED: 0.05,
        WorkflowStatus.ARTIFACTS_REGISTERED: 0.15,
        WorkflowStatus.COMPILING: 0.25,
        WorkflowStatus.COMPILING_IR: 0.25,
        WorkflowStatus.ANALYZING: 0.4,
        WorkflowStatus.DIFFING: 0.35,
        WorkflowStatus.IMPACTING: 0.4,
        WorkflowStatus.REHEARSING: 0.5,
        WorkflowStatus.PLANNING: 0.55,
        WorkflowStatus.GATING: 0.6,
        WorkflowStatus.EXECUTING_SAFE_ACTIONS: 0.7,
        WorkflowStatus.EXECUTING_GREEN: 0.7,
        WorkflowStatus.AWAITING_APPROVAL: 0.75,
        WorkflowStatus.RESUMING: 0.8,
        WorkflowStatus.EXECUTING_APPROVED_AMBER: 0.85,
        WorkflowStatus.VERIFYING: 0.9,
        WorkflowStatus.MANIFEST_READY: 0.95,
        WorkflowStatus.COMPLETED: 1.0,
        WorkflowStatus.COMPLETED_WITH_BLOCKS: 1.0,
        WorkflowStatus.PARTIAL: 0.95,
        WorkflowStatus.FAILED: 1.0,
        WorkflowStatus.FAILED_RETRYABLE: 1.0,
        WorkflowStatus.FAILED_TERMINAL: 1.0,
    }
    return mapping.get(status, 0.0)
