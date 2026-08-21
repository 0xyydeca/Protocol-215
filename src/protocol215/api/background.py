"""Background workflow kick — never blocks the HTTP response path."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from protocol215.api.container import AppContainer

logger = logging.getLogger("protocol215.api.worker_bridge")


async def kick_amendment_received(container: AppContainer, run_id: str) -> None:
    """Consume amendment.received locally by running the async pipeline."""
    # Yield so HTTP 202 is observed before status advances (local demo / tests).
    await asyncio.sleep(0.05)
    try:
        run = container.state.get_run(run_id)
        if run is None:
            return
        old_key = run.object_keys.get(run.from_version) or f"runs/{run_id}/protocols/v{run.from_version}.pdf"
        new_key = run.object_keys.get(run.to_version) or f"runs/{run_id}/protocols/v{run.to_version}.pdf"
        old_bytes = container.objects.get_bytes(old_key)
        new_bytes = container.objects.get_bytes(new_key)
        await asyncio.to_thread(_run_local_pipeline, container, run_id, old_bytes, new_bytes)
    except Exception:  # noqa: BLE001
        logger.exception("background amendment.received failed run_id=%s", run_id)
        run = container.state.get_run(run_id)
        if run is not None:
            from protocol215.domain.enums import WorkflowStatus

            container.state.save_run(
                run.model_copy(
                    update={
                        "status": WorkflowStatus.FAILED_RETRYABLE,
                        "failure_class": "transient_model_error",
                        "failure_detail": "background workflow failed",
                    }
                )
            )


def _run_local_pipeline(
    container: AppContainer,
    run_id: str,
    old_bytes: bytes,
    new_bytes: bytes,
) -> None:
    """Deterministic local pipeline on API service state (async worker stand-in)."""
    from protocol215.application.amendment_analysis import AmendmentAnalysisPipeline
    from protocol215.domain.enums import RiskTier, WorkflowStatus
    from protocol215.policy.matrix import authorize_proposal
    from protocol215.simulator.twin import rehearse_amendment

    svc = container.service
    run = svc._require_run(run_id)

    def set_status(status: WorkflowStatus, checkpoint: str) -> None:
        r = svc._require_run(run_id)
        svc.state.save_run(
            r.model_copy(
                update={
                    "status": status,
                    "checkpoint": checkpoint,
                    "state_version": r.state_version + 1,
                    "event_sequence": list(r.event_sequence) + [checkpoint],
                }
            )
        )

    set_status(WorkflowStatus.ARTIFACTS_REGISTERED, "RegisterArtifacts")
    # Artifacts already registered by API; ensure IRs exist
    set_status(WorkflowStatus.COMPILING, "CompileOldProtocol")
    old_ir = svc.compiler.compile(pdf_bytes=old_bytes, version_hint=run.from_version)
    svc.state.save_protocol_ir(run_id, run.from_version, old_ir)
    set_status(WorkflowStatus.COMPILING, "CompileNewProtocol")
    new_ir = svc.compiler.compile(pdf_bytes=new_bytes, version_hint=run.to_version)
    svc.state.save_protocol_ir(run_id, run.to_version, new_ir)

    set_status(WorkflowStatus.ANALYZING, "SemanticDiff")
    analysis = AmendmentAnalysisPipeline().analyze(old_ir, new_ir, explain=True)
    svc.save_changes(run_id, analysis.changes)

    set_status(WorkflowStatus.ANALYZING, "ImpactGraphBuilder")
    sites, participants = svc.load_synthetic_study_state(run_id)
    analysis2 = AmendmentAnalysisPipeline().analyze(
        old_ir, new_ir, sites=sites, participants=participants, explain=False
    )
    # stash impact counts on session extra
    meta = svc.state.get_session_metadata(run_id)
    if meta is not None:
        extra = dict(meta.extra)
        extra["impact_nodes"] = len(analysis2.impact_graph.nodes)
        extra["impact_edges"] = len(analysis2.impact_graph.edges)
        extra["impact_graph"] = analysis2.impact_graph.model_dump(mode="json")
        svc.state.save_session_metadata(meta.model_copy(update={"extra": extra}))

    set_status(WorkflowStatus.REHEARSING, "TrialTwinSimulator")
    findings = rehearse_amendment(
        changes=analysis.changes, sites=sites, participants=participants
    )
    svc.save_findings(run_id, findings)

    set_status(WorkflowStatus.PLANNING, "ActionPlanner")
    proposals = svc.propose_actions(run_id)
    meta = svc.state.get_session_metadata(run_id)
    if meta is not None:
        extra = dict(meta.extra)
        extra["proposals"] = [p.model_dump(mode="json") for p in proposals]
        svc.state.save_session_metadata(meta.model_copy(update={"extra": extra}))

    set_status(WorkflowStatus.EXECUTING_SAFE_ACTIONS, "SafeActionExecutor")
    amber: list = []
    for proposal in proposals:
        tier = authorize_proposal(proposal)
        proposal.proposed_tier = tier
        if tier == RiskTier.GREEN:
            svc.execute_idempotent_action(
                run_id=run_id,
                proposal=proposal,
                protocol_version=run.to_version,
                target_id=proposal.site_id or proposal.proposal_id,
                approved=False,
            )
        elif tier == RiskTier.AMBER:
            amber.append(proposal)
        else:
            svc.execute_idempotent_action(
                run_id=run_id,
                proposal=proposal,
                protocol_version=run.to_version,
                target_id=proposal.site_id or proposal.proposal_id,
                approved=False,
            )

    if amber:
        from protocol215.policy.approval import build_approval_request

        primary = next(
            (p for p in amber if p.tool_name == "draft_participant_transition_plan"),
            amber[0],
        )
        r = svc._require_run(run_id)
        meta = svc.state.get_session_metadata(run_id)
        req = build_approval_request(
            approval_id=svc.ids.new_id("apr-"),
            run=r,
            proposal=primary,
            before_state={"status": "pending"},
            proposed_after_state={"tool": primary.tool_name, "args": primary.args},
            change_evidence=list(primary.evidence),
            operational_evidence=list(primary.evidence),
            session_id=meta.session_id if meta else None,
            invocation_id=None,
            interrupt_id=f"approval-{run_id}",
            reason=f"AMBER authorization required for {primary.tool_name}",
            consequences_of_approval="AMBER actions execute after policy re-check.",
            consequences_of_rejection="AMBER actions remain blocked.",
        )
        req = req.model_copy(update={"action_ids": [p.proposal_id for p in amber]})
        svc.state.save_approval_request(req)
        set_status(WorkflowStatus.AWAITING_APPROVAL, "ApprovalRouter")
        return

    set_status(WorkflowStatus.VERIFYING, "InvariantVerifier")
    svc.generate_manifest(
        run_id=run_id,
        study_id=run.study_id,
        from_version=run.from_version,
        to_version=run.to_version,
    )
    set_status(WorkflowStatus.COMPLETED, "CompleteRun")


async def kick_amendment_resume(
    container: AppContainer,
    run_id: str,
    approval_id: str,
    approved: bool,
) -> None:
    try:
        await asyncio.to_thread(
            _run_resume_pipeline, container, run_id, approval_id, approved
        )
    except Exception:  # noqa: BLE001
        logger.exception("background amendment.resume failed run_id=%s", run_id)


def _run_resume_pipeline(
    container: AppContainer,
    run_id: str,
    approval_id: str,
    approved: bool,
) -> None:
    from protocol215.domain.enums import ApprovalStatus, RiskTier, WorkflowStatus
    from protocol215.policy.matrix import authorize_proposal

    svc = container.service
    run = svc._require_run(run_id)
    svc.state.save_run(
        run.model_copy(
            update={
                "status": WorkflowStatus.RESUMING,
                "checkpoint": "HumanApproval",
                "state_version": run.state_version + 1,
                "event_sequence": list(run.event_sequence) + ["HumanApproval"],
            }
        )
    )
    request = svc.state.get_approval_request(approval_id)
    if request is None:
        return
    if approved:
        from protocol215.domain.models import ActionProposal

        meta = svc.state.get_session_metadata(run_id)
        raw_proposals = (meta.extra or {}).get("proposals", []) if meta else []
        proposals = [ActionProposal.model_validate(p) for p in raw_proposals]
        if not proposals:
            proposals = svc.propose_actions(run_id)
        wanted = set(request.action_ids)
        for proposal in proposals:
            if proposal.proposal_id not in wanted:
                continue
            tier = authorize_proposal(proposal)
            if tier != RiskTier.AMBER:
                continue
            svc.execute_idempotent_action(
                run_id=run_id,
                proposal=proposal,
                protocol_version=run.to_version,
                target_id=proposal.site_id or proposal.proposal_id,
                approved=True,
            )
        svc.state.save_approval_request(
            request.model_copy(update={"status": ApprovalStatus.CONSUMED})
        )

    run = svc._require_run(run_id)
    svc.state.save_run(
        run.model_copy(
            update={
                "status": WorkflowStatus.VERIFYING,
                "checkpoint": "InvariantVerifier",
                "state_version": run.state_version + 1,
                "event_sequence": list(run.event_sequence) + ["InvariantVerifier"],
            }
        )
    )
    svc.generate_manifest(
        run_id=run_id,
        study_id=run.study_id,
        from_version=run.from_version,
        to_version=run.to_version,
    )
    run = svc._require_run(run_id)
    final = (
        WorkflowStatus.COMPLETED_WITH_BLOCKS
        if any(
            a.status.value == "blocked"
            for a in svc.state.list_actions(run_id)
        )
        else WorkflowStatus.COMPLETED
    )
    svc.state.save_run(
        run.model_copy(
            update={
                "status": final,
                "checkpoint": "CompleteRun",
                "state_version": run.state_version + 1,
                "event_sequence": list(run.event_sequence) + ["CompleteRun"],
            }
        )
    )
