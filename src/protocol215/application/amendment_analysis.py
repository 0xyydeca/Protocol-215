"""Amendment analysis pipeline: deterministic diff → graph → explanations."""

from __future__ import annotations

from dataclasses import dataclass, field

from protocol215.adapters.fake_explainer import FakeChangeExplainer
from protocol215.application.explanation_validation import apply_validated_explanations
from protocol215.application.impact import artifacts_for_change, build_layered_impact_graph
from protocol215.application.normalize import normalize_synonymous_changes
from protocol215.application.semantic_diff import diff_protocol_irs
from protocol215.domain.models import (
    ActionProposal,
    ImpactGraph,
    ParticipantState,
    ProtocolIR,
    RehearsalFinding,
    SemanticChange,
    SiteState,
)
from protocol215.ports import ChangeExplainer


@dataclass
class AmendmentAnalysisResult:
    old_ir: ProtocolIR
    new_ir: ProtocolIR
    raw_changes: list[SemanticChange]
    changes: list[SemanticChange]
    normalization_notes: list[str] = field(default_factory=list)
    impact_graph: ImpactGraph = field(default_factory=ImpactGraph)


class AmendmentAnalysisPipeline:
    """
    Primary semantic diff is deterministic over validated ProtocolIR objects.

    Gemini (ChangeExplainer) may only produce concise explanations after the
    impact graph exists. It must not override changes, invent evidence, remove
    safety-sensitive detections, or decide authorization.
    """

    def __init__(self, explainer: ChangeExplainer | None = None) -> None:
        self.explainer = explainer or FakeChangeExplainer()

    def analyze(
        self,
        old_ir: ProtocolIR,
        new_ir: ProtocolIR,
        *,
        sites: list[SiteState] | None = None,
        participants: list[ParticipantState] | None = None,
        findings: list[RehearsalFinding] | None = None,
        proposals: list[ActionProposal] | None = None,
        explain: bool = True,
    ) -> AmendmentAnalysisResult:
        # 1–2 load already done by caller; 3 deterministic semantic diff
        raw = diff_protocol_irs(old_ir, new_ir)

        # Normalize synonymous/duplicate concepts (record, do not hide)
        normalized, notes = normalize_synonymous_changes(raw)

        # 4–5 evidence already linked; candidate severity already assigned;
        # ensure affected artifacts populated
        enriched: list[SemanticChange] = []
        for change in normalized:
            arts = change.affected_artifact_ids or artifacts_for_change(change)
            enriched.append(change.model_copy(update={"affected_artifact_ids": arts}))

        # 6 build deterministic impact graph
        graph = build_layered_impact_graph(
            changes=enriched,
            sites=sites,
            participants=participants,
            findings=findings,
            proposals=proposals,
        )

        # 7–8 explanations only after graph; validate before attach
        final = enriched
        if explain:
            explanations = self.explainer.explain_changes(
                changes=enriched, old_ir=old_ir, new_ir=new_ir
            )
            final = apply_validated_explanations(enriched, explanations)

        return AmendmentAnalysisResult(
            old_ir=old_ir,
            new_ir=new_ir,
            raw_changes=raw,
            changes=final,
            normalization_notes=notes,
            impact_graph=graph,
        )
