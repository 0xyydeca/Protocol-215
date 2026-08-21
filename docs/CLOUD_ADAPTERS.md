# Cloud Adapters (Prompt 11)

Adapters implement the existing ports (`ObjectStore`, `StateStore`, `EventBus`) for Google Cloud.
**No resources are deployed by this stage.** Live GCP success is not claimed.

## Components

| Adapter | Module | Port |
| --- | --- | --- |
| GCS object store | `protocol215.adapters.object_store_gcs.GCSObjectStore` | `ObjectStore` |
| Firestore state | `protocol215.adapters.state_store_firestore.FirestoreStateStore` | `StateStore` |
| Pub/Sub bus | `protocol215.adapters.event_bus_pubsub.PubSubEventBus` | `EventBus` |
| Push parser | `parse_pubsub_push_envelope` | — |
| Worker handler | `protocol215.cloud.worker.AmendmentWorkerHandler` | — |
| Worker HTTP | `apps.worker.main:create_worker_app` → `POST /pubsub/push` | — |
| Structured logs | `protocol215.cloud.logging.emit_cloud_log` | — |

### Deterministic GCS paths

- `runs/{run_id}/protocols/v{version}.pdf`
- `runs/{run_id}/manifest.json`
- `runs/{run_id}/manifest.html`
- `runs/{run_id}/artifacts/{name}`
- `demo/{name}`

Uploads carry `content_type`, `sha256`, and `access=private` metadata. Size is bounded by `GCS_MAX_UPLOAD_BYTES` / constructor `max_upload_bytes`. Credentials use ADC / runtime service account only — never JSON keys in code.

### Firestore collections

`runs`, `protocol_versions` (metadata only — **no PDF bytes**), `protocol_irs`, `changes`, `sites`, `participants`, `findings`, `actions`, `action_keys`, `approvals`, `approval_decisions`, `audit_events`, `manifests`, `workflow_sessions`, `processed_events`.

Transactions cover:

- idempotent action writes (`save_action_idempotent`)
- approval consumption + state-version checks (`consume_approval`)
- manifest finalization (`finalize_manifest`)
- event dedupe (`record_processed_event`)

Cloud mode uses `SERVER_TIMESTAMP` on `_updated_at`.

### Pub/Sub envelope (`schema_version=1`)

Fields: `event_id`, `event_type`, `schema_version`, `run_id`, `occurred_at`, `invocation_id`, `approval_id`, `correlation_id`, plus optional dead-letter metadata.

Event types: `amendment.received`, `amendment.resume`.

Worker ACK rules:

- **2xx** — processed, duplicate, pause (`AWAITING_APPROVAL`), completion, or terminal/permanent error (for DLQ policy)
- **5xx** — retryable workflow failure (`RetryableWorkerError`)
- Does **not** hold the request open waiting for human approval

### IAM (documented intent — not provisioned here)

Separate least-privilege SAs for web vs worker: scoped GCS object R/W, Pub/Sub publish/consume, Firestore R/W, Logging write. No public bucket ACLs.

## Optional install

```bash
# From protocol-215/
uv sync --extra cloud
# or: pip install -e ".[cloud]"
```

## Test matrix

| Test | Mode | Notes |
| --- | --- | --- |
| `test_gcs_metadata_and_size_bound` | **Mocked** | MagicMock Storage client |
| `test_firestore_action_idempotency_across_restarts` | **Fake / emulated** | In-memory `FakeFirestore` |
| `test_firestore_approval_consumption_and_stale_version` | **Fake / emulated** | Transactional consume |
| `test_firestore_manifest_finalization_state_version` | **Fake / emulated** | |
| `test_firestore_audit_persistence` | **Fake / emulated** | |
| `test_malformed_pubsub_envelope` | **Unit** | No network |
| `test_duplicate_pubsub_event` | **Fake** | Worker + FakeFirestore |
| `test_start_and_resume_events` | **Fake** | |
| `test_retryable_and_terminal_worker_errors` | **Fake** | |
| `test_worker_http_push_endpoint` | **Mocked HTTP** | FastAPI TestClient |
| `test_pubsub_publisher_attributes` | **Mocked** | MagicMock Publisher |
| `test_cloud_log_redacts_sensitive_fields` | **Unit** | |

**Live GCP:** not executed. Marker `live_cloud` is reserved for future opt-in (`RUN_LIVE_CLOUD_TESTS=1`). Do not treat green unit tests as proof of live cloud connectivity.

```bash
.venv/bin/pytest tests/unit/test_cloud_adapters.py -q
```
