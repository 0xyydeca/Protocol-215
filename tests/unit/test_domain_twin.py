"""Unit tests for deterministic domain, diff, impact, twin, policy, and invariants."""

from __future__ import annotations

import json

from protocol215.application.impact import PK_ADD_ARTIFACTS, build_impact_graph
from protocol215.application.invariants import (
    check_every_action_has_evidence,
    check_every_action_has_idempotency_key,
    check_no_completed_visit_changed,
    check_no_red_action_executes,
    check_no_sensitive_without_approval,
    check_no_site_activates_before_approval,
    check_no_site_activates_before_training,
    check_pk_feasibility,
    check_protocol_history_immutable,
    evaluate_all,
)
from protocol215.application.semantic_diff import diff_protocol_irs
from protocol215.domain.enums import (
    ActionStatus,
    FindingCode,
    RiskTier,
)
from protocol215.domain.models import (
    ActionExecution,
    ActionProposal,
    EvidenceReference,
    SiteState,
)
from protocol215.fixtures import GOLD_AMENDMENT
from protocol215.fixtures.aurora_ir import build_aurora_v1_ir, build_aurora_v2_ir
from protocol215.policy.matrix import (
    authorize_proposal,
    classify_change,
    classify_tool,
    is_executable,
)
from protocol215.simulator.twin import (
    add_hours_to_hhmm,
    evaluate_effective_state,
    load_participants,
    load_sites,
    rehearse_amendment,
    site_can_activate_v2,
)

GOLD_IDS = [
    "CHG-001-LAB-CONTACT",
    "CHG-002-PK-6H",
    "CHG-003-FASTING-4H",
    "CHG-004-EDC-TEMP",
    "CHG-005-CONDITIONAL-ECG",
]


def test_hand_built_irs_diff_detects_five_gold_changes() -> None:
    changes = diff_protocol_irs(build_aurora_v1_ir(), build_aurora_v2_ir())
    by_id = {c.change_id: c for c in changes}
    for gold_id in GOLD_IDS:
        assert gold_id in by_id, f"missing {gold_id}; have {sorted(by_id)}"

    gold = json.loads(GOLD_AMENDMENT.read_text(encoding="utf-8"))
    for expected in gold["changes"]:
        actual = by_id[expected["change_id"]]
        assert actual.concept_type == expected["concept_type"]
        assert actual.operation.value == expected["operation"]
        assert classify_change(actual).value == expected["expected_risk_tier"]
        assert actual.evidence, f"{actual.change_id} missing evidence"
        assert any(
            e.page == expected["expected_evidence_page"]
            and e.section_id == expected["expected_evidence_section"]
            for e in actual.evidence
        )


def test_diff_preserves_evidence_not_text_primary() -> None:
    changes = diff_protocol_irs(build_aurora_v1_ir(), build_aurora_v2_ir())
    pk = next(c for c in changes if c.change_id == "CHG-002-PK-6H")
    assert pk.evidence[0].section_id == "SEC-PK"
    assert "added_timepoint_hours" in (pk.after or {})


def test_pk_impact_connects_required_artifacts() -> None:
    changes = diff_protocol_irs(build_aurora_v1_ir(), build_aurora_v2_ir())
    graph = build_impact_graph(changes)
    artifacts = graph.artifact_types_for_change("CHG-002-PK-6H")
    assert set(PK_ADD_ARTIFACTS).issubset(artifacts)


def test_primary_scenario_findings() -> None:
    changes = diff_protocol_irs(build_aurora_v1_ir(), build_aurora_v2_ir())
    sites = load_sites()
    participants = load_participants()
    findings = rehearse_amendment(changes=changes, sites=sites, participants=participants)
    codes = {f.code for f in findings}

    required = {
        FindingCode.LAB_CONTACT_SAFE.value,
        FindingCode.EDC_SPEC_DRAFTABLE.value,
        FindingCode.BOSTON_TRAINING_REQUIRED.value,
        FindingCode.SEATTLE_APPROVAL_TRAINING_REQUIRED.value,
        FindingCode.PK_KITS_MAY_BE_REQUIRED.value,
        FindingCode.P001_DAY1_IMMUTABLE.value,
        FindingCode.P002_COURIER_STORAGE_CONFLICT.value,
        FindingCode.FASTING_REQUIRES_REVIEW.value,
        FindingCode.ECG_REQUIRES_REVIEW.value,
        FindingCode.NO_GLOBAL_ACTIVATION.value,
    }
    assert required.issubset(codes)

    p002 = next(f for f in findings if f.code == FindingCode.P002_COURIER_STORAGE_CONFLICT.value)
    assert p002.details["sample_time"] == "18:00"
    assert p002.details["courier_departure"] == "17:30"
    assert p002.details["overnight_storage"] is False


def test_phoenix_boston_seattle_blocks() -> None:
    sites = {s.site_id: s for s in load_sites()}
    assert site_can_activate_v2(sites["SITE-001"])[0] is True
    assert site_can_activate_v2(sites["SITE-002"])[0] is False
    assert "training" in site_can_activate_v2(sites["SITE-002"])[1]
    assert site_can_activate_v2(sites["SITE-003"])[0] is False
    assert "approval" in site_can_activate_v2(sites["SITE-003"])[1]


