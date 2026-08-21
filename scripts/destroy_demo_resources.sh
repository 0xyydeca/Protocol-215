#!/usr/bin/env bash
# Destroy Protocol 215 demo resources (requires explicit confirmation).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TF_DIR="${ROOT}/infra/terraform"

echo "This will run 'terraform destroy' in ${TF_DIR}."
echo "Resources that may still incur charges until destroyed/cleaned:"
echo "  - Artifact Registry image storage"
echo "  - GCS object storage"
echo "  - Firestore storage / ops"
echo "  - Pub/Sub message retention"
echo "  - Cloud Logging retention"
echo "  - Vertex AI usage (if any)"
echo
read -r -p "Type 'destroy-protocol-215' to confirm: " answer
if [[ "$answer" != "destroy-protocol-215" ]]; then
  echo "Aborted."
  exit 0
fi

cd "$TF_DIR"
if [[ ! -f terraform.tfvars ]]; then
  echo "terraform.tfvars not found. Create it from terraform.tfvars.example first." >&2
  exit 1
fi

terraform init -input=false
terraform destroy -input=false -auto-approve

echo "Destroy complete. Verify the GCP console for leftover images or logs."
