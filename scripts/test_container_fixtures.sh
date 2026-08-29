#!/usr/bin/env bash
# Verify Trial Twin + protocol fixtures exist inside built images.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TAG="${IMAGE_TAG:-local-fixtures}"
WEB_IMG="protocol-215-web:${TAG}"
WORKER_IMG="protocol-215-worker:${TAG}"

cd "$ROOT"
echo "Building web image ${WEB_IMG}"
docker build -f apps/web/Dockerfile -t "$WEB_IMG" .
echo "Building worker image ${WORKER_IMG}"
docker build -f apps/worker/Dockerfile -t "$WORKER_IMG" .

check_image() {
  local img="$1"
  echo "==> fixture check ${img}"
  docker run --rm --entrypoint bash "$img" -c '
    set -e
    test -f /app/fixtures/protocols/AURORA-101_Protocol_v1.0.pdf
    test -f /app/fixtures/protocols/AURORA-101_Protocol_v2.0.pdf
    test -f /app/fixtures/study_state/aurora_101_sites.json
    test -f /app/fixtures/study_state/aurora_101_participants.json
    cd /app
    uv run python - <<PY
from protocol215.simulator.twin import load_sites, load_participants
sites=load_sites()
parts=load_participants()
assert len(sites)>=1 and len(parts)>=1, (len(sites), len(parts))
print("OK sites", len(sites), "participants", len(parts))
PY
  '
}

check_image "$WEB_IMG"
check_image "$WORKER_IMG"
echo "PASS container fixture checks"
