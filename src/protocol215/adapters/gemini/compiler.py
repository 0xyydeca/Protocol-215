"""Vertex AI Gemini 3.5 Flash protocol compiler (Google Gen AI SDK).

Uses only documented SDK methods validated against google-genai 2.x:
- genai.Client(vertexai=True, project=..., location=...)
- types.Part.from_bytes / types.Part.from_uri
- client.models.generate_content(..., config=GenerateContentConfig)
- response_mime_type='application/json' + response_schema=ProtocolIR
- No tools; PDF content treated as untrusted data.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from pypdf import PdfReader
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from protocol215.adapters.gemini.prompts import SYSTEM_INSTRUCTION, USER_PROMPT_TEMPLATE
from protocol215.adapters.gemini.types import CompilationResult, CompilerObservability
from protocol215.adapters.gemini.validation import (
    ProtocolIRValidationError,
    count_low_confidence_facts,
    validate_protocol_ir,
)
from protocol215.application.hashing import sha256_hex
from protocol215.domain.models import ProtocolIR


class TransientGeminiError(RuntimeError):
    """Retryable Gemini/API failure."""


class SchemaGeminiError(ProtocolIRValidationError):
    """Retryable schema/parse failure."""


class VertexGeminiProtocolCompiler:
    """Tool-less Vertex Gemini compiler. Never mutates app state or authorizes actions."""

    def __init__(
        self,
        *,
        project: str,
        location: str,
        model: str,
        client: Any | None = None,
        max_retries: int = 3,
    ) -> None:
        self.project = project
        self.location = location
        self.model = model
        self.max_retries = max_retries
        self._client = client
        self.last_result: CompilationResult | None = None
        self.last_observability: CompilerObservability | None = None

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        from google import genai

        self._client = genai.Client(
            vertexai=True,
            project=self.project,
            location=self.location,
        )
        return self._client

    def compile(
        self,
        *,
        pdf_bytes: bytes | None = None,
        pdf_path: str | None = None,
        gcs_uri: str | None = None,
        version_hint: str | None = None,
    ) -> ProtocolIR:
        result = self.compile_with_metadata(
            pdf_bytes=pdf_bytes,
            pdf_path=pdf_path,
            gcs_uri=gcs_uri,
            version_hint=version_hint,
        )
        return result.ir

    def compile_with_metadata(
        self,
        *,
        pdf_bytes: bytes | None = None,
        pdf_path: str | None = None,
        gcs_uri: str | None = None,
        version_hint: str | None = None,
    ) -> CompilationResult:
        _resolved_bytes, page_count, artifact_hash, pdf_part = self._resolve_pdf_input(
            pdf_bytes=pdf_bytes,
            pdf_path=pdf_path,
            gcs_uri=gcs_uri,
        )
        obs = CompilerObservability(
            model_id=self.model,
            artifact_hash=artifact_hash,
            mode="vertex",
        )
        retry_count = 0
        last_error: Exception | None = None

        @retry(
            reraise=True,
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
            retry=retry_if_exception_type((TransientGeminiError, SchemaGeminiError)),
        )
        def _call() -> CompilationResult:
            nonlocal retry_count, last_error
            try:
                return self._generate_once(
                    pdf_part=pdf_part,
                    page_count=page_count,
                    version_hint=version_hint,
                    observability=obs,
                    artifact_hash=artifact_hash,
                )
            except (TransientGeminiError, SchemaGeminiError) as exc:
                retry_count += 1
                obs.retry_count = retry_count
                last_error = exc
                raise

        try:
            result = _call()
            # retry_count increments on each failed attempt before success
            result.observability.retry_count = retry_count
            self.last_result = result
            self.last_observability = result.observability
            return result
        except Exception:
            obs.retry_count = retry_count
            obs.validation_ok = False
            if last_error is not None:
                obs.validation_errors = [str(last_error)]
            self.last_result = None
            self.last_observability = obs
            raise

    def _resolve_pdf_input(
        self,
        *,
        pdf_bytes: bytes | None,
        pdf_path: str | None,
        gcs_uri: str | None,
    ) -> tuple[bytes | None, int, str, Any]:
        from google.genai import types

        provided = sum(x is not None for x in (pdf_bytes, pdf_path, gcs_uri))
        if provided != 1:
            raise ValueError("Provide exactly one of pdf_bytes, pdf_path, or gcs_uri")

        if gcs_uri is not None:
            if not gcs_uri.startswith("gs://"):
                raise ValueError("gcs_uri must start with gs://")
            # Page count unknown without download; use a conservative placeholder
            # validated loosely — callers in cloud should pass known page counts later.
            # For validation we download metadata via bytes when possible; here we
            # require page count from a lightweight HEAD is unavailable, so we set
            # page_count after optional bytes fetch is skipped and validate with
            # a high ceiling only if bytes unavailable.
            part = types.Part.from_uri(file_uri=gcs_uri, mime_type="application/pdf")
            return None, 10_000, sha256_hex(gcs_uri.encode("utf-8")), part

        if pdf_path is not None:
            data = Path(pdf_path).read_bytes()
        else:
            assert pdf_bytes is not None
            data = pdf_bytes

        if not data.startswith(b"%PDF"):
            raise ValueError("input is not a PDF (missing %PDF signature)")
        page_count = len(PdfReader(__import__("io").BytesIO(data)).pages)
        part = types.Part.from_bytes(data=data, mime_type="application/pdf")
        return data, page_count, sha256_hex(data), part

    def _generate_once(
        self,
        *,
        pdf_part: Any,
        page_count: int,
        version_hint: str | None,
        observability: CompilerObservability,
        artifact_hash: str,
    ) -> CompilationResult:
        from google.genai import types

        client = self._get_client()
        user_prompt = USER_PROMPT_TEMPLATE.format(
            version_hint=version_hint or "unknown",
            pdf_page_count=page_count if page_count < 10_000 else "unknown",
        )
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.1,
            response_mime_type="application/json",
            response_schema=ProtocolIR,
            # Intentionally omit tools — extraction model is tool-less.
        )
        started = time.perf_counter()
        try:
            response = client.models.generate_content(
                model=self.model,
                contents=[pdf_part, user_prompt],
                config=config,
            )
        except Exception as exc:  # noqa: BLE001 — normalize to retryable/non-retryable
            msg = str(exc).lower()
            if any(
                tok in msg for tok in ("timeout", "temporarily", "unavailable", "429", "500", "503")
            ):
                raise TransientGeminiError(str(exc)) from exc
            raise

        latency_ms = (time.perf_counter() - started) * 1000.0
        observability.latency_ms = latency_ms
        observability.request_id = getattr(response, "response_id", None)
        usage = getattr(response, "usage_metadata", None)
        if usage is not None:
            observability.prompt_token_count = getattr(usage, "prompt_token_count", None)
            observability.candidates_token_count = getattr(usage, "candidates_token_count", None)
            observability.total_token_count = getattr(usage, "total_token_count", None)
        if getattr(response, "model_version", None):
            observability.model_id = str(response.model_version)

        ir, raw = _parse_response(response)
        # For GCS URI path with unknown pages, skip strict upper bound by using reported max page.
        effective_pages = page_count
        if page_count >= 10_000:
            pages = _iter_pages(ir)
            effective_pages = max(pages) if pages else 1

        errors = validate_protocol_ir(ir, pdf_page_count=effective_pages)
        observability.validation_errors = errors
        observability.validation_ok = not errors
        observability.low_confidence_fact_count = count_low_confidence_facts(ir)
        observability.artifact_hash = artifact_hash

        if errors:
            raise SchemaGeminiError("; ".join(errors))

        return CompilationResult(ir=ir, observability=observability, raw_json=raw)


def _parse_response(response: Any) -> tuple[ProtocolIR, dict[str, Any] | None]:
    parsed = getattr(response, "parsed", None)
    if isinstance(parsed, ProtocolIR):
        return parsed, parsed.model_dump()
    if parsed is not None and hasattr(parsed, "model_dump"):
        data = parsed.model_dump()
        try:
            return ProtocolIR.model_validate(data), data
        except Exception as exc:  # noqa: BLE001
            raise SchemaGeminiError(f"Pydantic validation failed: {exc}") from exc

    text = getattr(response, "text", None)
    if not text:
        raise SchemaGeminiError("empty Gemini response")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SchemaGeminiError(f"invalid JSON: {exc}") from exc
    try:
        return ProtocolIR.model_validate(data), data
    except Exception as exc:  # noqa: BLE001
        raise SchemaGeminiError(f"Pydantic validation failed: {exc}") from exc


def _iter_pages(ir: ProtocolIR) -> list[int]:
    pages: list[int] = []
    for visit in ir.visits:
        pages.extend(e.page for e in visit.evidence)
    for activity in ir.activities:
        pages.extend(e.page for e in activity.evidence)
    for sample in ir.pk_samples:
        pages.extend(e.page for e in sample.evidence)
    for lab in ir.laboratory:
        pages.extend(e.page for e in lab.evidence)
    for ecg in ir.ecg:
        pages.extend(e.page for e in ecg.evidence)
    for restriction in ir.restrictions:
        pages.extend(e.page for e in restriction.evidence)
    for edc in ir.edc_fields:
        pages.extend(e.page for e in edc.evidence)
    return pages
