"""ADK FunctionNodes for the Protocol 215 amendment workflow."""

from __future__ import annotations

from typing import Any

from google.adk.events.event import Event
from google.adk.events.request_input import RequestInput
from google.adk.workflow import node
from pydantic import BaseModel

from protocol215.application.amendment_analysis import AmendmentAnalysisPipeline
from protocol215.application.hashing import sha256_hex
from protocol215.application.invariants import evaluate_all
from protocol215.domain.enums import (
    ApprovalStatus,
    FailureClass,
    RiskTier,
    WorkflowStatus,
)
from protocol215.domain.models import SessionMetadata
from protocol215.policy.approval import build_approval_request, validate_approval_not_stale
from protocol215.policy.matrix import authorize_proposal, is_executable
from protocol215.simulator.twin import rehearse_amendment
from protocol215.workflow.errors import WorkflowFailure, classify_exception
from protocol215.workflow.runtime import (
    proposal_idempotency_key,
    runtime_from_ctx,
)


class HumanApprovalResponse(BaseModel):
    approved: bool
    comment: str = ""
    approval_id: str | None = None
    state_version: int | None = None


def _skip_if_done(ctx: Any, name: str) -> dict[str, Any] | None:
    rt = runtime_from_ctx(ctx)
    if rt.node_done(name):
        rt.append_event(f"{name}:skipped_replay")
        return {"skipped": True, "node": name}
    return None


