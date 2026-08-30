"""Tests for amendment analysis pipeline and evaluation."""

from __future__ import annotations

from protocol215.application.amendment_analysis import AmendmentAnalysisPipeline
from protocol215.application.evaluation import evaluate_changes
from protocol215.application.normalize import normalize_synonymous_changes
from protocol215.application.semantic_diff import diff_protocol_irs
from protocol215.domain.enums import ImpactLayer
from protocol215.fixtures.aurora_ir import build_aurora_v1_ir, build_aurora_v2_ir
from protocol215.simulator.twin import load_participants, load_sites

GOLD_IDS = {
    "CHG-001-LAB-CONTACT",
    "CHG-002-PK-6H",
    "CHG-003-FASTING-4H",
    "CHG-004-EDC-TEMP",
    "CHG-005-CONDITIONAL-ECG",
}


def test_primary_fixture_yields_exactly_five_changes() -> None:
    result = AmendmentAnalysisPipeline().analyze(
        build_aurora_v1_ir(),
        build_aurora_v2_ir(),
        sites=load_sites(),
        participants=load_participants(),
    )
    assert {c.change_id for c in result.changes} == GOLD_IDS
    assert len(result.changes) == 5
    assert all(c.explanation for c in result.changes)
    assert all(c.candidate_risk is not None for c in result.changes)
    assert all(c.affected_artifact_ids for c in result.changes)


def test_normalization_absorbs_activity_synonyms() -> None:
    raw = diff_protocol_irs(build_aurora_v1_ir(), build_aurora_v2_ir())
    assert any(c.change_id.startswith("CHG-ACT-ADD-") for c in raw)
    normalized, notes = normalize_synonymous_changes(raw)
    assert {c.change_id for c in normalized} == GOLD_IDS
    assert any("Normalized" in n for n in notes)


def test_gemini_noisy_fasting_restriction_collapses_to_gold_five() -> None:
    """Live Gemini often emits fasting as participant_restriction plus spurious activity ADDs."""
    from protocol215.application.semantic_diff import _canonicalize_aurora_change_ids
    from protocol215.domain.enums import ChangeOperation, RiskTier
    from protocol215.domain.models import SemanticChange

    noisy = [
        SemanticChange(
            change_id="CHG-001-LAB-CONTACT",
            concept_type="central_lab_contact",
            operation=ChangeOperation.UPDATE,
            before={"email": "a"},
            after={"email": "b"},
            candidate_risk=RiskTier.GREEN,
        ),
        SemanticChange(
            change_id="CHG-002-PK-6H",
            concept_type="pk_timepoint",
            operation=ChangeOperation.ADD,
            before=None,
            after={"added_timepoint_hours": 6.0},
            candidate_risk=RiskTier.AMBER,
        ),
        SemanticChange(
            change_id="CHG-REST-ADD-REST-FASTING",
            concept_type="participant_restriction",
            operation=ChangeOperation.ADD,
            before=None,
            after={"kind": "fasting", "unit": "hours", "value": 4},
            candidate_risk=RiskTier.AMBER,
        ),
        SemanticChange(
            change_id="CHG-004-EDC-TEMP",
            concept_type="edc_field",
            operation=ChangeOperation.ADD,
            before=None,
            after={"field": "sample_processing_temperature_c"},
            candidate_risk=RiskTier.AMBER,
        ),
        SemanticChange(
            change_id="CHG-005-CONDITIONAL-ECG",
            concept_type="conditional_repeat_ecg",
            operation=ChangeOperation.UPDATE,
            before={"conditional_repeat_required": False},
            after={"conditional_repeat_required": True},
            candidate_risk=RiskTier.AMBER,
        ),
        SemanticChange(
            change_id="CHG-ACT-ADD-ACT-VS-D1",
            concept_type="scheduled_activity",
            operation=ChangeOperation.ADD,
            before=None,
            after={"name": "Vital signs"},
            candidate_risk=RiskTier.GREEN,
        ),
    ]
    remapped = _canonicalize_aurora_change_ids(noisy)
    assert any(c.change_id == "CHG-003-FASTING-4H" for c in remapped)
    normalized, notes = normalize_synonymous_changes(remapped)
    assert {c.change_id for c in normalized} == GOLD_IDS
    assert len(normalized) == 5
    assert any("Excluded from primary card set" in n for n in notes)


def test_layered_impact_graph_is_deterministic() -> None:
    pipeline = AmendmentAnalysisPipeline()
    a = pipeline.analyze(
        build_aurora_v1_ir(),
        build_aurora_v2_ir(),
        sites=load_sites(),
        participants=load_participants(),
    )
    b = pipeline.analyze(
        build_aurora_v1_ir(),
        build_aurora_v2_ir(),
        sites=load_sites(),
        participants=load_participants(),
    )
    assert a.impact_graph.model_dump() == b.impact_graph.model_dump()
    layers = {n.layer for n in a.impact_graph.nodes}
    assert ImpactLayer.PROTOCOL_CHANGE in layers
    assert ImpactLayer.OPERATIONAL_ARTIFACT in layers
    assert ImpactLayer.SITE in layers
    assert ImpactLayer.PARTICIPANT in layers
    assert len(a.impact_graph.nodes) > 0
    assert len(a.impact_graph.edges) > 0


def test_evaluation_report_metrics_present() -> None:
    result = AmendmentAnalysisPipeline().analyze(
        build_aurora_v1_ir(),
        build_aurora_v2_ir(),
    )
    report = evaluate_changes(result.changes)
    metrics = report["metrics"]
    assert metrics["exact_match_change_recall"] == 1.0
    assert metrics["unsupported_change_count"] == 0
    assert metrics["evidence_page_accuracy"] == 1.0
    assert "affected_artifact_recall" in metrics
    # Do not hard-assert 100% overall unless report says so.
    assert "claims_perfect_score" in report
