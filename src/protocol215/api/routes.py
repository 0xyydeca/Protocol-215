"""FastAPI route handlers."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, File, Form, Header, Request, UploadFile

from protocol215.api.background import kick_amendment_received, kick_amendment_resume
from protocol215.api.container import AppContainer, submission_fingerprint
from protocol215.api.errors import ApiError, ApiErrorCode
from protocol215.api.pdf_validation import validate_pdf_upload
from protocol215.api.schemas import (
    ApprovalDecisionRequest,
    ApprovalDecisionResponse,
    CreateRunResponse,
    DemoResetResponse,
    ImpactGraphResponse,
    RunListItem,
    RunStatusResponse,
)
from protocol215.api.status import build_run_status
from protocol215.domain.enums import ApprovalStatus, WorkflowStatus
from protocol215.domain.models import ProtocolArtifactRecord, SessionMetadata
from protocol215.policy.approval import validate_approval_not_stale

router = APIRouter()


def _container(request: Request) -> AppContainer:
    return request.app.state.container  # type: ignore[no-any-return]


@router.post("/api/runs", response_model=CreateRunResponse, status_code=202)
async def create_run(
    request: Request,
    background_tasks: BackgroundTasks,
    old_protocol: UploadFile = File(..., description="Prior protocol PDF"),  # noqa: B008
    new_protocol: UploadFile = File(..., description="Amended protocol PDF"),  # noqa: B008
    study_id: str | None = Form(None),
    from_version: str | None = Form(None),
    to_version: str | None = Form(None),
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> CreateRunResponse:
    container = _container(request)
    settings = container.settings
    study = study_id or settings.default_study_id
    from_ver = from_version or settings.default_from_version
    to_ver = to_version or settings.default_to_version

    old_bytes = await old_protocol.read()
    new_bytes = await new_protocol.read()
    old_sha, old_pages = validate_pdf_upload(
        filename=old_protocol.filename,
        data=old_bytes,
        max_bytes=settings.max_pdf_bytes,
        max_pages=settings.max_pdf_pages,
    )
    new_sha, new_pages = validate_pdf_upload(
        filename=new_protocol.filename,
        data=new_bytes,
        max_bytes=settings.max_pdf_bytes,
        max_pages=settings.max_pdf_pages,
    )

    fp = idempotency_key or submission_fingerprint(old_sha, new_sha, study)
    if fp in container.submission_index:
        existing_id = container.submission_index[fp]
        existing = container.state.get_run(existing_id)
        if existing is not None:
            raise ApiError(
                error_code=ApiErrorCode.DUPLICATE,
                message="Duplicate submission; run already exists for these artifacts.",
                status_code=409,
                details={"run_id": existing_id},
            )

    run = container.service.create_run(study_id=study, from_version=from_ver, to_version=to_ver)
    old_key = f"runs/{run.run_id}/protocols/v{from_ver}.pdf"
    new_key = f"runs/{run.run_id}/protocols/v{to_ver}.pdf"
    container.objects.put_bytes(old_key, old_bytes, content_type="application/pdf")
    container.objects.put_bytes(new_key, new_bytes, content_type="application/pdf")
    now = container.service.clock.now()
    container.state.save_protocol_artifact(
        ProtocolArtifactRecord(
            run_id=run.run_id,
            version=from_ver,
            object_key=old_key,
            content_sha256=old_sha,
            registered_at=now,
        )
    )
    container.state.save_protocol_artifact(
        ProtocolArtifactRecord(
            run_id=run.run_id,
            version=to_ver,
            object_key=new_key,
            content_sha256=new_sha,
            registered_at=now,
        )
    )
    container.state.save_run(
        run.model_copy(
            update={
                "object_keys": {from_ver: old_key, to_ver: new_key},
                "status": WorkflowStatus.CREATED,
                "checkpoint": "CREATED",
            }
        )
    )
    container.state.save_session_metadata(
        SessionMetadata(
            run_id=run.run_id,
            session_id=container.service.ids.new_id("sess-"),
            cursor="CREATED",
            extra={"old_sha256": old_sha, "new_sha256": new_sha},
        )
    )

    event = container.service.publish_run_event(
        run_id=run.run_id,
        event_type="amendment.received",
        payload={
            "study_id": study,
            "from_version": from_ver,
            "to_version": to_ver,
            "old_sha256": old_sha,
            "new_sha256": new_sha,
        },
        idempotency_key=f"{run.run_id}:amendment.received:{fp}",
    )
    container.submission_index[fp] = run.run_id

    # Kick workflow AFTER response is prepared (BackgroundTasks); do not await Gemini.
    background_tasks.add_task(kick_amendment_received, container, run.run_id)

    return CreateRunResponse(
        run_id=run.run_id,
        status=WorkflowStatus.CREATED,
        study_id=study,
        from_version=from_ver,
        to_version=to_ver,
        old_sha256=old_sha,
        new_sha256=new_sha,
        old_pages=old_pages,
        new_pages=new_pages,
        event_published=event is not None,
    )


@router.get("/api/runs", response_model=list[RunListItem])
def list_runs(request: Request) -> list[RunListItem]:
    container = _container(request)
    items: list[RunListItem] = []
    for run in container.state.list_runs():
        items.append(
            RunListItem(
                run_id=run.run_id,
                study_id=run.study_id,
                status=run.status,
                from_version=run.from_version,
                to_version=run.to_version,
                created_at=run.created_at,
                current_stage=run.checkpoint or run.status.value,
            )
        )
    return items


@router.get("/api/runs/{run_id}", response_model=RunStatusResponse)
def get_run(run_id: str, request: Request) -> RunStatusResponse:
    container = _container(request)
    try:
        return build_run_status(container.service, container.settings, run_id)
    except KeyError as exc:
        raise ApiError(
            error_code=ApiErrorCode.NOT_FOUND,
            message="Run not found.",
            status_code=404,
            details={"run_id": run_id},
        ) from exc


@router.get("/api/runs/{run_id}/changes")
def get_changes(run_id: str, request: Request) -> list[dict[str, Any]]:
    container = _container(request)
    if container.state.get_run(run_id) is None:
        raise ApiError(error_code=ApiErrorCode.NOT_FOUND, message="Run not found.", status_code=404)
    return [c.model_dump(mode="json") for c in container.state.list_changes(run_id)]


@router.get("/api/runs/{run_id}/impact", response_model=ImpactGraphResponse)
def get_impact(run_id: str, request: Request) -> ImpactGraphResponse:
    container = _container(request)
    if container.state.get_run(run_id) is None:
        raise ApiError(error_code=ApiErrorCode.NOT_FOUND, message="Run not found.", status_code=404)
    meta = container.state.get_session_metadata(run_id)
    graph = (meta.extra or {}).get("impact_graph") if meta else None
    if graph:
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])
        return ImpactGraphResponse(
            nodes=nodes,
            edges=edges,
            node_count=len(nodes),
            edge_count=len(edges),
        )
    # Rebuild if not cached
    from protocol215.application.impact import build_layered_impact_graph

    changes = container.state.list_changes(run_id)
    sites = container.state.list_sites(run_id)
    participants = container.state.list_participants(run_id)
    findings = container.state.list_findings(run_id)
    built = build_layered_impact_graph(
        changes=changes, sites=sites, participants=participants, findings=findings
    )
    return ImpactGraphResponse(
        nodes=[n.model_dump(mode="json") for n in built.nodes],
        edges=[e.model_dump(mode="json") for e in built.edges],
        node_count=len(built.nodes),
        edge_count=len(built.edges),
    )


@router.get("/api/runs/{run_id}/findings")
def get_findings(run_id: str, request: Request) -> list[dict[str, Any]]:
    container = _container(request)
    if container.state.get_run(run_id) is None:
        raise ApiError(error_code=ApiErrorCode.NOT_FOUND, message="Run not found.", status_code=404)
    return [f.model_dump(mode="json") for f in container.state.list_findings(run_id)]


@router.get("/api/runs/{run_id}/actions")
def get_actions(run_id: str, request: Request) -> list[dict[str, Any]]:
    container = _container(request)
    if container.state.get_run(run_id) is None:
        raise ApiError(error_code=ApiErrorCode.NOT_FOUND, message="Run not found.", status_code=404)
    return [a.model_dump(mode="json") for a in container.state.list_actions(run_id)]


@router.get("/api/runs/{run_id}/approvals")
def get_approvals(run_id: str, request: Request) -> list[dict[str, Any]]:
    container = _container(request)
    if container.state.get_run(run_id) is None:
        raise ApiError(error_code=ApiErrorCode.NOT_FOUND, message="Run not found.", status_code=404)
    return [a.model_dump(mode="json") for a in container.state.list_approval_requests(run_id)]


@router.post(
    "/api/runs/{run_id}/approvals/{approval_id}",
    response_model=ApprovalDecisionResponse,
    status_code=202,
)
async def submit_approval(
    run_id: str,
    approval_id: str,
    body: ApprovalDecisionRequest,
    request: Request,
    background_tasks: BackgroundTasks,
) -> ApprovalDecisionResponse:
    container = _container(request)
    run = container.state.get_run(run_id)
    if run is None:
        raise ApiError(error_code=ApiErrorCode.NOT_FOUND, message="Run not found.", status_code=404)
    apr = container.state.get_approval_request(approval_id)
    if apr is None or apr.run_id != run_id:
        raise ApiError(
            error_code=ApiErrorCode.NOT_FOUND,
            message="Approval request not found.",
            status_code=404,
        )
    if body.decision not in {ApprovalStatus.APPROVED, ApprovalStatus.REJECTED}:
        raise ApiError(
            error_code=ApiErrorCode.INVALID_INPUT,
            message="decision must be APPROVED or REJECTED.",
            status_code=400,
        )

    try:
        validate_approval_not_stale(
            request=apr,
            run=run,
            submitted_state_version=body.expected_state_version,
        )
    except Exception as exc:  # noqa: BLE001 — map to API error
        from protocol215.workflow.errors import WorkflowFailure

        if isinstance(exc, WorkflowFailure):
            raise ApiError(
                error_code=ApiErrorCode.STALE_APPROVAL,
                message=str(exc),
                status_code=409,
                retryable=False,
            ) from exc
        raise

    # Store decision only — do NOT execute sensitive tools in the request handler.
    container.service.record_approval(
        approval_id=approval_id,
        decision=body.decision,
        actor=body.actor,
    )
    event = container.service.publish_run_event(
        run_id=run_id,
        event_type="amendment.resume",
        payload={
            "approval_id": approval_id,
            "decision": body.decision.value,
            "comment": body.comment,
        },
        idempotency_key=f"{run_id}:amendment.resume:{approval_id}:{body.decision.value}",
    )
    background_tasks.add_task(
        kick_amendment_resume,
        container,
        run_id,
        approval_id,
        body.decision == ApprovalStatus.APPROVED,
    )
    return ApprovalDecisionResponse(
        approval_id=approval_id,
        run_id=run_id,
        decision=body.decision,
        event_published=event is not None,
    )


@router.get("/api/runs/{run_id}/audit")
def get_audit(run_id: str, request: Request) -> list[dict[str, Any]]:
    container = _container(request)
    if container.state.get_run(run_id) is None:
        raise ApiError(error_code=ApiErrorCode.NOT_FOUND, message="Run not found.", status_code=404)
    return [e.model_dump(mode="json") for e in container.state.list_audit_events(run_id)]


@router.get("/api/runs/{run_id}/audit/verify")
def verify_audit(run_id: str, request: Request) -> dict[str, Any]:
    container = _container(request)
    if container.state.get_run(run_id) is None:
        raise ApiError(error_code=ApiErrorCode.NOT_FOUND, message="Run not found.", status_code=404)
    from protocol215.adapters.audit_log import verify_audit_chain

    events = container.state.list_audit_events(run_id)
    ok, errors = verify_audit_chain(events)
    return {
        "ok": ok,
        "events_checked": len(events),
        "errors": errors,
        "message": "Audit chain intact." if ok else "Audit chain verification failed.",
    }


@router.get("/api/runs/{run_id}/manifest")
def get_manifest(run_id: str, request: Request) -> dict[str, Any]:
    container = _container(request)
    if container.state.get_run(run_id) is None:
        raise ApiError(error_code=ApiErrorCode.NOT_FOUND, message="Run not found.", status_code=404)
    manifest = container.state.get_manifest(run_id)
    if manifest is None:
        raise ApiError(
            error_code=ApiErrorCode.NOT_FOUND,
            message="Manifest not ready.",
            status_code=404,
            details={"run_id": run_id},
        )
    return manifest.model_dump(mode="json")


@router.post("/api/demo/reset", response_model=DemoResetResponse)
def demo_reset(
    request: Request,
    confirm: bool = False,
) -> DemoResetResponse:
    """
    Clear synthetic demo runs/actions/approvals/manifests.

    Cloud mode requires confirm=true (or CONFIRM_DEMO_RESET=yes via script).
    Does not delete fixtures/ source PDFs or GCP infrastructure.
    """
    import os

    container = _container(request)
    confirmed = confirm or os.environ.get("CONFIRM_DEMO_RESET", "").lower() in {
        "1",
        "true",
        "yes",
    }
    try:
        result = container.reset(confirmed=confirmed)
    except PermissionError as exc:
        raise ApiError(
            error_code=ApiErrorCode.INVALID_INPUT,
            message=str(exc),
            status_code=403,
            retryable=False,
        ) from exc
    return DemoResetResponse(
        ok=result.ok,
        message=result.message,
        sites_restored=result.sites_restored,
        participants_restored=result.participants_restored,
        runs_cleared=result.runs_cleared,
        objects_cleared=result.objects_cleared,
        fixtures_preserved=result.fixtures_preserved,
        twin_snapshot=result.twin_snapshot,
    )
