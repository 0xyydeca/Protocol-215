"""Typed API errors — no stack traces to clients."""

from __future__ import annotations

from enum import StrEnum
from typing import Any
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


class ApiErrorCode(StrEnum):
    INVALID_INPUT = "invalid_input"
    INVALID_PDF = "invalid_pdf"
    FILE_TOO_LARGE = "file_too_large"
    TOO_MANY_PAGES = "too_many_pages"
    ENCRYPTED_PDF = "encrypted_pdf"
    MALFORMED_PDF = "malformed_pdf"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    DUPLICATE = "duplicate"
    STALE_APPROVAL = "stale_approval"
    POLICY_VIOLATION = "policy_violation"
    INTERNAL = "internal"


class ApiErrorBody(BaseModel):
    error_code: ApiErrorCode
    message: str
    correlation_id: str = Field(default_factory=lambda: str(uuid4()))
    retryable: bool = False
    details: dict[str, Any] = Field(default_factory=dict)


class ApiError(Exception):
    def __init__(
        self,
        *,
        error_code: ApiErrorCode,
        message: str,
        status_code: int = 400,
        retryable: bool = False,
        details: dict[str, Any] | None = None,
        correlation_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.retryable = retryable
        self.details = details or {}
        self.correlation_id = correlation_id or str(uuid4())

    def to_body(self) -> ApiErrorBody:
        return ApiErrorBody(
            error_code=self.error_code,
            message=self.message,
            correlation_id=self.correlation_id,
            retryable=self.retryable,
            details=self.details,
        )


async def api_error_handler(_request: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_body().model_dump(),
    )


async def unhandled_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    _ = exc  # logged by middleware / observability; never leak stack to client
    body = ApiErrorBody(
        error_code=ApiErrorCode.INTERNAL,
        message="An unexpected error occurred.",
        retryable=True,
    )
    return JSONResponse(status_code=500, content=body.model_dump())
