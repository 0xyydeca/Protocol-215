"""Local ADK workflow driver — start / pause / resume without holding HTTP."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from protocol215.adapters.audit_log import HashChainedAuditLog
from protocol215.adapters.clock import SystemClock
from protocol215.adapters.event_bus_inprocess import InProcessEventBus
from protocol215.adapters.fake_explainer import FakeChangeExplainer
from protocol215.adapters.fakes import FakeActionPlanner, FakeProtocolCompiler
from protocol215.adapters.identifiers import UUIDIdentifierGenerator
from protocol215.adapters.object_store_local import LocalFileObjectStore
from protocol215.adapters.state_store_sqlite import SQLiteStateStore
from protocol215.application.services import AmendmentAppService
from protocol215.domain.enums import FailureClass, WorkflowStatus
from protocol215.domain.models import SessionMetadata, WorkflowRun
from protocol215.workflow.errors import WorkflowFailure, classify_exception
from protocol215.workflow.graph import APP_NAME, build_app
from protocol215.workflow.nodes import _failure_handler_impl
from protocol215.workflow.runtime import WorkflowRuntime, clear_runtime, register_runtime


@dataclass
class PauseState:
    run_id: str
    session_id: str
    invocation_id: str
    interrupt_id: str
    approval_id: str | None
    expected_state_version: int
    function_call_id: str


@dataclass
class WorkflowDriveResult:
    run: WorkflowRun
    session_id: str
    invocation_id: str | None
    paused: bool = False
    pause: PauseState | None = None
    events: list[str] = field(default_factory=list)
    adk_event_authors: list[str] = field(default_factory=list)
    error: str | None = None


class LocalWorkflowDriver:
    """Runs the ADK App locally with SQLite + local object store + fakes."""

    def __init__(
        self,
        *,
        work_dir: Path | None = None,
        include_amber: bool = True,
        planner: FakeActionPlanner | None = None,
    ) -> None:
        self.work_dir = Path(work_dir or tempfile.mkdtemp(prefix="p215-wf-"))
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.objects = LocalFileObjectStore(self.work_dir / "objects")
        self.state = SQLiteStateStore(self.work_dir / "state.sqlite3")
        self.events = InProcessEventBus()
        self.clock = SystemClock()
        self.ids = UUIDIdentifierGenerator()
        self.audit = HashChainedAuditLog(self.state, self.clock, self.ids)
        self.compiler = FakeProtocolCompiler()
        self.planner = planner or FakeActionPlanner(include_amber=include_amber)
        self.service = AmendmentAppService(
            state=self.state,
            objects=self.objects,
            events=self.events,
            audit=self.audit,
            compiler=self.compiler,
            planner=self.planner,
            clock=self.clock,
            ids=self.ids,
        )
        self.session_service = InMemorySessionService()
        self.app = build_app()
        self.runner = Runner(app=self.app, session_service=self.session_service)
        self._pause_by_run: dict[str, PauseState] = {}
        # Keep FakeChangeExplainer import used (explanations via analysis pipeline).
        _ = FakeChangeExplainer

    def seed_pdfs(self, run_id: str, *, old_bytes: bytes, new_bytes: bytes) -> tuple[str, str]:
        old_key = f"runs/{run_id}/protocols/v1.pdf"
        new_key = f"runs/{run_id}/protocols/v2.pdf"
        self.objects.put_bytes(old_key, old_bytes, content_type="application/pdf")
        self.objects.put_bytes(new_key, new_bytes, content_type="application/pdf")
        return old_key, new_key

    async def start(
        self,
        *,
        study_id: str = "AURORA-101",
        from_version: str = "1.0",
        to_version: str = "2.0",
        old_pdf: bytes | None = None,
        new_pdf: bytes | None = None,
        run_id: str | None = None,
    ) -> WorkflowDriveResult:
        run = self.service.create_run(
            study_id=study_id,
            from_version=from_version,
            to_version=to_version,
            run_id=run_id,
        )
        old_pdf = old_pdf or b"%PDF-1.4\nProtocol Version: 1.0\n%%EOF\n"
        new_pdf = new_pdf or b"%PDF-1.4\nProtocol Version: 2.0\n%%EOF\n"
        old_key, new_key = self.seed_pdfs(run.run_id, old_bytes=old_pdf, new_bytes=new_pdf)

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

        runtime = WorkflowRuntime(
            service=self.service,
            state=self.state,
            objects=self.objects,
            events=self.events,
            audit=self.audit,
            compiler=self.compiler,
            planner=self.planner,
            clock=self.clock,
            ids=self.ids,
            run_id=run.run_id,
        )
        register_runtime(runtime)

        state_delta = {
            "run_id": run.run_id,
            "old_pdf_key": old_key,
            "new_pdf_key": new_key,
            "session_id": session.id,
        }
        return await self._drive(
            runtime=runtime,
            session_id=session.id,
            invocation_id=None,
            new_message=types.Content(
                role="user",
                parts=[types.Part(text=f"amendment.received:{run.run_id}")],
            ),
            state_delta=state_delta,
        )

    async def resume(
        self,
        *,
        run_id: str,
        approved: bool,
        comment: str = "",
        state_version: int | None = None,
        force_stale: bool = False,
    ) -> WorkflowDriveResult:
        pause = self._pause_by_run.get(run_id)
        meta = self.state.get_session_metadata(run_id)
        if pause is None and meta is not None:
            # Restart recovery: rebuild PauseState from persisted metadata.
            pause = PauseState(
                run_id=run_id,
                session_id=meta.session_id,
                invocation_id=meta.invocation_id or "",
                interrupt_id=meta.interrupt_id or f"approval-{run_id}",
                approval_id=(meta.extra or {}).get("approval_id"),
                expected_state_version=meta.expected_state_version,
                function_call_id=meta.interrupt_id or f"approval-{run_id}",
            )
            self._pause_by_run[run_id] = pause
        if pause is None:
            raise WorkflowFailure(
                "nothing to resume",
                failure_class=FailureClass.INVALID_INPUT,
            )

        runtime = self._ensure_runtime(run_id)
        sv = state_version if state_version is not None else pause.expected_state_version
        if force_stale:
            sv = (pause.expected_state_version or 0) - 1

        response = types.Content(
            role="user",
            parts=[
                types.Part(
                    function_response=types.FunctionResponse(
                        id=pause.function_call_id,
                        name="adk_request_input",
                        response={
                            "approved": approved,
                            "comment": comment,
                            "approval_id": pause.approval_id,
                            "state_version": sv,
                        },
                    )
                )
            ],
        )
        return await self._drive(
            runtime=runtime,
            session_id=pause.session_id,
            invocation_id=pause.invocation_id,
            new_message=response,
            state_delta={"run_id": run_id},
        )

    def _ensure_runtime(self, run_id: str) -> WorkflowRuntime:
        try:
            from protocol215.workflow.runtime import get_runtime

            return get_runtime(run_id)
        except KeyError:
            runtime = WorkflowRuntime(
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
            # Restore proposal buckets from state actions / re-propose
            run = runtime.run()
            proposals = self.planner.propose(
                run=run,
                changes=self.state.list_changes(run_id),
                findings=self.state.list_findings(run_id),
            )
            runtime.proposals = proposals
            from protocol215.policy.matrix import authorize_proposal
            from protocol215.domain.enums import RiskTier

            for p in proposals:
                tier = authorize_proposal(p)
                if tier == RiskTier.GREEN:
                    runtime.green_proposal_ids.append(p.proposal_id)
                elif tier == RiskTier.AMBER:
                    runtime.amber_proposal_ids.append(p.proposal_id)
                else:
                    runtime.red_proposal_ids.append(p.proposal_id)
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
                            approval_id = runtime.pending_approval_id or runtime.state.get_session_metadata(
                                runtime.run_id
                            )
                            apr_id = None
                            expected_sv = 0
                            meta = runtime.state.get_session_metadata(runtime.run_id)
                            if meta:
                                apr_id = (meta.extra or {}).get("approval_id")
                                expected_sv = meta.expected_state_version
                                # Persist invocation for resume
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
                            ctx_state = (await self.session_service.get_session(
                                app_name=APP_NAME, user_id="operator", session_id=session_id
                            )).state
                            ctx_state["invocation_id"] = final_inv
                # Capture node outputs into event log if present
                if event.output and isinstance(event.output, dict) and event.output.get("node"):
                    pass
        except Exception as exc:  # noqa: BLE001 — classify, persist via FailureHandler, re-raise path
            fclass = classify_exception(exc)
            runtime.diagnostics.update(
                {
                    "failure_class": fclass.value,
                    "failure_detail": str(exc),
                    "failure_retryable": isinstance(exc, WorkflowFailure) and exc.retryable,
                }
            )
            # Invoke FailureHandler node logic directly to preserve diagnostics.
            class _Ctx:
                state = {
                    "run_id": runtime.run_id,
                    "failure_class": fclass.value,
                    "failure_detail": str(exc),
                    "failure_retryable": isinstance(exc, WorkflowFailure) and exc.retryable,
                }

            _failure_handler_impl(_Ctx())  # type: ignore[arg-type]
            error = str(exc)
            run = runtime.run()
            result = WorkflowDriveResult(
                run=run,
                session_id=session_id,
                invocation_id=final_inv,
                paused=False,
                pause=None,
                events=list(runtime.event_log) or list(run.event_sequence),
                adk_event_authors=adk_authors,
                error=error,
            )
            # Do not swallow — surface after diagnostics preserved.
            raise WorkflowFailure(
                str(exc),
                failure_class=fclass if isinstance(exc, WorkflowFailure) else classify_exception(exc),
                retryable=isinstance(exc, WorkflowFailure) and exc.retryable,
                details={"drive_result": "diagnostics_preserved"},
            ) from exc
        run = runtime.run()
        # Sync invocation into session metadata
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

    def green_execution_counts(self, run_id: str) -> dict[str, int]:
        from protocol215.workflow.runtime import get_runtime

        return dict(get_runtime(run_id).green_execution_counts)

    def shutdown_runtime(self, run_id: str) -> None:
        """Simulate worker crash — drop in-memory runtime, keep SQLite/session."""
        clear_runtime(run_id)
        self._pause_by_run.pop(run_id, None)
