"""Recording-readiness checks for the judge-facing demo video.

Performs real bounded probes. Never mutates demo/application state.
Never returns secrets or credential material.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any

from protocol215.adapters.audit_log import verify_audit_chain
from protocol215.config import (
    EventBusBackend,
    GeminiBackend,
    ObjectStoreBackend,
    Settings,
    StateStoreBackend,
)
from protocol215.domain.enums import WorkflowStatus
from protocol215.fixtures import PDF_V1, PDF_V2
from protocol215.ports import StateStore

_TERMINAL = {
    WorkflowStatus.COMPLETED,
    WorkflowStatus.COMPLETED_WITH_BLOCKS,
    WorkflowStatus.FAILED_TERMINAL,
    WorkflowStatus.FAILED_RETRYABLE,
    WorkflowStatus.FAILED,
    WorkflowStatus.PARTIAL,
    WorkflowStatus.MANIFEST_READY,
}


@dataclass(frozen=True)
class ReadinessCheck:
    name: str
    status: str  # PASS | FAIL
    detail: str

    def as_dict(self) -> dict[str, str]:
        return {"name": self.name, "status": self.status, "detail": self.detail}


def _pass(name: str, detail: str) -> ReadinessCheck:
    return ReadinessCheck(name=name, status="PASS", detail=detail)


def _fail(name: str, detail: str) -> ReadinessCheck:
    return ReadinessCheck(name=name, status="FAIL", detail=detail)


def is_gemini_3_5_plus(model: str) -> bool:
    """True when model id indicates Gemini 3.5 or newer (not 1.x/2.x)."""
    m = (model or "").strip().lower()
    if not m:
        return False
    # Accept gemini-3.5-*, gemini-3.5flash, publishers/.../gemini-3.5-flash, gemini-4*
    if re.search(r"gemini[-_]?([4-9](?:\.\d+)?|3\.([5-9]|\d{2,}))", m):
        return True
    return bool(re.search(r"gemini[-_]?3\.5", m))


def _check_cloud_execution_mode(settings: Settings) -> ReadinessCheck:
    cloud = settings.execution_mode == "cloud" or settings.app_env.value == "cloud"
    if cloud:
        return _pass(
            "cloud_execution_mode",
            f"execution_mode={settings.execution_mode} app_env={settings.app_env.value}",
        )
    return _fail(
        "cloud_execution_mode",
        f"not cloud (execution_mode={settings.execution_mode}, app_env={settings.app_env.value})",
    )


def _check_live_gemini(settings: Settings) -> ReadinessCheck:
    if settings.gemini_backend == GeminiBackend.VERTEX:
        return _pass("live_gemini_backend", "GEMINI_BACKEND=vertex")
    return _fail(
        "live_gemini_backend",
        f"GEMINI_BACKEND={settings.gemini_backend.value} (require vertex)",
    )


def _check_model_3_5(settings: Settings) -> ReadinessCheck:
    model = settings.gemini_model
    if is_gemini_3_5_plus(model):
        return _pass("model_is_gemini_3_5_plus", f"model={model}")
    return _fail("model_is_gemini_3_5_plus", f"model={model!r} is not Gemini 3.5+")


def _check_revision() -> ReadinessCheck:
    rev = os.environ.get("K_REVISION") or os.environ.get("CLOUD_RUN_REVISION")
    if rev:
        return _pass("cloud_run_revision_available", f"revision={rev}")
    return _fail(
        "cloud_run_revision_available",
        "K_REVISION / CLOUD_RUN_REVISION not set (not on Cloud Run)",
    )


def _check_gcs(settings: Settings) -> ReadinessCheck:
    name = "gcs_reachable"
    if settings.object_store_backend != ObjectStoreBackend.GCS:
        return _fail(name, f"OBJECT_STORE_BACKEND={settings.object_store_backend.value}")
    if not settings.google_cloud_project or not settings.gcs_bucket:
        return _fail(name, "GOOGLE_CLOUD_PROJECT and GCS_BUCKET required")
    try:
        from google.cloud import storage

        client = storage.Client(project=settings.google_cloud_project)
        bucket = client.bucket(settings.gcs_bucket)
        # Bounded metadata fetch — no writes.
        exists = bool(bucket.exists(timeout=8))
        if not exists:
            return _fail(name, f"bucket not found: {settings.gcs_bucket}")
        return _pass(name, f"bucket={settings.gcs_bucket} reachable")
    except Exception as exc:  # noqa: BLE001 — surface real probe failure
        return _fail(name, f"{type(exc).__name__}: {exc}")


def _check_firestore(settings: Settings) -> ReadinessCheck:
    name = "firestore_reachable"
    if settings.state_store_backend != StateStoreBackend.FIRESTORE:
        return _fail(name, f"STATE_STORE_BACKEND={settings.state_store_backend.value}")
    if not settings.google_cloud_project:
        return _fail(name, "GOOGLE_CLOUD_PROJECT required")
    try:
        from google.cloud import firestore

        db = firestore.Client(
            project=settings.google_cloud_project,
            database=settings.firestore_database or "(default)",
        )
        # Bounded read of a non-mutating sentinel; list collections is read-only.
        _ = list(db.collections(page_size=1))
        return _pass(name, f"project={settings.google_cloud_project} reachable")
    except Exception as exc:  # noqa: BLE001
        return _fail(name, f"{type(exc).__name__}: {exc}")


def _check_pubsub(settings: Settings) -> ReadinessCheck:
    name = "pubsub_topic_reachable"
    if settings.event_bus_backend != EventBusBackend.PUBSUB:
        return _fail(name, f"EVENT_BUS_BACKEND={settings.event_bus_backend.value}")
    if not settings.google_cloud_project:
        return _fail(name, "GOOGLE_CLOUD_PROJECT required")
    topic = settings.pubsub_topic_received
    try:
        from google.cloud import pubsub_v1

        client = pubsub_v1.PublisherClient()
        path = client.topic_path(settings.google_cloud_project, topic)
        client.get_topic(request={"topic": path}, timeout=8)
        return _pass(name, f"topic={topic} reachable")
    except Exception as exc:  # noqa: BLE001
        return _fail(name, f"{type(exc).__name__}: {exc}")


def _check_worker_handler(settings: Settings) -> ReadinessCheck:
    name = "worker_handler_configured"
    flagged = os.environ.get("WORKER_HANDLER_CONFIGURED", "").lower() in {
        "1",
        "true",
        "yes",
    }
    if flagged:
        return _pass(name, "WORKER_HANDLER_CONFIGURED=true")
    # Cloud Pub/Sub push to worker implies handler wiring for the demo.
    if settings.event_bus_backend == EventBusBackend.PUBSUB and settings.google_cloud_project:
        pub = _check_pubsub(settings)
        if pub.status == "PASS":
            return _pass(name, "Pub/Sub topic reachable (worker push path expected)")
        return _fail(name, f"Pub/Sub not reachable: {pub.detail}")
    return _fail(
        name,
        "worker handler not configured (require Pub/Sub cloud path or WORKER_HANDLER_CONFIGURED)",
    )


def _check_fixture_pdfs() -> ReadinessCheck:
    name = "fixture_pdfs_available"
    missing: list[str] = []
    if not PDF_V1.is_file():
        missing.append(str(PDF_V1.name))
    if not PDF_V2.is_file():
        missing.append(str(PDF_V2.name))
    if missing:
        return _fail(name, f"missing: {', '.join(missing)}")
    return _pass(name, f"{PDF_V1.name} and {PDF_V2.name} present")


def _check_no_stale_runs(state: StateStore | None) -> ReadinessCheck:
    name = "no_active_stale_demo_run"
    if state is None:
        return _fail(name, "state store unavailable")
    try:
        runs = state.list_runs()
    except Exception as exc:  # noqa: BLE001
        return _fail(name, f"{type(exc).__name__}: {exc}")
    active = [r for r in runs if r.status not in _TERMINAL]
    if active:
        sample = ", ".join(f"{r.run_id}:{r.status.value}" for r in active[:3])
        return _fail(name, f"{len(active)} non-terminal run(s): {sample}")
    return _pass(name, f"{len(runs)} run(s), none active/stale")


def _check_audit_verifier(state: StateStore | None) -> ReadinessCheck:
    name = "audit_verifier_operational"
    if state is None:
        return _fail(name, "state store unavailable")
    try:
        # Empty chain must verify True — proves verifier callable without mutation.
        ok, errors = verify_audit_chain([])
        if not ok:
            return _fail(name, f"empty-chain unexpected errors: {errors}")
        # If any run exists, verify its chain read-only.
        runs = state.list_runs()
        if runs:
            events = state.list_audit_events(runs[0].run_id)
            ok2, errors2 = verify_audit_chain(events)
            if not ok2:
                return _fail(
                    name,
                    f"chain verify failed for {runs[0].run_id}: {errors2[:3]}",
                )
            return _pass(name, f"verified empty + run {runs[0].run_id} ({len(events)} events)")
        return _pass(name, "empty-chain verify ok")
    except Exception as exc:  # noqa: BLE001
        return _fail(name, f"{type(exc).__name__}: {exc}")


def evaluate_recording_readiness(
    settings: Settings,
    *,
    state: StateStore | None = None,
) -> dict[str, Any]:
    """Return PASS/FAIL report. Does not mutate state."""
    checks = [
        _check_cloud_execution_mode(settings),
        _check_live_gemini(settings),
        _check_model_3_5(settings),
        _check_revision(),
        _check_gcs(settings),
        _check_firestore(settings),
        _check_pubsub(settings),
        _check_worker_handler(settings),
        _check_fixture_pdfs(),
        _check_no_stale_runs(state),
        _check_audit_verifier(state),
    ]
    failed = [c for c in checks if c.status != "PASS"]
    overall = "PASS" if not failed else "FAIL"
    return {
        "overall": overall,
        "checks": [c.as_dict() for c in checks],
        "failed_count": len(failed),
        "passed_count": len(checks) - len(failed),
        "observed": {
            "app_env": settings.app_env.value,
            "execution_mode": settings.execution_mode,
            "gemini_backend": settings.gemini_backend.value,
            "gemini_model": settings.gemini_model,
            "object_store_backend": settings.object_store_backend.value,
            "state_store_backend": settings.state_store_backend.value,
            "event_bus_backend": settings.event_bus_backend.value,
            "cloud_run_revision": os.environ.get("K_REVISION")
            or os.environ.get("CLOUD_RUN_REVISION"),
            # Never include secrets / project billing ids beyond non-secret project id.
            "google_cloud_project_set": bool(settings.google_cloud_project),
            "google_cloud_location": settings.google_cloud_location,
        },
    }
