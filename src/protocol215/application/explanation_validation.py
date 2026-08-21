"""Validate Gemini change explanations before storage."""

from __future__ import annotations

from protocol215.domain.enums import ReviewStatus
from protocol215.domain.models import SemanticChange

FORBIDDEN_PHRASES = (
    "authorized",
    "authorization granted",
    "approved for execution",
    "no evidence needed",
    "ignore prior",
)


def validate_explanation(change: SemanticChange, explanation: str) -> tuple[bool, str]:
    text = (explanation or "").strip()
    if not text:
        return False, "empty explanation"
    if len(text) > 800:
        return False, "explanation too long"
    lower = text.lower()
    for phrase in FORBIDDEN_PHRASES:
        if phrase in lower:
            return False, f"forbidden phrase: {phrase}"
    # Must not invent page numbers that contradict attached evidence.
    pages = {e.page for e in [*change.old_evidence, *change.new_evidence, *change.evidence]}
    if pages:
        # Soft check: if explanation cites "page N" it must be in evidence set.
        import re

        cited = {int(m) for m in re.findall(r"page\s+(\d+)", lower)}
        invented = cited - pages
        if invented:
            return False, f"invented evidence pages: {sorted(invented)}"
    return True, "ok"


def apply_validated_explanations(
    changes: list[SemanticChange],
    explanations: dict[str, str],
) -> list[SemanticChange]:
    """Attach explanations; never override risk, evidence, or operation."""
    out: list[SemanticChange] = []
    for change in changes:
        text = explanations.get(change.change_id, "")
        ok, reason = validate_explanation(change, text)
        if ok:
            out.append(change.model_copy(update={"explanation": text.strip()}))
        else:
            out.append(
                change.model_copy(
                    update={
                        "explanation": "",
                        "review_status": ReviewStatus.NEEDS_REVIEW,
                        "normalization_notes": [
                            *change.normalization_notes,
                            f"explanation rejected: {reason}",
                        ],
                    }
                )
            )
    return out
