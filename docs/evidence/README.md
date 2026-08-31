# Google Cloud evidence — Protocol 215

Sanitized submission evidence captured from **verified** GCP CLI/API queries on **2026-08-31 04:28 UTC**. Values are not fabricated; HTML sources are in this folder for reproducibility via `scripts/render_evidence_screenshots.py`.

**Video demo run (screenshots 01–05):** `run-43534f6f-af0a-4e46-8757-d52c91aec564`  
**Automated release E2E run:** see `docs/CLOUD_E2E_RESULTS.md` → **Final release E2E** (may differ after demo reset).

| Field | Value |
| --- | --- |
| GCP project | `protocol-215-demo` |
| Region | `us-central1` |
| Hosted URL | https://protocol-215-web-u6nfupvmhq-uc.a.run.app |
| Web revision (video + capture) | `protocol-215-web-00014-vjz` |
| Worker revision (video run doc) | `protocol-215-worker-00012-zvc` |
| Model | `gemini-3.5-flash` |
| GCS bucket | `protocol-215-artifacts-ky20260829` |

## Images

### `01-firestore-completed-run.png`

| | |
| --- | --- |
| **Proves** | Video run exists in Firestore; `status=COMPLETED`, `checkpoint=CompleteRun`, `compiler_model=gemini-3.5-flash`, full `event_sequence`; `processed_events` includes `amendment.received` (`evt-c13a2077-…`) and `amendment.resume` (`evt-f5ee4f91-…`) |
| **Run ID** | `run-43534f6f-af0a-4e46-8757-d52c91aec564` |
| **Source** | Firestore `runs/{run_id}` + `processed_events` via `google-cloud-firestore` |

### `02-gcs-protocols-same-run.png`

| | |
| --- | --- |
| **Proves** | Both protocol PDFs stored under **exactly** `runs/run-43534f6f-af0a-4e46-8757-d52c91aec564/protocols/` (`v1.0.pdf`, `v2.0.pdf`) |
| **Run ID** | `run-43534f6f-af0a-4e46-8757-d52c91aec564` |
| **Source** | `gsutil ls -l gs://protocol-215-artifacts-ky20260829/runs/run-43534…/protocols/` |

### `03-pubsub-workflow.png`

| | |
| --- | --- |
| **Proves** | Topics `protocol-215-events` and `protocol-215-dead-letter`; push subscription `protocol-215-worker-push` → worker `/pubsub/push` (OIDC) |
| **Run ID** | N/A (infrastructure) |
| **Source** | `gcloud pubsub topics list` + `gcloud pubsub subscriptions list` |
| **Note** | Does **not** show historical message bodies; event delivery for the video run is proven via `processed_events` and worker logs |

### `04-cloud-run-services.png`

| | |
| --- | --- |
| **Proves** | Separate public **web** and authenticated **worker** services; active revisions; `/readyz` reports Live Gemini + `gemini-3.5-flash` |
| **Web revision** | `protocol-215-web-00014-vjz` |
| **Worker revision** | `protocol-215-worker-00012-zvc` |
| **Source** | `gcloud run services describe` + `GET /readyz` |

### `05-manifest.png`

| | |
| --- | --- |
| **Proves** | Completed run manifest (5 changes, 10 actions); audit chain verify `ok: true`, 20 events |
| **Run ID** | `run-43534f6f-af0a-4e46-8757-d52c91aec564` |
| **Source** | `GET /api/runs/{id}/manifest` + `GET /api/runs/{id}/audit/verify` |

## Reproduce

```bash
# Requires: gcloud auth, gsutil, uv + cloud extras, apps/web npm ci + playwright chromium
.tools/uv sync --extra cloud
cd apps/web && npm ci && npx playwright install chromium && cd ../..
.tools/uv run python scripts/render_evidence_screenshots.py
```

## Verification limits (honest)

| Check | Result |
| --- | --- |
| Release git commit embedded in Cloud Run image | **Not verified** — containers do not expose `GIT_SHA`; E2E records `git rev-parse HEAD` at test time |
| Video run survives demo reset | E2E reset may delete demo runs; capture **before** reset or re-verify Firestore if needed |
| `session_id` on completed status API | May be `null` after completion; resume proof captured at approval time in E2E |

## Related

- Automated acceptance: `docs/CLOUD_E2E_RESULTS.md`
- Video timestamp map: `docs/VIDEO_EVIDENCE.md`
- Submission checklist: `docs/SUBMISSION_CHECKLIST.md`
