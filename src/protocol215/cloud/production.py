"""Production Cloud Run worker composition."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Response, status

from protocol215.adapters.gemini.factory import build_protocol_compiler
from protocol215.adapters.session_store_firestore import FirestoreSessionService
from protocol215.api.factories import (
    adapter_class_name,
    build_event_bus,
    build_object_store,
    build_state_store,
    log_selected_adapters,
)
from protocol215.cloud.worker import AmendmentWorkerHandler
from protocol215.config import (
    AdkSessionBackend,
    EventBusBackend,
    ObjectStoreBackend,
    Settings,
    StateStoreBackend,
    get_settings,
)
from protocol215.observability import configure_logging
from protocol215.simulator.twin import load_participants, load_sites
from protocol215.workflow.cloud_driver import CloudWorkflowDriver

logger = logging.getLogger("protocol215.worker.production")

# Written on successful production composition for recording-readiness probes.
WORKER_HEARTBEAT_COLLECTION = "worker_heartbeats"


def build_adk_session_service(settings: Settings) -> Any:
    """Persistent ADK SessionService for cloud; Sqlite for local/tests."""
    if settings.adk_session_backend == AdkSessionBackend.FIRESTORE:
        return FirestoreSessionService(project=settings.google_cloud_project)
    if settings.adk_session_backend == AdkSessionBackend.SQLITE:
        from google.adk.sessions.sqlite_session_service import SqliteSessionService

        path = Path(settings.adk_session_sqlite_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        return SqliteSessionService(str(path))
    from google.adk.sessions import InMemorySessionService

    return InMemorySessionService()  # type: ignore[no-untyped-call]


def build_cloud_workflow_runner(settings: Settings) -> CloudWorkflowDriver:
    state = build_state_store(settings)
    objects = build_object_store(settings)
    events = build_event_bus(settings)
    compiler = build_protocol_compiler(settings)
    session_service = build_adk_session_service(settings)
    log_selected_adapters(
        settings=settings,
        object_store=objects,
        state_store=state,
        event_bus=events,
        compiler=compiler,
    )
    return CloudWorkflowDriver(
        settings=settings,
        state=state,
        objects=objects,
        events=events,
        session_service=session_service,
        compiler=compiler,
    )


def build_worker_handler(settings: Settings) -> AmendmentWorkerHandler:
    runner = build_cloud_workflow_runner(settings)
    return AmendmentWorkerHandler(state=runner.state, runner=runner)


def _write_worker_heartbeat(settings: Settings, *, handler_ok: bool) -> None:
    """Persist current revision heartbeat for recording-readiness (best-effort)."""
    if settings.state_store_backend != StateStoreBackend.FIRESTORE:
        return
    try:
        from google.cloud import firestore

        revision = os.environ.get("K_REVISION") or os.environ.get("CLOUD_RUN_REVISION") or "local"
        db = firestore.Client(project=settings.google_cloud_project)
        db.collection(WORKER_HEARTBEAT_COLLECTION).document("current").set(
            {
                "revision": revision,
                "handler_configured": handler_ok,
                "updated_at": firestore.SERVER_TIMESTAMP,
                "service": "protocol-215-worker",
            },
            merge=True,
        )
    except Exception:  # noqa: BLE001
        logger.exception("worker.heartbeat_write_failed")


def _fixtures_ok() -> tuple[bool, str]:
    try:
        sites = load_sites()
        participants = load_participants()
        root = Path(__file__).resolve().parents[3]
        pdf_v1 = root / "fixtures/protocols/AURORA-101_Protocol_v1.0.pdf"
        pdf_v2 = root / "fixtures/protocols/AURORA-101_Protocol_v2.0.pdf"
        if not pdf_v1.is_file() or not pdf_v2.is_file():
            return False, "protocol fixture PDFs missing"
        if not sites or not participants:
            return False, "twin sites/participants empty"
        return True, f"sites={len(sites)} participants={len(participants)}"
    except Exception as exc:  # noqa: BLE001
        return False, f"{type(exc).__name__}: {exc}"


def create_production_worker_app(settings: Settings | None = None) -> FastAPI:
    """Compose a fully wired worker: handler required, readiness is strict."""
    from protocol215.cloud.http_worker import create_worker_app

    configure_logging()
    cfg = settings or get_settings()
    handler = build_worker_handler(cfg)
    app = create_worker_app(handler=handler, require_oidc=cfg.worker_require_oidc)
    app.state.production = True
    app.state.settings = cfg
    app.state.handler = handler
    _write_worker_heartbeat(cfg, handler_ok=True)

    @app.get("/readyz")
    def worker_readyz(response: Response) -> dict[str, Any]:
        checks: dict[str, dict[str, Any]] = {}
        ok = True

        def add(name: str, passed: bool, detail: str) -> None:
            nonlocal ok
            checks[name] = {"ok": passed, "detail": detail}
            if not passed:
                ok = False

        active = app.state.handler
        add("handler_configured", active is not None, type(active).__name__ if active else "none")

        # Adapter honesty: cloud worker must not be on local/memory/inprocess.
        add(
            "state_store_firestore",
            cfg.state_store_backend == StateStoreBackend.FIRESTORE,
            cfg.state_store_backend.value,
        )
        add(
            "object_store_gcs",
            cfg.object_store_backend == ObjectStoreBackend.GCS,
            cfg.object_store_backend.value,
        )
        add(
            "event_bus_pubsub",
            cfg.event_bus_backend == EventBusBackend.PUBSUB,
            cfg.event_bus_backend.value,
        )

        try:
            _ = active.state.list_runs() if active else None
            add("firestore_readable", True, "list_runs ok")
        except Exception as exc:  # noqa: BLE001
            add("firestore_readable", False, f"{type(exc).__name__}: {exc}")

        try:
            from google.cloud import storage as gcs  # type: ignore[attr-defined]

            if not cfg.gcs_bucket:
                add("gcs_readable", False, "GCS_BUCKET unset")
            else:
                client = gcs.Client(project=cfg.google_cloud_project)
                bucket = client.bucket(cfg.gcs_bucket)
                # Prefer objects.list over buckets.get (IAM often lacks buckets.get).
                next(bucket.list_blobs(max_results=1), None)
                add("gcs_readable", True, f"bucket={cfg.gcs_bucket}")
        except Exception as exc:  # noqa: BLE001
            add("gcs_readable", False, f"{type(exc).__name__}: {exc}")

        try:
            from google.cloud import pubsub_v1  # type: ignore[attr-defined]

            pub = pubsub_v1.PublisherClient()
            path = pub.topic_path(cfg.google_cloud_project, cfg.pubsub_topic_received)
            pub.get_topic(request={"topic": path}, timeout=8)
            add("pubsub_valid", True, cfg.pubsub_topic_received)
        except Exception as exc:  # noqa: BLE001
            add("pubsub_valid", False, f"{type(exc).__name__}: {exc}")

        try:
            from protocol215.adapters.gemini.client import probe_vertex_gemini

            if cfg.gemini_backend.value != "vertex":
                add("vertex_gemini", False, f"backend={cfg.gemini_backend.value}")
            else:
                probe_vertex_gemini(
                    project=cfg.google_cloud_project or "",
                    location=cfg.google_cloud_location,
                    model=cfg.gemini_model,
                )
                add("vertex_gemini", True, cfg.gemini_model)
        except Exception as exc:  # noqa: BLE001
            add("vertex_gemini", False, f"{type(exc).__name__}: {exc}")

        fix_ok, fix_detail = _fixtures_ok()
        add("fixtures_available", fix_ok, fix_detail)

        runner = getattr(active, "runner", None) if active else None
        actual = {
            "object_store": adapter_class_name(getattr(runner, "objects", None) or object()),
            "state_store": adapter_class_name(getattr(runner, "state", None) or object()),
            "event_bus": adapter_class_name(getattr(runner, "events", None) or object()),
            "compiler": adapter_class_name(getattr(runner, "compiler", None) or object()),
            "session_service": adapter_class_name(
                getattr(runner, "session_service", None) or object()
            ),
            "handler": adapter_class_name(active) if active else None,
        }

        if not ok:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "ok" if ok else "unavailable",
            "service": "protocol-215-worker",
            "checks": checks,
            "actual_adapters": actual,
            "cloud_run_revision": os.environ.get("K_REVISION")
            or os.environ.get("CLOUD_RUN_REVISION"),
        }

    return app


def create_production_worker_app_default() -> FastAPI:
    return create_production_worker_app()
