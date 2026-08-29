"""Strongly typed Pydantic domain models for Protocol 215."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from protocol215.domain.enums import (
    ActionStatus,
    ApprovalStatus,
    ChangeOperation,
    ImpactLayer,
    ProtocolApplicability,
    ReviewStatus,
    RiskTier,
    Severity,
    WorkflowStatus,
)


def utc_now() -> datetime:
    return datetime.now(UTC)


class EvidenceReference(BaseModel):
    page: int = Field(ge=1)
    section_id: str
    quote: str | None = Field(
        default=None,
        description="Short evidence excerpt only — never a long verbatim passage.",
        max_length=160,
    )
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    review_status: ReviewStatus = ReviewStatus.ACCEPTED
    protocol_version: str | None = None


class ProtocolMetadata(BaseModel):
    study_id: str
    version: str
    title: str
    document_id: str
    synthetic: bool = True


class StudyArm(BaseModel):
    arm_id: str
    name: str
    description: str | None = None


class VisitDefinition(BaseModel):
    visit_code: str
    name: str
    sequence: int = 0
    evidence: list[EvidenceReference] = Field(default_factory=list)


class ScheduledActivity(BaseModel):
    activity_id: str
    name: str
    visit_code: str
    required: bool = True
    timing_hours_post_dose: float | None = None
    evidence: list[EvidenceReference] = Field(default_factory=list)


class PKSample(BaseModel):
    sample_id: str
    timepoint_hours: float
    visit_code: str = "Day 1"
    label: str | None = None
    evidence: list[EvidenceReference] = Field(default_factory=list)


class LaboratoryRequirement(BaseModel):
    requirement_id: str
    description: str
    central_lab_email: str | None = None
    sample_processing_window_minutes: int | None = None
    evidence: list[EvidenceReference] = Field(default_factory=list)


class ECGRequirement(BaseModel):
    requirement_id: str
    baseline_required: bool = True
    predose_required: bool = True
    conditional_repeat: bool = False
    trigger_description: str | None = None
    evidence: list[EvidenceReference] = Field(default_factory=list)


class ParticipantRestriction(BaseModel):
    restriction_id: str
    kind: str
    value: str | float | int
    unit: str | None = None
    evidence: list[EvidenceReference] = Field(default_factory=list)


class EDCField(BaseModel):
    name: str
    evidence: list[EvidenceReference] = Field(default_factory=list)


class ProtocolIR(BaseModel):
    metadata: ProtocolMetadata
    arms: list[StudyArm] = Field(default_factory=list)
    visits: list[VisitDefinition] = Field(default_factory=list)
    activities: list[ScheduledActivity] = Field(default_factory=list)
    pk_samples: list[PKSample] = Field(default_factory=list)
    laboratory: list[LaboratoryRequirement] = Field(default_factory=list)
    ecg: list[ECGRequirement] = Field(default_factory=list)
    restrictions: list[ParticipantRestriction] = Field(default_factory=list)
    edc_fields: list[EDCField] = Field(default_factory=list)
    administrative_contacts: dict[str, str] = Field(default_factory=dict)


class SemanticChange(BaseModel):
    change_id: str
    concept_type: str
    operation: ChangeOperation
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None
    # Legacy combined evidence list (old ∪ new) for earlier callers.
    evidence: list[EvidenceReference] = Field(default_factory=list)
    old_evidence: list[EvidenceReference] = Field(default_factory=list)
    new_evidence: list[EvidenceReference] = Field(default_factory=list)
    expected_risk_tier: RiskTier | None = None
    candidate_risk: RiskTier | None = None
    affected_artifact_ids: list[str] = Field(default_factory=list)
    explanation: str = ""
    review_status: ReviewStatus = ReviewStatus.ACCEPTED
    normalization_notes: list[str] = Field(default_factory=list)

    def model_post_init(self, __context: Any) -> None:
        if self.candidate_risk is None and self.expected_risk_tier is not None:
            self.candidate_risk = self.expected_risk_tier
        elif self.expected_risk_tier is None and self.candidate_risk is not None:
            self.expected_risk_tier = self.candidate_risk
        if not self.evidence and (self.old_evidence or self.new_evidence):
            self.evidence = [*self.old_evidence, *self.new_evidence]
        if not self.old_evidence and not self.new_evidence and self.evidence:
            # Legacy path: treat combined evidence as new evidence.
            self.new_evidence = list(self.evidence)


class ImpactNode(BaseModel):
    node_id: str
    artifact_type: str
    label: str
    layer: ImpactLayer = ImpactLayer.OPERATIONAL_ARTIFACT
    ref_id: str | None = None


class ImpactEdge(BaseModel):
    edge_id: str
    change_id: str
    from_node_id: str
    to_node_id: str
    relationship: str


class ImpactGraph(BaseModel):
    nodes: list[ImpactNode] = Field(default_factory=list)
    edges: list[ImpactEdge] = Field(default_factory=list)

    def artifact_types_for_change(self, change_id: str) -> set[str]:
        node_by_id = {n.node_id: n for n in self.nodes}
        artifacts: set[str] = set()
        for edge in self.edges:
            if edge.change_id != change_id:
                continue
            target = node_by_id.get(edge.to_node_id)
            if target is not None and target.layer == ImpactLayer.OPERATIONAL_ARTIFACT:
                artifacts.add(target.artifact_type)
        return artifacts

    def nodes_by_layer(self, layer: ImpactLayer) -> list[ImpactNode]:
        return [n for n in self.nodes if n.layer == layer]


class InventoryState(BaseModel):
    extra_pk_kits: int = 0
    pk_kit_sku: str = "SYNTH-PK-KIT"


class LogisticsState(BaseModel):
    courier_departure_local_time: str
    validated_overnight_storage_available: bool


class ConsentState(BaseModel):
    consent_version: str | None
    applicable: ProtocolApplicability = ProtocolApplicability.ACTIVE


class VisitState(BaseModel):
    visit_code: str
    completed: bool = False
    immutable: bool = False
    scheduled: bool = True
    planned_dose_time_local: str | None = None


class SiteState(BaseModel):
    site_id: str
    name: str
    city: str
    local_approval_complete: bool
    amendment_training_complete: bool
    active_protocol_version: str
    logistics: LogisticsState
    inventory: InventoryState
    v2_activated: bool = False


class ParticipantState(BaseModel):
    participant_id: str
    site_id: str
    consent: ConsentState
    visits: list[VisitState] = Field(default_factory=list)

    def visit(self, visit_code: str) -> VisitState | None:
        for item in self.visits:
            if item.visit_code == visit_code:
                return item
        return None


class RehearsalFinding(BaseModel):
    finding_id: str
    code: str
    severity: Severity
    summary: str
    site_id: str | None = None
    participant_id: str | None = None
    change_ids: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class ActionProposal(BaseModel):
    proposal_id: str
    tool_name: str
    change_ids: list[str] = Field(default_factory=list)
    site_id: str | None = None
    participant_id: str | None = None
    rationale: str
    evidence: list[EvidenceReference] = Field(default_factory=list)
    args: dict[str, Any] = Field(default_factory=dict)
    proposed_tier: RiskTier | None = None
    idempotency_key: str | None = None


class ActionExecution(BaseModel):
    execution_id: str
    proposal_id: str
    tool_name: str
    status: ActionStatus
    authorized_tier: RiskTier
    evidence: list[EvidenceReference] = Field(default_factory=list)
    idempotency_key: str
    site_id: str | None = None
    participant_id: str | None = None
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None
    approved: bool = False
    executed: bool = False
    executed_at: datetime | None = None
    replayed: bool = False


class ApprovalRequest(BaseModel):
    approval_id: str
    run_id: str
    action_ids: list[str]
    status: ApprovalStatus = ApprovalStatus.PENDING
    state_hash: str
    created_at: datetime = Field(default_factory=utc_now)
    session_id: str | None = None
    invocation_id: str | None = None
    interrupt_id: str | None = None
    expected_state_version: int = 0
    # Enriched approval card fields (Prompt 8)
    action_id: str | None = None
    tool_name: str | None = None
    affected_site_id: str | None = None
    affected_participant_id: str | None = None
    change_evidence: list[EvidenceReference] = Field(default_factory=list)
    operational_evidence: list[EvidenceReference] = Field(default_factory=list)
    before_state: dict[str, Any] = Field(default_factory=dict)
    proposed_after_state: dict[str, Any] = Field(default_factory=dict)
    reason_approval_required: str = ""
    consequences_of_approval: str = ""
    consequences_of_rejection: str = ""
    evidence_hash: str | None = None
    policy_hash: str | None = None


class ApprovalDecision(BaseModel):
    approval_id: str
    decision: ApprovalStatus
    decided_at: datetime = Field(default_factory=utc_now)
    actor: str = "synthetic_operator"


class AuditEvent(BaseModel):
    event_id: str
    run_id: str
    sequence_number: int
    event_type: str
    actor: str
    timestamp: datetime
    evidence: list[EvidenceReference] = Field(default_factory=list)
    input_hash: str
    output_hash: str
    previous_event_hash: str
    current_event_hash: str
    decision_summary: str
    action_id: str | None = None
    tool_id: str | None = None
    idempotency_key: str | None = None

    @property
    def prev_hash(self) -> str:
        return self.previous_event_hash

    @property
    def event_hash(self) -> str:
        return self.current_event_hash


class InvariantResult(BaseModel):
    invariant_id: str
    name: str
    passed: bool
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class AmendmentReleaseManifest(BaseModel):
    run_id: str
    study_id: str
    from_version: str
    to_version: str
    changes: list[SemanticChange] = Field(default_factory=list)
    findings: list[RehearsalFinding] = Field(default_factory=list)
    actions: list[ActionExecution] = Field(default_factory=list)
    invariants: list[InvariantResult] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=utc_now)


class WorkflowRun(BaseModel):
    run_id: str
    study_id: str
    status: WorkflowStatus = WorkflowStatus.CREATED
    from_version: str
    to_version: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    checkpoint: str | None = None
    last_checkpoint_at: datetime | None = None
    completed_idempotency_keys: list[str] = Field(default_factory=list)
    object_keys: dict[str, str] = Field(default_factory=dict)
    state_version: int = 0
    completed_nodes: list[str] = Field(default_factory=list)
    event_sequence: list[str] = Field(default_factory=list)
    last_worker_event_id: str | None = None
    failure_class: str | None = None
    failure_detail: str | None = None
    correlation_id: str | None = None
    worker_revision: str | None = None
    compiler_model: str | None = None


class ProtocolArtifactRecord(BaseModel):
    run_id: str
    version: str
    object_key: str
    content_sha256: str
    registered_at: datetime = Field(default_factory=utc_now)


class DomainEvent(BaseModel):
    event_id: str
    event_type: str
    run_id: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    idempotency_key: str | None = None


class SessionMetadata(BaseModel):
    """ADK session / invocation metadata for pause-resume."""

    run_id: str
    session_id: str
    invocation_id: str | None = None
    interrupt_id: str | None = None
    cursor: str | None = None
    expected_state_version: int = 0
    extra: dict[str, Any] = Field(default_factory=dict)
