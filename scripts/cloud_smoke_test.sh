#!/usr/bin/env bash
# Cloud smoke + optional e2e against deployed Protocol 215.
set -euo pipefail

WEB_URL="${WEB_URL:-}"
WORKER_URL="${WORKER_URL:-}"
LEVEL="${1:-smoke}" # smoke | e2e

if [[ -z "$WEB_URL" ]]; then
  if command -v terraform >/dev/null 2>&1 && [[ -d infra/terraform ]]; then
    WEB_URL="$(cd infra/terraform && terraform output -raw web_url 2>/dev/null || true)"
    WORKER_URL="$(cd infra/terraform && terraform output -raw worker_url 2>/dev/null || true)"
  fi
fi

if [[ -z "$WEB_URL" ]]; then
  echo "WEB_URL is required (or terraform outputs available)" >&2
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
fail=0

echo "==> Smoke level=${LEVEL} web=${WEB_URL}"

HZ="$(curl -fsS --max-time 30 "${WEB_URL%/}/healthz" || true)"
echo "  /healthz => ${HZ:0:200}"
echo "$HZ" | grep -q '"status"' || { echo "FAIL healthz"; fail=1; }

RZ_CODE="$(curl -sS -o /tmp/p215-readyz.json -w '%{http_code}' --max-time 60 "${WEB_URL%/}/readyz" || true)"
echo "  /readyz HTTP ${RZ_CODE}"
cat /tmp/p215-readyz.json || true
echo
python3 - <<'PY' || fail=1
import json,sys
d=json.load(open("/tmp/p215-readyz.json"))
adapters=d.get("actual_adapters") or {}
print("actual_adapters", adapters)
if d.get("status") != "ok":
    print("FAIL readyz status", d.get("status"))
    sys.exit(1)
# Cloud must not report local adapters
bad=False
for k, expect in [
    ("object_store","GCSObjectStore"),
    ("state_store","FirestoreStateStore"),
    ("event_bus","PubSubEventBus"),
]:
    got=adapters.get(k)
    if got and got != expect:
        print(f"FAIL adapter {k}: {got} != {expect}")
        bad=True
if bad:
    sys.exit(1)
print("PASS readyz + actual_adapters")
PY

if [[ -n "$WORKER_URL" ]]; then
  echo "Worker URL (private): ${WORKER_URL}"
  if curl -fsS --max-time 10 "${WORKER_URL%/}/healthz" >/tmp/p215-worker-hz.json 2>/dev/null; then
    echo "  WARNING: worker /healthz publicly reachable"
    fail=1
  else
    echo "  OK: worker not publicly reachable"
  fi
fi

if [[ "$LEVEL" == "e2e" ]]; then
  echo "==> E2E fixture upload through approval/manifest"
  PDF1="$ROOT/fixtures/protocols/AURORA-101_Protocol_v1.0.pdf"
  PDF2="$ROOT/fixtures/protocols/AURORA-101_Protocol_v2.0.pdf"
  [[ -f "$PDF1" && -f "$PDF2" ]] || { echo "FAIL missing fixture PDFs"; exit 1; }
  curl -fsS -X POST "${WEB_URL%/}/api/demo/reset?confirm=true" >/tmp/p215-reset.json
  CREATE="$(curl -fsS --max-time 120 -X POST "${WEB_URL%/}/api/runs" \
    -F "old_protocol=@${PDF1}" -F "new_protocol=@${PDF2}" -F "study_id=AURORA-101")"
  echo "$CREATE" > /tmp/p215-create.json
  RID="$(python3 -c 'import json;print(json.load(open("/tmp/p215-create.json"))["run_id"])')"
  echo "run_id=$RID"
  python3 - <<PY
import json, time, urllib.request, urllib.error, sys
base="${WEB_URL}".rstrip("/")
rid="$RID"
terminal={"AWAITING_APPROVAL","COMPLETED","COMPLETED_WITH_BLOCKS","FAILED_RETRYABLE","FAILED_TERMINAL","FAILED"}
start=time.time()
d={}
while time.time()-start < 540:
    with urllib.request.urlopen(f"{base}/api/runs/{rid}", timeout=30) as r:
        d=json.load(r)
    print(time.strftime("%H:%M:%S"), d.get("status"), d.get("checkpoint"), d.get("error_summary"))
    if d.get("status") in terminal:
        break
    time.sleep(3)
else:
    print("FAIL timeout waiting for terminal/pause")
    sys.exit(1)
if d.get("status") in {"FAILED_RETRYABLE","FAILED_TERMINAL","FAILED"}:
    print("FAIL workflow", d.get("error_summary"))
    sys.exit(1)
if d.get("status") != "AWAITING_APPROVAL":
    print("FAIL expected AWAITING_APPROVAL got", d.get("status"))
    sys.exit(1)
# approve
with urllib.request.urlopen(f"{base}/api/runs/{rid}/approvals", timeout=30) as r:
    apps=json.load(r)
if not apps:
    print("FAIL no approvals")
    sys.exit(1)
aid=apps[0]["approval_id"]
sv=d["state_version"]
req=urllib.request.Request(
    f"{base}/api/runs/{rid}/approvals/{aid}",
    data=json.dumps({"decision":"approved","expected_state_version":apps[0].get("expected_state_version", sv)}).encode(),
    headers={"Content-Type":"application/json"},
    method="POST",
)
with urllib.request.urlopen(req, timeout=60) as r:
    print("approve", r.status, r.read()[:200])
# wait for complete
start=time.time()
while time.time()-start < 540:
    with urllib.request.urlopen(f"{base}/api/runs/{rid}", timeout=30) as r:
        d=json.load(r)
    print(time.strftime("%H:%M:%S"), d.get("status"), d.get("checkpoint"))
    if d.get("status") in {"COMPLETED","COMPLETED_WITH_BLOCKS","FAILED_RETRYABLE","FAILED_TERMINAL","FAILED"}:
        break
    time.sleep(3)
else:
    print("FAIL timeout after approve")
    sys.exit(1)
if d.get("status") not in {"COMPLETED","COMPLETED_WITH_BLOCKS"}:
    print("FAIL final", d.get("status"), d.get("error_summary"))
    sys.exit(1)
try:
    with urllib.request.urlopen(f"{base}/api/runs/{rid}/manifest", timeout=30) as r:
        m=json.load(r)
    print("PASS e2e manifest keys", list(m)[:8] if isinstance(m, dict) else type(m))
except urllib.error.HTTPError as e:
    print("FAIL manifest", e.code, e.read()[:200])
    sys.exit(1)
PY
fi

if [[ "$fail" -ne 0 ]]; then
  echo "Smoke test FAILED"
  exit 1
fi
echo "Smoke test passed (level=${LEVEL})"
