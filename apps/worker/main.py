"""FastAPI Cloud Run worker — private Pub/Sub push endpoint."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Header, Request, Response, status

from protocol215.adapters.event_bus_pubsub import parse_pubsub_push_envelope
from protocol215.cloud.errors import RetryableWorkerError, TerminalWorkerError
from protocol215.cloud.logging import emit_cloud_log
from protocol215.cloud.worker import AmendmentWorkerHandler, WorkerResult
from protocol215.config import get_settings
from protocol215.observability import configure_logging


def create_worker_app(
    *,
    handler: AmendmentWorkerHandler | None = None,
    require_oidc: bool = False,
) -> FastAPI:
    """
    Create the worker FastAPI app.

    In production, Cloud Run ingress should be internal + Pub/Sub OIDC.
    OIDC verification is optional here so unit tests can inject a handler.
    """
    configure_logging()
    app = FastAPI(title="Protocol 215 Worker", version="0.1.0")
    app.state.handler = handler
    app.state.require_oidc = require_oidc

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok", "service": "protocol-215-worker"}

    @app.post("/pubsub/push")
    async def pubsub_push(
        request: Request,
        response: Response,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        settings = get_settings()
        if request.app.state.require_oidc:
            if not authorization or not authorization.startswith("Bearer "):
                response.status_code = status.HTTP_401_UNAUTHORIZED
                return {"error": "missing_oidc_token"}

        active: AmendmentWorkerHandler | None = request.app.state.handler
        if active is None:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return {"error": "handler_not_configured", "app_env": settings.app_env.value}

        body = await request.json()
        try:
            envelope = parse_pubsub_push_envelope(body)
            result: WorkerResult = active.handle(envelope)
        except TerminalWorkerError as exc:
            emit_cloud_log(
                severity="ERROR",
                message="worker.terminal_error",
                correlation_id=exc.correlation_id,
                outcome="terminal",
                dead_letter_reason=exc.dead_letter_reason,
                error=str(exc),
            )
            # ACK malformed / permanent failures so they can land in DLQ via subscription policy.
            response.status_code = status.HTTP_200_OK
            return {
                "status": "terminal_error",
                "retryable": False,
                "dead_letter_reason": exc.dead_letter_reason,
                "message": str(exc),
            }
        except RetryableWorkerError as exc:
            emit_cloud_log(
                severity="WARNING",
                message="worker.retryable_error",
                correlation_id=exc.correlation_id,
                outcome="retryable",
                error=str(exc),
            )
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return {"status": "retryable_error", "retryable": True, "message": str(exc)}

        response.status_code = status.HTTP_200_OK
        return {
            "status": "ok",
            "outcome": result.outcome,
            "workflow_status": result.status.value,
            "duplicate": result.duplicate,
        }

    return app


# Default ASGI app for `uvicorn apps.worker.main:app` once handler is wired in cloud deploy.
app = create_worker_app()
