"""GCS ObjectStore adapter — private bucket, metadata, size bounds."""

from __future__ import annotations

from typing import Any

from protocol215.application.hashing import sha256_hex
from protocol215.cloud.paths import (
    demo_artifact_key,
    manifest_html_key,
    manifest_json_key,
    protocol_pdf_key,
    run_artifact_key,
)


class GCSObjectStoreError(Exception):
    pass


class GCSObjectStore:
    """
    Cloud Storage adapter behind ObjectStore.

    Credentials: Application Default Credentials / attached service account only.
    Never pass JSON keys through this constructor.
    """

    def __init__(
        self,
        *,
        bucket_name: str,
        project: str | None = None,
        max_upload_bytes: int = 20 * 1024 * 1024,
        client: Any | None = None,
    ) -> None:
        if not bucket_name:
            raise GCSObjectStoreError("GCS_BUCKET is required")
        self.bucket_name = bucket_name
        self.project = project
        self.max_upload_bytes = max_upload_bytes
        if client is not None:
            self._client = client
        else:
            from google.cloud import storage  # lazy — optional cloud dep

            self._client = storage.Client(project=project)
        self._bucket = self._client.bucket(bucket_name)

    def put_bytes(
        self, key: str, data: bytes, *, content_type: str = "application/octet-stream"
    ) -> str:
        if len(data) > self.max_upload_bytes:
            raise GCSObjectStoreError(
                f"upload exceeds max size {self.max_upload_bytes} bytes (got {len(data)})"
            )
        digest = sha256_hex(data)
        blob = self._bucket.blob(key)
        # Private by default under uniform bucket-level access; never set public ACL.
        blob.metadata = {
            "sha256": digest,
            "content_type": content_type,
            "access": "private",
        }
        blob.upload_from_string(data, content_type=content_type)
        return key

    def get_bytes(self, key: str) -> bytes:
        blob = self._bucket.blob(key)
        if not blob.exists():
            raise FileNotFoundError(key)
        return blob.download_as_bytes()

    def exists(self, key: str) -> bool:
        return bool(self._bucket.blob(key).exists())

    def get_metadata(self, key: str) -> dict[str, str]:
        blob = self._bucket.blob(key)
        blob.reload()
        meta = dict(blob.metadata or {})
        meta["content_type"] = blob.content_type or meta.get("content_type", "")
        return meta

    # Convenience writers with deterministic paths
    def put_protocol_pdf(self, run_id: str, version: str, data: bytes) -> str:
        return self.put_bytes(
            protocol_pdf_key(run_id, version), data, content_type="application/pdf"
        )

    def put_manifest_json(self, run_id: str, data: bytes) -> str:
        return self.put_bytes(
            manifest_json_key(run_id), data, content_type="application/json"
        )

    def put_manifest_html(self, run_id: str, data: bytes) -> str:
        return self.put_bytes(
            manifest_html_key(run_id), data, content_type="text/html; charset=utf-8"
        )

    def put_demo_artifact(self, name: str, data: bytes, *, content_type: str) -> str:
        return self.put_bytes(demo_artifact_key(name), data, content_type=content_type)

    def put_run_artifact(
        self, run_id: str, name: str, data: bytes, *, content_type: str
    ) -> str:
        return self.put_bytes(
            run_artifact_key(run_id, name), data, content_type=content_type
        )
