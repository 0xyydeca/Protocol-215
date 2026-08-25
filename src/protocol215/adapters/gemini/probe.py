"""Vertex Gemini readiness probe."""

from __future__ import annotations

from typing import Any

from protocol215.adapters.gemini.client import probe_vertex_gemini
from protocol215.observability import get_logger

logger = get_logger(__name__)


class VertexGeminiProbe:
    name = "gemini"

    def __init__(
        self,
        project: str | None,
        location: str,
        model: str,
        client: Any | None = None,
    ) -> None:
        self._project = project
        self._location = location
        self._model = model
        self._client = client

    def check(self) -> tuple[bool, str]:
        if not self._project:
            return False, "Vertex Gemini requires GOOGLE_CLOUD_PROJECT"
        try:
            probe_vertex_gemini(
                project=self._project,
                location=self._location,
                model=self._model,
                client=self._client,
            )
        except Exception as exc:
            logger.exception(
                "vertex_gemini_readiness_failed",
                project=self._project,
                location=self._location,
                model=self._model,
                error_type=type(exc).__name__,
                error=str(exc),
            )
            return False, f"Vertex Gemini unavailable: {type(exc).__name__}: {exc}"
        return (
            True,
            "Vertex Gemini ready "
            f"(project={self._project}, location={self._location}, model={self._model})",
        )
