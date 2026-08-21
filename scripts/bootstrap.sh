#!/usr/bin/env bash
# Bootstrap local Python + Node dependencies for Protocol 215.
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
    echo "uv not found. Install uv or place a binary at .tools/uv" >&2
    exit 1
  fi
fi

echo "==> Using uv: $UV_BIN"
"$UV_BIN" python install 3.12
"$UV_BIN" sync --extra dev

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "==> Created .env from .env.example"
fi

mkdir -p data/object_store data/sqlite

echo "==> Installing frontend dependencies"
(cd apps/web && npm install)

echo "==> Bootstrap complete"