def test_p001_immutability_and_effective_state() -> None:
    participants = {p.participant_id: p for p in load_participants()}
    sites = {s.site_id: s for s in load_sites()}
    p001 = participants["P001"]
    day1 = p001.visit("Day 1")
    assert day1 is not None
    assert day1.completed is True
    assert day1.immutable is True
    state = evaluate_effective_state(sites["SITE-001"], p001)
    assert state["day1_immutable"] is True
    assert state["protocol_version_applies"] == "1.0"


def test_risk_classifications() -> None:
    changes = {
        c.change_id: c for c in diff_protocol_irs(build_aurora_v1_ir(), build_aurora_v2_ir())
    }
    assert classify_change(changes["CHG-001-LAB-CONTACT"]) == RiskTier.GREEN
    assert classify_change(changes["CHG-004-EDC-TEMP"]) == RiskTier.GREEN
    assert classify_change(changes["CHG-002-PK-6H"]) == RiskTier.AMBER
    assert classify_change(changes["CHG-003-FASTING-4H"]) == RiskTier.AMBER
    assert classify_change(changes["CHG-005-CONDITIONAL-ECG"]) == RiskTier.AMBER
    assert classify_tool("update_contact_directory") == RiskTier.GREEN
    assert classify_tool("request_site_activation_review") == RiskTier.AMBER
    assert classify_tool("modify_completed_visit") == RiskTier.RED
    assert classify_tool("unknown_tool_xyz") == RiskTier.RED


def test_red_never_executable_even_if_approved() -> None:
    proposal = ActionProposal(
        proposal_id="p-red",
        tool_name="modify_completed_visit",
        rationale="alter P001",
        evidence=[EvidenceReference(page=8, section_id="SEC-DAY1")],
        idempotency_key="red-1",
    )
    tier = authorize_proposal(proposal)
    assert tier == RiskTier.RED
    assert is_executable(tier, approved=True) is False
    assert is_executable(RiskTier.AMBER, approved=False) is False
    assert is_executable(RiskTier.AMBER, approved=True) is True
    assert is_executable(RiskTier.GREEN, approved=False) is True


def test_uncited_action_is_red() -> None:
    proposal = ActionProposal(
        proposal_id="p-uncited",
        tool_name="update_contact_directory",
        rationale="no evidence",
        evidence=[],
        idempotency_key="u-1",
    )
    assert authorize_proposal(proposal) == RiskTier.RED


def test_invariants_pass_and_fail_cases() -> None:
    sites = load_sites()
    participants = load_participants()
    evidence = [EvidenceReference(page=10, section_id="SEC-LAB-CONTACT")]

    ok_actions = [
        ActionExecution(
            execution_id="e1",
            proposal_id="p1",
            tool_name="update_contact_directory",
            status=ActionStatus.EXECUTED,
            authorized_tier=RiskTier.GREEN,
            evidence=evidence,
            idempotency_key="idem-1",
            executed=True,
        )
    ]
    passed = evaluate_all(sites=sites, participants=participants, actions=ok_actions)
    assert all(r.passed for r in passed if r.invariant_id != "INV-PK-FEASIBILITY")

    bad_site = sites[2].model_copy(update={"v2_activated": True})
    assert check_no_site_activates_before_approval([bad_site]).passed is False
    assert (
        check_no_site_activates_before_training(
            [sites[1].model_copy(update={"v2_activated": True})]
        ).passed
        is False
    )

    assert (
        check_no_completed_visit_changed(
            participants, attempted_modifications=[("P001", "Day 1")]
        ).passed
        is False
    )
    assert (
        check_no_completed_visit_changed(
            participants, attempted_modifications=[("P002", "Day 1")]
        ).passed
        is True
    )

    amber_unapproved = ActionExecution(
        execution_id="e2",
        proposal_id="p2",
        tool_name="update_fasting_requirement",
        status=ActionStatus.EXECUTED,
        authorized_tier=RiskTier.AMBER,
        evidence=evidence,
        idempotency_key="idem-2",
        approved=False,
        executed=True,
    )
    assert check_no_sensitive_without_approval([amber_unapproved]).passed is False

    no_evidence = ok_actions[0].model_copy(update={"evidence": [], "execution_id": "e3"})
    assert check_every_action_has_evidence([no_evidence]).passed is False

    no_key = ok_actions[0].model_copy(update={"idempotency_key": "", "execution_id": "e4"})
    assert check_every_action_has_idempotency_key([no_key]).passed is False

    red_exec = ActionExecution(
        execution_id="e5",
        proposal_id="p5",
        tool_name="modify_completed_visit",
        status=ActionStatus.EXECUTED,
        authorized_tier=RiskTier.RED,
        evidence=evidence,
        idempotency_key="idem-5",
        approved=True,
        executed=True,
    )
    assert check_no_red_action_executes([red_exec]).passed is False

    assert (
        check_pk_feasibility(
            sample_local_time="18:00",
            courier_departure_local_time="17:30",
            overnight_storage_available=False,
        ).passed
        is False
    )
    assert (
        check_pk_feasibility(
            sample_local_time="18:00",
            courier_departure_local_time="20:00",
            overnight_storage_available=False,
        ).passed
        is True
    )
    assert check_protocol_history_immutable(historical_versions=["1.0"]).passed is True
    assert (
        check_protocol_history_immutable(
            historical_versions=["1.0"], attempted_rewrite="1.0"
        ).passed
        is False
    )


def test_add_hours_helper() -> None:
    assert add_hours_to_hhmm("12:00", 6.0) == "18:00"


def test_site_state_model_roundtrip() -> None:
    site = load_sites()[0]
    assert isinstance(site, SiteState)
    assert site.city == "Phoenix"
