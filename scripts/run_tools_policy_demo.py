"""Primary scenario: green tools, Phoenix AMBER pause, RED blocked, audit chain."""

from __future__ import annotations

import asyncio
import json
import sys

from protocol215.adapters.audit_log import verify_audit_chain
from protocol215.adapters.constrained_planner import ConstrainedActionPlanner
from protocol215.domain.enums import RiskTier
from protocol215.workflow.driver import LocalWorkflowDriver


async def main() -> int:
    driver = LocalWorkflowDriver(
        include_amber=True,
        planner=ConstrainedActionPlanner(include_amber=True, include_red_bait=True),
    )
    started = await driver.start()
    print("=== Primary scenario (amendment.received) ===")
    print(f"run_id={started.run.run_id}")
    print(f"status={started.run.status.value}")
    print(f"paused={started.paused}")

    actions = driver.state.list_actions(started.run.run_id)
    green = [
        {"tool": a.tool_name, "executed": a.executed, "tier": a.authorized_tier.value}
        for a in actions
        if a.authorized_tier == RiskTier.GREEN
    ]
    red = [
        {
            "tool": a.tool_name,
            "executed": a.executed,
            "tier": a.authorized_tier.value,
            "after": a.after,
        }
        for a in actions
        if a.authorized_tier == RiskTier.RED
    ]
    print("green_actions=", json.dumps(green, indent=2))
    print("red_actions_blocked=", json.dumps(red, indent=2))

    if started.pause and started.pause.approval_id:
        apr = driver.state.get_approval_request(started.pause.approval_id)
        print("phoenix_approval_paused=")
        print(
            json.dumps(
                {
                    "approval_id": apr.approval_id if apr else None,
                    "action_id": apr.action_id if apr else None,
                    "tool_name": apr.tool_name if apr else None,
                    "affected_site": apr.affected_site_id if apr else None,
                    "affected_participant": apr.affected_participant_id if apr else None,
                    "reason": apr.reason_approval_required if apr else None,
                    "consequences_of_approval": apr.consequences_of_approval if apr else None,
                    "consequences_of_rejection": apr.consequences_of_rejection if apr else None,
                    "expected_state_version": apr.expected_state_version if apr else None,
                    "invocation_id": apr.invocation_id if apr else None,
                    "interrupt_id": apr.interrupt_id if apr else None,
                },
                indent=2,
            )
        )

    resumed = await driver.resume(
        run_id=started.run.run_id, approved=True, comment="approve phoenix transition"
    )
    print("=== After approval (amendment.resume) ===")
    print(f"status={resumed.run.status.value}")
    print(f"same_invocation={started.invocation_id == resumed.invocation_id}")

    events = driver.state.list_audit_events(started.run.run_id)
    ok, errs = verify_audit_chain(events)
    print(f"audit_chain_valid={ok} events={len(events)}")
    if errs:
        print("audit_errors=", errs)
    print(
        "audit_tail=",
        [
            {
                "seq": e.sequence_number,
                "type": e.event_type,
                "tool": e.tool_id,
                "prev": e.previous_event_hash[:12],
                "hash": e.current_event_hash[:12],
            }
            for e in events[-12:]
        ],
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
