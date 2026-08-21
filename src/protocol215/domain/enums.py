"""Domain enumerations for Protocol 215."""

from __future__ import annotations

from enum import StrEnum


class WorkflowStatus(StrEnum):
    # Prompt 7 explicit statuses (primary)
    CREATED = "CREATED"
    ARTIFACTS_REGISTERED = "ARTIFACTS_REGISTERED"
    COMPILING = "COMPILING"
    ANALYZING = "ANALYZING"
    REHEARSING = "REHEARSING"
    PLANNING = "PLANNING"
    EXECUTING_SAFE_ACTIONS = "EXECUTING_SAFE_ACTIONS"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    RESUMING = "RESUMING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_BLOCKS = "COMPLETED_WITH_BLOCKS"
    FAILED_RETRYABLE = "FAILED_RETRYABLE"
    FAILED_TERMINAL = "FAILED_TERMINAL"
    # Legacy aliases kept for earlier stages / fixtures
    RECEIVED = "RECEIVED"
    INTAKE_COMPLETE = "INTAKE_COMPLETE"
    COMPILING_IR = "COMPILING_IR"
    DIFFING = "DIFFING"
    IMPACTING = "IMPACTING"
    GATING = "GATING"
    EXECUTING_GREEN = "EXECUTING_GREEN"
    EXECUTING_APPROVED_AMBER = "EXECUTING_APPROVED_AMBER"
    MANIFEST_READY = "MANIFEST_READY"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class FailureClass(StrEnum):
    INVALID_INPUT = "invalid_input"
    TRANSIENT_MODEL_ERROR = "transient_model_error"
    MODEL_SCHEMA_ERROR = "model_schema_error"
    PERSISTENCE_ERROR = "persistence_error"
    DUPLICATE_EVENT = "duplicate_event"
    STALE_APPROVAL = "stale_approval"
    POLICY_VIOLATION = "policy_violation"
    INVARIANT_FAILURE = "invariant_failure"
    TERMINAL_UNSUPPORTED_CHANGE = "terminal_unsupported_change"
    UNKNOWN = "unknown"


class ChangeOperation(StrEnum):
    ADD = "add"
    REMOVE = "remove"
    UPDATE = "update"


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    BLOCKER = "blocker"
    CRITICAL = "critical"


class RiskTier(StrEnum):
    GREEN = "GREEN"
    AMBER = "AMBER"
    RED = "RED"


class ActionStatus(StrEnum):
    PROPOSED = "proposed"
    AUTHORIZED = "authorized"
    BLOCKED = "blocked"
    EXECUTED = "executed"
    REJECTED = "rejected"
    SKIPPED = "skipped"


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CONSUMED = "consumed"


class ProtocolApplicability(StrEnum):
    ACTIVE = "active"
    PENDING_ACTIVATION = "pending_activation"
    NOT_APPLICABLE = "not_applicable"
    SUPERSEDED = "superseded"
    HISTORICAL_IMMUTABLE = "historical_immutable"


class ReviewStatus(StrEnum):
    ACCEPTED = "accepted"
    NEEDS_REVIEW = "needs_review"
    REJECTED = "rejected"


class ImpactLayer(StrEnum):
    PROTOCOL_CHANGE = "protocol_change"
    OPERATIONAL_ARTIFACT = "operational_artifact"
    SITE = "site"
    PARTICIPANT = "participant"
    FINDING = "finding"
    PROPOSED_ACTION = "proposed_action"


class FindingCode(StrEnum):
    LAB_CONTACT_SAFE = "FINDING_LAB_CONTACT_SAFE"
    EDC_SPEC_DRAFTABLE = "FINDING_EDC_SPEC_DRAFTABLE"
    BOSTON_TRAINING_REQUIRED = "FINDING_BOSTON_TRAINING_REQUIRED"
    SEATTLE_APPROVAL_TRAINING_REQUIRED = "FINDING_SEATTLE_APPROVAL_TRAINING_REQUIRED"
    PK_KITS_MAY_BE_REQUIRED = "FINDING_PK_KITS_MAY_BE_REQUIRED"
    P001_DAY1_IMMUTABLE = "FINDING_P001_DAY1_IMMUTABLE"
    P002_COURIER_STORAGE_CONFLICT = "FINDING_P002_COURIER_STORAGE_CONFLICT"
    FASTING_REQUIRES_REVIEW = "FINDING_FASTING_REQUIRES_REVIEW"
    ECG_REQUIRES_REVIEW = "FINDING_ECG_REQUIRES_REVIEW"
    NO_GLOBAL_ACTIVATION = "FINDING_NO_GLOBAL_ACTIVATION"
