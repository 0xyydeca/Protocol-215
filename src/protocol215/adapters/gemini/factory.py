"""Factory for protocol compilers based on settings."""

from __future__ import annotations

from protocol215.adapters.fakes import FakeProtocolCompiler
from protocol215.adapters.gemini.compiler import VertexGeminiProtocolCompiler
from protocol215.config import GeminiBackend, Settings, get_settings
from protocol215.ports import ProtocolCompiler


def build_protocol_compiler(settings: Settings | None = None) -> ProtocolCompiler:
    cfg = settings or get_settings()
    if cfg.gemini_backend == GeminiBackend.FAKE:
        return FakeProtocolCompiler()
    if not cfg.google_cloud_project:
        raise ValueError("GOOGLE_CLOUD_PROJECT required for Vertex Gemini compiler")
    return VertexGeminiProtocolCompiler(
        project=cfg.google_cloud_project,
        location=cfg.google_cloud_location,
        model=cfg.gemini_model,
        max_retries=cfg.gemini_max_retries,
        http_timeout_ms=cfg.gemini_http_timeout_ms,
        max_output_tokens=cfg.gemini_max_output_tokens,
        compile_deadline_seconds=cfg.gemini_compile_deadline_seconds,
    )
