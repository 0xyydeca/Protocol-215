"""Tests for allowlisted tools, policy tiers, and stale approvals."""

from __future__ import annotations

import asyncio

import pytest

from protocol215.adapters.audit_log import HashChainedAuditLog, verify_audit_chain
from protocol215.adapters.clock import DeterministicClock
from protocol215.adapters.constrained_planner import ConstrainedActionPlanner
from protocol215.adapters.fakes import FakeProtocolCompiler
from protocol215.adapters.identifiers import DeterministicIdentifierGenerator
from protocol215.adapters.object_store_local import LocalFileObjectStore
from protocol215.adapters.state_store_memory import InMemoryStateStore
from protocol215.application.hashing import hash_payload
from protocol215.application.services import AmendmentAppService
from protocol215.domain.enums import ActionStatus, ApprovalStatus, RiskTier, WorkflowStatus
from protocol215.domain.models import (
    ActionProposal,
    EvidenceReference,
    WorkflowRun,
)
from protocol215.policy.approval import build_approval_request, validate_approval_not_stale
from protocol215.policy.matrix import authorize_proposal
from protocol215.simulator.twin import load_participants, load_sites, rehearse_amendment
from protocol215.fixtures.aurora_ir import build_aurora_v1_ir, build_aurora_v2_ir
from protocol215.application.amendment_analysis import AmendmentAnalysisPipeline
from protocol215.tools.executor import ToolExecutor
from protocol215.tools.registry import ALLOWED_ACTION_NAMES, GREEN_TOOLS, AMBER_TOOLS
from protocol215.workflow.driver import LocalWorkflowDriver
from protocol215.workflow.errors import WorkflowFailure


def _svc(tmp_path):
    state = InMemoryStateStore()
    clock = DeterministicClock()
    ids = DeterministicIdentifierGenerator()
    audit = HashChainedAuditLog(state, clock, ids)
    from protocol215.adapters.event_bus_inprocess import InProcessEventBus

    return AmendmentAppService(
        state=state,
        objects=LocalFileObjectStore(tmp_path / "obj"),
        events=InProcessEventBus(),
        audit=audit,
        compiler=FakeProtocolCompiler(),
        planner=ConstrainedActionPlanner(include_amber=True),
        clock=clock,
        ids=ids,
    )


def _proposals_for_aurora(run: WorkflowRun):
    changes = AmendmentAnalysisPipeline().analyze(
        build_aurora_v1_ir(), build_aurora_v2_ir()
    ).changes
    sites = load_sites()
    participants = load_participants()
    findings = rehearse_amendment(changes=changes, sites=sites, participants=participants)
    return ConstrainedActionPlanner(include_amber=True, include_red_bait=True).propose(
        run=run, changes=changes, findings=findings
    )


def test_every_allowed_tool_has_schema_and_handler() -> None:
    from protocol215.tools.handlers import HANDLERS
    from protocol215.tools.schemas import TOOL_ARGS_BY_NAME

    assert set(TOOL_ARGS_BY_NAME) == ALLOWED_ACTION_NAMES
    assert set(HANDLERS) == ALLOWED_ACTION_NAMES


def test_green_amber_red_tiers(tmp_path) -> None:
    svc = _svc(tmp_path)
    run = svc.create_run(study_id="AURORA-101", from_version="1.0", to_version="2.0")
    svc.state.save_sites(run.run_id, load_sites())
    proposals = _proposals_for_aurora(run)
    assert all(
        p.tool_name in ALLOWED_ACTION_NAMES or p.tool_name == "change_dose" for p in proposals
    )
    greens = [p for p in proposals if authorize_proposal(p) == RiskTier.GREEN]
    ambers = [p for p in proposals if authorize_proposal(p) == RiskTier.AMBER]
    reds = [p for p in proposals if authorize_proposal(p) == RiskTier.RED]
    assert greens
    assert ambers
    assert any(p.tool_name == "change_dose" for p in reds)
    assert any(p.tool_name == "draft_participant_transition_plan" for p in ambers)
    assert any(p.tool_name == "create_courier_exception_task" for p in greens)


