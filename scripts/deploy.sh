#!/usr/bin/env bash
# Deploy Protocol 215 to Google Cloud (requires explicit confirmation).
# Does not run unless the operator types 'yes'.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TF_DIR="${ROOT}/infra/terraform"
cd "$ROOT"

confirm() {
  local prompt="$1"
  read -r -p "${prompt} [yes/NO]: " answer
  [[ "$answer" == "yes" ]]
}

echo "==> Checking gcloud authentication"
if ! gcloud auth print-access-token >/dev/null 2>&1; then
  echo "gcloud is not authenticated. Run: gcloud auth login" >&2
  exit 1
fi

ACTIVE_ACCOUNT="$(gcloud config get-value account 2>/dev/null || true)"
ACTIVE_PROJECT="$(gcloud config get-value project 2>/dev/null || true)"
echo "    account: ${ACTIVE_ACCOUNT:-unknown}"
echo "    gcloud project: ${ACTIVE_PROJECT:-unset}"

PROJECT_ID="${PROJECT_ID:-${GOOGLE_CLOUD_PROJECT:-$ACTIVE_PROJECT}}"
REGION="${REGION:-us-central1}"
BUCKET_SUFFIX="${BUCKET_SUFFIX:-}"
IMAGE_TAG="${IMAGE_TAG:-$(git rev-parse --short HEAD 2>/dev/null || date +%Y%m%d%H%M%S)}"
GEMINI_MODEL="${GEMINI_MODEL:-gemini-3.5-flash}"
MAX_INSTANCES="${MAX_INSTANCES:-2}"

if [[ -z "$PROJECT_ID" ]]; then
  echo "PROJECT_ID / GOOGLE_CLOUD_PROJECT is required" >&2
  exit 1
fi
if [[ -z "$BUCKET_SUFFIX" ]]; then
  echo "BUCKET_SUFFIX is required (used for globally unique GCS bucket name)" >&2
  exit 1
fi

echo "==> Selected project: ${PROJECT_ID}"
if [[ -n "$ACTIVE_PROJECT" && "$ACTIVE_PROJECT" != "$PROJECT_ID" ]]; then
  echo "WARNING: gcloud default project (${ACTIVE_PROJECT}) differs from PROJECT_ID (${PROJECT_ID})"
fi

echo
echo "Resources that will be created / updated (summary):"
echo "  - Required Google APIs"
echo "  - Artifact Registry: protocol-215-images"
echo "  - GCS bucket: protocol-215-artifacts-${BUCKET_SUFFIX} (private)"
echo "  - Firestore Native database (if create_firestore_database=true)"
echo "  - Pub/Sub topics: protocol-215-events, protocol-215-dead-letter"
echo "  - Authenticated push subscription → private worker"
echo "  - Cloud Run: protocol-215-web (public), protocol-215-worker (private)"
echo "  - Service accounts: web, worker, pubsub-invoker + least-privilege IAM"
echo "  - Image tag: ${IMAGE_TAG}"
echo "  - Max instances: ${MAX_INSTANCES} (min 0 / scale-to-zero)"
echo "  - Gemini model: ${GEMINI_MODEL}"
echo

if ! confirm "Proceed with image build + terraform plan/apply for project ${PROJECT_ID}?"; then
  echo "Aborted (no changes applied)."
  exit 0
fi

export PROJECT_ID REGION IMAGE_TAG
export PUSH=true
echo "==> Building and pushing versioned images"
bash "${ROOT}/scripts/build_images.sh"

echo "==> Writing terraform.tfvars (local only; gitignored)"
cat >"${TF_DIR}/terraform.tfvars" <<EOF
project_id    = "${PROJECT_ID}"
region        = "${REGION}"
bucket_suffix = "${BUCKET_SUFFIX}"
gemini_model  = "${GEMINI_MODEL}"
web_image_tag = "${IMAGE_TAG}"
worker_image_tag = "${IMAGE_TAG}"
max_instances = ${MAX_INSTANCES}
min_instances = 0
EOF

cd "$TF_DIR"
terraform init -input=false

echo "==> terraform fmt"
terraform fmt -recursive
terraform fmt -check -recursive

echo "==> terraform validate"
terraform validate

echo "==> terraform plan"
terraform plan -input=false -out=tfplan

echo
if ! confirm "Apply this Terraform plan now? This creates/updates billable resources"; then
  echo "Plan saved as tfplan but not applied."
  exit 0
fi

echo "==> terraform apply"
terraform apply -input=false tfplan

WEB_URL="$(terraform output -raw web_url)"
WORKER_URL="$(terraform output -raw worker_url)"

echo
echo "Web URL (public):    ${WEB_URL}"
echo "Worker URL (private): ${WORKER_URL}"
echo

export WEB_URL WORKER_URL
bash "${ROOT}/scripts/cloud_smoke_test.sh"
