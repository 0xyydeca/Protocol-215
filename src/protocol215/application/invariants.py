"""Deterministic invariant checks (no cloud)."""

from __future__ import annotations

from protocol215.domain.enums import ActionStatus, RiskTier
from protocol215.domain.models import (
    ActionExecution,
    InvariantResult,
    ParticipantState,
    SiteState,
)


def check_no_site_activates_before_approval(sites: list[SiteState]) -> InvariantResult:
    violations = [s.site_id for s in sites if s.v2_activated and not s.local_approval_complete]
    return InvariantResult(
        invariant_id="INV-SITE-APPROVAL",
        name="no_site_activates_before_local_approval",
        passed=not violations,
        message="ok" if not violations else f"activated without approval: {violations}",
        details={"violations": violations},
    )


def check_no_site_activates_before_training(sites: list[SiteState]) -> InvariantResult:
    violations = [s.site_id for s in sites if s.v2_activated and not s.amendment_training_complete]
    return InvariantResult(
        invariant_id="INV-SITE-TRAINING",
        name="no_site_activates_before_required_training",
        passed=not violations,
        message="ok" if not violations else f"activated without training: {violations}",
        details={"violations": violations},
    )


def check_no_completed_visit_changed(
    participants: list[ParticipantState],
    *,
    attempted_modifications: list[tuple[str, str]] | None = None,
) -> InvariantResult:
    """Fail if any attempted modification targets an immutable completed visit."""
    attempted = attempted_modifications or []
    immutable = {
        (p.participant_id, v.visit_code)
        for p in participants
        for v in p.visits
        if v.completed and v.immutable
    }
    violations = [f"{pid}:{visit}" for pid, visit in attempted if (pid, visit) in immutable]
    return InvariantResult(
        invariant_id="INV-VISIT-IMMUTABLE",
        name="no_completed_visit_is_changed",
        passed=not violations,
        message="ok" if not violations else f"attempted immutable edits: {violations}",
        details={"violations": violations},
    )


def check_no_sensitive_without_approval(actions: list[ActionExecution]) -> InvariantResult:
    violations = [
        a.execution_id
        for a in actions
        if a.authorized_tier == RiskTier.AMBER and a.executed and not a.approved
    ]
    return InvariantResult(
        invariant_id="INV-AMBER-APPROVAL",
        name="no_sensitive_action_executes_without_approval",
        passed=not violations,
        message="ok" if not violations else f"amber without approval: {violations}",
        details={"violations": violations},
    )


def check_every_action_has_evidence(actions: list[ActionExecution]) -> InvariantResult:
    violations = [a.execution_id for a in actions if a.executed and not a.evidence]
    return InvariantResult(
        invariant_id="INV-EVIDENCE",
        name="every_action_has_evidence",
        passed=not violations,
        message="ok" if not violations else f"missing evidence: {violations}",
        details={"violations": violations},
    )


def check_every_action_has_idempotency_key(actions: list[ActionExecution]) -> InvariantResult:
    violations = [a.execution_id for a in actions if not a.idempotency_key]
    return InvariantResult(
        invariant_id="INV-IDEMPOTENCY",
        name="every_action_has_idempotency_key",
        passed=not violations,
        message="ok" if not violations else f"missing idempotency key: {violations}",
        details={"violations": violations},
    )


def check_no_red_action_executes(actions: list[ActionExecution]) -> InvariantResult:
    violations = [
        a.execution_id
        for a in actions
        if a.authorized_tier == RiskTier.RED and (a.executed or a.status == ActionStatus.EXECUTED)
    ]
    return InvariantResult(
        invariant_id="INV-NO-RED",
        name="no_red_action_executes",
        passed=not violations,
        message="ok" if not violations else f"red executed: {violations}",
        details={"violations": violations},
    )


def check_pk_feasibility(
    *,
    sample_local_time: str,
    courier_departure_local_time: str,
    overnight_storage_available: bool,
    processing_window_ok: bool = True,
) -> InvariantResult:
    sample_hm = _to_minutes(sample_local_time)
    courier_hm = _to_minutes(courier_departure_local_time)
    shipment_ok = sample_hm <= courier_hm or overnight_storage_available
    passed = processing_window_ok and shipment_ok
    return InvariantResult(
        invariant_id="INV-PK-FEASIBILITY",
        name="pk_sample_collection_processing_storage_shipment_feasible",
        passed=passed,
        message="ok" if passed else "PK sample not feasible under courier/storage constraints",
        details={
            "sample_local_time": sample_local_time,
            "courier_departure_local_time": courier_departure_local_time,
            "overnight_storage_available": overnight_storage_available,
            "processing_window_ok": processing_window_ok,
        },
    )


def check_protocol_history_immutable(
    *,
    historical_versions: list[str],
    attempted_rewrite: str | None = None,
) -> InvariantResult:
    passed = attempted_rewrite is None or attempted_rewrite not in historical_versions
    return InvariantResult(
        invariant_id="INV-HISTORY-IMMUTABLE",
        name="protocol_history_is_immutable",
        passed=passed,
        message="ok" if passed else f"attempted rewrite of {attempted_rewrite}",
        details={
            "historical_versions": historical_versions,
            "attempted_rewrite": attempted_rewrite,
        },
    )


def evaluate_all(
    *,
    sites: list[SiteState],
    participants: list[ParticipantState],
    actions: list[ActionExecution],
    attempted_visit_mods: list[tuple[str, str]] | None = None,
    pk_checks: list[dict[str, object]] | None = None,
    historical_versions: list[str] | None = None,
    attempted_history_rewrite: str | None = None,
) -> list[InvariantResult]:
    results = [
        check_no_site_activates_before_approval(sites),
        check_no_site_activates_before_training(sites),
        check_no_completed_visit_changed(
            participants, attempted_modifications=attempted_visit_mods
        ),
        check_no_sensitive_without_approval(actions),
        check_every_action_has_evidence(actions),
        check_every_action_has_idempotency_key(actions),
        check_no_red_action_executes(actions),
        check_protocol_history_immutable(
            historical_versions=historical_versions or ["1.0"],
            attempted_rewrite=attempted_history_rewrite,
        ),
    ]
    for pk in pk_checks or []:
        results.append(
            check_pk_feasibility(
                sample_local_time=str(pk["sample_local_time"]),
                courier_departure_local_time=str(pk["courier_departure_local_time"]),
                overnight_storage_available=bool(pk["overnight_storage_available"]),
                processing_window_ok=bool(pk.get("processing_window_ok", True)),
            )
        )
    return results


def _to_minutes(hhmm: str) -> int:
    hours, minutes = hhmm.split(":")
    return int(hours) * 60 + int(minutes)
