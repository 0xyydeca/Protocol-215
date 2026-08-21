"""Validation tests for synthetic AURORA-101 fixtures (no Gemini / extraction)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest
from pypdf import PdfReader

from protocol215.fixtures import (
    EXPECTED_PAGE_COUNT_MAX,
    EXPECTED_PAGE_COUNT_MIN,
    GOLD_AMENDMENT,
    PARTICIPANTS_PATH,
    PDF_ADVERSARIAL,
    PDF_V1,
    PDF_V2,
    PROMPT_INJECTION_STRING,
    SITES_PATH,
    SOURCE_ADVERSARIAL,
    SOURCE_V1,
    SOURCE_V2,
    STUDY_ID,
)
from protocol215.fixtures.semantic_diff_sources import intentional_semantic_deltas


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _pdf_text_by_page(path: Path) -> list[str]:
    reader = PdfReader(str(path))
    return [(page.extract_text() or "") for page in reader.pages]


def _all_fixture_json_text() -> str:
    chunks: list[str] = []
    roots = [
        SOURCE_V1.parent,
        GOLD_AMENDMENT.parent,
        SITES_PATH.parent,
        SOURCE_ADVERSARIAL.parent,
    ]
    seen: set[Path] = set()
    for root in roots:
        for path in root.glob("*.json"):
            if path in seen:
                continue
            seen.add(path)
            chunks.append(path.read_text(encoding="utf-8"))
    return "\n".join(chunks)


@pytest.mark.parametrize("pdf_path", [PDF_V1, PDF_V2, PDF_ADVERSARIAL])
def test_pdfs_exist_with_signature(pdf_path: Path) -> None:
    assert pdf_path.is_file(), f"missing {pdf_path}"
    header = pdf_path.read_bytes()[:5]
    assert header == b"%PDF-", f"{pdf_path} missing PDF signature"


@pytest.mark.parametrize("pdf_path", [PDF_V1, PDF_V2, PDF_ADVERSARIAL])
def test_page_counts_in_range(pdf_path: Path) -> None:
    count = len(PdfReader(str(pdf_path)).pages)
    assert EXPECTED_PAGE_COUNT_MIN <= count <= EXPECTED_PAGE_COUNT_MAX, (
        f"{pdf_path.name} has {count} pages"
    )


def test_version_labels() -> None:
    v1_pages = _pdf_text_by_page(PDF_V1)
    v2_pages = _pdf_text_by_page(PDF_V2)
    assert any("Protocol Version: 1.0" in p for p in v1_pages)
    assert any("Protocol Version: 2.0" in p for p in v2_pages)
    assert any(STUDY_ID in p for p in v1_pages)
    assert any(STUDY_ID in p for p in v2_pages)


def test_exactly_five_semantic_changes_in_sources_and_gold() -> None:
    v1 = _load_json(SOURCE_V1)
    v2 = _load_json(SOURCE_V2)
    deltas = intentional_semantic_deltas(v1, v2)
    assert deltas == [
        "CHG-001-LAB-CONTACT",
        "CHG-002-PK-6H",
        "CHG-003-FASTING-4H",
        "CHG-004-EDC-TEMP",
        "CHG-005-CONDITIONAL-ECG",
    ]
    gold = _load_json(GOLD_AMENDMENT)
    assert len(gold["changes"]) == 5
    assert [c["change_id"] for c in gold["changes"]] == deltas


def test_expected_evidence_pages_exist() -> None:
    gold = _load_json(GOLD_AMENDMENT)
    v2_pages = _pdf_text_by_page(PDF_V2)
    for change in gold["changes"]:
        page_idx = int(change["expected_evidence_page"]) - 1
        assert 0 <= page_idx < len(v2_pages)
        section = change["expected_evidence_section"]
        assert section in v2_pages[page_idx], (
            f"{change['change_id']}: {section} not on page {page_idx + 1}"
        )


def test_emails_use_reserved_test_domain() -> None:
    blob = _all_fixture_json_text()
    for pdf in (PDF_V1, PDF_V2, PDF_ADVERSARIAL):
        blob += "\n".join(_pdf_text_by_page(pdf))
    emails = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", blob)
    assert emails, "expected at least one email in fixtures"
    for email in emails:
        assert email.endswith(".test"), f"non-.test email: {email}"


def test_site_and_participant_identifiers_are_synthetic() -> None:
    sites = _load_json(SITES_PATH)
    participants = _load_json(PARTICIPANTS_PATH)
    assert sites["synthetic"] is True
    assert participants["synthetic"] is True
    site_ids = {s["site_id"] for s in sites["sites"]}
    assert site_ids == {"SITE-001", "SITE-002", "SITE-003"}
    participant_ids = {p["participant_id"] for p in participants["participants"]}
    assert participant_ids == {"P001", "P002", "P003", "P004", "P005"}
    for site in sites["sites"]:
        assert site["site_id"].startswith("SITE-")
    for person in participants["participants"]:
        assert person["participant_id"].startswith("P")
        assert person["site_id"] in site_ids


def test_p002_creates_1800_vs_1730_conflict() -> None:
    sites = _load_json(SITES_PATH)
    participants = _load_json(PARTICIPANTS_PATH)
    phoenix = next(s for s in sites["sites"] if s["site_id"] == "SITE-001")
    p002 = next(p for p in participants["participants"] if p["participant_id"] == "P002")
    assert phoenix["courier_departure_local_time"] == "17:30"
    assert phoenix["validated_overnight_storage_available"] is False
    assert p002["planned_dose_time_local"] == "12:00"
    assert p002["v2_pk_6h_local_time"] == "18:00"
    conflict = p002["conflict_with_courier"]
    assert conflict["courier_departure_local_time"] == "17:30"
    assert conflict["sample_time_local"] == "18:00"
    assert conflict["overnight_storage_available"] is False
    # 12:00 + 6h = 18:00, which is after 17:30 courier with no overnight storage.
    dose_h, dose_m = map(int, p002["planned_dose_time_local"].split(":"))
    sample_h = dose_h + 6
    assert f"{sample_h:02d}:{dose_m:02d}" == "18:00"
    courier_h, courier_m = map(int, phoenix["courier_departure_local_time"].split(":"))
    assert (sample_h, dose_m) > (courier_h, courier_m)


def test_p001_completed_visit_immutable() -> None:
    participants = _load_json(PARTICIPANTS_PATH)
    p001 = next(p for p in participants["participants"] if p["participant_id"] == "P001")
    assert p001["day1_completed"] is True
    assert p001["day1_immutable"] is True
    assert p001["day1_status"] == "completed"
    assert p001["next_visit"] == "Day 8"


def test_adversarial_fixture_contains_injection_string() -> None:
    source = _load_json(SOURCE_ADVERSARIAL)
    assert PROMPT_INJECTION_STRING in json.dumps(source)
    pages = _pdf_text_by_page(PDF_ADVERSARIAL)
    combined = "\n".join(pages)
    assert PROMPT_INJECTION_STRING in combined


def test_site_operational_fields() -> None:
    sites = {s["site_id"]: s for s in _load_json(SITES_PATH)["sites"]}
    assert sites["SITE-001"]["amendment_training_status"] == "complete"
    assert sites["SITE-001"]["extra_pk_kits"] == 2
    assert sites["SITE-002"]["amendment_training_status"] == "incomplete"
    assert sites["SITE-002"]["courier_departure_local_time"] == "20:00"
    assert sites["SITE-002"]["extra_pk_kits"] == 10
    assert sites["SITE-003"]["local_approval_status"] == "pending"
    assert sites["SITE-003"]["amendment_training_status"] == "not_started"
    assert sites["SITE-003"]["extra_pk_kits"] == 6
