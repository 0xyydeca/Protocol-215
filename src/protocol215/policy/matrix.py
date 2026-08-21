"""Deterministic GREEN / AMBER / RED policy matrix."""

from __future__ import annotations

from protocol215.domain.enums import RiskTier
from protocol215.domain.models import ActionProposal, EvidenceReference, SemanticChange
from protocol215.tools.registry import (
    ALLOWED_ACTION_NAMES,
    AMBER_TOOLS,
    GREEN_TOOLS,
    RED_TOOLS,
    default_tier_for_tool,
)

# Re-export for existing imports
__all__ = [
    "ALLOWED_ACTION_NAMES",
    "AMBER_TOOLS",
    "GREEN_TOOLS",
    "RED_TOOLS",
    "authorize_proposal",
    "classify_change",
    "classify_tool",
    "evidence_or_empty",
    "is_executable",
    "requires_human_approval",
]

CONCEPT_TIER: dict[str, RiskTier] = {
    "central_lab_contact": RiskTier.GREEN,
    "edc_field": RiskTier.GREEN,
    "pk_timepoint": RiskTier.AMBER,
    "post_dose_fasting": RiskTier.AMBER,
    "conditional_repeat_ecg": RiskTier.AMBER,
    "scheduled_activity": RiskTier.AMBER,
    "activity_timing": RiskTier.AMBER,
    "participant_restriction": RiskTier.AMBER,
    "safety_monitoring_removal": RiskTier.RED,
}


def classify_tool(tool_name: str) -> RiskTier:
    return default_tier_for_tool(tool_name)


def classify_change(change: SemanticChange) -> RiskTier:
    if change.candidate_risk is not None:
        return change.candidate_risk
    if change.expected_risk_tier is not None:
        return change.expected_risk_tier
    return CONCEPT_TIER.get(change.concept_type, RiskTier.AMBER)


def authorize_proposal(proposal: ActionProposal) -> RiskTier:
    """Deterministic authorization. RED stays RED even if later approved."""
    if proposal.proposed_tier == RiskTier.RED:
        return RiskTier.RED

    if proposal.tool_name in RED_TOOLS or proposal.tool_name not in ALLOWED_ACTION_NAMES:
        return RiskTier.RED

    tier = classify_tool(proposal.tool_name)

    # Uncited → RED (never execute)
    if not proposal.evidence:
        return RiskTier.RED

    if tier == RiskTier.GREEN and proposal.proposed_tier == RiskTier.AMBER:
        return RiskTier.AMBER
    return tier


def requires_human_approval(tier: RiskTier) -> bool:
    return tier == RiskTier.AMBER


def is_executable(tier: RiskTier, *, approved: bool) -> bool:
    if tier == RiskTier.RED:
        return False
    if tier == RiskTier.GREEN:
        return True
    return approved


def evidence_or_empty(items: list[EvidenceReference] | None) -> list[EvidenceReference]:
    return list(items or [])
