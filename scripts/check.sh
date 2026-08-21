#!/usr/bin/env bash
# Run formatting, lint, typecheck, pytest, and frontend checks.
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

echo "==> ruff format check"
"$UV_BIN" run ruff format --check src apps/api apps/worker tests

echo "==> ruff lint"
"$UV_BIN" run ruff check src apps/api apps/worker tests

echo "==> mypy"
"$UV_BIN" run mypy src/protocol215

echo "==> pytest"
"$UV_BIN" run pytest

echo "==> frontend vitest"
(cd apps/web && npm test -- --run)

echo "==> frontend build"
(cd apps/web && npm run build)

echo "==> All checks passed"
