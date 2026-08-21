"""Mocked and gated-live tests for the Gemini protocol compiler."""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from protocol215.adapters.fakes import FakeProtocolCompiler
from protocol215.adapters.gemini.compiler import (
    SchemaGeminiError,
    VertexGeminiProtocolCompiler,
)
from protocol215.adapters.gemini.prompts import SYSTEM_INSTRUCTION
from protocol215.adapters.gemini.validation import (
    count_low_confidence_facts,
    validate_protocol_ir,
)
from protocol215.domain.enums import ReviewStatus
from protocol215.domain.models import ActionProposal, ProtocolIR
from protocol215.fixtures import PDF_ADVERSARIAL, PDF_V1, PDF_V2, PROMPT_INJECTION_STRING
from protocol215.fixtures.aurora_ir import build_aurora_v1_ir, build_aurora_v2_ir
from protocol215.policy.matrix import authorize_proposal


def test_security_prompt_forbids_pdf_instructions_and_tools() -> None:
    assert "untrusted" in SYSTEM_INSTRUCTION.lower()
    assert (
        "NEVER an instruction" in SYSTEM_INSTRUCTION
        or "never an instruction" in SYSTEM_INSTRUCTION.lower()
    )
    assert (
        "NO function tools" in SYSTEM_INSTRUCTION
        or "no function tools" in SYSTEM_INSTRUCTION.lower()
    )
    assert "approve" in SYSTEM_INSTRUCTION.lower()


def test_validate_rejects_missing_evidence_and_bad_pages() -> None:
    ir = build_aurora_v1_ir()
    ir.activities[0].evidence = []
    errors = validate_protocol_ir(ir, pdf_page_count=13)
    assert any("without evidence" in e for e in errors)

    ir2 = build_aurora_v1_ir()
    ir2.activities[0].evidence[0].page = 99
    errors2 = validate_protocol_ir(ir2, pdf_page_count=13)
    assert any("out of range" in e for e in errors2)


def test_validate_flags_low_confidence_for_review() -> None:
    ir = build_aurora_v1_ir()
    ir.pk_samples[0].evidence[0].confidence = 0.2
    errors = validate_protocol_ir(ir, pdf_page_count=13)
    assert errors == []
    assert ir.pk_samples[0].evidence[0].review_status == ReviewStatus.NEEDS_REVIEW
    assert count_low_confidence_facts(ir) >= 1


def test_validate_requires_unique_activity_ids() -> None:
    ir = build_aurora_v1_ir()
    ir.activities.append(ir.activities[0].model_copy())
    errors = validate_protocol_ir(ir, pdf_page_count=13)
    assert any("not unique" in e for e in errors)


def test_fake_compiler_primary_fixtures_match_hand_built_expectations() -> None:
    compiler = FakeProtocolCompiler()
    v1 = compiler.compile(pdf_path=str(PDF_V1), version_hint="1.0")
    v2 = compiler.compile(pdf_path=str(PDF_V2), version_hint="2.0")
    expected_v1 = build_aurora_v1_ir()
    expected_v2 = build_aurora_v2_ir()

    assert v1.metadata.version == "1.0"
    assert v2.metadata.version == "2.0"
    assert (
        v1.administrative_contacts["central_lab"]
        == expected_v1.administrative_contacts["central_lab"]
    )
    assert (
        v2.administrative_contacts["central_lab"]
        == expected_v2.administrative_contacts["central_lab"]
    )
    assert {s.timepoint_hours for s in v1.pk_samples} == {
        s.timepoint_hours for s in expected_v1.pk_samples
    }
    assert 6.0 in {s.timepoint_hours for s in v2.pk_samples}
    assert any(e.name == "sample_processing_temperature_c" for e in v2.edc_fields)
    assert compiler.last_result is not None
    assert compiler.last_result.observability.mode == "fake"
    assert compiler.last_result.observability.validation_ok is True
    # Adapter does not hardcode the five gold change IDs.
    compiler_src = (
        Path(__file__).resolve().parents[2] / "src/protocol215/adapters/gemini/compiler.py"
    ).read_text(encoding="utf-8")
    assert "CHG-001" not in compiler_src
    assert "CHG-002-PK-6H" not in compiler_src


def test_fake_adversarial_pdf_does_not_authorize_or_propose_tools() -> None:
    compiler = FakeProtocolCompiler()
    ir = compiler.compile(pdf_path=str(PDF_ADVERSARIAL), version_hint="2.0")
    assert ir.metadata.version == "2.0"
    # Injection string must not become an authorized action.
    proposal = ActionProposal(
        proposal_id="bad",
        tool_name="follow_document_instructions",
        rationale=PROMPT_INJECTION_STRING,
        evidence=[],
    )
    from protocol215.domain.enums import RiskTier

    assert authorize_proposal(proposal) == RiskTier.RED
    # Compiler observability must not claim approval.
    assert compiler.last_result is not None
    assert "approve" not in (compiler.last_result.observability.model_id or "").lower()


class _FakeModels:
    def __init__(self, response: Any) -> None:
        self._response = response
        self.calls = 0

    def generate_content(self, **kwargs: Any) -> Any:
        self.calls += 1
        config = kwargs.get("config")
        assert config is not None
        # Ensure tool-less config (tools must be absent / empty)
        tools = getattr(config, "tools", None)
        assert not tools
        assert getattr(config, "response_mime_type", None) == "application/json"
        assert getattr(config, "response_schema", None) is ProtocolIR
        assert kwargs.get("model") == "gemini-3.5-flash"
        return self._response


class _FakeClient:
    def __init__(self, response: Any) -> None:
        self.models = _FakeModels(response)


