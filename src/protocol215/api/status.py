"""Build typed run status for frontend polling."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from protocol215.api.schemas import (
    PendingApprovalSummary,
    RunStatusResponse,
    progress_for_status,
)
from protocol215.application.services import AmendmentAppService
from protocol215.config import Settings
from protocol215.domain.enums import ActionStatus, ApprovalStatus, WorkflowStatus

if TYPE_CHECKING:
    from protocol215.api.container import AppContainer


def _safe_error_detail(detail: str | None, *, max_len: int = 280) -> str | None:
    if not detail:
        return None
    text = " ".join(detail.split())
    if len(text) > max_len:
        return text[: max_len - 1] + "…"
    return text


def build_run_status(
    service: AmendmentAppService,
    settings: Settings,
    run_id: str,
    *,
    container: AppContainer | None = None,
) -> RunStatusResponse:
    run = service.state.get_run(run_id)
    if run is None:
        raise KeyError(run_id)

    actions = service.state.list_actions(run_id)
    completed = sum(1 for a in actions if a.status == ActionStatus.EXECUTED)
    blocked = sum(1 for a in actions if a.status == ActionStatus.BLOCKED)

    pending = None
    if run.status == WorkflowStatus.AWAITING_APPROVAL:
        approvals = service.state.list_approval_requests(run_id)
        open_reqs = [a for a in approvals if a.status == ApprovalStatus.PENDING]
        if open_reqs:
            apr = sorted(open_reqs, key=lambda a: a.created_at)[-1]
            pending = PendingApprovalSummary(
                approval_id=apr.approval_id,
                action_id=apr.action_id,
                tool_name=apr.tool_name,
                affected_site_id=apr.affected_site_id,
                affected_participant_id=apr.affected_participant_id,
                expected_state_version=apr.expected_state_version,
                reason_approval_required=apr.reason_approval_required,
                interrupt_id=apr.interrupt_id,
                invocation_id=apr.invocation_id,
            )

    seq = list(run.event_sequence)
    last_event = seq[-1] if seq else None
    audit = service.state.list_audit_events(run_id)
    if audit:
        last_event = audit[-1].event_type

    error_summary = None
    if run.status in {
        WorkflowStatus.FAILED,
        WorkflowStatus.FAILED_RETRYABLE,
        WorkflowStatus.FAILED_TERMINAL,
    }:
        error_summary = run.failure_detail or run.failure_class or "failed"

    stage = run.checkpoint or run.status.value
    mode = settings.execution_mode
    if settings.app_env.value == "cloud":
        mode = "cloud"

    actual_adapters: dict[str, str] = {}
    if container is not None:
        actual_adapters = dict(container.actual_adapters)

    compiler_model = run.compiler_model
    if not compiler_model:
        if settings.gemini_backend.value == "fake":
            compiler_model = "fake-protocol-compiler"
        else:
            compiler_model = settings.gemini_model

    web_revision = os.environ.get("K_REVISION")
    worker_revision = run.worker_revision

    return RunStatusResponse(
        run_id=run.run_id,
        study_id=run.study_id,
        from_version=run.from_version,
        to_version=run.to_version,
        status=run.status,
        current_stage=stage,
        progress=progress_for_status(run.status),
        last_event=last_event,
        pending_approval=pending,
        completed_action_count=completed,
        blocked_action_count=blocked,
        error_summary=error_summary,
        execution_mode=mode,
        state_version=run.state_version,
        checkpoint=run.checkpoint,
        created_at=run.created_at,
        event_sequence=seq,
        updated_at=run.updated_at or run.created_at,
        last_checkpoint_at=run.last_checkpoint_at,
        last_worker_event_id=run.last_worker_event_id or (seq[-1] if seq else None),
        last_error_code=run.failure_class,
        last_error_detail_safe=_safe_error_detail(run.failure_detail),
        correlation_id=run.correlation_id or run.run_id,
        web_revision=web_revision,
        worker_revision=worker_revision,
        actual_adapters=actual_adapters,
        compiler_model=compiler_model,
    )
