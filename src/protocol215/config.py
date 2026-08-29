"""Application settings loaded from environment / .env."""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnv(StrEnum):
    LOCAL = "local"
    TEST = "test"
    CLOUD = "cloud"


class ObjectStoreBackend(StrEnum):
    LOCAL = "local"
    GCS = "gcs"


class StateStoreBackend(StrEnum):
    MEMORY = "memory"
    SQLITE = "sqlite"
    FIRESTORE = "firestore"


class EventBusBackend(StrEnum):
    INPROCESS = "inprocess"
    PUBSUB = "pubsub"


class GeminiBackend(StrEnum):
    FAKE = "fake"
    VERTEX = "vertex"


class AdkSessionBackend(StrEnum):
    MEMORY = "memory"
    SQLITE = "sqlite"
    FIRESTORE = "firestore"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: AppEnv = AppEnv.LOCAL
    object_store_backend: ObjectStoreBackend = ObjectStoreBackend.LOCAL
    state_store_backend: StateStoreBackend = StateStoreBackend.MEMORY
    event_bus_backend: EventBusBackend = EventBusBackend.INPROCESS
    gemini_backend: GeminiBackend = GeminiBackend.FAKE
    gemini_model: str = "gemini-3.5-flash"
    google_cloud_project: str | None = None
    google_cloud_location: str = "us-central1"

    max_pdf_bytes: int = 20 * 1024 * 1024
    max_pdf_pages: int = 200
    default_study_id: str = "AURORA-101"
    default_from_version: str = "1.0"
    default_to_version: str = "2.0"
    execution_mode: str = "local"  # local | cloud — surfaced in status

    # Cloud adapter settings (no credentials — ADC / runtime SA only)
    gcs_bucket: str | None = None
    gcs_max_upload_bytes: int = 20 * 1024 * 1024
    firestore_database: str | None = None  # "(default)" when unset
    pubsub_topic_received: str = "protocol-215-events"
    pubsub_topic_resume: str = "protocol-215-events"
    worker_require_oidc: bool = False

    # ADK session persistence (cloud → firestore; tests → sqlite)
    adk_session_backend: AdkSessionBackend = AdkSessionBackend.MEMORY
    adk_session_sqlite_path: Path = Field(default=Path("data/adk_sessions.sqlite3"))

    # Gemini bounds (HttpOptions.timeout is milliseconds per google-genai)
    gemini_http_timeout_ms: int = 120_000
    gemini_max_output_tokens: int = 8192
    gemini_compile_deadline_seconds: float = 180.0
    gemini_max_retries: int = 3

    static_assets_dir: Path | None = None  # when set, serve built React (Cloud Run web)

    local_object_store_path: Path = Field(default=Path("data/object_store"))
    sqlite_path: Path = Field(default=Path("data/sqlite/protocol215.db"))
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    cors_origins: str = "http://127.0.0.1:5173,http://localhost:5173"
    # Optional authenticated worker URL for recording-readiness (server-side probe)
    worker_readyz_url: str | None = None

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def requires_gcp_project(self) -> bool:
        return (
            self.object_store_backend == ObjectStoreBackend.GCS
            or self.state_store_backend == StateStoreBackend.FIRESTORE
            or self.event_bus_backend == EventBusBackend.PUBSUB
            or self.gemini_backend == GeminiBackend.VERTEX
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


def clear_settings_cache() -> None:
    get_settings.cache_clear()
