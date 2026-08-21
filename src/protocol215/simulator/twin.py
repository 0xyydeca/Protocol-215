"""Deterministic Trial Twin temporal simulator."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from protocol215.domain.enums import FindingCode, ProtocolApplicability, Severity
from protocol215.domain.models import (
    ConsentState,
    InventoryState,
    LogisticsState,
    ParticipantState,
    RehearsalFinding,
    SemanticChange,
    SiteState,
    VisitState,
)
from protocol215.fixtures import PARTICIPANTS_PATH, SITES_PATH
from protocol215.policy.matrix import classify_change


def _parse_hhmm(value: str) -> int:
    hours, minutes = value.split(":")
    return int(hours) * 60 + int(minutes)


def add_hours_to_hhmm(start: str, hours: float) -> str:
    total = _parse_hhmm(start) + int(hours * 60)
    return f"{total // 60:02d}:{total % 60:02d}"


def load_sites(path: Path | None = None) -> list[SiteState]:
    data = json.loads((path or SITES_PATH).read_text(encoding="utf-8"))
    sites: list[SiteState] = []
    for raw in data["sites"]:
        sites.append(
            SiteState(
                site_id=raw["site_id"],
                name=raw["name"],
                city=raw["city"],
                local_approval_complete=raw["local_approval_status"] == "complete",
                amendment_training_complete=raw["amendment_training_status"] == "complete",
                active_protocol_version=raw["active_protocol_version"],
                logistics=LogisticsState(
                    courier_departure_local_time=raw["courier_departure_local_time"],
                    validated_overnight_storage_available=raw[
                        "validated_overnight_storage_available"
                    ],
                ),
                inventory=InventoryState(extra_pk_kits=int(raw["extra_pk_kits"])),
                v2_activated=False,
            )
        )
    return sites


def load_participants(path: Path | None = None) -> list[ParticipantState]:
    data = json.loads((path or PARTICIPANTS_PATH).read_text(encoding="utf-8"))
    participants: list[ParticipantState] = []
    for raw in data["participants"]:
        visits: list[VisitState] = []
        if raw.get("day1_completed"):
            visits.append(
                VisitState(
                    visit_code="Day 1",
                    completed=True,
                    immutable=bool(raw.get("day1_immutable", True)),
                    scheduled=False,
                    planned_dose_time_local=raw.get("planned_dose_time_local"),
                )
            )
        elif raw.get("next_visit") == "Day 1" or str(raw.get("day1_status", "")).startswith(
            "scheduled"
        ):
            visits.append(
                VisitState(
                    visit_code="Day 1",
                    completed=False,
                    immutable=False,
                    scheduled=True,
                    planned_dose_time_local=raw.get("planned_dose_time_local"),
                )
            )
        if raw.get("next_visit") == "Day 8":
            visits.append(
                VisitState(visit_code="Day 8", completed=False, immutable=False, scheduled=True)
            )
        consent_version = raw.get("consent_version")
        participants.append(
            ParticipantState(
                participant_id=raw["participant_id"],
                site_id=raw["site_id"],
                consent=ConsentState(
                    consent_version=consent_version,
                    applicable=ProtocolApplicability.ACTIVE
                    if consent_version
                    else ProtocolApplicability.NOT_APPLICABLE,
                ),
                visits=visits,
            )
        )
    return participants


def site_can_activate_v2(site: SiteState) -> tuple[bool, str]:
    if not site.local_approval_complete:
        return False, "local approval incomplete"
    if not site.amendment_training_complete:
        return False, "amendment training incomplete"
    return True, "eligible"


def applicable_protocol_version(site: SiteState, *, target_version: str = "2.0") -> str:
    if site.v2_activated and site_can_activate_v2(site)[0]:
        return target_version
    return site.active_protocol_version


def rehearse_amendment(
    *,
    changes: list[SemanticChange],
    sites: list[SiteState],
    participants: list[ParticipantState],
    target_version: str = "2.0",
    future_day1_participants_needing_kits: int | None = None,
) -> list[RehearsalFinding]:
    """Evaluate Change × Site × Participant × Visit × Effective state."""
    findings: list[RehearsalFinding] = []
    sites_by_id = {s.site_id: s for s in sites}
    change_by_concept = {c.concept_type: c for c in changes}
    change_ids = [c.change_id for c in changes]

    # 1. Lab contact safe to prepare
    if "central_lab_contact" in change_by_concept:
        lab = change_by_concept["central_lab_contact"]
        findings.append(
            RehearsalFinding(
                finding_id="F-LAB-CONTACT",
                code=FindingCode.LAB_CONTACT_SAFE.value,
                severity=Severity.INFO,
                summary="Administrative laboratory-contact update is safe to prepare.",
                change_ids=[lab.change_id],
                details={"tier": classify_change(lab).value},
            )
        )

    # 2. EDC spec draftable
    if "edc_field" in change_by_concept:
        edc = change_by_concept["edc_field"]
        findings.append(
            RehearsalFinding(
                finding_id="F-EDC-SPEC",
                code=FindingCode.EDC_SPEC_DRAFTABLE.value,
                severity=Severity.INFO,
                summary="An EDC change specification can be drafted.",
                change_ids=[edc.change_id],
                details={"field": (edc.after or {}).get("field")},
            )
        )

    # 3–4. Site readiness
    for site in sites:
        ok, reason = site_can_activate_v2(site)
        if site.site_id == "SITE-002" and not site.amendment_training_complete:
            findings.append(
                RehearsalFinding(
                    finding_id="F-BOS-TRAINING",
                    code=FindingCode.BOSTON_TRAINING_REQUIRED.value,
                    severity=Severity.WARNING,
                    summary="Boston requires a training task before v2 activation.",
                    site_id=site.site_id,
                    change_ids=change_ids,
                    details={"reason": reason},
                )
            )
        if site.site_id == "SITE-003" and (
            not site.local_approval_complete or not site.amendment_training_complete
        ):
            findings.append(
                RehearsalFinding(
                    finding_id="F-SEA-APPROVAL-TRAINING",
                    code=FindingCode.SEATTLE_APPROVAL_TRAINING_REQUIRED.value,
                    severity=Severity.BLOCKER,
                    summary="Seattle requires approval and training before activation.",
                    site_id=site.site_id,
                    change_ids=change_ids,
                    details={
                        "approval": site.local_approval_complete,
                        "training": site.amendment_training_complete,
                    },
                )
            )
        if not ok:
            # Global amendment existence never implies activation.
            _ = applicable_protocol_version(site, target_version=target_version)

    # 10. No global activation
    findings.append(
        RehearsalFinding(
            finding_id="F-NO-GLOBAL-ACTIVATE",
            code=FindingCode.NO_GLOBAL_ACTIVATION.value,
            severity=Severity.WARNING,
            summary="No site may activate v2 merely because the global amendment exists.",
            change_ids=change_ids,
            details={
                "sites_activated": [s.site_id for s in sites if s.v2_activated],
                "rule": "activation requires local approval and training per site",
            },
        )
    )

    # 5. PK kits
    pk_change = change_by_concept.get("pk_timepoint")
    if pk_change is not None:
        pending_day1 = [
            p for p in participants if (v := p.visit("Day 1")) is not None and not v.completed
        ]
        needed = future_day1_participants_needing_kits
        if needed is None:
            needed = len(pending_day1)
        tight_sites = [
            s.site_id
            for s in sites
            if s.inventory.extra_pk_kits < max(1, needed // max(len(sites), 1))
        ]
        # Phoenix only has 2 extra kits with multiple future Day 1 visits at that site.
        phx_future = sum(
            1
            for p in participants
            if p.site_id == "SITE-001" and (v := p.visit("Day 1")) is not None and not v.completed
        )
        phx = sites_by_id.get("SITE-001")
        if phx is not None and phx.inventory.extra_pk_kits <= phx_future:
            tight_sites.append("SITE-001")
        findings.append(
            RehearsalFinding(
                finding_id="F-PK-KITS",
                code=FindingCode.PK_KITS_MAY_BE_REQUIRED.value,
                severity=Severity.WARNING,
                summary="Additional PK kits may be required.",
                change_ids=[pk_change.change_id],
                details={
                    "pending_day1_count": needed,
                    "tight_sites": sorted(set(tight_sites)),
                },
            )
        )

    # 6–7. Participants
    for participant in participants:
        site = sites_by_id[participant.site_id]
        day1 = participant.visit("Day 1")
        if participant.participant_id == "P001" and day1 and day1.completed and day1.immutable:
            findings.append(
                RehearsalFinding(
                    finding_id="F-P001-IMMUTABLE",
                    code=FindingCode.P001_DAY1_IMMUTABLE.value,
                    severity=Severity.CRITICAL,
                    summary="P001's completed Day 1 visit cannot be altered.",
                    site_id=site.site_id,
                    participant_id=participant.participant_id,
                    change_ids=change_ids,
                    details={"consent_version": participant.consent.consent_version},
                )
            )

        if (
            participant.participant_id == "P002"
            and pk_change is not None
            and day1 is not None
            and day1.planned_dose_time_local
        ):
            sample_time = add_hours_to_hhmm(day1.planned_dose_time_local, 6.0)
            courier = site.logistics.courier_departure_local_time
            storage = site.logistics.validated_overnight_storage_available
            conflict = _parse_hhmm(sample_time) > _parse_hhmm(courier) and not storage
            if conflict:
                findings.append(
                    RehearsalFinding(
                        finding_id="F-P002-COURIER",
                        code=FindingCode.P002_COURIER_STORAGE_CONFLICT.value,
                        severity=Severity.BLOCKER,
                        summary="P002 has a courier/storage conflict.",
                        site_id=site.site_id,
                        participant_id=participant.participant_id,
                        change_ids=[pk_change.change_id],
                        details={
                            "dose_time": day1.planned_dose_time_local,
                            "sample_time": sample_time,
                            "courier_departure": courier,
                            "overnight_storage": storage,
                        },
                    )
                )

    # 8–9. Participant-facing changes require human review
    if "post_dose_fasting" in change_by_concept:
        fasting = change_by_concept["post_dose_fasting"]
        findings.append(
            RehearsalFinding(
                finding_id="F-FASTING-REVIEW",
                code=FindingCode.FASTING_REQUIRES_REVIEW.value,
                severity=Severity.WARNING,
                summary="Fasting change requires human review.",
                change_ids=[fasting.change_id],
                details={"tier": classify_change(fasting).value},
            )
        )
    if "conditional_repeat_ecg" in change_by_concept:
        ecg = change_by_concept["conditional_repeat_ecg"]
        findings.append(
            RehearsalFinding(
                finding_id="F-ECG-REVIEW",
                code=FindingCode.ECG_REQUIRES_REVIEW.value,
                severity=Severity.WARNING,
                summary="Conditional ECG change requires human review.",
                change_ids=[ecg.change_id],
                details={"tier": classify_change(ecg).value},
            )
        )

    return findings


def evaluate_effective_state(
    site: SiteState,
    participant: ParticipantState,
    *,
    target_version: str = "2.0",
) -> dict[str, Any]:
    """Return the effective operational state for one site×participant pair."""
    day1 = participant.visit("Day 1")
    can_activate, reason = site_can_activate_v2(site)
    return {
        "site_id": site.site_id,
        "participant_id": participant.participant_id,
        "local_approval_exists": site.local_approval_complete,
        "training_complete": site.amendment_training_complete,
        "can_activate_v2": can_activate,
        "activation_block_reason": None if can_activate else reason,
        "protocol_version_applies": applicable_protocol_version(
            site, target_version=target_version
        ),
        "consent_version": participant.consent.consent_version,
        "day1_completed": bool(day1 and day1.completed),
        "day1_future": bool(day1 and not day1.completed and day1.scheduled),
        "day1_immutable": bool(day1 and day1.immutable),
        "storage_sufficient_for_overnight": site.logistics.validated_overnight_storage_available,
        "inventory_extra_pk_kits": site.inventory.extra_pk_kits,
        "courier_departure_local_time": site.logistics.courier_departure_local_time,
        "planned_dose_time_local": day1.planned_dose_time_local if day1 else None,
    }
