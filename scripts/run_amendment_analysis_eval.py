"""Run primary AURORA fixture amendment analysis + evaluation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from protocol215.application.amendment_analysis import AmendmentAnalysisPipeline
from protocol215.application.evaluation import evaluate_changes, write_report
from protocol215.fixtures.aurora_ir import build_aurora_v1_ir, build_aurora_v2_ir
from protocol215.simulator.twin import load_participants, load_sites, rehearse_amendment


def main() -> int:
    old_ir = build_aurora_v1_ir()
    new_ir = build_aurora_v2_ir()
    sites = load_sites()
    participants = load_participants()

    # Pre-graph twin findings feed the layered graph (change→…→finding).
    # Explanations still run only after the graph is built inside the pipeline.
    pipeline = AmendmentAnalysisPipeline()
    draft = pipeline.analyze(
        old_ir,
        new_ir,
        sites=sites,
        participants=participants,
        explain=False,
    )
    findings = rehearse_amendment(
        changes=draft.changes,
        sites=sites,
        participants=participants,
    )
    result = pipeline.analyze(
        old_ir,
        new_ir,
        sites=sites,
        participants=participants,
        findings=findings,
        explain=True,
    )
    report = evaluate_changes(result.changes)

    out_dir = Path(__file__).resolve().parents[1] / "artifacts" / "eval"
    write_report(report, out_dir / "amendment_v1_to_v2_report.json")

    print("=== Five change cards ===")
    for change in result.changes:
        card = {
            "change_id": change.change_id,
            "concept_type": change.concept_type,
            "operation": change.operation.value,
            "before": change.before,
            "after": change.after,
            "old_evidence": [e.model_dump() for e in change.old_evidence],
            "new_evidence": [e.model_dump() for e in change.new_evidence],
            "candidate_risk": (change.candidate_risk or change.expected_risk_tier or "").value
            if (change.candidate_risk or change.expected_risk_tier)
            else None,
            "affected_artifact_ids": change.affected_artifact_ids,
            "explanation": change.explanation,
            "review_status": change.review_status.value,
            "normalization_notes": change.normalization_notes,
        }
        print(json.dumps(card, indent=2))
        print("---")

    print("=== Impact graph ===")
    print(f"nodes={len(result.impact_graph.nodes)} edges={len(result.impact_graph.edges)}")
    by_layer: dict[str, int] = {}
    for node in result.impact_graph.nodes:
        by_layer[node.layer.value] = by_layer.get(node.layer.value, 0) + 1
    print(f"nodes_by_layer={json.dumps(by_layer, sort_keys=True)}")

    print("=== Evaluation metrics ===")
    print(json.dumps(report["metrics"], indent=2))
    print(f"claims_perfect_score={report['claims_perfect_score']}")
    if report["mismatches"]:
        print("=== Gold mismatches ===")
        for item in report["mismatches"]:
            print(f"- {item}")
    else:
        print("=== Gold mismatches ===")
        print("(none)")

    if result.normalization_notes:
        print("=== Normalization notes ===")
        for note in result.normalization_notes:
            print(f"- {note}")

    print(f"report_written={out_dir / 'amendment_v1_to_v2_report.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
