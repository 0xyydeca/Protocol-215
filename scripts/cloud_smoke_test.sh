#!/usr/bin/env bash
# Health smoke test against deployed web service (and optional private worker check notes).
set -euo pipefail

WEB_URL="${WEB_URL:-}"
WORKER_URL="${WORKER_URL:-}"

if [[ -z "$WEB_URL" ]]; then
  if [[ -f infra/terraform/terraform.tfstate ]] || [[ -d infra/terraform ]]; then
    if command -v terraform >/dev/null 2>&1 && [[ -d infra/terraform ]]; then
      WEB_URL="$(cd infra/terraform && terraform output -raw web_url 2>/dev/null || true)"
      WORKER_URL="$(cd infra/terraform && terraform output -raw worker_url 2>/dev/null || true)"
    fi
  fi
fi

if [[ -z "$WEB_URL" ]]; then
  echo "WEB_URL is required (or terraform outputs available)" >&2
  exit 1
fi

echo "Smoke testing web: ${WEB_URL}"
HZ="$(curl -fsS --max-time 30 "${WEB_URL%/}/healthz")"
echo "  /healthz => ${HZ}"
echo "$HZ" | grep -q '"status"' 

RZ_CODE="$(curl -sS -o /tmp/p215-readyz.json -w '%{http_code}' --max-time 30 "${WEB_URL%/}/readyz" || true)"
echo "  /readyz HTTP ${RZ_CODE}"
cat /tmp/p215-readyz.json || true
echo

if [[ -n "$WORKER_URL" ]]; then
  echo "Worker URL (private — expect failure from public networks): ${WORKER_URL}"
  if curl -fsS --max-time 10 "${WORKER_URL%/}/healthz" >/tmp/p215-worker-hz.json 2>/dev/null; then
    echo "  WARNING: worker /healthz was reachable publicly. Check ingress/IAM."
    cat /tmp/p215-worker-hz.json
    exit 2
  else
    echo "  OK: worker not publicly reachable (or requires auth) from this network."
  fi
fi

echo "Smoke test passed for web health endpoint."
