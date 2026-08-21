"""Shared constants and paths for synthetic AURORA-101 fixtures."""

from __future__ import annotations

from pathlib import Path

from protocol215.fixtures.constants import (
    EXPECTED_PAGE_COUNT_MAX,
    EXPECTED_PAGE_COUNT_MIN,
    PAGE_APPENDIX,
    PAGE_DATA,
    PAGE_DAY1_PK_FASTING,
    PAGE_DESIGN,
    PAGE_ECG,
    PAGE_ELIGIBILITY,
    PAGE_LAB,
    PAGE_OBJECTIVES,
    PAGE_SITE,
    PAGE_SOA,
    PAGE_SYNOPSIS,
    PAGE_TITLE,
    PAGE_TREATMENT,
    PROMPT_INJECTION_STRING,
    STUDY_ID,
    STUDY_TITLE,
)

__all__ = [
    "ADVERSARIAL",
    "EXPECTED_PAGE_COUNT_MAX",
    "EXPECTED_PAGE_COUNT_MIN",
    "GOLD",
    "GOLD_AMENDMENT",
    "PAGE_APPENDIX",
    "PAGE_DATA",
    "PAGE_DAY1_PK_FASTING",
    "PAGE_DESIGN",
    "PAGE_ECG",
    "PAGE_ELIGIBILITY",
    "PAGE_LAB",
    "PAGE_OBJECTIVES",
    "PAGE_SITE",
    "PAGE_SOA",
    "PAGE_SYNOPSIS",
    "PAGE_TITLE",
    "PAGE_TREATMENT",
    "PARTICIPANTS_PATH",
    "PDF_ADVERSARIAL",
    "PDF_V1",
    "PDF_V2",
    "PROTOCOL_SOURCE",
    "PROTOCOLS",
    "PROMPT_INJECTION_STRING",
    "SITES_PATH",
    "SOURCE_ADVERSARIAL",
    "SOURCE_V1",
    "SOURCE_V2",
    "STUDY_ID",
    "STUDY_STATE",
    "STUDY_TITLE",
    "fixtures_root",
    "repo_root",
]


def repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").is_file() and (parent / "fixtures").is_dir():
            return parent
    return Path.cwd()


def fixtures_root() -> Path:
    return repo_root() / "fixtures"


_ROOT = fixtures_root()
PROTOCOLS = _ROOT / "protocols"
PROTOCOL_SOURCE = PROTOCOLS / "source"
GOLD = _ROOT / "gold"
STUDY_STATE = _ROOT / "study_state"
ADVERSARIAL = _ROOT / "adversarial"

PDF_V1 = PROTOCOLS / "AURORA-101_Protocol_v1.0.pdf"
PDF_V2 = PROTOCOLS / "AURORA-101_Protocol_v2.0.pdf"
PDF_ADVERSARIAL = ADVERSARIAL / "AURORA-101_Protocol_v2.0_adversarial.pdf"

SOURCE_V1 = PROTOCOL_SOURCE / "aurora_101_v1.json"
SOURCE_V2 = PROTOCOL_SOURCE / "aurora_101_v2.json"
SOURCE_ADVERSARIAL = PROTOCOL_SOURCE / "aurora_101_v2_adversarial.json"

GOLD_AMENDMENT = GOLD / "amendment_v1_to_v2_expected.json"
SITES_PATH = STUDY_STATE / "aurora_101_sites.json"
PARTICIPANTS_PATH = STUDY_STATE / "aurora_101_participants.json"
