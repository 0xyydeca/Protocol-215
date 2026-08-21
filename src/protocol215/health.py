"""Health and readiness aggregation."""

from __future__ import annotations

from typing import Any

from protocol215 import __version__
from protocol215.adapters import build_probes
from protocol215.config import Settings, get_settings


def liveness(settings: Settings | None = None) -> dict[str, Any]:
    """Process is up; does not require external backends."""
    cfg = settings or get_settings()
    return {
        "status": "ok",
        "service": "protocol-215-api",
        "version": __version__,
        "app_env": cfg.app_env.value,
    }


def readiness(settings: Settings | None = None) -> dict[str, Any]:
    """Required backends must be available for the configured mode."""
    import os

    cfg = settings or get_settings()
    checks: dict[str, dict[str, Any]] = {}
    all_ok = True
    for probe in build_probes(cfg):
        ok, detail = probe.check()
        checks[probe.name] = {"ok": ok, "detail": detail}
        if not ok:
            all_ok = False

    gemini = cfg.gemini_backend.value
    cloud = cfg.execution_mode == "cloud" or cfg.app_env.value == "cloud"
    revision = os.environ.get("K_REVISION") or os.environ.get("CLOUD_RUN_REVISION")

    return {
        "status": "ok" if all_ok else "unavailable",
        "service": "protocol-215-api",
        "version": __version__,
        "app_env": cfg.app_env.value,
        "execution_mode": cfg.execution_mode,
        "synthetic_study": True,
        "study_id": cfg.default_study_id,
        "compiler_mode": "fake" if gemini == "fake" else "live_gemini",
        "gemini_model": cfg.gemini_model,
        "cloud_run_revision": revision,
        "backends": {
            "object_store": cfg.object_store_backend.value,
            "state_store": cfg.state_store_backend.value,
            "event_bus": cfg.event_bus_backend.value,
            "gemini": gemini,
            "gemini_model": cfg.gemini_model,
        },
        "checks": checks,
        "demo_mode": {
            "synthetic_study": "Synthetic Study",
            "runtime": "Google Cloud" if cloud else "Local",
            "compiler": (
                "Fake Compiler" if gemini == "fake" else f"Live Gemini ({cfg.gemini_model})"
            ),
            "model_id": cfg.gemini_model,
            "cloud_run_revision": revision,
        },
    }
