"""Run local ADK amendment workflow demo (approval path)."""

from __future__ import annotations

import asyncio
import json
import sys

from protocol215.workflow.driver import LocalWorkflowDriver


async def main() -> int:
    driver = LocalWorkflowDriver(include_amber=True)
    started = await driver.start()
    print("=== amendment.received ===")
    print(f"run_id={started.run.run_id}")
    print(f"status={started.run.status.value}")
    print(f"session_id={started.session_id}")
    print(f"invocation_id_before={started.invocation_id}")
    print(f"paused={started.paused}")
    if started.pause:
        print(
            json.dumps(
                {
                    "interrupt_id": started.pause.interrupt_id,
                    "approval_id": started.pause.approval_id,
                    "expected_state_version": started.pause.expected_state_version,
                },
                indent=2,
            )
        )
    print("event_sequence=", started.events)
    print("green_execution_counts=", driver.green_execution_counts(started.run.run_id))

    resumed = await driver.resume(
        run_id=started.run.run_id, approved=True, comment="operator approve"
    )
    print("=== amendment.resume ===")
    print(f"status={resumed.run.status.value}")
    print(f"invocation_id_after={resumed.invocation_id}")
    print(f"same_invocation={started.invocation_id == resumed.invocation_id}")
    print("event_sequence=", resumed.events)
    counts = driver.green_execution_counts(started.run.run_id)
    print("green_execution_counts=", counts)
    print("green_actions_ran_only_once=", all(v == 1 for v in counts.values()))
    actions = driver.state.list_actions(started.run.run_id)
    print(
        "actions=",
        [
            {
                "tool": a.tool_name,
                "tier": a.authorized_tier.value,
                "executed": a.executed,
                "approved": a.approved,
                "replayed": a.replayed,
            }
            for a in actions
        ],
    )
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
