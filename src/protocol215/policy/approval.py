"""Enriched approval requests and stale-approval rejection."""

from __future__ import annotations

from typing import Any

from protocol215.application.hashing import hash_payload
from protocol215.domain.enums import ApprovalStatus, FailureClass, WorkflowStatus
from protocol215.domain.models import (
    ActionProposal,
    ApprovalRequest,
    EvidenceReference,
    WorkflowRun,
)
from protocol215.workflow.errors import WorkflowFailure


def build_approval_request(
    *,
    approval_id: str,
    run: WorkflowRun,
    proposal: ActionProposal,
    before_state: dict[str, Any],
    proposed_after_state: dict[str, Any],
    change_evidence: list[EvidenceReference],
    operational_evidence: list[EvidenceReference],
    session_id: str | None,
    invocation_id: str | None,
    interrupt_id: str | None,
    reason: str,
    consequences_of_approval: str,
    consequences_of_rejection: str,
) -> ApprovalRequest:
    state_hash = hash_payload(
        {
            "run_id": run.run_id,
            "state_version": run.state_version,
            "proposal_id": proposal.proposal_id,
            "tool_name": proposal.tool_name,
            "args": proposal.args,
            "evidence": [e.model_dump() for e in proposal.evidence],
            "before": before_state,
            "after": proposed_after_state,
        }
    )
    return ApprovalRequest(
        approval_id=approval_id,
        run_id=run.run_id,
        action_ids=[proposal.proposal_id],
        status=ApprovalStatus.PENDING,
        state_hash=state_hash,
        session_id=session_id,
        invocation_id=invocation_id,
        interrupt_id=interrupt_id,
        expected_state_version=run.state_version,
        action_id=proposal.proposal_id,
        tool_name=proposal.tool_name,
        affected_site_id=proposal.site_id,
        affected_participant_id=proposal.participant_id,
        change_evidence=list(change_evidence),
        operational_evidence=list(operational_evidence),
        before_state=before_state,
        proposed_after_state=proposed_after_state,
        reason_approval_required=reason,
        consequences_of_approval=consequences_of_approval,
        consequences_of_rejection=consequences_of_rejection,
        evidence_hash=hash_payload([e.model_dump() for e in proposal.evidence]),
        policy_hash=hash_payload({"tool": proposal.tool_name, "tier": "AMBER"}),
    )


def validate_approval_not_stale(
    *,
    request: ApprovalRequest,
    run: WorkflowRun,
    current_invocation_id: str | None = None,
    submitted_state_version: int | None = None,
    current_proposal: ActionProposal | None = None,
    current_evidence_hash: str | None = None,
    current_policy_hash: str | None = None,
    allow_consumed_duplicate: bool = False,
) -> None:
    """Raise WorkflowFailure(STALE_APPROVAL) when resume must be rejected."""
    if request.status == ApprovalStatus.CONSUMED and not allow_consumed_duplicate:
        raise WorkflowFailure(
            "approval already used",
            failure_class=FailureClass.STALE_APPROVAL,
        )
    # Single-use: once a decision is recorded (API path) the request is no longer pending.
    if request.status in {ApprovalStatus.APPROVED, ApprovalStatus.REJECTED}:
        raise WorkflowFailure(
            "approval already submitted",
            failure_class=FailureClass.STALE_APPROVAL,
        )

    if run.status not in {
        WorkflowStatus.AWAITING_APPROVAL,
        WorkflowStatus.RESUMING,
    }:
        raise WorkflowFailure(
            f"run is no longer awaiting approval (status={run.status.value})",
            failure_class=FailureClass.STALE_APPROVAL,
        )

    if (
        submitted_state_version is not None
        and submitted_state_version != request.expected_state_version
    ):
        raise WorkflowFailure(
            "expected state version mismatch",
            failure_class=FailureClass.STALE_APPROVAL,
        )

    if (
        request.invocation_id
        and current_invocation_id
        and request.invocation_id != current_invocation_id
    ):
        raise WorkflowFailure(
            "invocation ID mismatches",
            failure_class=FailureClass.STALE_APPROVAL,
        )

    if current_proposal is not None:
        recomputed = hash_payload(
            {
                "run_id": run.run_id,
                "state_version": request.expected_state_version,
                "proposal_id": current_proposal.proposal_id,
                "tool_name": current_proposal.tool_name,
                "args": current_proposal.args,
                "evidence": [e.model_dump() for e in current_proposal.evidence],
                "before": request.before_state,
                "after": request.proposed_after_state,
            }
        )
        if recomputed != request.state_hash:
            raise WorkflowFailure(
                "action state changed since approval request",
                failure_class=FailureClass.STALE_APPROVAL,
            )

    if (
        current_evidence_hash
        and request.evidence_hash
        and current_evidence_hash != request.evidence_hash
    ):
        raise WorkflowFailure(
            "evidence changed since approval request",
            failure_class=FailureClass.STALE_APPROVAL,
        )

    if current_policy_hash and request.policy_hash and current_policy_hash != request.policy_hash:
        raise WorkflowFailure(
            "policy changed since approval request",
            failure_class=FailureClass.STALE_APPROVAL,
        )
