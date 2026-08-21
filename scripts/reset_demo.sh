#!/usr/bin/env bash
# Reset Protocol 215 synthetic demo state only (preserve fixtures + infra).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

API_BASE="${API_BASE:-http://127.0.0.1:8000}"
APP_ENV="${APP_ENV:-local}"
CONFIRM="${CONFIRM_DEMO_RESET:-}"

usage() {
  cat <<'EOF'
Usage: ./scripts/reset_demo.sh [--confirm] [--api URL]

Clears runs, actions, approvals, manifests, and local object-store uploads.
Restores twin baseline from fixtures (3 sites, 5 participants, logistics).
Does NOT delete fixtures/protocols or GCP infrastructure.

Cloud mode (APP_ENV=cloud) requires --confirm or CONFIRM_DEMO_RESET=yes.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --confirm) CONFIRM=yes; shift ;;
    --api) API_BASE="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage; exit 1 ;;
  esac
done

if [[ "${APP_ENV}" == "cloud" && "${CONFIRM}" != "yes" && "${CONFIRM}" != "true" && "${CONFIRM}" != "1" ]]; then
  echo "ERROR: Cloud demo reset requires confirmation." >&2
  echo "Re-run with: CONFIRM_DEMO_RESET=yes ./scripts/reset_demo.sh --confirm" >&2
  exit 2
fi

QUERY=""
if [[ "${CONFIRM}" == "yes" || "${CONFIRM}" == "true" || "${CONFIRM}" == "1" ]]; then
  QUERY="?confirm=true"
fi

echo "Resetting Protocol 215 demo via ${API_BASE}/api/demo/reset${QUERY}"
if command -v curl >/dev/null 2>&1; then
  RESP="$(curl -sS -X POST "${API_BASE}/api/demo/reset${QUERY}" -H 'Accept: application/json' || true)"
  if [[ -z "${RESP}" ]]; then
    echo "API unreachable — performing local filesystem reset fallback."
    rm -f data/sqlite/protocol215.db
    rm -rf data/object_store
    mkdir -p data/object_store data/sqlite
    echo "Local sqlite + object store cleared. Fixtures under fixtures/ untouched."
    exit 0
  fi
  echo "${RESP}"
  echo "${RESP}" | grep -q '"ok":\s*true\|"ok": true' || {
    echo "Reset failed." >&2
    exit 1
  }
else
  echo "curl not found; clearing local demo files only."
  rm -f data/sqlite/protocol215.db
  rm -rf data/object_store
  mkdir -p data/object_store data/sqlite
fi

echo "Done. Twin baseline available from fixtures (SITE-001/002/003, P001–P005)."
exit 0
