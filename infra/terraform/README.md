# Protocol 215 — Terraform (Prompt 12A)

Infrastructure-as-code for the hackathon demo. **Do not apply from CI without an explicit human confirmation.** This stage ships plans and scripts only; applying creates billable GCP resources.

## Layout

| File | Purpose |
| --- | --- |
| `apis.tf` | Required Google API enablement |
| `storage.tf` | Artifact Registry, private GCS bucket, Firestore Native |
| `pubsub.tf` | `protocol-215-events`, dead-letter topic, authenticated push sub |
| `iam.tf` | Web / worker / Pub/Sub invoker SAs + least-privilege bindings |
| `cloud_run.tf` | Public web + private worker Cloud Run services |
| `variables.tf` / `outputs.tf` | Inputs and URLs |
| `terraform.tfvars.example` | Safe example values (no secrets) |

## Resources created

1. Project APIs (Run, AR, Storage, Pub/Sub, Firestore, Vertex, Logging, IAM, …)
2. Artifact Registry repo `protocol-215-images`
3. Private GCS bucket `protocol-215-artifacts-{bucket_suffix}` (UBLA + public access prevention)
4. Firestore Native database `(default)` (optional via `create_firestore_database`)
5. Pub/Sub topic `protocol-215-events`
6. Dead-letter topic `protocol-215-dead-letter`
7. Authenticated push subscription → worker `/pubsub/push` (OIDC)
8. Cloud Run `protocol-215-web` (public invoker for judging)
9. Cloud Run `protocol-215-worker` (internal ingress; invoker = Pub/Sub SA only)
10–12. Service accounts: web, worker, pubsub-invoker
13. Least-privilege IAM (no Owner/Editor)
14. Structured JSON logs via runtime `structlog` + Cloud Logging agent on Cloud Run

## IAM intent

| Principal | Allowed |
| --- | --- |
| Web SA | GCS object R/W on demo bucket, Firestore user, publish to events topic, log writer |
| Worker SA | GCS object R/W, Firestore user, Vertex AI user, log writer |
| Pub/Sub invoker SA | `roles/run.invoker` **only** on the worker service |

Pub/Sub service agent receives `roles/iam.serviceAccountTokenCreator` on the invoker SA (OIDC) and publisher on the DLQ topic.

## Cloud Run

**Web:** public (`allUsers` invoker), min 0 / max 2, serves built React from the same container (`STATIC_ASSETS_DIR`), same-origin API.

**Worker:** HTTPS URL exists for Pub/Sub push, but **no `allUsers` invoker** — only the Pub/Sub OIDC service account can invoke. Min 0 / max 2, concurrency 1, bounded timeout (default 300s).

## Prerequisites

- Terraform >= 1.5
- `gcloud` authenticated to the target project
- Docker (for image builds)
- Billing enabled on the project (your responsibility; **do not commit billing account IDs**)

## Usage (manual apply)

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars   # edit project_id / bucket_suffix
terraform init
terraform fmt -check -recursive
terraform validate
terraform plan -out=tfplan
# Only after explicit confirmation:
# terraform apply tfplan
```

Preferred path: `../../scripts/deploy.sh` (checks auth, prints resources, requires confirmation, builds images, fmt/validate/plan/apply, smoke test).

## Cost controls

- **Scale-to-zero:** `min_instances = 0` on both Cloud Run services.
- **Caps:** `max_instances = 2` (override via variable).
- **GCS lifecycle:** objects deleted after 30 days (demo).
- **Budget alert:** Cloud Console → Billing → Budgets & alerts → create budget for this project. Do **not** embed a billing account ID in Terraform or git.
- **Disable / destroy:** `../../scripts/destroy_demo_resources.sh` (confirmed `terraform destroy`).
- **May still incur charges after scale-to-zero:** Artifact Registry storage, GCS storage, Firestore storage/ops, Pub/Sub retention, logging ingestion, idle Firestore, and any leftover images. Vertex calls bill when used.

## Secrets

- No service-account JSON in Terraform.
- No API keys in `tfvars` examples.
- Do not commit `terraform.tfvars`, `*.tfstate`, or `.terraform/`.

## Related scripts

- `scripts/build_images.sh`
- `scripts/deploy.sh`
- `scripts/destroy_demo_resources.sh`
- `scripts/cloud_smoke_test.sh`
