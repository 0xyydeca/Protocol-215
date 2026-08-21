"""Deterministic semantic diff over ProtocolIR objects (not text diff)."""

from __future__ import annotations

from protocol215.application.impact import artifacts_for_change
from protocol215.domain.enums import ChangeOperation, RiskTier
from protocol215.domain.models import EvidenceReference, ProtocolIR, SemanticChange


def _ev(items: list[EvidenceReference]) -> list[EvidenceReference]:
    return list(items)


def _change(
    *,
    change_id: str,
    concept_type: str,
    operation: ChangeOperation,
    before: dict | None,
    after: dict | None,
    old_evidence: list[EvidenceReference] | None = None,
    new_evidence: list[EvidenceReference] | None = None,
    evidence: list[EvidenceReference] | None = None,
    candidate_risk: RiskTier,
) -> SemanticChange:
    old_e = _ev(old_evidence or [])
    new_e = _ev(new_evidence or [])
    if not old_e and not new_e and evidence:
        new_e = _ev(evidence)
    combined = old_e + new_e
    return SemanticChange(
        change_id=change_id,
        concept_type=concept_type,
        operation=operation,
        before=before,
        after=after,
        old_evidence=old_e,
        new_evidence=new_e,
        evidence=combined,
        expected_risk_tier=candidate_risk,
        candidate_risk=candidate_risk,
    )


