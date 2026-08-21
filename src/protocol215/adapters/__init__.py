"""Local adapters package exports (no Google Cloud SDK in application services)."""

from __future__ import annotations

from pathlib import Path

from protocol215.adapters.audit_log import HashChainedAuditLog, verify_audit_chain
from protocol215.adapters.clock import DeterministicClock, SystemClock
from protocol215.adapters.event_bus_inprocess import InProcessEventBus
from protocol215.adapters.fakes import FakeActionPlanner, FakeProtocolCompiler
from protocol215.adapters.gemini import VertexGeminiProtocolCompiler
from protocol215.adapters.gemini.factory import build_protocol_compiler
from protocol215.adapters.identifiers import (
    DeterministicIdentifierGenerator,
    UUIDIdentifierGenerator,
)
from protocol215.adapters.object_store_local import LocalFileObjectStore
from protocol215.adapters.state_store_memory import InMemoryStateStore
from protocol215.adapters.state_store_sqlite import SQLiteStateStore
from protocol215.config import (
    EventBusBackend,
    GeminiBackend,
    ObjectStoreBackend,
    Settings,
    StateStoreBackend,
)
from protocol215.ports import HealthProbe


class LocalObjectStoreProbe:
    name = "object_store"

    def __init__(self, root: Path) -> None:
        self._root = root

    def check(self) -> tuple[bool, str]:
        try:
            self._root.mkdir(parents=True, exist_ok=True)
            probe = self._root / ".health_probe"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return True, f"local writable at {self._root}"
        except OSError as exc:
            return False, f"local object store unavailable: {exc}"


class GcsObjectStoreProbe:
    name = "object_store"

    def __init__(self, project: str | None, bucket: str | None = None) -> None:
        self._project = project
        self._bucket = bucket

    def check(self) -> tuple[bool, str]:
        if not self._project:
            return False, "GCS backend requires GOOGLE_CLOUD_PROJECT"
        if not self._bucket:
            return False, "GCS backend requires GCS_BUCKET"
        return (
            True,
            f"GCS configured (project={self._project}, bucket={self._bucket}; live I/O deferred)",
        )


class MemoryStateStoreProbe:
    name = "state_store"

    def check(self) -> tuple[bool, str]:
        return True, "in-memory state store ready"


class SqliteStateStoreProbe:
    name = "state_store"

    def __init__(self, path: Path) -> None:
        self._path = path

    def check(self) -> tuple[bool, str]:
        try:
            store = SQLiteStateStore(self._path)
            store.close()
            return True, f"sqlite ready at {self._path}"
        except OSError as exc:
            return False, f"sqlite unavailable: {exc}"


class FirestoreStateStoreProbe:
    name = "state_store"

    def __init__(self, project: str | None) -> None:
        self._project = project

    def check(self) -> tuple[bool, str]:
        if not self._project:
            return False, "Firestore backend requires GOOGLE_CLOUD_PROJECT"
        return True, f"Firestore configured (project={self._project}; live I/O deferred)"


class InProcessEventBusProbe:
    name = "event_bus"

    def check(self) -> tuple[bool, str]:
        return True, "in-process event bus ready"


class PubSubEventBusProbe:
    name = "event_bus"

    def __init__(self, project: str | None) -> None:
        self._project = project

    def check(self) -> tuple[bool, str]:
        if not self._project:
            return False, "Pub/Sub backend requires GOOGLE_CLOUD_PROJECT"
        return True, f"Pub/Sub configured (project={self._project}; live I/O deferred)"


class FakeGeminiProbe:
    name = "gemini"

    def __init__(self, model: str) -> None:
        self._model = model

    def check(self) -> tuple[bool, str]:
        return True, f"fake Gemini ready (model={self._model})"


class VertexGeminiProbe:
    name = "gemini"

    def __init__(self, project: str | None, model: str) -> None:
        self._project = project
        self._model = model

    def check(self) -> tuple[bool, str]:
        if not self._project:
            return False, "Vertex Gemini requires GOOGLE_CLOUD_PROJECT"
        return False, "Vertex Gemini not configured in scaffold (use GEMINI_BACKEND=fake)"


def build_probes(settings: Settings) -> list[HealthProbe]:
    probes: list[HealthProbe] = []

    if settings.object_store_backend == ObjectStoreBackend.LOCAL:
        probes.append(LocalObjectStoreProbe(settings.local_object_store_path))
    else:
        probes.append(
            GcsObjectStoreProbe(settings.google_cloud_project, settings.gcs_bucket)
        )

    if settings.state_store_backend == StateStoreBackend.MEMORY:
        probes.append(MemoryStateStoreProbe())
    elif settings.state_store_backend == StateStoreBackend.SQLITE:
        probes.append(SqliteStateStoreProbe(settings.sqlite_path))
    else:
        probes.append(FirestoreStateStoreProbe(settings.google_cloud_project))

    if settings.event_bus_backend == EventBusBackend.INPROCESS:
        probes.append(InProcessEventBusProbe())
    else:
        probes.append(PubSubEventBusProbe(settings.google_cloud_project))

    if settings.gemini_backend == GeminiBackend.FAKE:
        probes.append(FakeGeminiProbe(settings.gemini_model))
    else:
        probes.append(VertexGeminiProbe(settings.google_cloud_project, settings.gemini_model))

    return probes


__all__ = [
    "DeterministicClock",
    "DeterministicIdentifierGenerator",
    "FakeActionPlanner",
    "FakeProtocolCompiler",
    "HashChainedAuditLog",
    "InMemoryStateStore",
    "InProcessEventBus",
    "LocalFileObjectStore",
    "SQLiteStateStore",
    "SystemClock",
    "UUIDIdentifierGenerator",
    "VertexGeminiProtocolCompiler",
    "build_probes",
    "build_protocol_compiler",
    "verify_audit_chain",
]
