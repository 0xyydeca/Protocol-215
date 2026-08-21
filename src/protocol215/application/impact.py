"""Deterministic layered impact graph builder.

Layers (fixed order, not force-directed):
  protocol_change → operational_artifact → site → participant → finding → proposed_action
"""

from __future__ import annotations

from protocol215.domain.enums import ChangeOperation, ImpactLayer
from protocol215.domain.models import (
    ActionProposal,
    ImpactEdge,
    ImpactGraph,
    ImpactNode,
    ParticipantState,
    RehearsalFinding,
    SemanticChange,
    SiteState,
)

# Artifacts required by Prompt 3 for an added PK sample.
PK_ADD_ARTIFACTS: tuple[str, ...] = (
    "schedule_of_activities",
    "consent_review",
    "site_training",
    "pk_sample_kits",
    "sample_labels",
    "laboratory_manual",
    "edc_pk_form",
    "edit_checks",
    "processing_instructions",
    "storage_capability",
    "courier_schedule",
    "participant_burden",
    "bioanalytical_transfer_specification",
)

# Gold-fixture artifact names → operational equivalents used by the graph.
GOLD_ARTIFACT_ALIASES: dict[str, str] = {
    "pk_kit_inventory": "pk_sample_kits",
    "courier_plan": "courier_schedule",
    "sample_storage": "storage_capability",
    "participant_visit_calendar": "participant_burden",
    "edc_pk_forms": "edc_pk_form",
    "site_data-entry_guide": "site_data_entry_guide",
}

CONCEPT_ARTIFACTS: dict[str, tuple[str, ...]] = {
    "central_lab_contact": (
        "contact_directory",
        "lab_manual",
        "site_shipping_instructions",
    ),
    "pk_timepoint": PK_ADD_ARTIFACTS,
    "post_dose_fasting": (
        "schedule_of_activities",
        "site_meal_instructions",
        "participant_instructions",
        "visit_nursing_checklist",
        "consent_review",
    ),
    "edc_field": (
        "edc_specification",
        "lab_manual_change_request",
        "site_data_entry_guide",
    ),
    "conditional_repeat_ecg": (
        "schedule_of_activities",
        "ecg_procedure",
        "site_training",
        "edc_ecg_forms",
        "consent_review",
    ),
}


def artifacts_for_change(change: SemanticChange) -> list[str]:
    artifacts = list(CONCEPT_ARTIFACTS.get(change.concept_type, ()))
    if change.concept_type == "pk_timepoint" and change.operation == ChangeOperation.ADD:
        artifacts = list(PK_ADD_ARTIFACTS)
    seen: set[str] = set()
    ordered: list[str] = []
    for item in artifacts:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def build_impact_graph(changes: list[SemanticChange]) -> ImpactGraph:
    """Backward-compatible artifact-only graph (change → artifacts). """
    return build_layered_impact_graph(changes=changes)


