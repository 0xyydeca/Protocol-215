"""Post-Gemini ProtocolIR validation (fail closed)."""

from __future__ import annotations

from protocol215.domain.enums import ReviewStatus
from protocol215.domain.models import EvidenceReference, ProtocolIR

LOW_CONFIDENCE_THRESHOLD = 0.7
MAX_EVIDENCE_EXCERPT = 160


class ProtocolIRValidationError(ValueError):
    """Raised when Gemini output fails ProtocolIR safety/schema checks."""


def _all_evidence(ir: ProtocolIR) -> list[EvidenceReference]:
    refs: list[EvidenceReference] = []
    for visit in ir.visits:
        refs.extend(visit.evidence)
    for activity in ir.activities:
        refs.extend(activity.evidence)
    for sample in ir.pk_samples:
        refs.extend(sample.evidence)
    for lab in ir.laboratory:
        refs.extend(lab.evidence)
    for ecg in ir.ecg:
        refs.extend(ecg.evidence)
    for restriction in ir.restrictions:
        refs.extend(restriction.evidence)
    for edc in ir.edc_fields:
        refs.extend(edc.evidence)
    return refs


def _executable_evidence_groups(ir: ProtocolIR) -> list[tuple[str, list[EvidenceReference]]]:
    groups: list[tuple[str, list[EvidenceReference]]] = []
    for activity in ir.activities:
        groups.append((f"activity:{activity.activity_id}", activity.evidence))
    for sample in ir.pk_samples:
        groups.append((f"pk:{sample.sample_id}", sample.evidence))
    for lab in ir.laboratory:
        groups.append((f"lab:{lab.requirement_id}", lab.evidence))
    for ecg in ir.ecg:
        groups.append((f"ecg:{ecg.requirement_id}", ecg.evidence))
    for restriction in ir.restrictions:
        groups.append((f"restriction:{restriction.restriction_id}", restriction.evidence))
    for edc in ir.edc_fields:
        groups.append((f"edc:{edc.name}", edc.evidence))
    return groups


def validate_protocol_ir(ir: ProtocolIR, *, pdf_page_count: int) -> list[str]:
    """Return validation errors (empty means OK). Mutates review_status for low confidence."""
    errors: list[str] = []

    if not ir.metadata.study_id or not ir.metadata.version or not ir.metadata.title:
        errors.append("required protocol metadata missing (study_id/version/title)")
    if not ir.metadata.document_id:
        errors.append("required protocol metadata missing (document_id)")

    activity_ids = [a.activity_id for a in ir.activities]
    if len(activity_ids) != len(set(activity_ids)):
        errors.append("activity identifiers are not unique")

    if pdf_page_count < 1:
        errors.append("pdf_page_count must be >= 1")

    for ref in _all_evidence(ir):
        if ref.page < 1 or ref.page > pdf_page_count:
            errors.append(
                f"evidence page {ref.page} out of range for PDF with {pdf_page_count} pages"
            )
        if ref.quote is not None and len(ref.quote) > MAX_EVIDENCE_EXCERPT:
            errors.append("evidence excerpt exceeds short-phrase limit")
        if ref.protocol_version is None:
            ref.protocol_version = ir.metadata.version
        if ref.confidence < LOW_CONFIDENCE_THRESHOLD:
            ref.review_status = ReviewStatus.NEEDS_REVIEW

    for label, evidence in _executable_evidence_groups(ir):
        if not evidence:
            errors.append(f"executable fact without evidence: {label}")
            continue
        if all(not e.quote and e.section_id == "" for e in evidence):
            errors.append(f"executable fact lacks usable evidence: {label}")

    # Contacts that imply lab email must be backed by laboratory evidence when present.
    if ir.administrative_contacts.get("central_lab") and not ir.laboratory:
        errors.append("central_lab contact present without laboratory evidence block")

    return errors


def count_low_confidence_facts(ir: ProtocolIR) -> int:
    return sum(
        1
        for ref in _all_evidence(ir)
        if ref.review_status == ReviewStatus.NEEDS_REVIEW
        or ref.confidence < LOW_CONFIDENCE_THRESHOLD
    )
