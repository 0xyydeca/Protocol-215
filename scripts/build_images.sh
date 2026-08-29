#!/usr/bin/env bash
# Build and (optionally) push versioned images to Artifact Registry.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PROJECT_ID="${PROJECT_ID:-${GOOGLE_CLOUD_PROJECT:-}}"
REGION="${REGION:-us-central1}"
IMAGE_TAG="${IMAGE_TAG:-$(git rev-parse --short HEAD 2>/dev/null || date +%Y%m%d%H%M%S)}"
AR_REPO="${AR_REPO:-protocol-215-images}"
PUSH="${PUSH:-false}"

if [[ -z "$PROJECT_ID" ]]; then
  echo "PROJECT_ID (or GOOGLE_CLOUD_PROJECT) is required" >&2
  exit 1
fi

REGISTRY="${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}"
WEB_IMAGE="${REGISTRY}/protocol-215-web:${IMAGE_TAG}"
WORKER_IMAGE="${REGISTRY}/protocol-215-worker:${IMAGE_TAG}"

echo "Building images with tag ${IMAGE_TAG}"
echo "  web:    ${WEB_IMAGE}"
echo "  worker: ${WORKER_IMAGE}"

PLATFORM="${DOCKER_PLATFORM:-linux/amd64}"
echo "  platform: ${PLATFORM}"

docker build --platform "${PLATFORM}" -f apps/web/Dockerfile -t "${WEB_IMAGE}" -t "${REGISTRY}/protocol-215-web:latest" .
docker build --platform "${PLATFORM}" -f apps/worker/Dockerfile -t "${WORKER_IMAGE}" -t "${REGISTRY}/protocol-215-worker:latest" .

if [[ "$PUSH" == "true" ]]; then
  echo "Configuring docker auth for Artifact Registry…"
  gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet
  docker push "${WEB_IMAGE}"
  docker push "${WORKER_IMAGE}"
  docker push "${REGISTRY}/protocol-215-web:latest"
  docker push "${REGISTRY}/protocol-215-worker:latest"
  echo "Pushed ${WEB_IMAGE} and ${WORKER_IMAGE}"
else
  echo "Images built locally (PUSH=false). Set PUSH=true to push to Artifact Registry."
fi

echo "WEB_IMAGE=${WEB_IMAGE}"
echo "WORKER_IMAGE=${WORKER_IMAGE}"
echo "IMAGE_TAG=${IMAGE_TAG}"