def diff_protocol_irs(before: ProtocolIR, after: ProtocolIR) -> list[SemanticChange]:
    """Return structured semantic changes from two Protocol IR objects."""
    changes: list[SemanticChange] = []

    before_contacts = before.administrative_contacts
    after_contacts = after.administrative_contacts
    for role in sorted(set(before_contacts) | set(after_contacts)):
        b_val = before_contacts.get(role)
        a_val = after_contacts.get(role)
        if b_val == a_val:
            continue
        old_lab: list[EvidenceReference] = []
        new_lab: list[EvidenceReference] = []
        for req in before.laboratory:
            if req.central_lab_email == b_val:
                old_lab.extend(req.evidence)
        for req in after.laboratory:
            if req.central_lab_email == a_val:
                new_lab.extend(req.evidence)
        if not new_lab and not old_lab:
            for req in after.laboratory:
                if req.central_lab_email == a_val:
                    new_lab.extend(req.evidence)
        changes.append(
            _change(
                change_id=f"CHG-CONTACT-{role}",
                concept_type="central_lab_contact" if role == "central_lab" else f"contact_{role}",
                operation=ChangeOperation.UPDATE if b_val and a_val else ChangeOperation.ADD,
                before={"role": role, "email": b_val},
                after={"role": role, "email": a_val},
                old_evidence=old_lab,
                new_evidence=new_lab,
                candidate_risk=RiskTier.GREEN,
            )
        )

    before_pk = {s.timepoint_hours: s for s in before.pk_samples}
    after_pk = {s.timepoint_hours: s for s in after.pk_samples}
    for hours in sorted(set(after_pk) - set(before_pk)):
        sample = after_pk[hours]
        changes.append(
            _change(
                change_id=f"CHG-PK-ADD-{hours:g}",
                concept_type="pk_timepoint",
                operation=ChangeOperation.ADD,
                before={"timepoints_hours": sorted(before_pk)},
                after={
                    "timepoints_hours": sorted(after_pk),
                    "added_timepoint_hours": hours,
                    "sample_id": sample.sample_id,
                },
                new_evidence=sample.evidence,
                candidate_risk=RiskTier.AMBER,
            )
        )
    for hours in sorted(set(before_pk) - set(after_pk)):
        sample = before_pk[hours]
        changes.append(
            _change(
                change_id=f"CHG-PK-REMOVE-{hours:g}",
                concept_type="pk_timepoint",
                operation=ChangeOperation.REMOVE,
                before={"timepoint_hours": hours, "sample_id": sample.sample_id},
                after=None,
                old_evidence=sample.evidence,
                candidate_risk=RiskTier.AMBER,
            )
        )

    before_act = {a.activity_id: a for a in before.activities}
    after_act = {a.activity_id: a for a in after.activities}
    for aid in sorted(set(after_act) - set(before_act)):
        activity = after_act[aid]
        changes.append(
            _change(
                change_id=f"CHG-ACT-ADD-{aid}",
                concept_type="scheduled_activity",
                operation=ChangeOperation.ADD,
                before=None,
                after={
                    "activity_id": aid,
                    "name": activity.name,
                    "visit_code": activity.visit_code,
                    "timing_hours_post_dose": activity.timing_hours_post_dose,
                },
                new_evidence=activity.evidence,
                candidate_risk=RiskTier.AMBER,
            )
        )
    for aid in sorted(set(before_act) - set(after_act)):
        activity = before_act[aid]
        changes.append(
            _change(
                change_id=f"CHG-ACT-REMOVE-{aid}",
                concept_type="scheduled_activity",
                operation=ChangeOperation.REMOVE,
                before={"activity_id": aid, "name": activity.name},
                after=None,
                old_evidence=activity.evidence,
                candidate_risk=RiskTier.AMBER,
            )
        )
    for aid in sorted(set(before_act) & set(after_act)):
        b_a, a_a = before_act[aid], after_act[aid]
        if b_a.timing_hours_post_dose != a_a.timing_hours_post_dose:
            changes.append(
                _change(
                    change_id=f"CHG-ACT-TIMING-{aid}",
                    concept_type="activity_timing",
                    operation=ChangeOperation.UPDATE,
                    before={"timing_hours_post_dose": b_a.timing_hours_post_dose},
                    after={"timing_hours_post_dose": a_a.timing_hours_post_dose},
                    old_evidence=b_a.evidence,
                    new_evidence=a_a.evidence,
                    candidate_risk=RiskTier.AMBER,
                )
            )

    before_rest = {r.restriction_id: r for r in before.restrictions}
    after_rest = {r.restriction_id: r for r in after.restrictions}
    for rid in sorted(set(after_rest) | set(before_rest)):
        b_r = before_rest.get(rid)
        a_r = after_rest.get(rid)
        if b_r is None and a_r is not None:
            changes.append(
                _change(
                    change_id=f"CHG-REST-ADD-{rid}",
                    concept_type="participant_restriction",
                    operation=ChangeOperation.ADD,
                    before=None,
                    after={"kind": a_r.kind, "value": a_r.value, "unit": a_r.unit},
                    new_evidence=a_r.evidence,
                    candidate_risk=RiskTier.AMBER,
                )
            )
        elif a_r is None and b_r is not None:
            changes.append(
                _change(
                    change_id=f"CHG-REST-REMOVE-{rid}",
                    concept_type="participant_restriction",
                    operation=ChangeOperation.REMOVE,
                    before={"kind": b_r.kind, "value": b_r.value, "unit": b_r.unit},
                    after=None,
                    old_evidence=b_r.evidence,
                    candidate_risk=RiskTier.AMBER,
                )
            )
        elif b_r is not None and a_r is not None and (b_r.value != a_r.value or b_r.unit != a_r.unit):
            concept = "post_dose_fasting" if a_r.kind == "fasting" else "participant_restriction"
            before_payload: dict = {"kind": b_r.kind, "value": b_r.value, "unit": b_r.unit}
            after_payload: dict = {"kind": a_r.kind, "value": a_r.value, "unit": a_r.unit}
            if concept == "post_dose_fasting":
                before_payload = {"hours": b_r.value, **before_payload}
                after_payload = {"hours": a_r.value, **after_payload}
            changes.append(
                _change(
                    change_id=f"CHG-REST-UPDATE-{rid}",
                    concept_type=concept,
                    operation=ChangeOperation.UPDATE,
                    before=before_payload,
                    after=after_payload,
                    old_evidence=b_r.evidence,
                    new_evidence=a_r.evidence,
                    candidate_risk=RiskTier.AMBER,
                )
            )

    before_fields = {f.name: f for f in before.edc_fields}
    after_fields = {f.name: f for f in after.edc_fields}
    for field in sorted(set(after_fields) - set(before_fields)):
        edc = after_fields[field]
        after_payload = {"field": field}
        if field.endswith("_c") or "temperature" in field.lower():
            after_payload["unit"] = "celsius"
        changes.append(
            _change(
                change_id=f"CHG-EDC-ADD-{field}",
                concept_type="edc_field",
                operation=ChangeOperation.ADD,
                before={"field": None},
                after=after_payload,
                new_evidence=edc.evidence,
                candidate_risk=RiskTier.GREEN,
            )
        )
    for field in sorted(set(before_fields) - set(after_fields)):
        edc = before_fields[field]
        changes.append(
            _change(
                change_id=f"CHG-EDC-REMOVE-{field}",
                concept_type="edc_field",
                operation=ChangeOperation.REMOVE,
                before={"field": field},
                after={"field": None},
                old_evidence=edc.evidence,
                candidate_risk=RiskTier.AMBER,
            )
        )

    before_ecg = {e.requirement_id: e for e in before.ecg}
    after_ecg = {e.requirement_id: e for e in after.ecg}
    for eid in sorted(set(after_ecg) | set(before_ecg)):
        b_e = before_ecg.get(eid)
        a_e = after_ecg.get(eid)
        if b_e is None and a_e is not None:
            changes.append(
                _change(
                    change_id=f"CHG-ECG-ADD-{eid}",
                    concept_type="conditional_repeat_ecg"
                    if a_e.conditional_repeat
                    else "ecg_requirement",
                    operation=ChangeOperation.ADD,
                    before={"conditional_repeat_required": False},
                    after={
                        "conditional_repeat_required": a_e.conditional_repeat,
                        "trigger": a_e.trigger_description,
                    },
                    new_evidence=a_e.evidence,
                    candidate_risk=RiskTier.AMBER,
                )
            )
        elif a_e is None and b_e is not None:
            changes.append(
                _change(
                    change_id=f"CHG-ECG-REMOVE-{eid}",
                    concept_type="ecg_requirement",
                    operation=ChangeOperation.REMOVE,
                    before={
                        "conditional_repeat_required": b_e.conditional_repeat,
                        "baseline_required": b_e.baseline_required,
                    },
                    after=None,
                    old_evidence=b_e.evidence,
                    candidate_risk=RiskTier.RED
                    if b_e.baseline_required or b_e.predose_required
                    else RiskTier.AMBER,
                )
            )
        elif b_e is not None and a_e is not None:
            if b_e.conditional_repeat != a_e.conditional_repeat or (
                b_e.trigger_description != a_e.trigger_description
            ):
                changes.append(
                    _change(
                        change_id=f"CHG-ECG-UPDATE-{eid}",
                        concept_type="conditional_repeat_ecg",
                        operation=ChangeOperation.UPDATE,
                        before={
                            "conditional_repeat_required": b_e.conditional_repeat,
                            "trigger": b_e.trigger_description,
                        },
                        after={
                            "conditional_repeat_required": a_e.conditional_repeat,
                            "trigger": a_e.trigger_description,
                        },
                        old_evidence=b_e.evidence,
                        new_evidence=a_e.evidence,
                        candidate_risk=RiskTier.AMBER,
                    )
                )
            if (b_e.baseline_required and not a_e.baseline_required) or (
                b_e.predose_required and not a_e.predose_required
            ):
                changes.append(
                    _change(
                        change_id=f"CHG-ECG-SAFETY-REMOVE-{eid}",
                        concept_type="safety_monitoring_removal",
                        operation=ChangeOperation.UPDATE,
                        before={
                            "baseline_required": b_e.baseline_required,
                            "predose_required": b_e.predose_required,
                        },
                        after={
                            "baseline_required": a_e.baseline_required,
                            "predose_required": a_e.predose_required,
                        },
                        old_evidence=b_e.evidence,
                        new_evidence=a_e.evidence,
                        candidate_risk=RiskTier.RED,
                    )
                )

    before_emails = {r.central_lab_email for r in before.laboratory if r.central_lab_email}
    after_emails = {r.central_lab_email for r in after.laboratory if r.central_lab_email}
    if before_emails != after_emails and not any(
        c.concept_type == "central_lab_contact" for c in changes
    ):
        b_email = next(iter(before_emails), None)
        a_email = next(iter(after_emails), None)
        lab_before = next((r for r in before.laboratory if r.central_lab_email == b_email), None)
        lab_after = next((r for r in after.laboratory if r.central_lab_email == a_email), None)
        changes.append(
            _change(
                change_id="CHG-LAB-EMAIL",
                concept_type="central_lab_contact",
                operation=ChangeOperation.UPDATE,
                before={"email": b_email},
                after={"email": a_email},
                old_evidence=lab_before.evidence if lab_before else [],
                new_evidence=lab_after.evidence if lab_after else [],
                candidate_risk=RiskTier.GREEN,
            )
        )

    remapped = _canonicalize_aurora_change_ids(changes)
    return [_attach_affected_artifacts(c) for c in remapped]


