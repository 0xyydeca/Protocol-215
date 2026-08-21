"""Fake change explainer for CI — deterministic templates, no Gemini."""

from __future__ import annotations

from protocol215.domain.models import ProtocolIR, SemanticChange


class FakeChangeExplainer:
    def explain_changes(
        self,
        *,
        changes: list[SemanticChange],
        old_ir: ProtocolIR,
        new_ir: ProtocolIR,
    ) -> dict[str, str]:
        _ = old_ir, new_ir
        out: dict[str, str] = {}
        for change in changes:
            before = change.before or {}
            after = change.after or {}
            if change.change_id == "CHG-001-LAB-CONTACT":
                out[change.change_id] = (
                    f"Central lab contact updated from {before.get('email')} "
                    f"to {after.get('email')}."
                )
            elif change.change_id == "CHG-002-PK-6H":
                out[change.change_id] = (
                    "A 6-hour post-dose PK sample timepoint was added to the Day 1 schedule."
                )
            elif change.change_id == "CHG-003-FASTING-4H":
                out[change.change_id] = (
                    f"Post-dose fasting extended from {before.get('hours')}h "
                    f"to {after.get('hours')}h."
                )
            elif change.change_id == "CHG-004-EDC-TEMP":
                out[change.change_id] = (
                    "EDC field sample_processing_temperature_c was added for lab data capture."
                )
            elif change.change_id == "CHG-005-CONDITIONAL-ECG":
                out[change.change_id] = (
                    "Conditional repeat ECG requirement was added with a protocol-defined trigger."
                )
            else:
                out[change.change_id] = (
                    f"{change.operation.value} on {change.concept_type} "
                    f"({change.change_id})."
                )
        return out
