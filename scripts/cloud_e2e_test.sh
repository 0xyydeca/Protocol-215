#!/usr/bin/env bash
# Real Protocol 215 cloud E2E acceptance wrapper.
# Refuses to claim PASS against fake/local adapters (enforced in Python).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export WEB_URL="${WEB_URL:-}"
export WORKER_URL="${WORKER_URL:-}"
export GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT:-${PROJECT_ID:-protocol-215-demo}}"
export REGION="${REGION:-us-central1}"
export GCS_BUCKET="${GCS_BUCKET:-}"
export CONFIRM_RESET="${CONFIRM_RESET:-}"
export POLL_SECONDS="${POLL_SECONDS:-600}"
export ALLOW_ONE_RETRY="${ALLOW_ONE_RETRY:-1}"
export COLD_RESUME="${COLD_RESUME:-0}"

if [[ -z "$WEB_URL" || -z "$GCS_BUCKET" || -z "$WORKER_URL" ]]; then
  if command -v terraform >/dev/null 2>&1 && [[ -d infra/terraform ]]; then
    pushd infra/terraform >/dev/null
    WEB_URL="${WEB_URL:-$(terraform output -raw web_url 2>/dev/null || true)}"
    WORKER_URL="${WORKER_URL:-$(terraform output -raw worker_url 2>/dev/null || true)}"
    GCS_BUCKET="${GCS_BUCKET:-$(terraform output -raw gcs_bucket 2>/dev/null || true)}"
    popd >/dev/null
    export WEB_URL WORKER_URL GCS_BUCKET
  fi
fi

if [[ -z "$WEB_URL" ]]; then
  echo "WEB_URL is required" >&2
  exit 1
fi
if [[ -z "$WORKER_URL" ]]; then
  echo "WORKER_URL is required (authenticated worker readiness)" >&2
  exit 1
fi
if [[ -z "$GCS_BUCKET" ]]; then
  echo "GCS_BUCKET is required" >&2
  exit 1
fi
if [[ "$CONFIRM_RESET" != "yes" ]]; then
  echo "Refusing to run without CONFIRM_RESET=yes (destructive synthetic reset)." >&2
  exit 1
fi

echo "==> Protocol 215 cloud E2E"
echo "    WEB_URL=$WEB_URL"
echo "    WORKER_URL=$WORKER_URL"
echo "    GCS_BUCKET=$GCS_BUCKET"
echo "    PROJECT=$GOOGLE_CLOUD_PROJECT REGION=$REGION"

if [[ -x "$ROOT/.tools/uv" ]]; then
  exec "$ROOT/.tools/uv" run python "$ROOT/scripts/cloud_e2e_test.py" "$@"
fi
exec python3 "$ROOT/scripts/cloud_e2e_test.py" "$@"
