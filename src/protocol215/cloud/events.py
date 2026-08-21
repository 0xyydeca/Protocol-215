"""Pub/Sub event envelope schema (schema_version=1)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from protocol215.domain.models import DomainEvent, utc_now


class AmendmentEventType(StrEnum):
    RECEIVED = "amendment.received"
    RESUME = "amendment.resume"


class EventEnvelope(BaseModel):
    """Canonical worker event envelope published on Pub/Sub."""

    event_id: str
    event_type: AmendmentEventType
    schema_version: str = "1"
    run_id: str
    occurred_at: datetime = Field(default_factory=utc_now)
    invocation_id: str | None = None
    approval_id: str | None = None
    correlation_id: str = Field(default_factory=lambda: str(uuid4()))
    payload: dict[str, Any] = Field(default_factory=dict)
    # Dead-letter / retry metadata (set by worker, optional on publish)
    delivery_attempt: int | None = None
    dead_letter_reason: str | None = None

    def to_domain_event(self) -> DomainEvent:
        return DomainEvent(
            event_id=self.event_id,
            event_type=self.event_type.value,
            run_id=self.run_id,
            payload={
                **self.payload,
                "schema_version": self.schema_version,
                "correlation_id": self.correlation_id,
                "invocation_id": self.invocation_id,
                "approval_id": self.approval_id,
            },
            created_at=self.occurred_at,
            idempotency_key=f"{self.run_id}:{self.event_type.value}:{self.event_id}",
        )


def envelope_from_domain(event: DomainEvent) -> EventEnvelope:
    payload = dict(event.payload or {})
    event_type = AmendmentEventType(event.event_type)
    return EventEnvelope(
        event_id=event.event_id,
        event_type=event_type,
        schema_version=str(payload.pop("schema_version", "1")),
        run_id=event.run_id,
        occurred_at=event.created_at,
        invocation_id=payload.pop("invocation_id", None),
        approval_id=payload.pop("approval_id", None),
        correlation_id=str(payload.pop("correlation_id", uuid4())),
        payload=payload,
    )
