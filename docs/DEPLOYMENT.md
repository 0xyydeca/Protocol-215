# DEPLOYMENT.md — Protocol 215

## Status

| Path | Status |
| --- | --- |
| Local fake-mode | Supported (`GEMINI_BACKEND=fake`) |
| Local Vertex Gemini | Supported with ADC + project |
| Cloud Run + Terraform | Scripts + IaC shipped; **apply only with explicit confirmation** |

Do not claim a hosted URL until `scripts/deploy.sh` has succeeded in your project.

## Prerequisites

- `gcloud` authenticated (`gcloud auth login`, `gcloud auth application-default login` as needed)
- Billing enabled on the target project (your responsibility; never commit billing account IDs)
- Terraform ≥ 1.5, Docker
- Unique `BUCKET_SUFFIX` for the GCS bucket name

## Local (no cloud)

```bash
./scripts/bootstrap.sh
./scripts/run_local.sh
cd apps/web && npm run dev
```

See README §15–16.

## Live Gemini (local process)

```bash
# .env
GEMINI_BACKEND=vertex
GOOGLE_CLOUD_PROJECT=YOUR_PROJECT
GOOGLE_CLOUD_LOCATION=us-central1
GEMINI_MODEL=gemini-3.5-flash
```

Confirm UI Mode bar shows **Live Gemini** and the model id. Vertex usage is billable.

## Google Cloud demo deploy

Preferred:

```bash
export PROJECT_ID=YOUR_PROJECT
export BUCKET_SUFFIX=your-unique-suffix
export REGION=us-central1
./scripts/deploy.sh
```

The script checks auth, prints resources, requires typing **`yes`**, builds images, runs `terraform fmt` / `validate` / `plan` / `apply`, then smoke tests (`scripts/cloud_smoke_test.sh`).

Manual Terraform: `infra/terraform/README.md`.

### After deploy — verify Mode bar

- **Google Cloud**
- **Live Gemini** (if `GEMINI_BACKEND=vertex` on the service)
- **Revision:** Cloud Run `K_REVISION`
- Web URL from Terraform outputs / Console

### Demo reset (cloud)

```bash
CONFIRM_DEMO_RESET=yes ./scripts/reset_demo.sh --confirm --api https://YOUR-WEB-URL
# or POST /api/demo/reset?confirm=true
```

## Cleanup / destroy

```bash
./scripts/destroy_demo_resources.sh
# confirm: destroy-protocol-215
```

Then inspect Artifact Registry, GCS, Firestore, Logging, and billing alerts. Scale-to-zero ≠ zero cost (storage/logs/images).

## Related files

- `scripts/deploy.sh`, `scripts/build_images.sh`, `scripts/destroy_demo_resources.sh`
- `infra/terraform/*.tf`
- `docs/CLOUD_ADAPTERS.md`
- `ARCHITECTURE.md`
