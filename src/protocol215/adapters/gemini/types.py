"""Observability and result types for protocol compilation (no secrets / no PDF dumps)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from protocol215.domain.models import ProtocolIR


@dataclass
class CompilerObservability:
    model_id: str
    request_id: str | None = None
    latency_ms: float | None = None
    prompt_token_count: int | None = None
    candidates_token_count: int | None = None
    total_token_count: int | None = None
    validation_ok: bool = False
    validation_errors: list[str] = field(default_factory=list)
    retry_count: int = 0
    artifact_hash: str | None = None
    mode: str = "fake"  # fake | vertex
    low_confidence_fact_count: int = 0


@dataclass
class CompilationResult:
    ir: ProtocolIR
    observability: CompilerObservability
    raw_json: dict[str, Any] | None = None
