"""Fake protocol compiler and re-exported constrained planner (no Gemini)."""

from __future__ import annotations

from pathlib import Path

from protocol215.adapters.constrained_planner import ConstrainedActionPlanner, FakeActionPlanner
from protocol215.adapters.gemini.types import CompilationResult, CompilerObservability
from protocol215.application.hashing import sha256_hex
from protocol215.domain.models import ProtocolIR
from protocol215.fixtures.aurora_ir import build_aurora_v1_ir, build_aurora_v2_ir

__all__ = [
    "ConstrainedActionPlanner",
    "FakeActionPlanner",
    "FakeProtocolCompiler",
]


class FakeProtocolCompiler:
    """Returns hand-built AURORA IRs based on version hint or PDF marker bytes."""

    def __init__(self) -> None:
        self.last_result: CompilationResult | None = None

    def compile(
        self,
        *,
        pdf_bytes: bytes | None = None,
        pdf_path: str | None = None,
        gcs_uri: str | None = None,
        version_hint: str | None = None,
    ) -> ProtocolIR:
        return self.compile_with_metadata(
            pdf_bytes=pdf_bytes,
            pdf_path=pdf_path,
            gcs_uri=gcs_uri,
            version_hint=version_hint,
        ).ir

    def compile_with_metadata(
        self,
        *,
        pdf_bytes: bytes | None = None,
        pdf_path: str | None = None,
        gcs_uri: str | None = None,
        version_hint: str | None = None,
    ) -> CompilationResult:
        if gcs_uri is not None:
            raise ValueError("FakeProtocolCompiler does not fetch GCS URIs")
        if pdf_path is not None:
            data = Path(pdf_path).read_bytes()
        elif pdf_bytes is not None:
            data = pdf_bytes
        else:
            raise ValueError("pdf_bytes or pdf_path required")

        text = data.decode("latin-1", errors="ignore")
        version = version_hint
        if version is None:
            version = (
                "2.0"
                if ("Protocol Version: 2.0" in text or b"v2.0" in data[:2000])
                else "1.0"
            )
        ir = build_aurora_v2_ir() if version.startswith("2") else build_aurora_v1_ir()
        obs = CompilerObservability(
            model_id="fake-protocol-compiler",
            latency_ms=0.0,
            validation_ok=True,
            retry_count=0,
            artifact_hash=sha256_hex(data),
            mode="fake",
        )
        result = CompilationResult(ir=ir, observability=obs)
        self.last_result = result
        return result
