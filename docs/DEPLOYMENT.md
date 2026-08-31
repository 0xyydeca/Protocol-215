# DEPLOYMENT.md — Protocol 215

## Live deployment (verified)

| Item | Value |
| --- | --- |
| **Hosted URL** | https://protocol-215-web-u6nfupvmhq-uc.a.run.app |
| **Recording mode** | https://protocol-215-web-u6nfupvmhq-uc.a.run.app/?demo=1 |
| **Repository** | https://github.com/0xyydeca/Protocol-215 |
| **GCP project** | `protocol-215-demo` |
| **Region** | `us-central1` |
| **Gemini model** | `gemini-3.5-flash` (Vertex AI) |
| **Latest verified E2E** | 2026-08-30 — see `docs/CLOUD_E2E_RESULTS.md` (**PASS**) |

### Runtime stack (cloud)

| Component | Service / adapter |
| --- | --- |
| Web UI + API | Cloud Run `protocol-215-web` (public) |
| Worker | Cloud Run `protocol-215-worker` (Pub/Sub push only) |
| Object store | `GCSObjectStore` |
| State | `FirestoreStateStore` |
| Events | `PubSubEventBus` on topic `protocol-215-events` |
| IR compilation | `VertexGeminiProtocolCompiler` |
| Orchestration | Google ADK 2.x resumable graph |

Terraform: `infra/terraform/`. Deploy entrypoint: `scripts/deploy.sh` (requires typing `yes`).

## Status matrix

| Path | Status |
| --- | --- |
| **Hosted cloud demo** | Deployed and E2E-verified (`docs/CLOUD_E2E_RESULTS.md`) |
| Local fake-mode | Supported (`GEMINI_BACKEND=fake`) for CI and offline dev |
| Local Vertex Gemini | Supported with ADC + project |
| Re-deploy / upgrade | Run `scripts/deploy.sh` with new image tag |

## Prerequisites (new deploy or rebuild)

- `gcloud` authenticated (`gcloud auth login`, `gcloud auth application-default login` as needed)
- Billing enabled on the target project (never commit billing account IDs)
- Terraform ≥ 1.5, Docker or Cloud Build for images
- Unique `BUCKET_SUFFIX` for the GCS bucket name

## Local development (no cloud)

```bash
./scripts/bootstrap.sh
./scripts/run_local.sh
cd apps/web && npm run dev
```

Default `.env` uses memory/local/inprocess/fake adapters — no GCP credentials required. See README §15–16.

## Live Gemini (local process)

```bash
# .env
GEMINI_BACKEND=vertex
GOOGLE_CLOUD_PROJECT=YOUR_PROJECT
GOOGLE_CLOUD_LOCATION=us-central1
GEMINI_MODEL=gemini-3.5-flash
```

Confirm UI Mode bar shows **Live Gemini** and the model id. Vertex usage is billable.

## Google Cloud deploy (initial or refresh)

```bash
export PROJECT_ID=YOUR_PROJECT
export BUCKET_SUFFIX=your-unique-suffix
export REGION=us-central1
./scripts/deploy.sh
```

The script checks auth, prints resources, requires typing **`yes`**, builds images, runs `terraform fmt` / `validate` / `plan` / `apply`, then smoke tests (`scripts/cloud_smoke_test.sh`).

Full cloud path test:

```bash
CONFIRM_RESET=yes ./scripts/cloud_e2e_test.sh
```

Manual Terraform: `infra/terraform/README.md`.

### After deploy — verify Mode bar

On the hosted URL, confirm backend-observed values:

- **Google Cloud**
- **Live Gemini** (when `GEMINI_BACKEND=vertex` on the service)
- **Model:** `gemini-3.5-flash` (or configured `GEMINI_MODEL`)
- **Revision:** Cloud Run `K_REVISION`

Evidence class: `docs/CLOUD_E2E_RESULTS.md`.

### Demo reset (cloud)

```bash
CONFIRM_DEMO_RESET=yes ./scripts/reset_demo.sh --confirm --api https://protocol-215-web-u6nfupvmhq-uc.a.run.app
# or POST /api/demo/reset?confirm=true
```

## Cleanup / destroy

```bash
./scripts/destroy_demo_resources.sh
# confirm: destroy-protocol-215
```

Then inspect Artifact Registry, GCS, Firestore, Logging, and billing alerts. Scale-to-zero ≠ zero cost (storage/logs/images).

## Related files

- `scripts/deploy.sh`, `scripts/build_images.sh`, `scripts/destroy_demo_resources.sh`, `scripts/cloud_e2e_test.py`
- `infra/terraform/*.tf`
- `docs/CLOUD_ADAPTERS.md`
- `docs/CLOUD_E2E_RESULTS.md`
- `ARCHITECTURE.md`
