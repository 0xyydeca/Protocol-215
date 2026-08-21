"""Helpers to enumerate intentional semantic deltas between protocol sources."""

from __future__ import annotations

from typing import Any


def intentional_semantic_deltas(v1: dict[str, Any], v2: dict[str, Any]) -> list[str]:
    """Return the controlled semantic change ids present between v1 and v2 sources."""
    found: list[str] = []
    c1 = v1["sections"]["lab_contact"]["paragraphs"][0]
    c2 = v2["sections"]["lab_contact"]["paragraphs"][0]
    if "lab-v1@example.test" in c1 and "lab-v2@example.test" in c2:
        found.append("CHG-001-LAB-CONTACT")

    t1 = set(v1["sections"]["pk"]["timepoints"])
    t2 = set(v2["sections"]["pk"]["timepoints"])
    if "6 hours post-dose" in (t2 - t1):
        found.append("CHG-002-PK-6H")

    f1 = " ".join(v1["sections"]["fasting"]["paragraphs"])
    f2 = " ".join(v2["sections"]["fasting"]["paragraphs"])
    if "through 2 hours" in f1 and "through 4 hours" in f2:
        found.append("CHG-003-FASTING-4H")

    d1 = " ".join(v1["sections"]["data_collection"]["paragraphs"])
    d2 = " ".join(v2["sections"]["data_collection"]["paragraphs"])
    if "sample_processing_temperature_c" not in d1 and "sample_processing_temperature_c" in d2:
        found.append("CHG-004-EDC-TEMP")

    e1 = " ".join(v1["sections"]["ecg"]["paragraphs"])
    e2 = " ".join(v2["sections"]["ecg"]["paragraphs"])
    if "Conditional repeat ECG" not in e1 and "Conditional repeat ECG" in e2:
        found.append("CHG-005-CONDITIONAL-ECG")

    return found