def _finish(ctx: Any, name: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    rt = runtime_from_ctx(ctx)
    rt.mark_node_complete(name)
    rt.append_event(name)
    out = {"node": name, **(payload or {})}
    return out


@node(name="IntakeValidator")
def intake_validator(ctx: Any) -> dict[str, Any]:
    skipped = _skip_if_done(ctx, "IntakeValidator")
    if skipped:
        return skipped
    rt = runtime_from_ctx(ctx)
    run = rt.run()
    if not run.study_id or not run.from_version or not run.to_version:
        raise WorkflowFailure(
            "missing study/version fields",
            failure_class=FailureClass.INVALID_INPUT,
        )
    old_key = ctx.state.get("old_pdf_key")
    new_key = ctx.state.get("new_pdf_key")
    if not old_key or not new_key:
        raise WorkflowFailure(
            "old_pdf_key and new_pdf_key required",
            failure_class=FailureClass.INVALID_INPUT,
        )
    if not rt.objects.exists(old_key) or not rt.objects.exists(new_key):
        raise WorkflowFailure(
            "protocol PDF artifacts missing from object store",
            failure_class=FailureClass.INVALID_INPUT,
        )
    rt.set_status(WorkflowStatus.CREATED, checkpoint="IntakeValidator")
    return _finish(ctx, "IntakeValidator", {"study_id": run.study_id})


@node(name="RegisterArtifacts")
def register_artifacts(ctx: Any) -> dict[str, Any]:
    skipped = _skip_if_done(ctx, "RegisterArtifacts")
    if skipped:
        return skipped
    rt = runtime_from_ctx(ctx)
    run = rt.run()
    old_key = ctx.state["old_pdf_key"]
    new_key = ctx.state["new_pdf_key"]
    old_bytes = rt.objects.get_bytes(old_key)
    new_bytes = rt.objects.get_bytes(new_key)
    rt.service.register_protocol_artifact(
        run_id=run.run_id, version=run.from_version, pdf_bytes=old_bytes, object_key=old_key
    )
    rt.service.register_protocol_artifact(
        run_id=run.run_id, version=run.to_version, pdf_bytes=new_bytes, object_key=new_key
    )
    rt.set_status(WorkflowStatus.ARTIFACTS_REGISTERED, checkpoint="RegisterArtifacts")
    return _finish(
        ctx,
        "RegisterArtifacts",
        {
            "old_sha256": sha256_hex(old_bytes),
            "new_sha256": sha256_hex(new_bytes),
        },
    )


@node(name="CompileOldProtocol")
def compile_old_protocol(ctx: Any) -> dict[str, Any]:
    skipped = _skip_if_done(ctx, "CompileOldProtocol")
    if skipped:
        return skipped
    rt = runtime_from_ctx(ctx)
    run = rt.run()
    rt.set_status(WorkflowStatus.COMPILING, checkpoint="CompileOldProtocol")
    try:
        # Prefer already-persisted IR from registration when present.
        ir = rt.state.get_protocol_ir(run.run_id, run.from_version)
        if ir is None:
            pdf = rt.objects.get_bytes(ctx.state["old_pdf_key"])
            ir = rt.compiler.compile(pdf_bytes=pdf, version_hint=run.from_version)
            rt.state.save_protocol_ir(run.run_id, run.from_version, ir)
    except Exception as exc:  # noqa: BLE001 — classify then re-raise
        raise WorkflowFailure(
            str(exc),
            failure_class=classify_exception(exc),
            retryable=classify_exception(exc) == FailureClass.TRANSIENT_MODEL_ERROR,
        ) from exc
    return _finish(ctx, "CompileOldProtocol", {"version": run.from_version})


@node(name="CompileNewProtocol")
def compile_new_protocol(ctx: Any) -> dict[str, Any]:
    skipped = _skip_if_done(ctx, "CompileNewProtocol")
    if skipped:
        return skipped
    rt = runtime_from_ctx(ctx)
    run = rt.run()
    rt.set_status(WorkflowStatus.COMPILING, checkpoint="CompileNewProtocol")
    try:
        ir = rt.state.get_protocol_ir(run.run_id, run.to_version)
        if ir is None:
            pdf = rt.objects.get_bytes(ctx.state["new_pdf_key"])
            ir = rt.compiler.compile(pdf_bytes=pdf, version_hint=run.to_version)
            rt.state.save_protocol_ir(run.run_id, run.to_version, ir)
    except Exception as exc:  # noqa: BLE001
        raise WorkflowFailure(
            str(exc),
            failure_class=classify_exception(exc),
            retryable=classify_exception(exc) == FailureClass.TRANSIENT_MODEL_ERROR,
        ) from exc
    return _finish(ctx, "CompileNewProtocol", {"version": run.to_version})


@node(name="SemanticDiff")
def semantic_diff_node(ctx: Any) -> dict[str, Any]:
    skipped = _skip_if_done(ctx, "SemanticDiff")
    if skipped:
        return skipped
    rt = runtime_from_ctx(ctx)
    run = rt.run()
    rt.set_status(WorkflowStatus.ANALYZING, checkpoint="SemanticDiff")
    old_ir = rt.state.get_protocol_ir(run.run_id, run.from_version)
    new_ir = rt.state.get_protocol_ir(run.run_id, run.to_version)
    if old_ir is None or new_ir is None:
        raise WorkflowFailure("missing ProtocolIR", failure_class=FailureClass.INVALID_INPUT)
    result = AmendmentAnalysisPipeline().analyze(old_ir, new_ir, explain=True)
    rt.service.save_changes(run.run_id, result.changes)
    ctx.state["change_ids"] = [c.change_id for c in result.changes]
    ctx.state["normalization_notes"] = result.normalization_notes
    return _finish(ctx, "SemanticDiff", {"change_count": len(result.changes)})


@node(name="ImpactGraphBuilder")
def impact_graph_builder(ctx: Any) -> dict[str, Any]:
    skipped = _skip_if_done(ctx, "ImpactGraphBuilder")
    if skipped:
        return skipped
    rt = runtime_from_ctx(ctx)
    run = rt.run()
    rt.set_status(WorkflowStatus.ANALYZING, checkpoint="ImpactGraphBuilder")
    changes = rt.state.list_changes(run.run_id)
    sites, participants = rt.service.load_synthetic_study_state(run.run_id)
    result = AmendmentAnalysisPipeline().analyze(
        rt.state.get_protocol_ir(run.run_id, run.from_version),  # type: ignore[arg-type]
        rt.state.get_protocol_ir(run.run_id, run.to_version),  # type: ignore[arg-type]
        sites=sites,
        participants=participants,
        explain=False,
    )
    # Re-save normalized changes if analysis refreshed them
    if result.changes:
        rt.service.save_changes(run.run_id, result.changes)
    ctx.state["impact_node_count"] = len(result.impact_graph.nodes)
    ctx.state["impact_edge_count"] = len(result.impact_graph.edges)
    _ = changes
    return _finish(
        ctx,
        "ImpactGraphBuilder",
        {
            "nodes": len(result.impact_graph.nodes),
            "edges": len(result.impact_graph.edges),
        },
    )


@node(name="TrialTwinSimulator")
def trial_twin_simulator(ctx: Any) -> dict[str, Any]:
    skipped = _skip_if_done(ctx, "TrialTwinSimulator")
    if skipped:
        return skipped
    rt = runtime_from_ctx(ctx)
    run = rt.run()
    rt.set_status(WorkflowStatus.REHEARSING, checkpoint="TrialTwinSimulator")
    changes = rt.state.list_changes(run.run_id)
    sites = rt.state.list_sites(run.run_id)
    participants = rt.state.list_participants(run.run_id)
    findings = rehearse_amendment(changes=changes, sites=sites, participants=participants)
    rt.service.save_findings(run.run_id, findings)
    return _finish(ctx, "TrialTwinSimulator", {"finding_count": len(findings)})


@node(name="ActionPlanner")
def action_planner(ctx: Any) -> dict[str, Any]:
    skipped = _skip_if_done(ctx, "ActionPlanner")
    if skipped:
        return skipped
    rt = runtime_from_ctx(ctx)
    run = rt.run()
    rt.set_status(WorkflowStatus.PLANNING, checkpoint="ActionPlanner")
    # Planner port — fake or Gemini; never receives PDF bytes.
    proposals = rt.service.propose_actions(run.run_id)
    rt.proposals = proposals
    ctx.state["proposal_ids"] = [p.proposal_id for p in proposals]
    return _finish(ctx, "ActionPlanner", {"proposal_count": len(proposals)})


@node(name="PolicyGate")
def policy_gate(ctx: Any) -> Any:
    skipped = _skip_if_done(ctx, "PolicyGate")
    if skipped:
        # Recompute route from persisted proposals
        rt = runtime_from_ctx(ctx)
        route = "safe" if not rt.amber_proposal_ids and not rt.red_proposal_ids else "safe"
        if rt.red_proposal_ids and not rt.green_proposal_ids and not rt.amber_proposal_ids:
            route = "blocked"
        yield Event(output=skipped, route=route)  # type: ignore[call-arg]
        return
    rt = runtime_from_ctx(ctx)
    green: list[str] = []
    amber: list[str] = []
    red: list[str] = []
    for proposal in rt.proposals:
        tier = authorize_proposal(proposal)
        proposal.proposed_tier = tier
        if tier == RiskTier.GREEN:
            green.append(proposal.proposal_id)
        elif tier == RiskTier.AMBER:
            amber.append(proposal.proposal_id)
        else:
            red.append(proposal.proposal_id)
    rt.green_proposal_ids = green
    rt.amber_proposal_ids = amber
    rt.red_proposal_ids = red
    ctx.state["green_proposal_ids"] = green
    ctx.state["amber_proposal_ids"] = amber
    ctx.state["red_proposal_ids"] = red
    # RED never routes to an executor path that can run them.
    route = "blocked" if red and not green and not amber else "safe"
    payload = _finish(
        ctx,
        "PolicyGate",
        {"green": green, "amber": amber, "red": red, "route": route},
    )
    yield Event(output=payload, route=route)  # type: ignore[call-arg]


@node(name="SafeActionExecutor")
def safe_action_executor(ctx: Any) -> dict[str, Any]:
    skipped = _skip_if_done(ctx, "SafeActionExecutor")
    if skipped:
        return skipped
    rt = runtime_from_ctx(ctx)
    run = rt.run()
    rt.set_status(WorkflowStatus.EXECUTING_SAFE_ACTIONS, checkpoint="SafeActionExecutor")
    executed: list[str] = []
    blocked_red: list[str] = []
    for proposal in rt.proposals:
        tier = authorize_proposal(proposal)
        if tier != RiskTier.GREEN:
            if tier == RiskTier.RED:
                # Explicitly refuse — never execute RED.
                rt.service.execute_idempotent_action(
                    run_id=run.run_id,
                    proposal=proposal,
                    protocol_version=run.to_version,
                    target_id=proposal.site_id or proposal.proposal_id,
                    approved=False,
                )
                blocked_red.append(proposal.proposal_id)
            continue
        key = proposal_idempotency_key(run.run_id, proposal, run.to_version)
        action = rt.service.execute_idempotent_action(
            run_id=run.run_id,
            proposal=proposal.model_copy(update={"idempotency_key": key}),
            protocol_version=run.to_version,
            target_id=proposal.site_id or proposal.proposal_id,
            approved=False,
        )
        if action.executed and not action.replayed:
            rt.bump_green_count(key)
        if action.executed:
            executed.append(action.execution_id)
    return _finish(
        ctx,
        "SafeActionExecutor",
        {"executed": executed, "blocked_red": blocked_red},
    )


@node(name="ApprovalRouter")
def approval_router(ctx: Any) -> Any:
    skipped = _skip_if_done(ctx, "ApprovalRouter")
    rt = runtime_from_ctx(ctx)
    amber_ids = rt.amber_proposal_ids or ctx.state.get("amber_proposal_ids") or []
    if skipped:
        route = "awaiting" if amber_ids else "skip"
        yield Event(output=skipped, route=route)  # type: ignore[call-arg]
        return
    if not amber_ids:
        payload = _finish(ctx, "ApprovalRouter", {"route": "skip"})
        yield Event(output=payload, route="skip")  # type: ignore[call-arg]
        return

    run = rt.run()
    session_meta = rt.state.get_session_metadata(run.run_id)
    session_id = session_meta.session_id if session_meta else ctx.state.get("session_id", "")
    invocation_id = ctx.state.get("invocation_id") or (
        session_meta.invocation_id if session_meta else None
    )
    interrupt_id = f"approval-{run.run_id}"

    # Primary AMBER card: prefer Phoenix P002 transition plan when present.
    amber_proposals = [p for p in rt.proposals if p.proposal_id in amber_ids]
    primary = next(
        (
            p
            for p in amber_proposals
            if p.tool_name == "draft_participant_transition_plan"
            and (p.participant_id == "P002" or "P002" in p.proposal_id)
        ),
        amber_proposals[0],
    )
    request = build_approval_request(
        approval_id=rt.ids.new_id("apr-"),
        run=run,
        proposal=primary,
        before_state={"status": "pending_transition"},
        proposed_after_state={
            "tool": primary.tool_name,
            "args": primary.args,
            "participant_id": primary.participant_id,
            "site_id": primary.site_id,
        },
        change_evidence=list(primary.evidence),
        operational_evidence=list(primary.evidence),
        session_id=session_id,
        invocation_id=invocation_id,
        interrupt_id=interrupt_id,
        reason=(
            "Participant- or safety-sensitive AMBER action requires human authorization "
            f"({primary.tool_name})."
        ),
        consequences_of_approval=(
            "Approved AMBER actions execute under re-checked policy; RED remains non-executable."
        ),
        consequences_of_rejection=(
            "AMBER actions stay blocked; GREEN work already done is retained; "
            "run completes with unresolved AMBER items."
        ),
    )
    # Include full amber set on the card
    request = request.model_copy(update={"action_ids": list(amber_ids)})
    rt.state.save_approval_request(request)
    rt.pending_approval_id = request.approval_id
    rt.set_status(WorkflowStatus.AWAITING_APPROVAL, checkpoint="ApprovalRouter")
    rt.state.save_session_metadata(
        SessionMetadata(
            run_id=run.run_id,
            session_id=session_id,
            invocation_id=invocation_id,
            interrupt_id=interrupt_id,
            cursor="AWAITING_APPROVAL",
            expected_state_version=request.expected_state_version,
            extra={"approval_id": request.approval_id, "primary_action_id": primary.proposal_id},
        )
    )
    ctx.state["approval_id"] = request.approval_id
    ctx.state["interrupt_id"] = interrupt_id
    ctx.state["expected_state_version"] = request.expected_state_version
    payload = _finish(
        ctx,
        "ApprovalRouter",
        {
            "route": "awaiting",
            "approval_id": request.approval_id,
            "interrupt_id": interrupt_id,
            "expected_state_version": request.expected_state_version,
            "primary_action_id": primary.proposal_id,
            "affected_participant": primary.participant_id,
            "affected_site": primary.site_id,
        },
    )
    yield Event(output=payload, route="awaiting")  # type: ignore[call-arg]


@node(name="HumanApproval", rerun_on_resume=True)
async def human_approval(ctx: Any) -> Any:
    rt = runtime_from_ctx(ctx)
    interrupt_id = ctx.state.get("interrupt_id") or f"approval-{rt.run_id}"
    approval_id = ctx.state.get("approval_id") or rt.pending_approval_id

    if ctx.resume_inputs and interrupt_id in ctx.resume_inputs:
        raw = ctx.resume_inputs[interrupt_id]
        resp = (
            HumanApprovalResponse.model_validate(raw)
            if not isinstance(raw, HumanApprovalResponse)
            else raw
        )
        request = rt.state.get_approval_request(approval_id) if approval_id else None
        if request is None:
            raise WorkflowFailure(
                "approval request missing on resume",
                failure_class=FailureClass.INVALID_INPUT,
            )
        if request.status == ApprovalStatus.CONSUMED:
            # Duplicate resume — do not re-apply mutations.
            rt.append_event("HumanApproval:duplicate_resume")
            prior = rt.state.get_approval_decision(request.approval_id)
            was_approved = prior is not None and prior.decision == ApprovalStatus.APPROVED
            yield Event(  # type: ignore[call-arg]
                output={"duplicate": True, "approval_id": approval_id},
                route="approved" if was_approved else "rejected",
            )
            return

        rt.set_status(WorkflowStatus.RESUMING, checkpoint="HumanApproval")
        primary = next(
            (p for p in rt.proposals if p.proposal_id == request.action_id),
            next((p for p in rt.proposals if p.proposal_id in request.action_ids), None),
        )
        validate_approval_not_stale(
            request=request,
            run=rt.run(),
            current_invocation_id=ctx.state.get("invocation_id") or request.invocation_id,
            submitted_state_version=resp.state_version,
            current_proposal=primary,
        )

        decision = ApprovalStatus.APPROVED if resp.approved else ApprovalStatus.REJECTED
        rt.service.record_approval(
            approval_id=request.approval_id,
            decision=decision,
            actor="synthetic_operator",
        )
        # Mark consumed so duplicate resume is safe.
        rt.state.save_approval_request(
            request.model_copy(update={"status": ApprovalStatus.CONSUMED})
        )
        rt.append_event("HumanApproval")
        rt.mark_node_complete("HumanApproval")
        yield Event(  # type: ignore[call-arg]
            output={
                "approved": resp.approved,
                "approval_id": request.approval_id,
                "comment": resp.comment,
                "action_id": request.action_id,
                "affected_participant": request.affected_participant_id,
                "affected_site": request.affected_site_id,
            },
            route="approved" if resp.approved else "rejected",
        )
        return

    # Pause — return control to worker (do not hold HTTP).
    yield RequestInput(
        interrupt_id=interrupt_id,
        message="Authorize AMBER amendment actions?",
        payload={
            "approval_id": approval_id,
            "amber_proposal_ids": rt.amber_proposal_ids,
            "expected_state_version": ctx.state.get("expected_state_version"),
            "run_id": rt.run_id,
        },
        response_schema=HumanApprovalResponse,
    )


@node(name="ApprovedActionExecutor")
def approved_action_executor(ctx: Any) -> dict[str, Any]:
    skipped = _skip_if_done(ctx, "ApprovedActionExecutor")
    if skipped:
        return skipped
    rt = runtime_from_ctx(ctx)
    run = rt.run()
    # Re-run policy immediately before sensitive execution.
    executed: list[str] = []
    for proposal in rt.proposals:
        tier = authorize_proposal(proposal)
        if tier == RiskTier.RED:
            # RED can never reach executor success path — skip (already blocked if attempted).
            continue
        if tier != RiskTier.AMBER:
            continue
        if proposal.proposal_id not in (rt.amber_proposal_ids or []):
            continue
        if not is_executable(tier, approved=True):
            raise WorkflowFailure(
                f"policy violation for {proposal.proposal_id}",
                failure_class=FailureClass.POLICY_VIOLATION,
            )
        key = proposal_idempotency_key(run.run_id, proposal, run.to_version)
        action = rt.service.execute_idempotent_action(
            run_id=run.run_id,
            proposal=proposal.model_copy(update={"idempotency_key": key}),
            protocol_version=run.to_version,
            target_id=proposal.site_id or proposal.proposal_id,
            approved=True,
        )
        if action.executed:
            executed.append(action.execution_id)
    return _finish(ctx, "ApprovedActionExecutor", {"executed": executed})


@node(name="InvariantVerifier")
def invariant_verifier(ctx: Any) -> dict[str, Any]:
    skipped = _skip_if_done(ctx, "InvariantVerifier")
    if skipped:
        return skipped
    rt = runtime_from_ctx(ctx)
    run = rt.run()
    rt.set_status(WorkflowStatus.VERIFYING, checkpoint="InvariantVerifier")
    sites = rt.state.list_sites(run.run_id)
    participants = rt.state.list_participants(run.run_id)
    actions = rt.state.list_actions(run.run_id)
    results = evaluate_all(sites=sites, participants=participants, actions=actions)
    failed = [r for r in results if not r.passed]
    if failed:
        # Soft-fail for demo twin: record diagnostics; CompleteRun decides terminal status.
        rt.diagnostics["invariant_failures"] = [r.model_dump() for r in failed]
    return _finish(
        ctx,
        "InvariantVerifier",
        {"passed": len(failed) == 0, "checked": len(results), "failed": len(failed)},
    )


@node(name="ManifestGenerator")
def manifest_generator(ctx: Any) -> dict[str, Any]:
    skipped = _skip_if_done(ctx, "ManifestGenerator")
    if skipped:
        return skipped
    rt = runtime_from_ctx(ctx)
    run = rt.run()
    manifest = rt.service.generate_manifest(
        run_id=run.run_id,
        study_id=run.study_id,
        from_version=run.from_version,
        to_version=run.to_version,
    )
    return _finish(ctx, "ManifestGenerator", {"manifest_run_id": manifest.run_id})


@node(name="CompleteRun")
def complete_run(ctx: Any) -> dict[str, Any]:
    skipped = _skip_if_done(ctx, "CompleteRun")
    if skipped:
        return skipped
    rt = runtime_from_ctx(ctx)
    has_blocks = bool(rt.red_proposal_ids) or bool(rt.diagnostics.get("invariant_failures"))
    # Rejection path without amber execution still completes with blocks if amber pending rejected
    status = WorkflowStatus.COMPLETED_WITH_BLOCKS if has_blocks else WorkflowStatus.COMPLETED
    rt.set_status(status, checkpoint="CompleteRun")
    return _finish(ctx, "CompleteRun", {"status": status.value})


def _failure_handler_impl(ctx: Any) -> dict[str, Any]:
    rt = runtime_from_ctx(ctx)
    detail = ctx.state.get("failure_detail") or rt.diagnostics.get("failure_detail") or "unknown"
    fclass = ctx.state.get("failure_class") or rt.diagnostics.get("failure_class") or "unknown"
    retryable = bool(ctx.state.get("failure_retryable") or rt.diagnostics.get("failure_retryable"))
    status = WorkflowStatus.FAILED_RETRYABLE if retryable else WorkflowStatus.FAILED_TERMINAL
    run = rt.run()
    rt.state.save_run(
        run.model_copy(
            update={
                "status": status,
                "failure_class": str(fclass),
                "failure_detail": str(detail),
                "checkpoint": "FailureHandler",
            }
        )
    )
    rt.append_event("FailureHandler")
    rt.diagnostics["preserved"] = True
    return {
        "node": "FailureHandler",
        "status": status.value,
        "failure_class": fclass,
        "failure_detail": detail,
        "diagnostics": rt.diagnostics,
    }


@node(name="FailureHandler")
def failure_handler(ctx: Any) -> dict[str, Any]:
    return _failure_handler_impl(ctx)