def test_each_green_tool_executes(tmp_path) -> None:
    svc = _svc(tmp_path)
    run = svc.create_run(study_id="AURORA-101", from_version="1.0", to_version="2.0")
    svc.state.save_sites(run.run_id, load_sites())
    proposals = [
        p
        for p in _proposals_for_aurora(run)
        if authorize_proposal(p) == RiskTier.GREEN
    ]
    assert proposals
    for p in proposals:
        action = svc.execute_idempotent_action(
            run_id=run.run_id,
            proposal=p,
            protocol_version="2.0",
            target_id=p.site_id or p.participant_id or p.proposal_id,
        )
        assert action.executed is True
        assert action.status == ActionStatus.EXECUTED
        assert action.before is not None and action.after is not None


def test_amber_requires_approval_red_never_executes(tmp_path) -> None:
    svc = _svc(tmp_path)
    run = svc.create_run(study_id="AURORA-101", from_version="1.0", to_version="2.0")
    svc.state.save_sites(run.run_id, load_sites())
    proposals = _proposals_for_aurora(run)
    amber = next(p for p in proposals if authorize_proposal(p) == RiskTier.AMBER)
    blocked = svc.execute_idempotent_action(
        run_id=run.run_id,
        proposal=amber,
        protocol_version="2.0",
        target_id=amber.participant_id or amber.proposal_id,
        approved=False,
    )
    assert blocked.executed is False
    approved = svc.execute_idempotent_action(
        run_id=run.run_id,
        proposal=amber.model_copy(
            update={"idempotency_key": amber.idempotency_key or amber.proposal_id + "-ok"}
        ),
        protocol_version="2.0",
        target_id=amber.participant_id or amber.proposal_id,
        approved=True,
    )
    assert approved.executed is True

    red = next(p for p in proposals if p.tool_name == "change_dose")
    red_blocked = svc.execute_idempotent_action(
        run_id=run.run_id,
        proposal=red,
        protocol_version="2.0",
        target_id="dose",
        approved=True,  # UI approve must not override
    )
    assert red_blocked.executed is False
    assert red_blocked.authorized_tier == RiskTier.RED
    assert red_blocked.after.get("approval_ignored") is True


def test_tool_replay_path(tmp_path) -> None:
    svc = _svc(tmp_path)
    run = svc.create_run(study_id="AURORA-101", from_version="1.0", to_version="2.0")
    svc.state.save_sites(run.run_id, load_sites())
    p = next(
        x
        for x in _proposals_for_aurora(run)
        if x.tool_name == "update_contact_directory"
    )
    a1 = svc.execute_idempotent_action(
        run_id=run.run_id, proposal=p, protocol_version="2.0", target_id="lab"
    )
    a2 = svc.execute_idempotent_action(
        run_id=run.run_id, proposal=p, protocol_version="2.0", target_id="lab"
    )
    assert a1.execution_id == a2.execution_id
    assert a2.replayed is True


def test_uncited_action_is_red(tmp_path) -> None:
    svc = _svc(tmp_path)
    run = svc.create_run(study_id="AURORA-101", from_version="1.0", to_version="2.0")
    p = ActionProposal(
        proposal_id="x",
        tool_name="update_contact_directory",
        rationale="no evidence",
        evidence=[],
        args={"run_id": run.run_id, "role": "central_lab", "email": "x@test"},
    )
    assert authorize_proposal(p) == RiskTier.RED


