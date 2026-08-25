"""Shared pytest configuration."""

from __future__ import annotations

import pytest

from protocol215.config import clear_settings_cache


@pytest.fixture(autouse=True)
def isolate_gemini_backend_from_local_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unit tests must not inherit GEMINI_BACKEND / project from developer .env."""
    monkeypatch.setenv("GEMINI_BACKEND", "fake")
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    clear_settings_cache()
    yield
    clear_settings_cache()
