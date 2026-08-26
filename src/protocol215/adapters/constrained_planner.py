"""Constrained action planner — allowlisted tools only; never sees PDFs."""

from __future__ import annotations

from typing import Any

from protocol215.domain.enums import FindingCode, RiskTier
from protocol215.domain.models import (
    ActionProposal,
    EvidenceReference,
    ImpactGraph,
    RehearsalFinding,
    SemanticChange,
    WorkflowRun,
)
from protocol215.tools.registry import (
    ACTION_DEFINITIONS,
    ALLOWED_ACTION_NAMES,
    POLICY_SUMMARIES,
)


class ConstrainedActionPlanner:
    """
    Produces ActionProposals from validated changes + findings only.

    Input surface (Gemini or fake):
      - schema-validated semantic changes
      - deterministic impact graph
      - deterministic rehearsal findings
      - allowed action definitions
      - applicable policy summaries

    Never receives: raw PDFs, injection text, credentials, DB handles.
    Cannot invent tool names outside ALLOWED_ACTION_NAMES.
    """

    def __init__(self, *, include_amber: bool = True, include_red_bait: bool = False) -> None:
        self.include_amber = include_amber
        self.include_red_bait = include_red_bait

    def planner_context(
        self,
        *,
        changes: list[SemanticChange],
        findings: list[RehearsalFinding],
        impact_graph: ImpactGraph | None = None,
    ) -> dict[str, Any]:
        """Payload a Gemini planner is allowed to see."""
        return {
            "semantic_changes": [c.model_dump(mode="json") for c in changes],
            "findings": [f.model_dump(mode="json") for f in findings],
            "impact_graph": impact_graph.model_dump(mode="json") if impact_graph else None,
            "allowed_actions": ACTION_DEFINITIONS,
            "policy_summaries": POLICY_SUMMARIES,
            # Explicit denials for the model prompt
            "forbidden": [
                "raw_pdf_bytes",
                "credentials",
                "database_handles",
                "unrestricted_system_access",
            ],
        }

    def propose(
        self,
        *,
        run: WorkflowRun,
        changes: list[SemanticChange],
        findings: list[RehearsalFinding],
        impact_graph: ImpactGraph | None = None,
    ) -> list[ActionProposal]:
        _ = self.planner_context(changes=changes, findings=findings, impact_graph=impact_graph)
        proposals: list[ActionProposal] = []
        by_concept = {c.concept_type: c for c in changes}
        finding_by_code = {f.code: f for f in findings}

        def add(p: ActionProposal) -> None:
            if p.tool_name not in ALLOWED_ACTION_NAMES:
                return  # hard filter — never invent
            p.args = {**p.args, "run_id": run.run_id}
            proposals.append(p)

        if "central_lab_contact" in by_concept:
            c = by_concept["central_lab_contact"]
            add(
                ActionProposal(
                    proposal_id=f"{run.run_id}-prop-lab",
                    tool_name="update_contact_directory",
                    change_ids=[c.change_id],
                    rationale="Update synthetic central lab contact",
                    evidence=list(c.evidence) or list(c.new_evidence),
                    args={
                        "role": "central_lab",
                        "email": (c.after or {}).get("email")
                        or (c.after or {}).get("role")
                        or "lab-v2@example.test",
                    },
                    proposed_tier=RiskTier.GREEN,
                )
            )
            add(
                ActionProposal(
                    proposal_id=f"{run.run_id}-prop-lab-manual",
                    tool_name="create_lab_manual_change_request",
                    change_ids=[c.change_id],
                    rationale="Draft lab manual contact update",
                    evidence=list(c.evidence) or list(c.new_evidence),
                    args={"change_summary": "Central lab email update for AURORA v2"},
                    proposed_tier=RiskTier.GREEN,
                )
            )

        if "edc_field" in by_concept:
            c = by_concept["edc_field"]
            add(
                ActionProposal(
                    proposal_id=f"{run.run_id}-prop-edc",
                    tool_name="create_edc_change_specification",
                    change_ids=[c.change_id],
                    rationale="Draft EDC field specification",
                    evidence=list(c.evidence)
                    or list(c.new_evidence)
                    or [EvidenceReference(page=12, section_id="SEC-DATA")],
                    args={
                        "field_name": (c.after or {}).get("field")
                        or "sample_processing_temperature_c",
                        "unit": (c.after or {}).get("unit"),
                    },
                    proposed_tier=RiskTier.GREEN,
                )
            )

        if FindingCode.BOSTON_TRAINING_REQUIRED.value in finding_by_code or any(
            "BOSTON" in f.code for f in findings
        ):
            add(
                ActionProposal(
                    proposal_id=f"{run.run_id}-prop-bos-train",
                    tool_name="create_site_training_task",
                    site_id="SITE-002",
                    change_ids=[c.change_id for c in changes],
                    rationale="Boston amendment training incomplete",
                    evidence=[EvidenceReference(page=11, section_id="SEC-SITE")],
                    args={"site_id": "SITE-002", "training_topic": "AURORA-101 amendment v2"},
                    proposed_tier=RiskTier.GREEN,
                )
            )

        if (
            FindingCode.PK_KITS_MAY_BE_REQUIRED.value in finding_by_code
            or "pk_timepoint" in by_concept
        ):
            site_id = "SITE-001"
            pk = by_concept.get("pk_timepoint")
            add(
                ActionProposal(
                    proposal_id=f"{run.run_id}-prop-kits",
                    tool_name="reserve_sample_kits",
                    site_id=site_id,
                    change_ids=[pk.change_id] if pk else [c.change_id for c in changes],
                    rationale="Reserve synthetic PK kits for 6h timepoint",
                    evidence=(list(pk.evidence) if pk else [])
                    or [EvidenceReference(page=8, section_id="SEC-PK")],
                    args={"site_id": site_id, "kit_type": "pk_6h", "quantity": 1},
                    proposed_tier=RiskTier.GREEN,
                )
            )

        # Phoenix courier conflict → GREEN exception task (auto) + AMBER transition plan
        p002 = finding_by_code.get(FindingCode.P002_COURIER_STORAGE_CONFLICT.value)
        if p002 is not None:
            add(
                ActionProposal(
                    proposal_id=f"{run.run_id}-prop-courier",
                    tool_name="create_courier_exception_task",
                    site_id=p002.site_id or "SITE-001",
                    participant_id=p002.participant_id or "P002",
                    change_ids=list(p002.change_ids),
                    rationale="Open courier/storage exception task for Phoenix P002",
                    evidence=[EvidenceReference(page=8, section_id="SEC-PK")],
                    args={
                        "site_id": p002.site_id or "SITE-001",
                        "participant_id": p002.participant_id or "P002",
                        "conflict_summary": p002.summary,
                    },
                    proposed_tier=RiskTier.GREEN,
                )
            )
            if self.include_amber:
                add(
                    ActionProposal(
                        proposal_id=f"{run.run_id}-prop-p002-transition",
                        tool_name="draft_participant_transition_plan",
                        site_id=p002.site_id or "SITE-001",
                        participant_id=p002.participant_id or "P002",
                        change_ids=list(p002.change_ids),
                        rationale="Phoenix P002 PK schedule transition requires approval",
                        evidence=[EvidenceReference(page=8, section_id="SEC-PK")],
                        args={
                            "site_id": p002.site_id or "SITE-001",
                            "participant_id": p002.participant_id or "P002",
                            "transition_summary": p002.summary,
                            "proposed_schedule": dict(p002.details or {}),
                        },
                        proposed_tier=RiskTier.AMBER,
                    )
                )

        if self.include_amber:
            if (
                "post_dose_fasting" in by_concept
                or FindingCode.FASTING_REQUIRES_REVIEW.value in finding_by_code
            ):
                fasting: SemanticChange | None = by_concept.get("post_dose_fasting")
                add(
                    ActionProposal(
                        proposal_id=f"{run.run_id}-prop-reconsent-fast",
                        tool_name="create_reconsent_review",
                        participant_id="P002",
                        change_ids=[fasting.change_id] if fasting else [],
                        rationale="Fasting change requires reconsent review",
                        evidence=(list(fasting.evidence) if fasting else [])
                        or [EvidenceReference(page=8, section_id="SEC-FASTING")],
                        args={
                            "participant_id": "P002",
                            "reason": "post-dose fasting extended",
                        },
                        proposed_tier=RiskTier.AMBER,
                    )
                )
            if (
                "conditional_repeat_ecg" in by_concept
                or FindingCode.ECG_REQUIRES_REVIEW.value in finding_by_code
            ):
                ecg: SemanticChange | None = by_concept.get("conditional_repeat_ecg")
                add(
                    ActionProposal(
                        proposal_id=f"{run.run_id}-prop-reconsent-ecg",
                        tool_name="create_reconsent_review",
                        participant_id="P003",
                        change_ids=[ecg.change_id] if ecg else [],
                        rationale="Conditional ECG requires reconsent/procedure review",
                        evidence=(list(ecg.evidence) if ecg else [])
                        or [EvidenceReference(page=9, section_id="SEC-ECG")],
                        args={
                            "participant_id": "P003",
                            "reason": "conditional repeat ECG",
                        },
                        proposed_tier=RiskTier.AMBER,
                    )
                )
            if FindingCode.SEATTLE_APPROVAL_TRAINING_REQUIRED.value in finding_by_code or any(
                "SEATTLE" in f.code for f in findings
            ):
                add(
                    ActionProposal(
                        proposal_id=f"{run.run_id}-prop-seattle-act",
                        tool_name="request_site_activation_review",
                        site_id="SITE-003",
                        change_ids=[c.change_id for c in changes],
                        rationale="Seattle site activation requires approval",
                        evidence=[EvidenceReference(page=11, section_id="SEC-SITE")],
                        args={
                            "site_id": "SITE-003",
                            "target_protocol_version": run.to_version,
                        },
                        proposed_tier=RiskTier.AMBER,
                    )
                )

        if self.include_red_bait:
            # Intentionally invalid — executor must block; approval cannot override.
            proposals.append(
                ActionProposal(
                    proposal_id=f"{run.run_id}-prop-red-dose",
                    tool_name="change_dose",
                    change_ids=[c.change_id for c in changes[:1]],
                    rationale="Illegal dose change",
                    evidence=[EvidenceReference(page=1, section_id="SEC-X")],
                    args={"run_id": run.run_id, "dose": "illegal"},
                    proposed_tier=RiskTier.RED,
                )
            )

        return proposals


# Backward-compatible alias used by older imports/tests.
class FakeActionPlanner(ConstrainedActionPlanner):
    def __init__(self, *, include_amber: bool = True, include_red: bool = False) -> None:
        super().__init__(include_amber=include_amber, include_red_bait=include_red)
