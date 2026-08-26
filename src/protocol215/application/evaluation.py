"""Machine-readable evaluation of amendment semantic extraction."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from protocol215.application.impact import GOLD_ARTIFACT_ALIASES
from protocol215.domain.models import SemanticChange

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_GOLD = ROOT / "fixtures" / "gold" / "amendment_v1_to_v2_expected.json"


def load_gold(path: Path | None = None) -> dict[str, Any]:
    gold_path = path or DEFAULT_GOLD
    return cast(dict[str, Any], json.loads(gold_path.read_text(encoding="utf-8")))


def _normalize_artifact(name: str) -> str:
    return GOLD_ARTIFACT_ALIASES.get(name, name)


def evaluate_changes(
    predicted: list[SemanticChange],
    gold: dict[str, Any] | None = None,
) -> dict[str, Any]:
    gold = gold or load_gold()
    gold_changes = gold["changes"]
    gold_by_id = {c["change_id"]: c for c in gold_changes}
    pred_by_id = {c.change_id: c for c in predicted}

    gold_ids = set(gold_by_id)
    pred_ids = set(pred_by_id)

    # Exact-match change recall: predicted gold IDs / gold IDs
    matched_ids = gold_ids & pred_ids
    if gold_ids:
        exact_match_change_recall = len(matched_ids) / len(gold_ids)
    else:
        # Vacuous recall: empty gold is perfect only when predictions are also empty.
        exact_match_change_recall = 1.0 if not pred_ids else 0.0

    # Concept-level precision: among predicted, share whose concept_type matches a gold change
    gold_concepts = {c["concept_type"] for c in gold_changes}
    concept_true_pos = sum(1 for c in predicted if c.concept_type in gold_concepts)
    concept_level_precision = concept_true_pos / len(predicted) if predicted else 0.0

    # Evidence-page accuracy: among matched IDs, page matches expected
    evidence_ok = 0
    evidence_checked = 0
    evidence_details: list[dict[str, Any]] = []
    for cid in sorted(matched_ids):
        g = gold_by_id[cid]
        p = pred_by_id[cid]
        expected_page = g.get("expected_evidence_page")
        if expected_page is None:
            continue
        evidence_checked += 1
        pages = {
            e.page for e in [*p.old_evidence, *p.new_evidence, *p.evidence] if e.page is not None
        }
        ok = expected_page in pages
        if ok:
            evidence_ok += 1
        evidence_details.append(
            {
                "change_id": cid,
                "expected_page": expected_page,
                "predicted_pages": sorted(pages),
                "match": ok,
            }
        )
    evidence_page_accuracy = evidence_ok / evidence_checked if evidence_checked else 0.0

    # Unsupported-change count: predicted without matching gold id
    unsupported = sorted(pred_ids - gold_ids)
    unsupported_change_count = len(unsupported)

    # Affected-artifact recall: for matched changes, gold artifacts covered (with alias map)
    artifact_hits = 0
    artifact_total = 0
    artifact_details: list[dict[str, Any]] = []
    for cid in sorted(matched_ids):
        g = gold_by_id[cid]
        p = pred_by_id[cid]
        expected = {_normalize_artifact(a) for a in g.get("expected_affected_artifacts", [])}
        predicted_arts = {_normalize_artifact(a) for a in p.affected_artifact_ids}
        # Also accept graph-style names already normalized
        artifact_total += len(expected)
        hits = expected & predicted_arts
        artifact_hits += len(hits)
        artifact_details.append(
            {
                "change_id": cid,
                "expected": sorted(expected),
                "predicted": sorted(predicted_arts),
                "hits": sorted(hits),
                "misses": sorted(expected - predicted_arts),
            }
        )
    affected_artifact_recall = artifact_hits / artifact_total if artifact_total else 0.0

    mismatches: list[str] = []
    for cid in sorted(gold_ids - pred_ids):
        mismatches.append(f"missing gold change: {cid}")
    for cid in unsupported:
        mismatches.append(f"unsupported predicted change: {cid}")
    for detail in evidence_details:
        if not detail["match"]:
            mismatches.append(
                f"evidence page mismatch {detail['change_id']}: "
                f"expected {detail['expected_page']} got {detail['predicted_pages']}"
            )
    for detail in artifact_details:
        if detail["misses"]:
            mismatches.append(f"artifact misses {detail['change_id']}: {detail['misses']}")

    report = {
        "study_id": gold.get("study_id"),
        "from_version": gold.get("from_version"),
        "to_version": gold.get("to_version"),
        "metrics": {
            "exact_match_change_recall": round(exact_match_change_recall, 4),
            "concept_level_precision": round(concept_level_precision, 4),
            "evidence_page_accuracy": round(evidence_page_accuracy, 4),
            "unsupported_change_count": unsupported_change_count,
            "affected_artifact_recall": round(affected_artifact_recall, 4),
            "predicted_change_count": len(predicted),
            "gold_change_count": len(gold_changes),
        },
        "matched_change_ids": sorted(matched_ids),
        "unsupported_change_ids": unsupported,
        "missing_change_ids": sorted(gold_ids - pred_ids),
        "evidence_details": evidence_details,
        "artifact_details": artifact_details,
        "mismatches": mismatches,
        "claims_perfect_score": False,
    }
    # Only set true when all metrics are perfect — never claim until proven.
    m = cast(dict[str, Any], report["metrics"])
    report["claims_perfect_score"] = (
        m["exact_match_change_recall"] == 1.0
        and m["concept_level_precision"] == 1.0
        and m["evidence_page_accuracy"] == 1.0
        and m["unsupported_change_count"] == 0
        and m["affected_artifact_recall"] == 1.0
        and m["predicted_change_count"] == m["gold_change_count"]
    )
    return report


def write_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
