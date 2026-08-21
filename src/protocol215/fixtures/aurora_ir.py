"""Hand-built AURORA-101 ProtocolIR objects for deterministic tests."""

from __future__ import annotations

from protocol215.domain.models import (
    ECGRequirement,
    EDCField,
    EvidenceReference,
    LaboratoryRequirement,
    ParticipantRestriction,
    PKSample,
    ProtocolIR,
    ProtocolMetadata,
    ScheduledActivity,
    StudyArm,
    VisitDefinition,
)
from protocol215.fixtures.constants import STUDY_TITLE


def _ev(page: int, section_id: str, quote: str | None = None) -> list[EvidenceReference]:
    return [EvidenceReference(page=page, section_id=section_id, quote=quote)]


def build_aurora_v1_ir() -> ProtocolIR:
    return ProtocolIR(
        metadata=ProtocolMetadata(
            study_id="AURORA-101",
            version="1.0",
            title=STUDY_TITLE,
            document_id="AURORA-101-PROT-V1.0",
        ),
        arms=[StudyArm(arm_id="AUR-101", name="AUR-101"), StudyArm(arm_id="PBO", name="Placebo")],
        visits=[
            VisitDefinition(visit_code="Screening", name="Screening", sequence=0),
            VisitDefinition(
                visit_code="Day 1", name="Day 1", sequence=1, evidence=_ev(8, "SEC-DAY1")
            ),
            VisitDefinition(visit_code="Day 8", name="Day 8", sequence=2),
        ],
        activities=[
            ScheduledActivity(
                activity_id="ACT-DOSE",
                name="Dosing",
                visit_code="Day 1",
                evidence=_ev(7, "SEC-SOA"),
            ),
            ScheduledActivity(
                activity_id="ACT-ECG-BASELINE",
                name="Baseline ECG",
                visit_code="Day 1",
                evidence=_ev(9, "SEC-ECG"),
            ),
        ],
        pk_samples=[
            PKSample(
                sample_id="PK-PRED",
                timepoint_hours=0.0,
                label="pre-dose",
                evidence=_ev(8, "SEC-PK"),
            ),
            PKSample(sample_id="PK-0.5", timepoint_hours=0.5, evidence=_ev(8, "SEC-PK")),
            PKSample(sample_id="PK-1", timepoint_hours=1.0, evidence=_ev(8, "SEC-PK")),
            PKSample(sample_id="PK-2", timepoint_hours=2.0, evidence=_ev(8, "SEC-PK")),
            PKSample(sample_id="PK-4", timepoint_hours=4.0, evidence=_ev(8, "SEC-PK")),
        ],
        laboratory=[
            LaboratoryRequirement(
                requirement_id="LAB-CENTRAL",
                description="Central laboratory processing",
                central_lab_email="lab-v1@example.test",
                sample_processing_window_minutes=60,
                evidence=_ev(10, "SEC-LAB-CONTACT", "lab-v1@example.test"),
            )
        ],
        ecg=[
            ECGRequirement(
                requirement_id="ECG-BASE",
                baseline_required=True,
                predose_required=True,
                conditional_repeat=False,
                evidence=_ev(9, "SEC-ECG"),
            )
        ],
        restrictions=[
            ParticipantRestriction(
                restriction_id="REST-FASTING",
                kind="fasting",
                value=2,
                unit="hours",
                evidence=_ev(8, "SEC-FASTING", "through 2 hours"),
            )
        ],
        edc_fields=[
            EDCField(name="pk_collection_time", evidence=_ev(12, "SEC-DATA")),
            EDCField(name="ecg_assessment", evidence=_ev(12, "SEC-DATA")),
            EDCField(name="lab_shipment_log", evidence=_ev(12, "SEC-DATA")),
        ],
        administrative_contacts={"central_lab": "lab-v1@example.test"},
    )


def build_aurora_v2_ir() -> ProtocolIR:
    ir = build_aurora_v1_ir().model_copy(deep=True)
    ir.metadata = ProtocolMetadata(
        study_id="AURORA-101",
        version="2.0",
        title=STUDY_TITLE,
        document_id="AURORA-101-PROT-V2.0",
    )
    ir.administrative_contacts = {"central_lab": "lab-v2@example.test"}
    ir.laboratory = [
        LaboratoryRequirement(
            requirement_id="LAB-CENTRAL",
            description="Central laboratory processing",
            central_lab_email="lab-v2@example.test",
            sample_processing_window_minutes=60,
            evidence=_ev(10, "SEC-LAB-CONTACT", "lab-v2@example.test"),
        )
    ]
    ir.pk_samples = [
        *ir.pk_samples,
        PKSample(
            sample_id="PK-6",
            timepoint_hours=6.0,
            label="6 hours post-dose",
            evidence=_ev(8, "SEC-PK", "6 hours post-dose"),
        ),
    ]
    ir.activities = [
        *ir.activities,
        ScheduledActivity(
            activity_id="ACT-PK-6H",
            name="PK sample 6 h",
            visit_code="Day 1",
            timing_hours_post_dose=6.0,
            evidence=_ev(7, "SEC-SOA"),
        ),
        ScheduledActivity(
            activity_id="ACT-ECG-CONDITIONAL",
            name="Conditional repeat ECG",
            visit_code="Day 1",
            evidence=_ev(9, "SEC-ECG"),
        ),
    ]
    ir.restrictions = [
        ParticipantRestriction(
            restriction_id="REST-FASTING",
            kind="fasting",
            value=4,
            unit="hours",
            evidence=_ev(8, "SEC-FASTING", "through 4 hours"),
        )
    ]
    ir.edc_fields = [
        *ir.edc_fields,
        EDCField(
            name="sample_processing_temperature_c",
            evidence=_ev(12, "SEC-DATA", "sample_processing_temperature_c"),
        ),
    ]
    ir.ecg = [
        ECGRequirement(
            requirement_id="ECG-BASE",
            baseline_required=True,
            predose_required=True,
            conditional_repeat=False,
            evidence=_ev(9, "SEC-ECG"),
        ),
        ECGRequirement(
            requirement_id="ECG-CONDITIONAL",
            baseline_required=False,
            predose_required=False,
            conditional_repeat=True,
            trigger_description="AURORA ECG review trigger (fictional protocol-defined)",
            evidence=_ev(9, "SEC-ECG", "Conditional repeat ECG"),
        ),
    ]
    return ir
