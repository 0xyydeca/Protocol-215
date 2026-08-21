"""Gemini adapters package."""

from protocol215.adapters.gemini.compiler import (
    SchemaGeminiError,
    TransientGeminiError,
    VertexGeminiProtocolCompiler,
)
from protocol215.adapters.gemini.types import CompilationResult, CompilerObservability
from protocol215.adapters.gemini.validation import (
    ProtocolIRValidationError,
    validate_protocol_ir,
)

__all__ = [
    "CompilationResult",
    "CompilerObservability",
    "ProtocolIRValidationError",
    "SchemaGeminiError",
    "TransientGeminiError",
    "VertexGeminiProtocolCompiler",
    "validate_protocol_ir",
]
