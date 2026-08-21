#!/usr/bin/env bash
# Start API (and optionally print web instructions) for local development.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

UV_BIN="${UV_BIN:-}"
if [[ -z "$UV_BIN" ]]; then
  if [[ -x "$ROOT/.tools/uv" ]]; then
    UV_BIN="$ROOT/.tools/uv"
  elif command -v uv >/dev/null 2>&1; then
    UV_BIN="$(command -v uv)"
  else
    echo "uv not found" >&2
    exit 1
  fi
fi

if [[ ! -f .env ]]; then
  cp .env.example .env
fi

# shellcheck disable=SC1091
set -a
source .env
set +a

HOST="${API_HOST:-127.0.0.1}"
PORT="${API_PORT:-8000}"

echo "Starting Protocol 215 API on http://${HOST}:${PORT}"
echo "In another terminal: cd apps/web && npm run dev"
exec "$UV_BIN" run uvicorn apps.api.main:app --reload --host "$HOST" --port "$PORT"