def test_stale_approval_conditions(tmp_path) -> None:
    svc = _svc(tmp_path)
    run = svc.create_run(study_id="AURORA-101", from_version="1.0", to_version="2.0")
    run = svc.state.save_run(
        run.model_copy(update={"status": WorkflowStatus.AWAITING_APPROVAL, "state_version": 3})
    ) or svc.state.get_run(run.run_id)
    assert run is not None
    proposal = ActionProposal(
        proposal_id="prop-1",
        tool_name="draft_participant_transition_plan",
        rationale="phoenix",
        evidence=[EvidenceReference(page=8, section_id="SEC-PK")],
        site_id="SITE-001",
        participant_id="P002",
        args={
            "run_id": run.run_id,
            "site_id": "SITE-001",
            "participant_id": "P002",
            "transition_summary": "conflict",
        },
    )
    req = build_approval_request(
        approval_id="apr-1",
        run=run,
        proposal=proposal,
        before_state={"a": 1},
        proposed_after_state={"b": 2},
        change_evidence=list(proposal.evidence),
        operational_evidence=list(proposal.evidence),
        session_id="sess",
        invocation_id="inv-1",
        interrupt_id="int-1",
        reason="amber",
        consequences_of_approval="go",
        consequences_of_rejection="stop",
    )
    svc.state.save_approval_request(req)

    # already used
    used = req.model_copy(update={"status": ApprovalStatus.CONSUMED})
    with pytest.raises(WorkflowFailure) as e1:
        validate_approval_not_stale(request=used, run=run)
    assert e1.value.failure_class.value == "stale_approval"

    # invocation mismatch
    with pytest.raises(WorkflowFailure):
        validate_approval_not_stale(
            request=req, run=run, current_invocation_id="other-inv"
        )

    # state version mismatch
    with pytest.raises(WorkflowFailure):
        validate_approval_not_stale(
            request=req, run=run, submitted_state_version=999
        )

    # evidence changed
    with pytest.raises(WorkflowFailure):
        validate_approval_not_stale(
            request=req,
            run=run,
            current_evidence_hash=hash_payload([{"page": 99}]),
        )

    # policy changed
    with pytest.raises(WorkflowFailure):
        validate_approval_not_stale(
            request=req,
            run=run,
            current_policy_hash=hash_payload({"tool": "x", "tier": "GREEN"}),
        )

    # run no longer awaiting
    done = run.model_copy(update={"status": WorkflowStatus.COMPLETED})
    with pytest.raises(WorkflowFailure):
        validate_approval_not_stale(request=req, run=done)

    # action state changed
    changed = proposal.model_copy(update={"args": {**proposal.args, "transition_summary": "changed"}})
    with pytest.raises(WorkflowFailure):
        validate_approval_not_stale(request=req, run=run, current_proposal=changed)


def test_primary_scenario_local_green_phoenix_pause_red_audit() -> None:
    driver = LocalWorkflowDriver(
        include_amber=True,
        planner=ConstrainedActionPlanner(include_amber=True, include_red_bait=True),
    )
    started = asyncio.run(driver.start())
    assert started.paused is True
    assert started.run.status == WorkflowStatus.AWAITING_APPROVAL
    actions = driver.state.list_actions(started.run.run_id)
    green_done = [a for a in actions if a.authorized_tier == RiskTier.GREEN and a.executed]
    assert green_done
    assert any(a.tool_name == "create_courier_exception_task" for a in green_done)
    assert any(a.tool_name == "update_contact_directory" for a in green_done)
    reds = [a for a in actions if a.authorized_tier == RiskTier.RED]
    assert reds
    assert all(a.executed is False for a in reds)

    apr = driver.state.get_approval_request(started.pause.approval_id)  # type: ignore[union-attr]
    assert apr is not None
    assert apr.affected_participant_id == "P002"
    assert apr.tool_name == "draft_participant_transition_plan"
    assert apr.reason_approval_required

    resumed = asyncio.run(driver.resume(run_id=started.run.run_id, approved=True))
    assert resumed.run.status in {
        WorkflowStatus.COMPLETED,
        WorkflowStatus.COMPLETED_WITH_BLOCKS,
    }
    ok, errs = verify_audit_chain(driver.state.list_audit_events(started.run.run_id))
    assert ok, errs
