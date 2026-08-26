"""Per-run workflow runtime registry for ADK FunctionNodes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from protocol215.application.hashing import build_idempotency_key
from protocol215.application.services import AmendmentAppService
from protocol215.domain.enums import WorkflowStatus
from protocol215.domain.models import (
    ActionProposal,
    SemanticChange,
    WorkflowRun,
)
from protocol215.ports import (
    ActionPlanner,
    AuditLog,
    Clock,
    EventBus,
    IdentifierGenerator,
    ObjectStore,
    ProtocolCompiler,
    StateStore,
)


@dataclass
class WorkflowRuntime:
    """Ports + working memory for one amendment run."""

    service: AmendmentAppService
    state: StateStore
    objects: ObjectStore
    events: EventBus
    audit: AuditLog
    compiler: ProtocolCompiler
    planner: ActionPlanner
    clock: Clock
    ids: IdentifierGenerator
    run_id: str
    # Working memory (also mirrored into WorkflowRun where durable)
    proposals: list[ActionProposal] = field(default_factory=list)
    green_proposal_ids: list[str] = field(default_factory=list)
    amber_proposal_ids: list[str] = field(default_factory=list)
    red_proposal_ids: list[str] = field(default_factory=list)
    pending_approval_id: str | None = None
    green_execution_counts: dict[str, int] = field(default_factory=dict)
    event_log: list[str] = field(default_factory=list)
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def run(self) -> WorkflowRun:
        run = self.state.get_run(self.run_id)
        if run is None:
            raise KeyError(self.run_id)
        return run

    def set_status(self, status: WorkflowStatus, *, checkpoint: str | None = None) -> WorkflowRun:
        run = self.run()
        updated = run.model_copy(
            update={
                "status": status,
                "checkpoint": checkpoint or status.value,
                "state_version": run.state_version + 1,
            }
        )
        self.state.save_run(updated)
        return updated

    def append_event(self, name: str) -> None:
        self.event_log.append(name)
        run = self.run()
        seq = list(run.event_sequence)
        seq.append(name)
        self.state.save_run(run.model_copy(update={"event_sequence": seq}))

    def mark_node_complete(self, node_name: str) -> None:
        run = self.run()
        nodes = list(run.completed_nodes)
        if node_name not in nodes:
            nodes.append(node_name)
            self.state.save_run(run.model_copy(update={"completed_nodes": nodes}))

    def node_done(self, node_name: str) -> bool:
        return node_name in self.run().completed_nodes

    def bump_green_count(self, idempotency_key: str) -> int:
        self.green_execution_counts[idempotency_key] = (
            self.green_execution_counts.get(idempotency_key, 0) + 1
        )
        return self.green_execution_counts[idempotency_key]


_REGISTRY: dict[str, WorkflowRuntime] = {}


def register_runtime(runtime: WorkflowRuntime) -> None:
    _REGISTRY[runtime.run_id] = runtime


def get_runtime(run_id: str) -> WorkflowRuntime:
    if run_id not in _REGISTRY:
        raise KeyError(f"No workflow runtime for run_id={run_id}")
    return _REGISTRY[run_id]


def clear_runtime(run_id: str) -> None:
    _REGISTRY.pop(run_id, None)


def runtime_from_ctx(ctx: Any) -> WorkflowRuntime:
    run_id = ctx.state.get("run_id")
    if not run_id:
        raise KeyError("session state missing run_id")
    return get_runtime(run_id)


def proposal_idempotency_key(run_id: str, proposal: ActionProposal, protocol_version: str) -> str:
    target = proposal.site_id or proposal.participant_id or proposal.proposal_id
    return proposal.idempotency_key or build_idempotency_key(
        run_id=run_id,
        action_type=proposal.tool_name,
        target_id=target,
        protocol_version=protocol_version,
    )


def changes_summary(changes: list[SemanticChange]) -> list[dict[str, Any]]:
    return [
        {
            "change_id": c.change_id,
            "concept_type": c.concept_type,
            "operation": c.operation.value,
        }
        for c in changes
    ]