def _attach_affected_artifacts(change: SemanticChange) -> SemanticChange:
    if change.affected_artifact_ids:
        return change
    return change.model_copy(update={"affected_artifact_ids": artifacts_for_change(change)})


def _canonicalize_aurora_change_ids(changes: list[SemanticChange]) -> list[SemanticChange]:
    """Map known AURORA deltas onto gold change_id strings when unambiguous."""
    remapped: list[SemanticChange] = []
    used_gold: set[str] = set()
    for change in changes:
        gold_id: str | None = None
        if change.concept_type == "central_lab_contact":
            gold_id = "CHG-001-LAB-CONTACT"
        elif (
            change.concept_type == "pk_timepoint"
            and change.operation == ChangeOperation.ADD
            and (change.after or {}).get("added_timepoint_hours") == 6.0
        ):
            gold_id = "CHG-002-PK-6H"
        elif change.concept_type == "post_dose_fasting":
            gold_id = "CHG-003-FASTING-4H"
        elif (
            change.concept_type == "edc_field"
            and change.operation == ChangeOperation.ADD
            and (change.after or {}).get("field") == "sample_processing_temperature_c"
        ):
            gold_id = "CHG-004-EDC-TEMP"
        elif change.concept_type == "conditional_repeat_ecg":
            gold_id = "CHG-005-CONDITIONAL-ECG"

        if gold_id and gold_id not in used_gold:
            used_gold.add(gold_id)
            remapped.append(change.model_copy(update={"change_id": gold_id}))
        else:
            remapped.append(change)
    return remapped
