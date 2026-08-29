"""Shared Vertex AI Gen AI client helpers (ADC only — no API keys)."""

from __future__ import annotations

from typing import Any

_PROBE_PROMPT = "Reply with exactly the single word: ok"


def build_vertex_genai_client(
    *,
    project: str,
    location: str,
    client: Any | None = None,
    http_timeout_ms: int | None = None,
) -> Any:
    """Return an injectable or lazily constructed Vertex-mode Gen AI client."""
    if client is not None:
        return client
    from google import genai
    from google.genai import types

    http_options = None
    if http_timeout_ms is not None:
        # google-genai HttpOptions.timeout is milliseconds (documented).
        http_options = types.HttpOptions(timeout=http_timeout_ms)

    return genai.Client(
        vertexai=True,
        project=project,
        location=location,
        http_options=http_options,
    )


def probe_vertex_gemini(
    *,
    project: str,
    location: str,
    model: str,
    client: Any | None = None,
) -> str:
    """Perform a minimal live Gemini request; raise on any failure."""
    genai_client = build_vertex_genai_client(
        project=project,
        location=location,
        client=client,
    )
    response = genai_client.models.generate_content(
        model=model,
        contents=_PROBE_PROMPT,
    )
    text = (getattr(response, "text", None) or "").strip().lower()
    if text != "ok":
        raise RuntimeError(f"unexpected probe response: {text!r}")
    return text
