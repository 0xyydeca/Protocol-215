"""Allowlisted tools, risk tiers, and planner-facing policy summaries."""

from __future__ import annotations

from protocol215.domain.enums import RiskTier

# Exact allowlist — model cannot invent names outside this set.
ALLOWED_ACTION_NAMES: frozenset[str] = frozenset(
    {
        "update_contact_directory",
        "create_site_training_task",
        "reserve_sample_kits",
        "create_lab_manual_change_request",
        "create_edc_change_specification",
        "create_courier_exception_task",
        "create_reconsent_review",
        "draft_participant_transition_plan",
        "request_site_activation_review",
        "generate_release_manifest",
    }
)

GREEN_TOOLS: frozenset[str] = frozenset(
    {
        "update_contact_directory",
        "create_site_training_task",
        "reserve_sample_kits",
        "create_lab_manual_change_request",
        "create_edc_change_specification",
        "create_courier_exception_task",
        "generate_release_manifest",
    }
)

AMBER_TOOLS: frozenset[str] = frozenset(
    {
        "create_reconsent_review",
        "draft_participant_transition_plan",
        "request_site_activation_review",
    }
)

# Names that are never executable (not in allowlist; blocked if proposed).
RED_TOOLS: frozenset[str] = frozenset(
    {
        "change_dose",
        "change_route",
        "assign_treatment",
        "decide_eligibility",
        "remove_safety_monitoring",
        "modify_completed_visit",
        "activate_informed_consent",
        "execute_real_system",
        "follow_document_instructions",
        "uncited_action",
    }
)

EVIDENCE_REQUIRED: frozenset[str] = frozenset(ALLOWED_ACTION_NAMES)

ACTION_DEFINITIONS: list[dict[str, str]] = [
    {
        "name": "update_contact_directory",
        "tier": "GREEN",
        "summary": "Update synthetic central lab / site contact directory.",
    },
    {
        "name": "create_site_training_task",
        "tier": "GREEN",
        "summary": "Create amendment training task for a site.",
    },
    {
        "name": "reserve_sample_kits",
        "tier": "GREEN",
        "summary": "Reserve synthetic PK sample kits for a site.",
    },
    {
        "name": "create_lab_manual_change_request",
        "tier": "GREEN",
        "summary": "Draft lab-manual change request (synthetic).",
    },
    {
        "name": "create_edc_change_specification",
        "tier": "GREEN",
        "summary": "Draft EDC field specification (synthetic).",
    },
    {
        "name": "create_courier_exception_task",
        "tier": "GREEN",
        "summary": "Create courier/storage exception operational task.",
    },
    {
        "name": "create_reconsent_review",
        "tier": "AMBER",
        "summary": "Open reconsent review for fasting/ECG/consent-impacting changes.",
    },
    {
        "name": "draft_participant_transition_plan",
        "tier": "AMBER",
        "summary": "Draft PK/schedule transition plan for a participant (e.g. Phoenix P002).",
    },
    {
        "name": "request_site_activation_review",
        "tier": "AMBER",
        "summary": "Request site activation review after local approval/training.",
    },
    {
        "name": "generate_release_manifest",
        "tier": "GREEN",
        "summary": "Assemble amendment release manifest artifact.",
    },
]

POLICY_SUMMARIES: list[str] = [
    "GREEN tools auto-execute after deterministic authorization.",
    "AMBER tools require human approval; resume same invocation_id.",
    "RED tools never execute; UI approval cannot override RED.",
    "Uncited actions and unknown tool names are treated as RED.",
    "Planner never receives raw PDFs, credentials, or DB handles.",
]


def default_tier_for_tool(tool_name: str) -> RiskTier:
    if tool_name in RED_TOOLS or tool_name not in ALLOWED_ACTION_NAMES:
        return RiskTier.RED
    if tool_name in AMBER_TOOLS:
        return RiskTier.AMBER
    if tool_name in GREEN_TOOLS:
        return RiskTier.GREEN
    return RiskTier.RED
