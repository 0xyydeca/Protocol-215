"""Backend adapter factories — honor Settings backend enums."""

from __future__ import annotations

import logging
from typing import Any

from protocol215.adapters.event_bus_inprocess import InProcessEventBus
from protocol215.adapters.event_bus_pubsub import PubSubEventBus
from protocol215.adapters.object_store_gcs import GCSObjectStore
from protocol215.adapters.object_store_local import LocalFileObjectStore
from protocol215.adapters.state_store_firestore import FirestoreStateStore
from protocol215.adapters.state_store_memory import InMemoryStateStore
from protocol215.adapters.state_store_sqlite import SQLiteStateStore
from protocol215.config import (
    EventBusBackend,
    ObjectStoreBackend,
    Settings,
    StateStoreBackend,
)
from protocol215.ports import EventBus, ObjectStore, StateStore

logger = logging.getLogger("protocol215.factories")


def build_object_store(settings: Settings) -> ObjectStore:
    if settings.object_store_backend == ObjectStoreBackend.GCS:
        if not settings.gcs_bucket:
            raise ValueError("GCS_BUCKET is required when OBJECT_STORE_BACKEND=gcs")
        return GCSObjectStore(
            bucket_name=settings.gcs_bucket,
            project=settings.google_cloud_project,
            max_upload_bytes=settings.gcs_max_upload_bytes,
        )
    settings.local_object_store_path.mkdir(parents=True, exist_ok=True)
    return LocalFileObjectStore(settings.local_object_store_path)


def build_state_store(settings: Settings) -> StateStore:
    if settings.state_store_backend == StateStoreBackend.FIRESTORE:
        return FirestoreStateStore(
            project=settings.google_cloud_project,
            database=settings.firestore_database,
        )
    if settings.state_store_backend == StateStoreBackend.SQLITE:
        settings.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        return SQLiteStateStore(settings.sqlite_path)
    return InMemoryStateStore()


def build_event_bus(settings: Settings) -> EventBus:
    if settings.event_bus_backend == EventBusBackend.PUBSUB:
        if not settings.google_cloud_project:
            raise ValueError("GOOGLE_CLOUD_PROJECT is required when EVENT_BUS_BACKEND=pubsub")
        return PubSubEventBus(
            project=settings.google_cloud_project,
            topic_received=settings.pubsub_topic_received,
            topic_resume=settings.pubsub_topic_resume,
        )
    return InProcessEventBus()


def adapter_class_name(obj: Any) -> str:
    return type(obj).__name__


def log_selected_adapters(
    *,
    settings: Settings,
    object_store: ObjectStore,
    state_store: StateStore,
    event_bus: EventBus,
    compiler: Any,
) -> None:
    """Log non-secret adapter selection at startup."""
    logger.info(
        "adapters.selected app_env=%s execution_mode=%s model_id=%s "
        "object_store=%s state_store=%s event_bus=%s compiler=%s",
        settings.app_env.value,
        settings.execution_mode,
        settings.gemini_model,
        adapter_class_name(object_store),
        adapter_class_name(state_store),
        adapter_class_name(event_bus),
        adapter_class_name(compiler),
    )
