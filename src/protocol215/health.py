"""Health and readiness aggregation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from protocol215 import __version__
from protocol215.adapters import build_probes
from protocol215.config import (
    EventBusBackend,
    ObjectStoreBackend,
    Settings,
    StateStoreBackend,
    get_settings,
)

if TYPE_CHECKING:
    from protocol215.api.container import AppContainer


def liveness(settings: Settings | None = None) -> dict[str, Any]:
    """Process is up; does not require external backends."""
    cfg = settings or get_settings()
    return {
        "status": "ok",
        "service": "protocol-215-api",
        "version": __version__,
        "app_env": cfg.app_env.value,
    }


def readiness(
    settings: Settings | None = None,
    container: AppContainer | None = None,
) -> dict[str, Any]:
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

    actual_adapters: dict[str, str] | None = None
    if container is not None:
        actual_adapters = container.actual_adapters
        # Cloud readiness cannot pass with local adapters when cloud backends are configured.
        if (
            cfg.object_store_backend == ObjectStoreBackend.GCS
            and actual_adapters.get("object_store") != "GCSObjectStore"
        ):
            checks["actual_object_store"] = {
                "ok": False,
                "detail": f"expected GCSObjectStore got {actual_adapters.get('object_store')}",
            }
            all_ok = False
        if (
            cfg.state_store_backend == StateStoreBackend.FIRESTORE
            and actual_adapters.get("state_store") != "FirestoreStateStore"
        ):
            checks["actual_state_store"] = {
                "ok": False,
                "detail": (
                    f"expected FirestoreStateStore got {actual_adapters.get('state_store')}"
                ),
            }
            all_ok = False
        if (
            cfg.event_bus_backend == EventBusBackend.PUBSUB
            and actual_adapters.get("event_bus") != "PubSubEventBus"
        ):
            checks["actual_event_bus"] = {
                "ok": False,
                "detail": f"expected PubSubEventBus got {actual_adapters.get('event_bus')}",
            }
            all_ok = False

    gemini = cfg.gemini_backend.value
    cloud = cfg.execution_mode == "cloud" or cfg.app_env.value == "cloud"
    revision = os.environ.get("K_REVISION") or os.environ.get("CLOUD_RUN_REVISION")

    payload: dict[str, Any] = {
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
    if actual_adapters is not None:
        payload["actual_adapters"] = actual_adapters
    return payload
