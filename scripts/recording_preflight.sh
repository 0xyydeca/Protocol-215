#!/usr/bin/env bash
# Judge-facing recording preflight for Protocol 215 (≤4 min demo video).
# Never prints secrets. May reset synthetic demo state only after confirmation.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

API_BASE="${API_BASE:-http://127.0.0.1:8000}"
WEB_URL="${WEB_URL:-}"
CONFIRM="${CONFIRM_DEMO_RESET:-}"
DO_RESET=0
OVERALL=PASS

usage() {
  cat <<'EOF'
Usage: ./scripts/recording_preflight.sh [--api URL] [--web URL] [--reset] [--confirm]

Checks:
  - GET /healthz and GET /readyz
  - GET /api/demo/recording-readiness (real bounded probes)
  - Public web URL reachable (WEB_URL / --web)
  - Live Gemini 3.5+ from readiness observed fields
  - Cloud Run revision present when cloud
  - Fixture PDFs on disk
  - Optional: reset synthetic demo state after confirmation

Never prints credentials, ADC paths, or API keys.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --api) API_BASE="$2"; shift 2 ;;
    --web) WEB_URL="$2"; shift 2 ;;
    --reset) DO_RESET=1; shift ;;
    --confirm) CONFIRM=yes; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage; exit 1 ;;
  esac
done

redact() {
  # Strip common secret-ish patterns if any tool leaks them into JSON.
  sed -E \
    -e 's/("?(api[_-]?key|token|password|secret|private_key|credential)"?\s*:\s*")[^"]*"/\1***"/Ig' \
    -e 's/Bearer [A-Za-z0-9._\-]+/Bearer ***/g'
}

report() {
  local status="$1"
  local name="$2"
  local detail="$3"
  printf '%-6s  %-40s  %s\n' "$status" "$name" "$detail"
  if [[ "$status" == "FAIL" ]]; then
    OVERALL=FAIL
  fi
}

echo "=== Protocol 215 recording preflight ==="
echo "API_BASE=${API_BASE}"
[[ -n "${WEB_URL}" ]] && echo "WEB_URL=${WEB_URL}"
echo

# --- healthz ---
HZ="$(curl -fsS --max-time 15 "${API_BASE%/}/healthz" 2>/dev/null || true)"
if [[ -n "${HZ}" ]] && echo "${HZ}" | grep -q '"status"[[:space:]]*:[[:space:]]*"ok"'; then
  report PASS "healthz" "ok"
else
  report FAIL "healthz" "unreachable or not ok"
fi

# --- readyz ---
RZ_CODE="$(curl -sS -o /tmp/p215-readyz.json -w '%{http_code}' --max-time 60 "${API_BASE%/}/readyz" 2>/dev/null || echo 000)"
RZ="$(cat /tmp/p215-readyz.json 2>/dev/null || true)"
if [[ "${RZ_CODE}" == "200" ]] && echo "${RZ}" | grep -q '"status"[[:space:]]*:[[:space:]]*"ok"'; then
  report PASS "readyz" "http ${RZ_CODE}"
else
  report FAIL "readyz" "http ${RZ_CODE} (local backends may still be ok for offline rehearsal)"
fi

# --- recording-readiness ---
RR_CODE="$(curl -sS -o /tmp/p215-recording.json -w '%{http_code}' --max-time 90 \
  "${API_BASE%/}/api/demo/recording-readiness" 2>/dev/null || echo 000)"
RR="$(cat /tmp/p215-recording.json 2>/dev/null | redact || true)"
if [[ -z "${RR}" ]]; then
  report FAIL "recording_readiness" "endpoint unreachable"
else
  echo
  echo "--- recording-readiness checks ---"
  # Print each check line without secrets
  python3 - "${RR}" <<'PY' 2>/dev/null || echo "${RR}" | head -c 2000
import json, sys
raw = sys.argv[1]
data = json.loads(raw)
print(f"overall={data.get('overall')} passed={data.get('passed_count')} failed={data.get('failed_count')}")
for c in data.get("checks", []):
    print(f"{c.get('status','?'):6}  {c.get('name','?'):40}  {c.get('detail','')[:160]}")
