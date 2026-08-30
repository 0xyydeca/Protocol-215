"""Tests for resumable ADK amendment workflow."""

from __future__ import annotations

import asyncio

import pytest

from protocol215.adapters.fakes import FakeActionPlanner
from protocol215.domain.enums import ActionStatus, RiskTier, WorkflowStatus
from protocol215.workflow.driver import LocalWorkflowDriver
from protocol215.workflow.errors import WorkflowFailure
from protocol215.workflow.runtime import get_runtime


def _run(coro):
    return asyncio.run(coro)


def test_happy_path_no_approval() -> None:
    driver = LocalWorkflowDriver(include_amber=False)
    result = _run(driver.start())
    assert result.paused is False
    assert result.run.status == WorkflowStatus.COMPLETED
    assert "SafeActionExecutor" in result.run.completed_nodes
    assert "HumanApproval" not in result.run.completed_nodes
    assert "CompleteRun" in result.events
    actions = driver.state.list_actions(result.run.run_id)
    assert actions
    assert all(a.authorized_tier == RiskTier.GREEN for a in actions if a.executed)


def test_path_with_one_approval() -> None:
    driver = LocalWorkflowDriver(include_amber=True)
    started = _run(driver.start())
    assert started.paused is True
    assert started.run.status == WorkflowStatus.AWAITING_APPROVAL
    inv_before = started.invocation_id
    resumed = _run(driver.resume(run_id=started.run.run_id, approved=True))
    assert resumed.paused is False
    assert resumed.invocation_id == inv_before
    assert resumed.run.status == WorkflowStatus.COMPLETED
    assert "HumanApproval" in resumed.events
    assert "ApprovedActionExecutor" in resumed.events
    amber = [
        a
        for a in driver.state.list_actions(started.run.run_id)
        if a.authorized_tier == RiskTier.AMBER
    ]
    assert amber
    assert all(a.executed and a.approved for a in amber)


def test_cloud_api_pre_recorded_approval_then_resume() -> None:
    """Web records APPROVED before Pub/Sub resume — must not fail as stale."""
    from protocol215.domain.enums import ApprovalStatus

    driver = LocalWorkflowDriver(include_amber=True)
    started = _run(driver.start())
    assert started.pause is not None and started.pause.approval_id
    driver.service.record_approval(
        approval_id=started.pause.approval_id,
        decision=ApprovalStatus.APPROVED,
        actor="synthetic_operator",
    )
    resumed = _run(driver.resume(run_id=started.run.run_id, approved=True))
    assert resumed.paused is False
    assert resumed.run.status == WorkflowStatus.COMPLETED
    assert "HumanApproval" in resumed.events
    assert "ApprovedActionExecutor" in resumed.events


def test_rejection_path() -> None:
    driver = LocalWorkflowDriver(include_amber=True)
    started = _run(driver.start())
    resumed = _run(driver.resume(run_id=started.run.run_id, approved=False, comment="no"))
    assert resumed.run.status in {
        WorkflowStatus.COMPLETED,
        WorkflowStatus.COMPLETED_WITH_BLOCKS,
    }
    amber = [
        a
        for a in driver.state.list_actions(started.run.run_id)
        if a.authorized_tier == RiskTier.AMBER and a.executed
    ]
    assert amber == []
    assert "ApprovedActionExecutor" not in resumed.events


def test_same_invocation_resumes() -> None:
    driver = LocalWorkflowDriver(include_amber=True)
    started = _run(driver.start())
    resumed = _run(driver.resume(run_id=started.run.run_id, approved=True))
    assert started.invocation_id
    assert started.invocation_id == resumed.invocation_id


def test_completed_nodes_do_not_repeat_green() -> None:
    driver = LocalWorkflowDriver(include_amber=True)
    started = _run(driver.start())
    counts_before = dict(driver.green_execution_counts(started.run.run_id))
    assert counts_before
    assert all(v == 1 for v in counts_before.values())
    _run(driver.resume(run_id=started.run.run_id, approved=True))
    counts_after = driver.green_execution_counts(started.run.run_id)
    assert counts_after == counts_before
    # Node skip markers present
    seq = driver.state.get_run(started.run.run_id).event_sequence
    assert seq.count("SafeActionExecutor") == 1


def test_duplicate_resume_event() -> None:
    driver = LocalWorkflowDriver(include_amber=True)
    started = _run(driver.start())
    first = _run(driver.resume(run_id=started.run.run_id, approved=True))
    amber_exec_1 = [
        a.execution_id
        for a in driver.state.list_actions(started.run.run_id)
        if a.authorized_tier == RiskTier.AMBER and a.executed
    ]
    second = _run(driver.resume(run_id=started.run.run_id, approved=True))
    amber_exec_2 = [
        a.execution_id
        for a in driver.state.list_actions(started.run.run_id)
        if a.authorized_tier == RiskTier.AMBER and a.executed
    ]
    assert amber_exec_1 == amber_exec_2
    assert (
        "HumanApproval:duplicate_resume" in second.events
        or first.run.status == WorkflowStatus.COMPLETED
    )


def test_crash_before_approval_restart_and_resume() -> None:
    driver = LocalWorkflowDriver(include_amber=True)
    started = _run(driver.start())
    assert started.paused
    inv = started.invocation_id
    # Crash: drop in-memory runtime + pause cache; SQLite + ADK session remain.
    driver.shutdown_runtime(started.run.run_id)
    resumed = _run(driver.resume(run_id=started.run.run_id, approved=True))
    assert resumed.invocation_id == inv
    assert resumed.run.status == WorkflowStatus.COMPLETED
    assert all(v == 1 for v in driver.green_execution_counts(started.run.run_id).values())


def test_failure_handler_preserves_diagnostics() -> None:
    driver = LocalWorkflowDriver(include_amber=False)

    async def boom():
        result = await driver.start()
        rt = get_runtime(result.run.run_id)
        rt.diagnostics.update(
            {
                "failure_class": "invalid_input",
                "failure_detail": "synthetic failure",
                "failure_retryable": False,
            }
        )
        from protocol215.workflow.nodes import _failure_handler_impl

        class Ctx:
            state = {
                "run_id": result.run.run_id,
                "failure_class": "invalid_input",
                "failure_detail": "synthetic failure",
                "failure_retryable": False,
            }

        out = _failure_handler_impl(Ctx())  # type: ignore[arg-type]
        assert out["diagnostics"]["preserved"] is True
        run = driver.state.get_run(result.run.run_id)
        assert run.status == WorkflowStatus.FAILED_TERMINAL
        assert run.failure_detail == "synthetic failure"
        return out

    _run(boom())


def test_red_action_never_reaches_executor_success() -> None:
    driver = LocalWorkflowDriver(planner=FakeActionPlanner(include_amber=False, include_red=True))
    result = _run(driver.start())
    reds = [a for a in driver.state.list_actions(result.run.run_id) if a.tool_name == "change_dose"]
    assert reds
    assert all(a.authorized_tier == RiskTier.RED for a in reds)
    assert all(a.executed is False for a in reds)
    assert all(a.status == ActionStatus.BLOCKED for a in reds)


def test_stale_approval_rejected() -> None:
    driver = LocalWorkflowDriver(include_amber=True)
    started = _run(driver.start())
    with pytest.raises(WorkflowFailure) as exc:
        _run(
            driver.resume(
                run_id=started.run.run_id,
                approved=True,
                force_stale=True,
            )
        )
    assert exc.value.failure_class.value == "stale_approval"
    run = driver.state.get_run(started.run.run_id)
    assert run.status == WorkflowStatus.FAILED_TERMINAL
    assert run.failure_detail
