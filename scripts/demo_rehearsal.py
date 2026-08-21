#!/usr/bin/env python3
"""Timed local demo rehearsal — exercises real workflow (no hardcoded UI state)."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fastapi.testclient import TestClient

from protocol215.api.app import create_app
from protocol215.api.container import build_container
from protocol215.config import AppEnv, Settings, clear_settings_cache
from protocol215.domain.enums import ApprovalStatus, WorkflowStatus
from protocol215.fixtures import PDF_V1, PDF_V2


def main() -> int:
    clear_settings_cache()
    tmp = ROOT / "data" / "demo_rehearsal"
    tmp.mkdir(parents=True, exist_ok=True)
    settings = Settings(
        app_env=AppEnv.TEST,
        local_object_store_path=tmp / "objects",
        sqlite_path=tmp / "db.sqlite",
        execution_mode="local",
        gemini_backend="fake",
    )
    container = build_container(settings)
    app = create_app(settings=settings, container=container)
    client = TestClient(app)

    t0 = time.perf_counter()
    clicks: list[str] = []

    # Reset
    r = client.post("/api/demo/reset")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["sites_restored"] == 3
    assert body["participants_restored"] == 5
    clicks.append("POST /api/demo/reset")

    ready = client.get("/readyz").json()
    clicks.append("GET /readyz (mode indicators)")
    assert ready.get("synthetic_study") is True
    assert ready.get("compiler_mode") == "fake"
    assert ready.get("demo_mode", {}).get("runtime") == "Local"

    # Upload start
    files = {
        "old_protocol": ("v1.pdf", PDF_V1.read_bytes(), "application/pdf"),
        "new_protocol": ("v2.pdf", PDF_V2.read_bytes(), "application/pdf"),
    }
    created = client.post("/api/runs", files=files)
    assert created.status_code == 202, created.text
    run_id = created.json()["run_id"]
    clicks.append("POST /api/runs (upload v1+v2)")
    t_upload = time.perf_counter()

    pending = None
    status = None
    for _ in range(80):
        status = client.get(f"/api/runs/{run_id}").json()
        if status["status"] == WorkflowStatus.AWAITING_APPROVAL.value:
            pending = status.get("pending_approval")
            break
        if status["status"] in {
            WorkflowStatus.FAILED_TERMINAL.value,
            WorkflowStatus.FAILED_RETRYABLE.value,
            WorkflowStatus.COMPLETED.value,
        }:
            break
        time.sleep(0.05)
    t_pause = time.perf_counter()
    clicks.append("poll GET /api/runs/{id} until AWAITING_APPROVAL")

    assert pending is not None, status
    changes = client.get(f"/api/runs/{run_id}/changes").json()
    findings = client.get(f"/api/runs/{run_id}/findings").json()
    actions = client.get(f"/api/runs/{run_id}/actions").json()
    clicks.extend(
        [
            "GET .../changes",
            "GET .../findings",
            "GET .../actions",
        ]
    )

    codes = {f.get("code", "") for f in findings}
    summaries = " ".join(f.get("summary", "") for f in findings).lower()

    checks = {
        "five_semantic_changes": len(changes) == 5,
        "green_actions_present": any(
            a.get("authorized_tier") == "GREEN" and (a.get("executed") or a.get("status") == "executed")
            for a in actions
        ),
        "boston_training_block": any("BOSTON" in c or "TRAINING" in c for c in codes)
        or "boston" in summaries,
        "seattle_approval_block": any("SEATTLE" in c or "APPROVAL" in c for c in codes)
        or "seattle" in summaries,
        "p001_immutability": any("P001" in c or "IMMUTABLE" in c for c in codes)
        or "p001" in summaries,
        "phoenix_p002_conflict": any("P002" in c or "COURIER" in c for c in codes)
        or "p002" in summaries
        or "courier" in summaries,
        "amber_pending": pending is not None,
    }

    # Approve + resume
    apr = client.post(
        f"/api/runs/{run_id}/approvals/{pending['approval_id']}",
        json={
            "decision": ApprovalStatus.APPROVED.value,
            "expected_state_version": pending["expected_state_version"],
        },
    )
    assert apr.status_code == 202, apr.text
    clicks.append("POST approval (Approve)")
    t_approve = time.perf_counter()

    for _ in range(80):
        status = client.get(f"/api/runs/{run_id}").json()
        if status["status"] in {
            WorkflowStatus.COMPLETED.value,
            WorkflowStatus.COMPLETED_WITH_BLOCKS.value,
            WorkflowStatus.MANIFEST_READY.value,
            WorkflowStatus.VERIFYING.value,
        }:
            break
        if status.get("manifest") or status["status"].startswith("COMPLETED"):
            break
        time.sleep(0.05)
        # Manifest may appear while status still completing
        man = client.get(f"/api/runs/{run_id}/manifest")
        if man.status_code == 200:
            break

    manifest_resp = None
    for _ in range(40):
        manifest_resp = client.get(f"/api/runs/{run_id}/manifest")
        if manifest_resp.status_code == 200:
            break
        time.sleep(0.05)
    clicks.append("GET .../manifest")
    t_end = time.perf_counter()

    assert manifest_resp is not None and manifest_resp.status_code == 200, status
    manifest = manifest_resp.json()
    audit = client.get(f"/api/runs/{run_id}/audit/verify").json()
    clicks.append("GET .../audit/verify")

    checks["successful_resume"] = status["status"] in {
        WorkflowStatus.COMPLETED.value,
        WorkflowStatus.COMPLETED_WITH_BLOCKS.value,
        WorkflowStatus.MANIFEST_READY.value,
        WorkflowStatus.VERIFYING.value,
    } or manifest is not None
    checks["verified_manifest"] = bool(manifest.get("invariants")) and audit.get("ok") is True
    checks["resume_after_approval"] = any(
        a.get("authorized_tier") == "AMBER" and (a.get("executed") or a.get("approved"))
        for a in client.get(f"/api/runs/{run_id}/actions").json()
    )

    report = {
        "elapsed_seconds": {
            "reset_to_upload": round(t_upload - t0, 3),
            "upload_to_approval_pause": round(t_pause - t_upload, 3),
            "approve_to_manifest": round(t_end - t_approve, 3),
            "total_wall": round(t_end - t0, 3),
        },
        "judge_facing_budget_seconds": 240,
        "within_4_minutes": (t_end - t0) < 240,
        "mode": {
            "execution_mode": ready.get("execution_mode"),
            "compiler_mode": ready.get("compiler_mode"),
            "gemini_model": ready.get("gemini_model"),
            "note": "Fake Compiler — do not call live",
        },
        "checks": checks,
        "all_demo_path_checks_passed": all(checks.values()),
        "clicks": clicks,
        "run_id": run_id,
        "change_count": len(changes),
        "finding_count": len(findings),
        "audit_ok": audit.get("ok"),
        "reset_twin": {
            "sites": body["sites_restored"],
            "participants": body["participants_restored"],
        },
    }

    out = ROOT / "demo" / "rehearsal_results.json"
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["all_demo_path_checks_passed"] and report["within_4_minutes"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