obs = data.get("observed") or {}
safe_keys = [
    "app_env", "execution_mode", "gemini_backend", "gemini_model",
    "object_store_backend", "state_store_backend", "event_bus_backend",
    "cloud_run_revision", "google_cloud_project_set", "google_cloud_location",
]
print("observed:", {k: obs.get(k) for k in safe_keys})
PY
  echo "----------------------------------"
  echo
  if echo "${RR}" | grep -q '"overall"[[:space:]]*:[[:space:]]*"PASS"'; then
    report PASS "recording_readiness" "overall PASS"
  else
    report FAIL "recording_readiness" "overall FAIL (http ${RR_CODE}) — required for official cloud recording"
  fi

  # Live Gemini 3.5+ from observed
  if echo "${RR}" | grep -q '"gemini_backend"[[:space:]]*:[[:space:]]*"vertex"' \
    && echo "${RR}" | grep -Eqi 'gemini[-_]?3\.5'; then
    report PASS "live_gemini_3_5_plus" "vertex + gemini-3.5+ observed"
  else
    report FAIL "live_gemini_3_5_plus" "require GEMINI_BACKEND=vertex and gemini-3.5+ model"
  fi

  # Cloud Run revision
  if echo "${RR}" | grep -q '"cloud_run_revision"[[:space:]]*:[[:space:]]*"'; then
    # null or empty
    if echo "${RR}" | grep -q '"cloud_run_revision"[[:space:]]*:[[:space:]]*null'; then
      report FAIL "cloud_run_revision" "revision null — not on Cloud Run"
    else
      report PASS "cloud_run_revision" "present"
    fi
  else
    report FAIL "cloud_run_revision" "missing from observed"
  fi
fi

# --- public web URL ---
if [[ -n "${WEB_URL}" ]]; then
  WCODE="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 20 "${WEB_URL%/}/" 2>/dev/null || echo 000)"
  if [[ "${WCODE}" =~ ^2|3 ]]; then
    report PASS "public_web_url" "http ${WCODE}"
  else
    report FAIL "public_web_url" "http ${WCODE} for WEB_URL"
  fi
  # Prefer Mode bar path via web /readyz proxy if same origin; optional second hit
else
  report FAIL "public_web_url" "WEB_URL / --web not provided"
fi

# --- fixture PDFs ---
V1="${ROOT}/fixtures/protocols/AURORA-101_Protocol_v1.0.pdf"
V2="${ROOT}/fixtures/protocols/AURORA-101_Protocol_v2.0.pdf"
if [[ -f "${V1}" && -f "${V2}" ]]; then
  report PASS "fixture_pdfs" "v1.0 and v2.0 present"
else
  report FAIL "fixture_pdfs" "missing fixture PDFs under fixtures/protocols/"
fi

# --- optional reset ---
if [[ "${DO_RESET}" == "1" ]]; then
  echo
  echo "Reset requested…"
  if [[ "${CONFIRM}" != "yes" && "${CONFIRM}" != "true" && "${CONFIRM}" != "1" ]]; then
    report FAIL "demo_reset" "refused — pass --confirm (or CONFIRM_DEMO_RESET=yes)"
  else
    RESET_RESP="$(curl -sS -X POST --max-time 60 \
      "${API_BASE%/}/api/demo/reset?confirm=true" -H 'Accept: application/json' 2>/dev/null | redact || true)"
    if echo "${RESET_RESP}" | grep -q '"ok"[[:space:]]*:[[:space:]]*true'; then
      report PASS "demo_reset" "synthetic demo state cleared"
    else
      report FAIL "demo_reset" "reset failed or API unreachable"
    fi
  fi
fi

echo
echo "=== PREFLIGHT ${OVERALL} ==="
if [[ "${OVERALL}" != "PASS" ]]; then
  echo "Do not claim Google Cloud / Live Gemini in the video until every required check PASSes."
  exit 1
fi
exit 0
