"""Workflow failure classification — exceptions are not swallowed."""

from __future__ import annotations

from typing import Any

from protocol215.domain.enums import FailureClass


class WorkflowFailure(Exception):
    """Typed workflow failure with explicit classification."""

    def __init__(
        self,
        message: str,
        *,
        failure_class: FailureClass,
        retryable: bool = False,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.failure_class = failure_class
        self.retryable = retryable
        self.details = details or {}


def classify_exception(exc: BaseException) -> FailureClass:
    if isinstance(exc, WorkflowFailure):
        return exc.failure_class
    name = type(exc).__name__.lower()
    msg = str(exc).lower()
    if "stale" in msg:
        return FailureClass.STALE_APPROVAL
    if "duplicate" in msg:
        return FailureClass.DUPLICATE_EVENT
    if "schema" in msg or "validation" in name:
        return FailureClass.MODEL_SCHEMA_ERROR
    if "timeout" in msg or "unavailable" in msg or "transient" in msg:
        return FailureClass.TRANSIENT_MODEL_ERROR
    if "sqlite" in msg or "persist" in msg or "disk" in msg:
        return FailureClass.PERSISTENCE_ERROR
    if "policy" in msg:
        return FailureClass.POLICY_VIOLATION
    if "invariant" in msg:
        return FailureClass.INVARIANT_FAILURE
    if "unsupported" in msg:
        return FailureClass.TERMINAL_UNSUPPORTED_CHANGE
    if isinstance(exc, (ValueError, KeyError, TypeError)):
        return FailureClass.INVALID_INPUT
    return FailureClass.UNKNOWN
