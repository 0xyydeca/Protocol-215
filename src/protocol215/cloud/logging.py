"""Structured cloud-oriented logging — never log PDFs, credentials, or CoT."""

from __future__ import annotations

import time
from collections.abc import Mapping
from contextlib import contextmanager
from typing import Any, Iterator

from protocol215.observability import get_logger

_REDACT_KEYS = {
    "pdf",
    "pdf_bytes",
    "credentials",
    "credential",
    "password",
    "token",
    "authorization",
    "api_key",
    "private_key",
    "prompt",
    "full_prompt",
    "chain_of_thought",
    "reasoning",
    "hidden_reasoning",
}


def _sanitize(value: Any) -> Any:
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for k, v in value.items():
            key = str(k).lower()
            if key in _REDACT_KEYS or any(r in key for r in ("pdf", "secret", "credential", "password")):
                out[str(k)] = "[REDACTED]"
            else:
                out[str(k)] = _sanitize(v)
        return out
    if isinstance(value, (list, tuple)):
        return [_sanitize(v) for v in value]
    if isinstance(value, (bytes, bytearray)):
        return f"[bytes:{len(value)}]"
    return value


def emit_cloud_log(
    *,
    severity: str,
    message: str,
    run_id: str | None = None,
    event_id: str | None = None,
    invocation_id: str | None = None,
    workflow_node: str | None = None,
    action_id: str | None = None,
    correlation_id: str | None = None,
    latency_ms: float | None = None,
    outcome: str | None = None,
    **extra: Any,
) -> None:
    """Emit a structured log line safe for Cloud Logging JSON ingestion."""
    log = get_logger("protocol215.cloud")
    payload = _sanitize(
        {
            "severity": severity.upper(),
            "message": message,
            "run_id": run_id,
            "event_id": event_id,
            "invocation_id": invocation_id,
            "workflow_node": workflow_node,
            "action_id": action_id,
            "correlation_id": correlation_id,
            "latency_ms": latency_ms,
            "outcome": outcome,
            **extra,
        }
    )
    level = severity.lower()
    if level in {"error", "critical", "alert", "emergency"}:
        log.error(message, **payload)
    elif level in {"warning", "warn"}:
        log.warning(message, **payload)
    else:
        log.info(message, **payload)


@contextmanager
def timed_operation(
    *,
    message: str,
    run_id: str | None = None,
    event_id: str | None = None,
    correlation_id: str | None = None,
    workflow_node: str | None = None,
) -> Iterator[dict[str, Any]]:
    """Context manager that logs latency + outcome."""
    ctx: dict[str, Any] = {"outcome": "ok"}
    start = time.perf_counter()
    try:
        yield ctx
    except Exception as exc:
        ctx["outcome"] = "error"
        ctx["error_type"] = type(exc).__name__
        emit_cloud_log(
            severity="ERROR",
            message=message,
            run_id=run_id,
            event_id=event_id,
            correlation_id=correlation_id,
            workflow_node=workflow_node,
            latency_ms=(time.perf_counter() - start) * 1000,
            outcome="error",
            error_type=type(exc).__name__,
        )
        raise
    else:
        emit_cloud_log(
            severity="INFO",
            message=message,
            run_id=run_id,
            event_id=event_id,
            correlation_id=correlation_id,
            workflow_node=workflow_node,
            latency_ms=(time.perf_counter() - start) * 1000,
            outcome=str(ctx.get("outcome", "ok")),
        )
