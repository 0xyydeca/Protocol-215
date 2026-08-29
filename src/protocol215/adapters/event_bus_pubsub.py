"""Pub/Sub publisher and authenticated push-envelope parser."""

from __future__ import annotations

import base64
import json
from typing import Any

from protocol215.cloud.errors import TerminalWorkerError
from protocol215.cloud.events import EventEnvelope, envelope_from_domain
from protocol215.domain.models import DomainEvent


class PubSubEventBus:
    """
    Publishes EventEnvelope JSON to topic paths.

    Topic map keys: amendment.received / amendment.resume → full topic paths or short names.
    Credentials via ADC / runtime SA only.
    """

    def __init__(
        self,
        *,
        project: str,
        topic_received: str,
        topic_resume: str,
        publisher: Any | None = None,
    ) -> None:
        self.project = project
        self.topic_received = topic_received
        self.topic_resume = topic_resume
        if publisher is not None:
            self._publisher = publisher
        else:
            from google.cloud import pubsub_v1  # type: ignore[attr-defined]

            self._publisher = pubsub_v1.PublisherClient()
        self._handlers: dict[str, list[Any]] = {}

    def _topic_path(self, event_type: str) -> str:
        name = self.topic_received if event_type == "amendment.received" else self.topic_resume
        if name.startswith("projects/"):
            return name
        return f"projects/{self.project}/topics/{name}"

    def publish(self, event: DomainEvent) -> None:
        envelope = envelope_from_domain(event)
        data = envelope.model_dump_json().encode("utf-8")
        attrs = {
            "event_type": envelope.event_type.value,
            "run_id": envelope.run_id,
            "event_id": envelope.event_id,
            "correlation_id": envelope.correlation_id,
            "schema_version": envelope.schema_version,
        }
        if envelope.approval_id:
            attrs["approval_id"] = envelope.approval_id
        if envelope.invocation_id:
            attrs["invocation_id"] = envelope.invocation_id
        future = self._publisher.publish(
            self._topic_path(envelope.event_type.value),
            data,
            **attrs,
        )
        # Wait for publish ack in sync path (Cloud Run web request should keep this short)
        future.result(timeout=30)

    def subscribe(self, event_type: str, handler: Any) -> None:
        self._handlers.setdefault(event_type, []).append(handler)


def parse_pubsub_push_envelope(
    body: dict[str, Any] | None,
    *,
    delivery_attempt: int | None = None,
) -> EventEnvelope:
    """
    Parse the standard Pub/Sub push JSON body:

      { "message": { "data": "<base64>", "messageId": "...", "attributes": {...} },
        "subscription": "..." }
    """
    if not body or "message" not in body:
        raise TerminalWorkerError(
            "malformed Pub/Sub envelope: missing message",
            dead_letter_reason="malformed_envelope",
        )
    message = body["message"]
    if not isinstance(message, dict):
        raise TerminalWorkerError(
            "malformed Pub/Sub envelope: message not an object",
            dead_letter_reason="malformed_envelope",
        )
    raw_b64 = message.get("data")
    if not raw_b64:
        raise TerminalWorkerError(
            "malformed Pub/Sub envelope: empty data",
            dead_letter_reason="malformed_envelope",
        )
    try:
        decoded = base64.b64decode(raw_b64)
        payload = json.loads(decoded.decode("utf-8"))
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise TerminalWorkerError(
            "malformed Pub/Sub envelope: invalid base64/json",
            dead_letter_reason="malformed_envelope",
        ) from exc

    try:
        envelope = EventEnvelope.model_validate(payload)
    except Exception as exc:  # noqa: BLE001 — pydantic ValidationError
        raise TerminalWorkerError(
            f"malformed event payload: {exc}",
            dead_letter_reason="malformed_envelope",
        ) from exc

    attrs = message.get("attributes") or {}
    if delivery_attempt is None and "deliveryAttempt" in (body or {}):
        try:
            delivery_attempt = int(body["deliveryAttempt"])
        except (TypeError, ValueError):
            delivery_attempt = None
    updates: dict[str, Any] = {}
    if delivery_attempt is not None:
        updates["delivery_attempt"] = delivery_attempt
    if attrs.get("correlation_id") and not envelope.correlation_id:
        updates["correlation_id"] = attrs["correlation_id"]
    if updates:
        envelope = envelope.model_copy(update=updates)
    return envelope


def encode_push_body(envelope: EventEnvelope) -> dict[str, Any]:
    """Test helper: build a Pub/Sub push body from an envelope."""
    data = base64.b64encode(envelope.model_dump_json().encode("utf-8")).decode("ascii")
    return {
        "message": {
            "data": data,
            "messageId": envelope.event_id,
            "attributes": {
                "event_type": envelope.event_type.value,
                "run_id": envelope.run_id,
                "correlation_id": envelope.correlation_id,
            },
        },
        "subscription": "projects/test/subscriptions/test",
    }
