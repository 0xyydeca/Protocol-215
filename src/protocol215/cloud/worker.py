"""Cloud Run worker: Pub/Sub push handler — never waits on human approval."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from protocol215.cloud.errors import RetryableWorkerError, TerminalWorkerError
from protocol215.cloud.events import AmendmentEventType, EventEnvelope
from protocol215.cloud.logging import emit_cloud_log, timed_operation
from protocol215.domain.enums import WorkflowStatus
from protocol215.ports import StateStore


class WorkflowRunner(Protocol):
    def start(self, envelope: EventEnvelope) -> WorkflowStatus: ...

    def resume(self, envelope: EventEnvelope) -> WorkflowStatus: ...


# Push handler may ACK when workflow reaches any of these states.
ACK_STATUSES = {
    WorkflowStatus.COMPLETED,
    WorkflowStatus.COMPLETED_WITH_BLOCKS,
    WorkflowStatus.AWAITING_APPROVAL,
    WorkflowStatus.FAILED_TERMINAL,
    WorkflowStatus.FAILED,
    WorkflowStatus.PARTIAL,
    WorkflowStatus.MANIFEST_READY,
    WorkflowStatus.VERIFYING,
    WorkflowStatus.RESUMING,
    WorkflowStatus.EXECUTING_SAFE_ACTIONS,
    WorkflowStatus.EXECUTING_APPROVED_AMBER,
    WorkflowStatus.ANALYZING,
    WorkflowStatus.COMPILING,
    WorkflowStatus.REHEARSING,
    WorkflowStatus.PLANNING,
    WorkflowStatus.ARTIFACTS_REGISTERED,
    WorkflowStatus.CREATED,
}


@dataclass
class WorkerResult:
    status: WorkflowStatus
    outcome: str
    duplicate: bool = False


class AmendmentWorkerHandler:
    """
    Validate → load run → dedupe → start/resume ADK workflow → ACK semantics.

    Success when workflow reaches completion, human-input pause, or terminal failure.
    Does not keep the HTTP request open while waiting for human approval.
    """

    def __init__(
        self,
        *,
        state: StateStore,
        runner: WorkflowRunner,
        persist_audit: Callable[[EventEnvelope, WorkflowStatus, str], None] | None = None,
    ) -> None:
        self.state = state
        self.runner = runner
        self.persist_audit = persist_audit

    def handle(self, envelope: EventEnvelope) -> WorkerResult:
        with timed_operation(
            message="worker.handle_event",
            run_id=envelope.run_id,
            event_id=envelope.event_id,
            correlation_id=envelope.correlation_id,
            workflow_node="WorkerIngress",
        ) as ctx:
            run = self.state.get_run(envelope.run_id)
            if run is None:
                raise TerminalWorkerError(
                    f"run not found: {envelope.run_id}",
                    correlation_id=envelope.correlation_id,
                    dead_letter_reason="run_not_found",
                )

            idem = envelope.to_domain_event().idempotency_key or envelope.event_id
            newly = self.state.record_processed_event(idem, envelope.event_id)
            if not newly:
                emit_cloud_log(
                    severity="INFO",
                    message="duplicate_event_suppressed",
                    run_id=envelope.run_id,
                    event_id=envelope.event_id,
                    correlation_id=envelope.correlation_id,
                    outcome="duplicate",
                )
                ctx["outcome"] = "duplicate"
                return WorkerResult(status=run.status, outcome="duplicate", duplicate=True)

            try:
                if envelope.event_type == AmendmentEventType.RECEIVED:
                    status = self.runner.start(envelope)
                elif envelope.event_type == AmendmentEventType.RESUME:
                    status = self.runner.resume(envelope)
                else:
                    raise TerminalWorkerError(
                        f"unsupported event type: {envelope.event_type}",
                        correlation_id=envelope.correlation_id,
                        dead_letter_reason="unsupported_event_type",
                    )
            except RetryableWorkerError:
                # Release claim so Pub/Sub redelivery can retry the same event_id.
                self.state.clear_processed_event(idem)
                raise
            except TerminalWorkerError:
                raise
            except Exception as exc:  # noqa: BLE001
                self.state.clear_processed_event(idem)
                raise RetryableWorkerError(
                    f"workflow failed: {exc}",
                    correlation_id=envelope.correlation_id,
                ) from exc

            if self.persist_audit is not None:
                self.persist_audit(envelope, status, "ok")

            if status == WorkflowStatus.FAILED_RETRYABLE:
                self.state.clear_processed_event(idem)
                raise RetryableWorkerError(
                    f"workflow retryable failure: {status.value}",
                    correlation_id=envelope.correlation_id,
                )

            # AWAITING_APPROVAL is an ACK success — human approval is a separate web POST.
            ctx["outcome"] = status.value
            emit_cloud_log(
                severity="INFO",
                message="worker.event_processed",
                run_id=envelope.run_id,
                event_id=envelope.event_id,
                correlation_id=envelope.correlation_id,
                invocation_id=envelope.invocation_id,
                outcome=status.value,
                action_id=envelope.approval_id,
            )
            return WorkerResult(status=status, outcome=status.value, duplicate=False)