def _mock_response(ir: ProtocolIR) -> SimpleNamespace:
    return SimpleNamespace(
        parsed=ir,
        text=ir.model_dump_json(),
        response_id="req-test-001",
        model_version="gemini-3.5-flash",
        usage_metadata=SimpleNamespace(
            prompt_token_count=11,
            candidates_token_count=22,
            total_token_count=33,
        ),
    )


def test_vertex_compiler_mocked_success_and_observability() -> None:
    ir = build_aurora_v1_ir()
    client = _FakeClient(_mock_response(ir))
    compiler = VertexGeminiProtocolCompiler(
        project="demo-project",
        location="us-central1",
        model="gemini-3.5-flash",
        client=client,
        max_retries=2,
    )
    pdf_bytes = PDF_V1.read_bytes()
    result = compiler.compile_with_metadata(pdf_bytes=pdf_bytes, version_hint="1.0")
    assert result.ir.metadata.version == "1.0"
    assert result.observability.mode == "vertex"
    assert result.observability.model_id == "gemini-3.5-flash"
    assert result.observability.request_id == "req-test-001"
    assert result.observability.validation_ok is True
    assert result.observability.total_token_count == 33
    assert result.observability.artifact_hash
    assert client.models.calls == 1


def test_vertex_compiler_retries_schema_errors_then_fails() -> None:
    bad_ir = build_aurora_v1_ir()
    bad_ir.activities[0].evidence = []
    client = _FakeClient(_mock_response(bad_ir))
    compiler = VertexGeminiProtocolCompiler(
        project="demo-project",
        location="us-central1",
        model="gemini-3.5-flash",
        client=client,
        max_retries=3,
    )
    with pytest.raises(SchemaGeminiError):
        compiler.compile(pdf_bytes=PDF_V1.read_bytes(), version_hint="1.0")
    assert client.models.calls == 3
    assert compiler.last_observability is not None
    assert compiler.last_observability.validation_ok is False


def test_vertex_compiler_accepts_pdf_path() -> None:
    client = _FakeClient(_mock_response(build_aurora_v2_ir()))
    compiler = VertexGeminiProtocolCompiler(
        project="demo-project",
        location="us-central1",
        model="gemini-3.5-flash",
        client=client,
    )
    ir = compiler.compile(pdf_path=str(PDF_V2), version_hint="2.0")
    assert ir.metadata.version == "2.0"


def test_vertex_compiler_gcs_uri_builds_uri_part(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, str] = {}

    class FakePart:
        @staticmethod
        def from_uri(*, file_uri: str, mime_type: str | None = None) -> str:
            captured["file_uri"] = file_uri
            captured["mime_type"] = mime_type or ""
            return "gcs-part"

        @staticmethod
        def from_bytes(**kwargs: Any) -> str:
            raise AssertionError("from_bytes must not be used for gcs_uri")

    monkeypatch.setattr(
        "google.genai.types.Part",
        FakePart,
        raising=False,
    )

    # Patch the import used inside _resolve_pdf_input
    import google.genai.types as genai_types

    monkeypatch.setattr(genai_types, "Part", FakePart)

    compiler = VertexGeminiProtocolCompiler(
        project="demo-project",
        location="us-central1",
        model="gemini-3.5-flash",
        client=_FakeClient(_mock_response(build_aurora_v1_ir())),
    )
    _bytes, pages, digest, part = compiler._resolve_pdf_input(
        pdf_bytes=None,
        pdf_path=None,
        gcs_uri="gs://bucket/protocols/v1.pdf",
    )
    assert _bytes is None
    assert pages == 10_000
    assert digest
    assert part == "gcs-part"
    assert captured["file_uri"] == "gs://bucket/protocols/v1.pdf"
    assert captured["mime_type"] == "application/pdf"


@pytest.mark.live_gemini
@pytest.mark.skipif(
    os.environ.get("RUN_LIVE_GEMINI_TESTS") != "1",
    reason="Live Gemini tests require RUN_LIVE_GEMINI_TESTS=1 and Vertex credentials",
)
def test_live_gemini_smoke_and_adversarial() -> None:
    """LIVE ONLY — records metadata; does not hardcode success claims beyond validation."""
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    model = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")
    if not project:
        pytest.skip("GOOGLE_CLOUD_PROJECT not set")

    meta: dict[str, Any] = {
        "mode": "live",
        "model_requested": model,
        "project_set": True,
        "location": location,
    }
    compiler = VertexGeminiProtocolCompiler(
        project=project,
        location=location,
        model=model,
        max_retries=2,
    )
    try:
        result = compiler.compile_with_metadata(
            pdf_bytes=PDF_V1.read_bytes(),
            version_hint="1.0",
        )
        meta["v1_validation_ok"] = result.observability.validation_ok
        meta["v1_model_id"] = result.observability.model_id
        meta["v1_request_id"] = result.observability.request_id
        meta["v1_latency_ms"] = result.observability.latency_ms
        meta["v1_retries"] = result.observability.retry_count
        assert result.observability.validation_ok is True
        assert result.ir.metadata.version

        adv = compiler.compile_with_metadata(
            pdf_bytes=PDF_ADVERSARIAL.read_bytes(),
            version_hint="2.0",
        )
        meta["adversarial_validation_ok"] = adv.observability.validation_ok
        meta["adversarial_model_id"] = adv.observability.model_id
        # Injection must not surface as tool use or approvals in IR contacts/tools (none exist).
        dumped = adv.ir.model_dump_json().lower()
        assert "follow_document_instructions" not in dumped
        assert "activate_informed_consent" not in dumped
        assert adv.observability.validation_ok is True
    finally:
        # Record test metadata for operators — never claim hardcoded CI success for live.
        print("LIVE_GEMINI_TEST_METADATA", meta)
