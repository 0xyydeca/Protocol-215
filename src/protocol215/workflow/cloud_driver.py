"""Cloud ADK workflow driver — durable sessions, GCS PDFs, Firestore state."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

from google.adk.runners import Runner
from google.genai import types

from protocol215.adapters.audit_log import HashChainedAuditLog
from protocol215.adapters.clock import SystemClock
from protocol215.adapters.fakes import FakeActionPlanner
from protocol215.adapters.gemini.factory import build_protocol_compiler
from protocol215.adapters.identifiers import UUIDIdentifierGenerator
from protocol215.application.services import AmendmentAppService
from protocol215.cloud.errors import RetryableWorkerError, TerminalWorkerError
from protocol215.cloud.events import EventEnvelope
from protocol215.config import Settings
from protocol215.domain.enums import FailureClass, WorkflowStatus
from protocol215.domain.models import SessionMetadata
from protocol215.ports import EventBus, ObjectStore, StateStore
from protocol215.workflow.driver import PauseState, WorkflowDriveResult
from protocol215.workflow.errors import WorkflowFailure, classify_exception
from protocol215.workflow.graph import APP_NAME, build_app
from protocol215.workflow.nodes import _failure_handler_impl
from protocol215.workflow.runtime import WorkflowRuntime, clear_runtime, register_runtime

logger = logging.getLogger("protocol215.cloud.driver")

_TERMINAL_OR_PAUSE = {
    WorkflowStatus.AWAITING_APPROVAL,
    WorkflowStatus.COMPLETED,
    WorkflowStatus.COMPLETED_WITH_BLOCKS,
    WorkflowStatus.FAILED_RETRYABLE,
    WorkflowStatus.FAILED_TERMINAL,
    WorkflowStatus.FAILED,
}


@dataclass
class CloudWorkflowDriver:
    """
    Drive the ADK amendment workflow against cloud adapters.

    Unlike LocalWorkflowDriver, start() loads an existing Firestore run and
    PDFs from the object store (GCS). Session history is persisted via the
    injected ADK SessionService (Firestore or Sqlite).
    """

    settings: Settings
    state: StateStore
    objects: ObjectStore
    events: EventBus
    session_service: Any
    compiler: Any | None = None
    planner: FakeActionPlanner | None = None
    clock: SystemClock = field(default_factory=SystemClock)
    ids: UUIDIdentifierGenerator = field(default_factory=UUIDIdentifierGenerator)
    _pause_by_run: dict[str, PauseState] = field(default_factory=dict)
    _runner: Runner | None = field(default=None, init=False, repr=False)
    _service: AmendmentAppService | None = field(default=None, init=False, repr=False)
    _audit: HashChainedAuditLog | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.compiler is None:
            self.compiler = build_protocol_compiler(self.settings)
        if self.planner is None:
            self.planner = FakeActionPlanner(include_amber=True)
        assert self.compiler is not None
        assert self.planner is not None
        self._audit = HashChainedAuditLog(self.state, self.clock, self.ids)
        self._service = AmendmentAppService(
            state=self.state,
            objects=self.objects,
            events=self.events,
            audit=self._audit,
            compiler=self.compiler,
            planner=self.planner,
            clock=self.clock,
            ids=self.ids,
        )
        app = build_app()
        self._runner = Runner(app=app, session_service=self.session_service)

    def _make_runtime(self, run_id: str) -> WorkflowRuntime:
        assert self.compiler is not None
        assert self.planner is not None
        return WorkflowRuntime(
            service=self.service,
            state=self.state,
            objects=self.objects,
            events=self.events,
            audit=self.audit,
            compiler=self.compiler,
            planner=self.planner,
            clock=self.clock,
            ids=self.ids,
            run_id=run_id,
        )

    @property
    def service(self) -> AmendmentAppService:
        assert self._service is not None
        return self._service

    @property
    def audit(self) -> HashChainedAuditLog:
        assert self._audit is not None
        return self._audit

    @property
    def runner(self) -> Runner:
        assert self._runner is not None
        return self._runner

    def start(self, envelope: EventEnvelope) -> WorkflowStatus:
        return asyncio.run(self.start_async(envelope))

    def resume(self, envelope: EventEnvelope) -> WorkflowStatus:
        return asyncio.run(self.resume_async(envelope))

    async def start_async(self, envelope: EventEnvelope) -> WorkflowStatus:
        run = self.state.get_run(envelope.run_id)
        if run is None:
            raise TerminalWorkerError(
                f"run not found: {envelope.run_id}",
                correlation_id=envelope.correlation_id,
                dead_letter_reason="run_not_found",
            )
        self._stamp_worker_diagnostics(run, envelope.correlation_id)
        old_key = (
            run.object_keys.get(run.from_version)
            or f"runs/{run.run_id}/protocols/v{run.from_version}.pdf"
        )
        new_key = (
            run.object_keys.get(run.to_version)
            or f"runs/{run.run_id}/protocols/v{run.to_version}.pdf"
        )
        # Prove PDFs are readable from the configured object store (GCS in cloud).
        if not self.objects.exists(old_key) or not self.objects.exists(new_key):
            self._fail_run(
                run.run_id,
                WorkflowStatus.FAILED_TERMINAL,
                "missing_protocol_pdfs",
                f"PDF missing in object store: {old_key} / {new_key}",
            )
            return WorkflowStatus.FAILED_TERMINAL

        session = await self.session_service.create_session(
            app_name=APP_NAME, user_id="operator", state={}
        )
        self.state.save_session_metadata(
            SessionMetadata(
                run_id=run.run_id,
                session_id=session.id,
                invocation_id=None,
                cursor="CREATED",
            )
        )
        runtime = self._make_runtime(run.run_id)
        register_runtime(runtime)
        result = await self._drive(
            runtime=runtime,
            session_id=session.id,
            invocation_id=None,
            new_message=types.Content(
                role="user",
                parts=[types.Part(text=f"amendment.received:{run.run_id}")],
            ),
            state_delta={
                "run_id": run.run_id,
                "old_pdf_key": old_key,
                "new_pdf_key": new_key,
                "session_id": session.id,
            },
        )
        return self._result_status(result)

    async def resume_async(self, envelope: EventEnvelope) -> WorkflowStatus:
        run_id = envelope.run_id
        run = self.state.get_run(run_id)
        if run is not None:
            self._stamp_worker_diagnostics(run, envelope.correlation_id)
        pause = self._pause_by_run.get(run_id)
        meta = self.state.get_session_metadata(run_id)
        if pause is None and meta is not None:
            pause = PauseState(
                run_id=run_id,
                session_id=meta.session_id,
                invocation_id=meta.invocation_id or "",
                interrupt_id=meta.interrupt_id or f"approval-{run_id}",
                approval_id=(meta.extra or {}).get("approval_id") or envelope.approval_id,
                expected_state_version=meta.expected_state_version,
                function_call_id=meta.interrupt_id or f"approval-{run_id}",
            )
            self._pause_by_run[run_id] = pause
        if pause is None:
            raise TerminalWorkerError(
                "nothing to resume — missing session metadata",
                correlation_id=envelope.correlation_id,
                dead_letter_reason="missing_session_metadata",
            )
        if not pause.session_id or not pause.invocation_id:
            raise TerminalWorkerError(
                "persisted session_id/invocation_id required for resume",
                correlation_id=envelope.correlation_id,
                dead_letter_reason="incomplete_session_metadata",
            )

        approved = True
        if envelope.payload:
            decision = str(envelope.payload.get("decision", "approved")).lower()
            approved = decision == "approved"

        runtime = self._ensure_runtime(run_id)
        response = types.Content(
            role="user",
            parts=[
                types.Part(
                    function_response=types.FunctionResponse(
                        id=pause.function_call_id,
                        name="adk_request_input",
                        response={
                            "approved": approved,
                            "comment": (envelope.payload or {}).get("comment", ""),
                            "approval_id": pause.approval_id or envelope.approval_id,
                            "state_version": pause.expected_state_version,
                        },
                    )
                )
            ],
        )
        result = await self._drive(
            runtime=runtime,
            session_id=pause.session_id,
            invocation_id=pause.invocation_id,
            new_message=response,
            state_delta={"run_id": run_id},
        )
        return self._result_status(result)

    def _ensure_runtime(self, run_id: str) -> WorkflowRuntime:
        try:
            from protocol215.workflow.runtime import get_runtime

            return get_runtime(run_id)
        except KeyError:
            runtime = self._make_runtime(run_id)
            run = runtime.run()
            proposals = self.planner.propose(  # type: ignore[union-attr]
                run=run,
                changes=self.state.list_changes(run_id),
                findings=self.state.list_findings(run_id),
            )
            runtime.proposals = proposals
            from protocol215.domain.enums import RiskTier
            from protocol215.policy.matrix import authorize_proposal

            for p in proposals:
                tier = authorize_proposal(p)
                if tier == RiskTier.GREEN:
                    runtime.green_proposal_ids.append(p.proposal_id)
                elif tier == RiskTier.AMBER:
                    runtime.amber_proposal_ids.append(p.proposal_id)
                else:
                    runtime.red_proposal_ids.append(p.proposal_id)
            # Already-executed GREEN actions stay in state; SafeActionExecutor is idempotent.
            register_runtime(runtime)
            return runtime

    async def _drive(
        self,
        *,
        runtime: WorkflowRuntime,
        session_id: str,
        invocation_id: str | None,
        new_message: types.Content,
        state_delta: dict[str, Any] | None = None,
    ) -> WorkflowDriveResult:
        adk_authors: list[str] = []
        final_inv = invocation_id
        pause: PauseState | None = None
        error: str | None = None
        try:
            async for event in self.runner.run_async(
                user_id="operator",
                session_id=session_id,
                invocation_id=invocation_id,
                new_message=new_message,
                state_delta=state_delta,
            ):
                final_inv = event.invocation_id or final_inv
                adk_authors.append(event.author or "")
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        fc = part.function_call
                        if fc and fc.name == "adk_request_input":
                            interrupt_id = fc.id or (fc.args or {}).get("interruptId")
                            apr_id = None
                            expected_sv = 0
                            meta = runtime.state.get_session_metadata(runtime.run_id)
                            if meta:
                                apr_id = (meta.extra or {}).get("approval_id")
                                expected_sv = meta.expected_state_version
                                runtime.state.save_session_metadata(
                                    meta.model_copy(
                                        update={
                                            "invocation_id": final_inv,
                                            "interrupt_id": interrupt_id,
                                        }
                                    )
                                )
                            pause = PauseState(
                                run_id=runtime.run_id,
                                session_id=session_id,
                                invocation_id=final_inv or "",
                                interrupt_id=interrupt_id or "",
                                approval_id=apr_id,
                                expected_state_version=expected_sv,
                                function_call_id=interrupt_id or "",
                            )
                            self._pause_by_run[runtime.run_id] = pause
                            if apr_id and final_inv:
                                req = runtime.state.get_approval_request(apr_id)
                                if req is not None and not req.invocation_id:
                                    runtime.state.save_approval_request(
                                        req.model_copy(update={"invocation_id": final_inv})
                                    )
        except Exception as exc:  # noqa: BLE001
            fclass = classify_exception(exc)
            runtime.diagnostics.update(
                {
                    "failure_class": fclass.value,
                    "failure_detail": str(exc),
                    "failure_retryable": isinstance(exc, WorkflowFailure) and exc.retryable,
                }
            )

            class _Ctx:
                state = {
                    "run_id": runtime.run_id,
                    "failure_class": fclass.value,
                    "failure_detail": str(exc),
                    "failure_retryable": isinstance(exc, WorkflowFailure) and exc.retryable,
                }

            _failure_handler_impl(_Ctx())
            error = str(exc)
            retryable = (isinstance(exc, WorkflowFailure) and exc.retryable) or fclass in {
                FailureClass.TRANSIENT_MODEL_ERROR,
                FailureClass.MODEL_SCHEMA_ERROR,
            }
            if retryable:
                raise RetryableWorkerError(error, correlation_id="") from exc
            raise TerminalWorkerError(
                error,
                correlation_id="",
                dead_letter_reason=fclass.value,
            ) from exc

        run = self.state.get_run(runtime.run_id)
        assert run is not None
        meta = self.state.get_session_metadata(runtime.run_id)
        if meta and final_inv:
            self.state.save_session_metadata(meta.model_copy(update={"invocation_id": final_inv}))
        return WorkflowDriveResult(
            run=run,
            session_id=session_id,
            invocation_id=final_inv,
            paused=pause is not None and run.status == WorkflowStatus.AWAITING_APPROVAL,
            pause=pause if run.status == WorkflowStatus.AWAITING_APPROVAL else None,
            events=list(runtime.event_log) or list(run.event_sequence),
            adk_event_authors=adk_authors,
            error=error,
        )

    def _result_status(self, result: WorkflowDriveResult) -> WorkflowStatus:
        status = result.run.status
        if status not in _TERMINAL_OR_PAUSE and result.paused:
            return WorkflowStatus.AWAITING_APPROVAL
        return status

    def _stamp_worker_diagnostics(self, run: Any, correlation_id: str | None) -> None:
        import os

        now = self.clock.now()
        updates: dict[str, Any] = {
            "updated_at": now,
            "worker_revision": os.environ.get("K_REVISION") or run.worker_revision,
        }
        if correlation_id and not run.correlation_id:
            updates["correlation_id"] = correlation_id
        model = getattr(self.compiler, "model", None) or getattr(self.compiler, "model_id", None)
        if model and not run.compiler_model:
            updates["compiler_model"] = str(model)
        self.state.save_run(run.model_copy(update=updates))

    def _fail_run(
        self,
        run_id: str,
        status: WorkflowStatus,
        failure_class: str,
        detail: str,
    ) -> None:
        run = self.state.get_run(run_id)
        if run is None:
            return
        self.state.save_run(
            run.model_copy(
                update={
                    "status": status,
                    "failure_class": failure_class,
                    "failure_detail": detail,
                    "checkpoint": run.checkpoint or "FAILED",
                    "state_version": run.state_version + 1,
                    "updated_at": self.clock.now(),
                }
            )
        )

    def shutdown(self) -> None:
        """Drop in-memory runtime/pause caches; durable state remains in stores."""
        for run_id in list(self._pause_by_run):
            clear_runtime(run_id)
        self._pause_by_run.clear()
