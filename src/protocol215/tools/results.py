"""Typed tool execution results."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from protocol215.domain.enums import ActionStatus, RiskTier


class ToolResult(BaseModel):
    tool_name: str
    status: ActionStatus
    authorized_tier: RiskTier
    executed: bool
    replayed: bool = False
    idempotency_key: str
    execution_id: str
    before: dict[str, Any] = Field(default_factory=dict)
    after: dict[str, Any] = Field(default_factory=dict)
    before_hash: str
    after_hash: str
    audit_event_id: str | None = None
    message: str = ""
    blocked_reason: str | None = None
