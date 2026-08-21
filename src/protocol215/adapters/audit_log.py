"""Append-only hash-chained audit log."""

from __future__ import annotations

from typing import Any

from protocol215.application.hashing import GENESIS_HASH, hash_payload, sha256_hex
from protocol215.domain.models import AuditEvent, EvidenceReference
from protocol215.ports import Clock, IdentifierGenerator, StateStore


class HashChainedAuditLog:
    def __init__(
        self,
        state: StateStore,
        clock: Clock,
        ids: IdentifierGenerator,
    ) -> None:
        self._state = state
        self._clock = clock
        self._ids = ids

    def append(
        self,
        *,
        run_id: str,
        event_type: str,
        actor: str,
        decision_summary: str,
        evidence: list[Any] | None = None,
        input_payload: dict[str, Any] | None = None,
        output_payload: dict[str, Any] | None = None,
        action_id: str | None = None,
        tool_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> AuditEvent:
        existing = self._state.list_audit_events(run_id)
        sequence = len(existing) + 1
        previous = existing[-1].current_event_hash if existing else GENESIS_HASH
        evidence_refs = [
            e if isinstance(e, EvidenceReference) else EvidenceReference.model_validate(e)
            for e in (evidence or [])
        ]
        input_hash = hash_payload(input_payload or {})
        output_hash = hash_payload(output_payload or {})
        timestamp = self._clock.now()
        event_id = self._ids.new_id("audit-")
        material = {
            "event_id": event_id,
            "run_id": run_id,
            "sequence_number": sequence,
            "event_type": event_type,
            "actor": actor,
            "timestamp": timestamp.isoformat(),
            "evidence": [e.model_dump() for e in evidence_refs],
            "input_hash": input_hash,
            "output_hash": output_hash,
            "previous_event_hash": previous,
            "decision_summary": decision_summary,
            "action_id": action_id,
            "tool_id": tool_id,
            "idempotency_key": idempotency_key,
        }
        current = sha256_hex(
            "|".join(
                [
                    previous,
                    str(sequence),
                    event_type,
                    actor,
                    timestamp.isoformat(),
                    input_hash,
                    output_hash,
                    decision_summary,
                    hash_payload(material),
                ]
            )
        )
        event = AuditEvent(
            event_id=event_id,
            run_id=run_id,
            sequence_number=sequence,
            event_type=event_type,
            actor=actor,
            timestamp=timestamp,
            evidence=evidence_refs,
            input_hash=input_hash,
            output_hash=output_hash,
            previous_event_hash=previous,
            current_event_hash=current,
            decision_summary=decision_summary,
            action_id=action_id,
            tool_id=tool_id,
            idempotency_key=idempotency_key,
        )
        self._state.append_audit_event(event)
        return event

    def list_events(self, run_id: str) -> list[AuditEvent]:
        return self._state.list_audit_events(run_id)

    def verify(self, run_id: str) -> tuple[bool, list[str]]:
        return verify_audit_chain(self._state.list_audit_events(run_id))


def verify_audit_chain(events: list[AuditEvent]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not events:
        return True, errors

    ordered = sorted(events, key=lambda e: e.sequence_number)
    expected_prev = GENESIS_HASH
    expected_seq = 1
    for event in ordered:
        if event.sequence_number != expected_seq:
            errors.append(
                f"missing or out-of-order sequence: expected {expected_seq}, "
                f"got {event.sequence_number}"
            )
        if event.previous_event_hash != expected_prev:
            errors.append(
                f"broken previous hash at seq {event.sequence_number}: "
                f"expected {expected_prev}, got {event.previous_event_hash}"
            )
        recomputed = _recompute_hash(event)
        if recomputed != event.current_event_hash:
            errors.append(f"invalid current hash at seq {event.sequence_number}")
        expected_prev = event.current_event_hash
        expected_seq += 1
    return (len(errors) == 0), errors


def _recompute_hash(event: AuditEvent) -> str:
    material = {
        "event_id": event.event_id,
        "run_id": event.run_id,
        "sequence_number": event.sequence_number,
        "event_type": event.event_type,
        "actor": event.actor,
        "timestamp": event.timestamp.isoformat(),
        "evidence": [e.model_dump() for e in event.evidence],
        "input_hash": event.input_hash,
        "output_hash": event.output_hash,
        "previous_event_hash": event.previous_event_hash,
        "decision_summary": event.decision_summary,
        "action_id": event.action_id,
        "tool_id": event.tool_id,
        "idempotency_key": event.idempotency_key,
    }
    return sha256_hex(
        "|".join(
            [
                event.previous_event_hash,
                str(event.sequence_number),
                event.event_type,
                event.actor,
                event.timestamp.isoformat(),
                event.input_hash,
                event.output_hash,
                event.decision_summary,
                hash_payload(material),
            ]
        )
    )


def detect_content_tamper(original: AuditEvent, tampered: AuditEvent) -> bool:
    """True when content changed but hash left intact (or hash no longer matches)."""
    if original.event_id != tampered.event_id:
        return True
    if original.decision_summary != tampered.decision_summary:
        return True
    return _recompute_hash(tampered) != tampered.current_event_hash