def build_layered_impact_graph(
    *,
    changes: list[SemanticChange],
    sites: list[SiteState] | None = None,
    participants: list[ParticipantState] | None = None,
    findings: list[RehearsalFinding] | None = None,
    proposals: list[ActionProposal] | None = None,
) -> ImpactGraph:
    nodes: dict[str, ImpactNode] = {}
    edges: list[ImpactEdge] = []
    edge_ids: set[str] = set()
    sites = sites or []
    participants = participants or []
    findings = findings or []
    proposals = proposals or []

    def ensure(node: ImpactNode) -> ImpactNode:
        if node.node_id not in nodes:
            nodes[node.node_id] = node
        return nodes[node.node_id]

    def add_edge(edge: ImpactEdge) -> None:
        if edge.edge_id in edge_ids:
            return
        edge_ids.add(edge.edge_id)
        edges.append(edge)

    for change in sorted(changes, key=lambda c: c.change_id):
        change_node = ensure(
            ImpactNode(
                node_id=f"change:{change.change_id}",
                artifact_type="semantic_change",
                label=change.change_id,
                layer=ImpactLayer.PROTOCOL_CHANGE,
                ref_id=change.change_id,
            )
        )
        artifact_ids = change.affected_artifact_ids or artifacts_for_change(change)
        art_nodes: list[ImpactNode] = []
        for artifact in artifact_ids:
            art_node = ensure(
                ImpactNode(
                    node_id=f"artifact:{artifact}",
                    artifact_type=artifact,
                    label=artifact.replace("_", " "),
                    layer=ImpactLayer.OPERATIONAL_ARTIFACT,
                    ref_id=artifact,
                )
            )
            art_nodes.append(art_node)
            add_edge(
                ImpactEdge(
                    edge_id=f"{change.change_id}->artifact:{artifact}",
                    change_id=change.change_id,
                    from_node_id=change_node.node_id,
                    to_node_id=art_node.node_id,
                    relationship="affects_artifact",
                )
            )

        # Layer: operational artifact → site (use first artifact as parent when present).
        parent_for_sites = art_nodes[0].node_id if art_nodes else change_node.node_id
        for site in sorted(sites, key=lambda s: s.site_id):
            site_node = ensure(
                ImpactNode(
                    node_id=f"site:{site.site_id}",
                    artifact_type="site",
                    label=site.name,
                    layer=ImpactLayer.SITE,
                    ref_id=site.site_id,
                )
            )
            add_edge(
                ImpactEdge(
                    edge_id=f"{change.change_id}->site:{site.site_id}",
                    change_id=change.change_id,
                    from_node_id=parent_for_sites,
                    to_node_id=site_node.node_id,
                    relationship="affects_site",
                )
            )
            for participant in sorted(
                (p for p in participants if p.site_id == site.site_id),
                key=lambda p: p.participant_id,
            ):
                p_node = ensure(
                    ImpactNode(
                        node_id=f"participant:{participant.participant_id}",
                        artifact_type="participant",
                        label=participant.participant_id,
                        layer=ImpactLayer.PARTICIPANT,
                        ref_id=participant.participant_id,
                    )
                )
                add_edge(
                    ImpactEdge(
                        edge_id=f"{change.change_id}:site:{site.site_id}->participant:{participant.participant_id}",
                        change_id=change.change_id,
                        from_node_id=site_node.node_id,
                        to_node_id=p_node.node_id,
                        relationship="affects_participant",
                    )
                )

        for finding in sorted(findings, key=lambda f: f.finding_id):
            if change.change_id not in finding.change_ids:
                continue
            f_node = ensure(
                ImpactNode(
                    node_id=f"finding:{finding.finding_id}",
                    artifact_type="finding",
                    label=finding.summary,
                    layer=ImpactLayer.FINDING,
                    ref_id=finding.finding_id,
                )
            )
            from_id = change_node.node_id
            if finding.participant_id and f"participant:{finding.participant_id}" in nodes:
                from_id = f"participant:{finding.participant_id}"
            elif finding.site_id and f"site:{finding.site_id}" in nodes:
                from_id = f"site:{finding.site_id}"
            add_edge(
                ImpactEdge(
                    edge_id=f"{change.change_id}->finding:{finding.finding_id}",
                    change_id=change.change_id,
                    from_node_id=from_id,
                    to_node_id=f_node.node_id,
                    relationship="produces_finding",
                )
            )

        for proposal in sorted(proposals, key=lambda p: p.proposal_id):
            if change.change_id not in proposal.change_ids:
                continue
            a_node = ensure(
                ImpactNode(
                    node_id=f"action:{proposal.proposal_id}",
                    artifact_type=proposal.tool_name,
                    label=proposal.tool_name,
                    layer=ImpactLayer.PROPOSED_ACTION,
                    ref_id=proposal.proposal_id,
                )
            )
            # Prefer finding → action when a finding for this change exists.
            finding_for_change = [
                f for f in findings if change.change_id in f.change_ids
            ]
            if finding_for_change:
                fid = sorted(finding_for_change, key=lambda f: f.finding_id)[0].finding_id
                add_edge(
                    ImpactEdge(
                        edge_id=f"finding:{fid}->action:{proposal.proposal_id}",
                        change_id=change.change_id,
                        from_node_id=f"finding:{fid}",
                        to_node_id=a_node.node_id,
                        relationship="proposes_action",
                    )
                )
            else:
                add_edge(
                    ImpactEdge(
                        edge_id=f"{change.change_id}->action:{proposal.proposal_id}",
                        change_id=change.change_id,
                        from_node_id=change_node.node_id,
                        to_node_id=a_node.node_id,
                        relationship="proposes_action",
                    )
                )

    ordered_nodes = sorted(nodes.values(), key=lambda n: (n.layer.value, n.node_id))
    ordered_edges = sorted(edges, key=lambda e: e.edge_id)
    return ImpactGraph(nodes=ordered_nodes, edges=ordered_edges)
