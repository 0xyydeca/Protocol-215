#!/usr/bin/env python3
"""Protocol 215 cloud end-to-end acceptance test.

Requires a live Cloud Run deployment with GCS, Firestore, Pub/Sub, ADK, and
Vertex Gemini 3.5+. Refuses to claim PASS when any required adapter is fake
or when probes are skipped.

Usage:
  WEB_URL=https://…run.app CONFIRM_RESET=yes python scripts/cloud_e2e_test.py
  # or: scripts/cloud_e2e_test.sh
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PDF_V1 = ROOT / "fixtures/protocols/AURORA-101_Protocol_v1.0.pdf"
PDF_V2 = ROOT / "fixtures/protocols/AURORA-101_Protocol_v2.0.pdf"
RESULTS_MD = ROOT / "docs/CLOUD_E2E_RESULTS.md"
E2E_COLLECTION = "cloud_e2e_results"
E2E_DOC = "latest"

REQUIRED_FINDINGS = {
    "FINDING_BOSTON_TRAINING_REQUIRED": "Boston training block",
    "FINDING_SEATTLE_APPROVAL_TRAINING_REQUIRED": "Seattle approval block",
    "FINDING_P001_DAY1_IMMUTABLE": "P001 completed-visit immutability",
    "FINDING_P002_COURIER_STORAGE_CONFLICT": "Phoenix P002 courier/storage conflict",
}

CLOUD_ADAPTERS = {
    "object_store": "GCSObjectStore",
    "state_store": "FirestoreStateStore",
    "event_bus": "PubSubEventBus",
}

FAKE_MARKERS = (
    "FakeProtocolCompiler",
    "InMemoryStateStore",
    "InProcessEventBus",
    "LocalFileObjectStore",
    "fake-protocol-compiler",
)


@dataclass
class FailureContext:
    run_id: str | None = None
    last_status: str | None = None
    last_checkpoint: str | None = None
    state_version: int | None = None
    elapsed_seconds: float = 0.0
    last_safe_error: str | None = None
    correlation_id: str | None = None
    pubsub_response_class: str | None = None
    dlq_message_count: int | None = None
    firestore_run_exists: bool | None = None
    gcs_pdfs_exist: bool | None = None
    web_logs: list[str] = field(default_factory=list)
    worker_logs: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


class E2EError(Exception):
    def __init__(self, message: str, ctx: FailureContext) -> None:
        super().__init__(message)
        self.ctx = ctx


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _http_json(
    method: str,
    url: str,
    *,
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 60.0,
    id_token: str | None = None,
) -> tuple[int, Any]:
    hdrs = dict(headers or {})
    if id_token:
        hdrs["Authorization"] = f"Bearer {id_token}"
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            raw = resp.read().decode("utf-8")
            body: Any = json.loads(raw) if raw else None
            return resp.status, body
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            body = json.loads(raw) if raw else {"message": str(exc)}
        except json.JSONDecodeError:
            body = {"message": raw[:500]}
        return exc.code, body


def _multipart_create(web: str, pdf1: Path, pdf2: Path, timeout: float = 60.0) -> tuple[int, Any]:
    import uuid

    boundary = f"----p215{uuid.uuid4().hex}"
    parts: list[bytes] = []

    def add_file(name: str, path: Path) -> None:
        parts.append(
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{name}"; filename="{path.name}"\r\n'
                f"Content-Type: application/pdf\r\n\r\n"
            ).encode()
            + path.read_bytes()
            + b"\r\n"
        )

    add_file("old_protocol", pdf1)
    add_file("new_protocol", pdf2)
    parts.append(
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="study_id"\r\n\r\n'
            f"AURORA-101\r\n"
            f"--{boundary}--\r\n"
        ).encode()
    )
    body = b"".join(parts)
    return _http_json(
        "POST",
        f"{web}/api/runs",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        timeout=timeout,
    )


def _gcloud_json(args: list[str]) -> Any:
    proc = subprocess.run(
        ["gcloud", *args, "--format=json"],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "gcloud failed")
    return json.loads(proc.stdout) if proc.stdout.strip() else None


def _gcloud_text(args: list[str]) -> str:
    proc = subprocess.run(
        ["gcloud", *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip()


def _fetch_id_token(audience: str, *, impersonate: str | None = None) -> str:
    """ID token for private Cloud Run. Prefer ADC; fall back to gcloud impersonation."""
    try:
        import google.auth.transport.requests
        import google.oauth2.id_token

        auth_req = google.auth.transport.requests.Request()
        return google.oauth2.id_token.fetch_id_token(auth_req, audience)  # type: ignore[no-untyped-call]
    except Exception:
        pass

    cmd = ["gcloud", "auth", "print-identity-token", f"--audiences={audience}"]
    if impersonate:
        cmd.append(f"--impersonate-service-account={impersonate}")
    proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    token = (proc.stdout or "").strip()
    if proc.returncode == 0 and token:
        return token

    # Common local path: user ADC cannot mint ID tokens — try web SA impersonation.
    if not impersonate:
        for sa in (
            os.environ.get("ID_TOKEN_IMPERSONATE_SA"),
            f"protocol-215-web@{os.environ.get('GOOGLE_CLOUD_PROJECT', 'protocol-215-demo')}.iam.gserviceaccount.com",
            f"protocol-215-pubsub-invoker@{os.environ.get('GOOGLE_CLOUD_PROJECT', 'protocol-215-demo')}.iam.gserviceaccount.com",
        ):
            if not sa:
                continue
            try:
                return _fetch_id_token(audience, impersonate=sa)
            except Exception:
                continue

    raise RuntimeError(
        f"cannot mint ID token for {audience}: {proc.stderr.strip() or proc.stdout or 'no credentials'}"
    )


def _is_gemini_3_5_plus(model: str) -> bool:
    m = (model or "").strip().lower()
    if not m:
        return False
    if re.search(r"gemini[-_]?([4-9](?:\.\d+)?|3\.([5-9]|\d{2,}))", m):
        return True
    return bool(re.search(r"gemini[-_]?3\.5", m))


def _print_failure(exc: E2EError) -> None:
    ctx = exc.ctx
    print("\n======== CLOUD E2E FAILURE ========")
    print(f"error: {exc}")
    print(f"run_id: {ctx.run_id}")
    print(f"last status: {ctx.last_status}")
    print(f"last checkpoint: {ctx.last_checkpoint}")
    print(f"state version: {ctx.state_version}")
    print(f"elapsed seconds: {ctx.elapsed_seconds:.1f}")
    print(f"last safe error: {ctx.last_safe_error}")
    print(f"correlation ID: {ctx.correlation_id}")
    print(f"Pub/Sub response class: {ctx.pubsub_response_class}")
    print(f"DLQ message count: {ctx.dlq_message_count}")
    print(f"Firestore run exists: {ctx.firestore_run_exists}")
    print(f"GCS PDFs exist: {ctx.gcs_pdfs_exist}")
    print("--- latest five web logs ---")
    for line in ctx.web_logs[-5:]:
        print(line)
    print("--- latest ten worker logs ---")
    for line in ctx.worker_logs[-10:]:
        print(line)
    for n in ctx.notes:
        print(f"note: {n}")
    print("===================================\n")


def _format_e2e_section(payload: dict[str, Any], *, heading: str) -> list[str]:
    lines = [
        heading,
        "",
        f"_Recorded: {payload.get('completed_at')} (UTC)_",
        "",
        f"**{payload.get('result')}**",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| commit_sha | `{payload.get('commit_sha')}` |",
        f"| web_url | `{payload.get('web_url')}` |",
        f"| web_revision | `{payload.get('web_revision')}` |",
        f"| worker_revision | `{payload.get('worker_revision')}` |",
        f"| gemini_model | `{payload.get('gemini_model')}` |",
        f"| run_id | `{payload.get('run_id')}` |",
        f"| correlation_id | `{payload.get('correlation_id')}` |",
        f"| start_event_id | `{payload.get('start_event_id')}` |",
        f"| session_id | `{payload.get('session_id')}` |",
        f"| invocation_id | `{payload.get('invocation_id')}` |",
        f"| elapsed_seconds | {payload.get('elapsed_seconds')} |",
        "",
        "### Adapter honesty",
        "",
        "```json",
        json.dumps(payload.get("actual_adapters") or {}, indent=2),
        "```",
        "",
        "### Checkpoint path observed",
        "",
        "```",
        " → ".join(payload.get("checkpoints_seen") or []),
        "```",
        "",
        "### Assertions",
        "",
    ]
    for name, ok in (payload.get("assertions") or {}).items():
        lines.append(f"- [{'x' if ok else ' '}] {name}")
    lines.append("")
    return lines


def _parse_historical_e2e_sections(existing: str) -> list[str]:
    marker = "## Historical E2E runs"
    if marker not in existing:
        return []
    tail = existing.split(marker, 1)[1]
    blocks: list[str] = []
    for part in tail.split("\n## E2E run "):
        part = part.strip()
        if not part:
            continue
        if part.startswith("("):
            blocks.append("## E2E run " + part)
        elif not part.startswith("## E2E run "):
            blocks.append("## E2E run " + part)
        else:
            blocks.append(part if part.startswith("##") else "## E2E run " + part)
    return blocks


def _write_results_md(payload: dict[str, Any]) -> None:
    prior = RESULTS_MD.read_text(encoding="utf-8") if RESULTS_MD.exists() else ""
    historical: list[str] = []
    if prior.strip():
        if "## Final release E2E" in prior:
            old_final = prior.split("## Historical E2E runs", 1)[0]
            archived = old_final.split("## Final release E2E", 1)[1].strip()
            if archived:
                historical.append("## E2E run (archived)\n\n" + archived)
        elif "## Verdict" in prior or "## Evidence" in prior:
            # Legacy single-block report — archive whole body after title.
            body = prior.split("\n", 1)[1].strip() if prior.startswith("# Cloud E2E") else prior.strip()
            historical.append("## E2E run (archived — pre-release layout)\n\n" + body)
        historical.extend(_parse_historical_e2e_sections(prior))

    lines = [
        "# Cloud E2E Results",
        "",
        f"_Last updated: {payload.get('completed_at')} (UTC)_",
        "",
        "Automated acceptance for the hosted Google Cloud demo. The **Final release E2E** "
        "section is the authoritative PASS for the current submission commit and revisions.",
        "",
        "## Final release E2E",
        "",
        f"**{payload.get('result')}**",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| commit_sha | `{payload.get('commit_sha')}` |",
        f"| web_url | `{payload.get('web_url')}` |",
        f"| web_revision | `{payload.get('web_revision')}` |",
        f"| worker_revision | `{payload.get('worker_revision')}` |",
        f"| gemini_model | `{payload.get('gemini_model')}` |",
        f"| run_id | `{payload.get('run_id')}` |",
        f"| correlation_id | `{payload.get('correlation_id')}` |",
        f"| start_event_id | `{payload.get('start_event_id')}` |",
        f"| session_id | `{payload.get('session_id')}` |",
        f"| invocation_id | `{payload.get('invocation_id')}` |",
        f"| elapsed_seconds | {payload.get('elapsed_seconds')} |",
        "",
        "### Adapter honesty",
        "",
        "```json",
        json.dumps(payload.get("actual_adapters") or {}, indent=2),
        "```",
        "",
        "### Checkpoint path observed",
        "",
        "```",
        " → ".join(payload.get("checkpoints_seen") or []),
        "```",
        "",
        "### Assertions",
        "",
    ]
    for name, ok in (payload.get("assertions") or {}).items():
        lines.append(f"- [{'x' if ok else ' '}] {name}")
    lines.append("")
    if historical:
        lines.extend(["## Historical E2E runs", ""])
        lines.extend(historical)
        if not lines[-1].endswith("\n"):
            lines.append("")
    RESULTS_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _persist_e2e_result(project: str, payload: dict[str, Any]) -> None:
    from google.cloud import firestore

    db = firestore.Client(project=project)
    db.collection(E2E_COLLECTION).document(E2E_DOC).set(payload)


class CloudE2E:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.web = args.web_url.rstrip("/")
        self.project = args.project
        self.region = args.region
        self.bucket = args.bucket
        self.dlq_sub = args.dlq_subscription
        self.worker_url = (args.worker_url or "").rstrip("/")
        self.ctx = FailureContext()
        self.start = time.time()
        self.checkpoints_seen: list[str] = []
        self.assertions: dict[str, bool] = {}
        self.retry_used = False

    def elapsed(self) -> float:
        return time.time() - self.start

    def fail(self, message: str, **updates: Any) -> None:
        for k, v in updates.items():
            setattr(self.ctx, k, v)
        self.ctx.elapsed_seconds = self.elapsed()
        self._enrich_diagnostics()
        raise E2EError(message, self.ctx)

    def mark(self, name: str, ok: bool, detail: str = "") -> None:
        self.assertions[name] = ok
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}{(': ' + detail) if detail else ''}")
        if not ok:
            self.fail(f"assertion failed: {name}", last_safe_error=detail or name)

    def _enrich_diagnostics(self) -> None:
        try:
            self.ctx.web_logs = self._recent_logs("protocol-215-web", limit=5)
            self.ctx.worker_logs = self._recent_logs("protocol-215-worker", limit=10)
        except Exception as exc:  # noqa: BLE001
            self.ctx.notes.append(f"log fetch failed: {type(exc).__name__}: {exc}")
        try:
            if self.dlq_sub:
                out = _gcloud_text(
                    [
                        "pubsub",
                        "subscriptions",
                        "describe",
                        self.dlq_sub,
                        f"--project={self.project}",
                        "--format=value(numUndeliveredMessages)",
                    ]
                )
                self.ctx.dlq_message_count = int(out) if out.isdigit() else None
        except Exception as exc:  # noqa: BLE001
            self.ctx.notes.append(f"dlq probe failed: {exc}")
        if self.ctx.run_id:
            try:
                from google.cloud import firestore

                db = firestore.Client(project=self.project)
                self.ctx.firestore_run_exists = (
                    db.collection("runs").document(self.ctx.run_id).get().exists
                )
            except Exception as exc:  # noqa: BLE001
                self.ctx.notes.append(f"firestore probe failed: {exc}")
            try:
                from google.cloud import storage

                client = storage.Client(project=self.project)
                bucket = client.bucket(self.bucket)
                v1 = f"runs/{self.ctx.run_id}/protocols/v1.0.pdf"
                v2 = f"runs/{self.ctx.run_id}/protocols/v2.0.pdf"
                self.ctx.gcs_pdfs_exist = bucket.blob(v1).exists() and bucket.blob(v2).exists()
            except Exception as exc:  # noqa: BLE001
                self.ctx.notes.append(f"gcs probe failed: {exc}")

    def _recent_logs(self, service: str, *, limit: int) -> list[str]:
        raw = _gcloud_json(
            [
                "logging",
                "read",
                f'resource.type="cloud_run_revision" AND resource.labels.service_name="{service}"',
                f"--project={self.project}",
                f"--limit={limit}",
                "--order=desc",
            ]
        )
        lines: list[str] = []
        if not isinstance(raw, list):
            return lines
        for entry in raw:
            ts = entry.get("timestamp", "")
            payload = entry.get("textPayload") or entry.get("jsonPayload") or {}
            if isinstance(payload, dict):
                msg = payload.get("message") or json.dumps(payload)[:200]
            else:
                msg = str(payload)[:200]
            lines.append(f"{ts} {msg}")
        return list(reversed(lines))

    def run(self) -> dict[str, Any]:
        print(f"==> Cloud E2E against {self.web}")
        print(f"    project={self.project} region={self.region} bucket={self.bucket}")

        # 1–2 health + revisions
        web_rev, worker_rev = self.step_revisions_and_health()
        # 3 readyz adapters
        ready, adapters, gemini_model = self.step_readyz()
        # 4 worker readiness
        self.step_worker_ready(worker_rev)
        # 5 reset
        self.step_reset()

        try:
            return self._run_once(web_rev, worker_rev, adapters, gemini_model, ready)
        except E2EError as first:
            if self.retry_used or not self.args.allow_one_retry:
                raise
            self.retry_used = True
            print("\n!! First attempt failed; performing one full retry as allowed\n")
            _print_failure(first)
            self.ctx = FailureContext()
            self.start = time.time()
            self.checkpoints_seen = []
            self.assertions = {}
            self.step_reset()
            return self._run_once(web_rev, worker_rev, adapters, gemini_model, ready)

    def _run_once(
        self,
        web_rev: str,
        worker_rev: str,
        adapters: dict[str, str],
        gemini_model: str,
        ready: dict[str, Any],
    ) -> dict[str, Any]:
        created = self.step_upload()
        run_id = created["run_id"]
        self.ctx.run_id = run_id
        self.ctx.correlation_id = created.get("correlation_id") or run_id
        start_event_id = created.get("event_id")
        self.mark("create_202", True, f"run_id={run_id} event_id={start_event_id}")

        status = self.step_poll_to_approval(run_id)
        self.step_assert_persistence(run_id, status, start_event_id)
        self.step_assert_changes_findings_actions(run_id, status)

        pre = self.step_capture_pre_approval(run_id, status)
        self.step_optional_worker_cold_path()
        self.step_approve(run_id, pre)
        final = self.step_poll_to_complete(run_id, pre)
        self.step_manifest_invariants_audit(run_id, final)

        commit = (
            subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            ).stdout.strip()
            or "unknown"
        )
        payload = {
            "result": "PASS",
            "completed_at": _now(),
            "commit_sha": commit,
            "web_url": self.web,
            "web_revision": web_rev,
            "worker_revision": worker_rev,
            "gemini_model": status.get("compiler_model") or gemini_model,
            "run_id": run_id,
            "correlation_id": self.ctx.correlation_id,
            "start_event_id": start_event_id,
            "session_id": pre.get("session_id"),
            "invocation_id": pre.get("invocation_id"),
            "elapsed_seconds": round(self.elapsed(), 1),
            "actual_adapters": adapters,
            "readyz": {
                "status": ready.get("status"),
                "compiler_mode": ready.get("compiler_mode"),
                "gemini_model": ready.get("gemini_model"),
            },
            "checkpoints_seen": self.checkpoints_seen,
            "assertions": dict(self.assertions),
            "retry_used": self.retry_used,
        }
        _write_results_md(payload)
        _persist_e2e_result(self.project, payload)
        self._print_pass(payload)
        return payload

    def step_revisions_and_health(self) -> tuple[str, str]:
        # Prefer /livez or /api/healthz — some Google frontends return HTML 404 for bare /healthz.
        hz_ok = False
        hz_body: Any = None
        for path in ("/livez", "/api/healthz", "/healthz"):
            code, hz_body = _http_json("GET", f"{self.web}{path}", timeout=30)
            if code == 200 and (hz_body or {}).get("status") == "ok":
                hz_ok = True
                self.mark("healthz", True, f"via {path}")
                break
        if not hz_ok:
            self.mark("healthz", False, str(hz_body)[:120])

        web_meta = _gcloud_json(
            [
                "run",
                "services",
                "describe",
                "protocol-215-web",
                f"--region={self.region}",
                f"--project={self.project}",
            ]
        )
        worker_meta = _gcloud_json(
            [
                "run",
                "services",
                "describe",
                "protocol-215-worker",
                f"--region={self.region}",
                f"--project={self.project}",
            ]
        )
        web_rev = (
            ((web_meta or {}).get("status") or {}).get("latestReadyRevisionName")
            or ((web_meta or {}).get("status") or {}).get("latestCreatedRevisionName")
            or "unknown"
        )
        worker_rev = (
            ((worker_meta or {}).get("status") or {}).get("latestReadyRevisionName")
            or ((worker_meta or {}).get("status") or {}).get("latestCreatedRevisionName")
            or "unknown"
        )
        print(f"  web revision: {web_rev}")
        print(f"  worker revision: {worker_rev}")
        # Traffic 100% on ready revision
        traffic = ((web_meta or {}).get("status") or {}).get("traffic") or []
        if traffic:
            ready_pct = sum(
                int(t.get("percent") or 0)
                for t in traffic
                if t.get("revisionName") == web_rev or t.get("latestRevision")
            )
            self.mark("web_traffic_100", ready_pct >= 100, f"percent={ready_pct}")
        return web_rev, worker_rev

    def step_readyz(self) -> tuple[dict[str, Any], dict[str, str], str]:
        code, ready = _http_json("GET", f"{self.web}/readyz", timeout=60)
        if code != 200:
            self.fail(f"/readyz HTTP {code}", last_safe_error=str(ready)[:300])
        adapters = dict((ready or {}).get("actual_adapters") or {})
        for key, expect in CLOUD_ADAPTERS.items():
            got = adapters.get(key)
            self.mark(f"adapter_{key}", got == expect, f"got={got}")
        for bad in FAKE_MARKERS:
            blob = json.dumps(ready)
            if bad in blob:
                self.fail(f"readyz still references fake/local component: {bad}")
        compiler = (ready or {}).get("compiler_mode")
        model = (
            (ready or {}).get("gemini_model")
            or ((ready or {}).get("backends") or {}).get("gemini_model")
            or ""
        )
        self.mark("live_gemini_readyz", compiler == "live_gemini", f"compiler_mode={compiler}")
        self.mark("gemini_3_5_plus", _is_gemini_3_5_plus(model), f"model={model}")
        return ready or {}, adapters, model

    def step_worker_ready(self, expected_worker_rev: str) -> None:
        if not self.worker_url:
            self.fail("WORKER_URL required for authenticated worker readiness")
        token: str | None = None
        try:
            token = _fetch_id_token(self.worker_url)
        except Exception as exc:  # noqa: BLE001
            # Fallback: Firestore heartbeat written by production worker on startup.
            try:
                from google.cloud import firestore

                db = firestore.Client(project=self.project)
                doc = db.collection("worker_heartbeats").document("current").get()
                data = doc.to_dict() if doc.exists else None
                ok = bool(data and data.get("handler_configured"))
                rev = (data or {}).get("revision")
                self.mark(
                    "worker_readyz",
                    ok,
                    f"heartbeat fallback after token error ({type(exc).__name__}); "
                    f"handler={ok} revision={rev}",
                )
                if expected_worker_rev != "unknown" and rev:
                    self.mark(
                        "worker_revision_observed",
                        str(rev) in expected_worker_rev or expected_worker_rev.endswith(str(rev)),
                        f"heartbeat_rev={rev} service={expected_worker_rev}",
                    )
                return
            except Exception as hb_exc:  # noqa: BLE001
                self.fail(
                    f"worker auth failed ({exc}); heartbeat also failed ({hb_exc})"
                )

        code, body = _http_json(
            "GET",
            f"{self.worker_url}/readyz",
            timeout=30,
            id_token=token,
        )
        ok = code == 200 and (body or {}).get("status") == "ok"
        checks = (body or {}).get("checks") or {}
        handler = checks.get("handler_configured") or {}
        self.mark(
            "worker_readyz",
            ok and bool(handler.get("ok", True)),
            f"status={code} body_status={(body or {}).get('status')}",
        )
        rev = (body or {}).get("cloud_run_revision")
        if rev and expected_worker_rev != "unknown":
            self.mark(
                "worker_revision_observed",
                rev in expected_worker_rev or expected_worker_rev.endswith(rev),
                f"readyz_rev={rev} service={expected_worker_rev}",
            )
        adapters = (body or {}).get("actual_adapters") or {}
        for bad in FAKE_MARKERS:
            if bad in json.dumps(adapters):
                self.fail(f"worker adapters include fake: {bad}")

    def step_reset(self) -> None:
        if self.args.confirm_reset != "yes":
            self.fail("Refusing reset without CONFIRM_RESET=yes")
        code, body = _http_json(
            "POST",
            f"{self.web}/api/demo/reset?confirm=true",
            timeout=120,
        )
        self.mark("demo_reset", code == 200 and (body or {}).get("ok") is True, str(body)[:160])

    def step_upload(self) -> dict[str, Any]:
        if not PDF_V1.is_file() or not PDF_V2.is_file():
            self.fail("fixture PDFs missing")
        t0 = time.time()
        code, body = _multipart_create(self.web, PDF_V1, PDF_V2, timeout=60)
        elapsed = time.time() - t0
        if code != 202:
            self.ctx.pubsub_response_class = f"create_http_{code}"
            self.fail(
                f"POST /api/runs expected 202 got {code}",
                last_safe_error=str(body)[:300],
            )
        self.mark("create_within_60s", elapsed <= 60.0, f"elapsed={elapsed:.1f}s")
        if not (body or {}).get("event_published"):
            self.fail("event_published=false — Pub/Sub publish did not succeed")
        return body or {}

    def step_poll_to_approval(self, run_id: str) -> dict[str, Any]:
        deadline = time.time() + self.args.poll_seconds
        last: dict[str, Any] = {}
        while time.time() < deadline:
            code, last = _http_json("GET", f"{self.web}/api/runs/{run_id}", timeout=15)
            if code != 200:
                time.sleep(3)
                continue
            cp = last.get("checkpoint") or last.get("current_stage")
            if cp and (not self.checkpoints_seen or self.checkpoints_seen[-1] != cp):
                self.checkpoints_seen.append(str(cp))
            status = last.get("status")
            print(
                f"  poll {status} @ {cp} sv={last.get('state_version')} "
                f"model={last.get('compiler_model')}"
            )
            self.ctx.last_status = status
            self.ctx.last_checkpoint = cp
            self.ctx.state_version = last.get("state_version")
            self.ctx.correlation_id = last.get("correlation_id") or self.ctx.correlation_id
            self.ctx.last_safe_error = last.get("last_error_detail_safe") or last.get(
                "error_summary"
            )
            if status in {"FAILED_RETRYABLE", "FAILED_TERMINAL", "FAILED"}:
                self.fail(f"run failed: {self.ctx.last_safe_error}")
            if status == "AWAITING_APPROVAL":
                self.mark("reached_awaiting_approval", True, f"checkpoints={self.checkpoints_seen}")
                # Must have moved through real compile-ish checkpoints
                joined = " ".join(self.checkpoints_seen)
                progressed = any(
                    x in joined
                    for x in (
                        "CompileOldProtocol",
                        "CompileNewProtocol",
                        "SemanticDiff",
                        "TrialTwinSimulator",
                        "ApprovalRouter",
                    )
                )
                self.mark("persisted_checkpoints", progressed, joined)
                return last
            time.sleep(3)
        self.fail("timeout waiting for AWAITING_APPROVAL", last_status=(last or {}).get("status"))

    def step_assert_persistence(
        self, run_id: str, status: dict[str, Any], start_event_id: str | None
    ) -> None:
        from google.cloud import firestore, storage

        db = firestore.Client(project=self.project)
        snap = db.collection("runs").document(run_id).get()
        self.mark("firestore_run_exists", snap.exists, run_id)
        self.ctx.firestore_run_exists = snap.exists

        client = storage.Client(project=self.project)
        bucket = client.bucket(self.bucket)
        v1 = f"runs/{run_id}/protocols/v1.0.pdf"
        v2 = f"runs/{run_id}/protocols/v2.0.pdf"
        ok_gcs = bucket.blob(v1).exists() and bucket.blob(v2).exists()
        self.ctx.gcs_pdfs_exist = ok_gcs
        self.mark("gcs_pdfs_exist", ok_gcs, f"{v1}, {v2}")

        # Pub/Sub delivery: worker must have advanced checkpoint beyond CREATED
        # and preferably logged the event. Prefer processed_events / audit.
        cp = status.get("checkpoint") or ""
        delivered = cp not in {"", "CREATED"} and status.get("status") != "CREATED"
        self.mark("pubsub_start_delivered", delivered, f"checkpoint={cp}")
        self.ctx.pubsub_response_class = "push_inferred_via_checkpoint_progress"

        # Live Gemini used on this run
        model = status.get("compiler_model") or ""
        adapters = status.get("actual_adapters") or {}
        for bad in FAKE_MARKERS:
            if bad in json.dumps({"m": model, "a": adapters}):
                self.fail(f"run still using fake/local component: {bad}")
        self.mark("run_live_gemini_3_5", _is_gemini_3_5_plus(model), f"compiler_model={model}")
        if start_event_id:
            self.mark("start_event_id_captured", True, start_event_id)

    def step_assert_changes_findings_actions(self, run_id: str, status: dict[str, Any]) -> None:
        _, changes = _http_json("GET", f"{self.web}/api/runs/{run_id}/changes", timeout=30)
        changes = changes or []
        self.mark("exactly_five_changes", len(changes) == 5, f"count={len(changes)}")
        for ch in changes:
            evidence = ch.get("evidence") or ch.get("old_evidence") or ch.get("new_evidence") or []
            if not evidence and (ch.get("old_evidence") or ch.get("new_evidence")):
                evidence = list(ch.get("old_evidence") or []) + list(ch.get("new_evidence") or [])
            pages = [e.get("page") for e in evidence if isinstance(e, dict)]
            ok = bool(pages) and all(isinstance(p, int) and p >= 1 for p in pages)
            if not ok:
                self.fail(
                    f"change {ch.get('change_id')} missing valid page evidence",
                    last_safe_error=str(ch.get("change_id")),
                )
        self.mark("all_changes_have_page_evidence", True)

        _, findings = _http_json("GET", f"{self.web}/api/runs/{run_id}/findings", timeout=30)
        codes = {f.get("code") for f in (findings or [])}
        for code, label in REQUIRED_FINDINGS.items():
            self.mark(f"finding_{code}", code in codes, label)

        _, actions = _http_json("GET", f"{self.web}/api/runs/{run_id}/actions", timeout=30)
        green = [
            a
            for a in (actions or [])
            if (a.get("authorized_tier") or "").upper() == "GREEN"
            and (a.get("status") == "executed" or a.get("executed"))
        ]
        self.mark("green_actions_completed", len(green) >= 1, f"count={len(green)}")
        # Idempotent once: each GREEN execution_id unique and executed_at present
        ids = [a.get("execution_id") for a in green]
        self.mark("green_ids_unique", len(ids) == len(set(ids)))

    def step_capture_pre_approval(self, run_id: str, status: dict[str, Any]) -> dict[str, Any]:
        _, actions = _http_json("GET", f"{self.web}/api/runs/{run_id}/actions", timeout=30)
        green = [
            a
            for a in (actions or [])
            if (a.get("authorized_tier") or "").upper() == "GREEN"
            and (a.get("status") == "executed" or a.get("executed"))
        ]
        _, approvals = _http_json("GET", f"{self.web}/api/runs/{run_id}/approvals", timeout=30)
        pending = next((a for a in (approvals or []) if a.get("status") == "pending"), None)
        if pending is None and status.get("pending_approval"):
            pending = {
                "approval_id": status["pending_approval"]["approval_id"],
                "expected_state_version": status["pending_approval"]["expected_state_version"],
                "session_id": status["pending_approval"].get("interrupt_id"),
                "invocation_id": status["pending_approval"].get("invocation_id"),
            }
        if not pending:
            self.fail("no pending approval to submit")

        # Prefer durable session metadata from Firestore
        from google.cloud import firestore

        db = firestore.Client(project=self.project)
        meta_snap = db.collection("workflow_sessions").document(run_id).get()
        meta = meta_snap.to_dict() if meta_snap.exists else {}
        session_id = (meta or {}).get("session_id") or pending.get("session_id")
        invocation_id = (meta or {}).get("invocation_id") or pending.get("invocation_id")
        return {
            "approval_id": pending["approval_id"],
            "expected_state_version": pending.get(
                "expected_state_version", status.get("state_version")
            ),
            "state_version": status.get("state_version"),
            "session_id": session_id,
            "invocation_id": invocation_id,
            "green": [
                {"execution_id": a.get("execution_id"), "executed_at": a.get("executed_at")}
                for a in green
            ],
        }

    def step_optional_worker_cold_path(self) -> None:
        """Encourage a fresh worker instance before resume when practical."""
        if not self.args.cold_resume:
            print("  [skip] worker cold-path (set COLD_RESUME=1 to force)")
            return
        print("  attempting worker scale-to-zero then restore for resume path…")
        _gcloud_text(
            [
                "run",
                "services",
                "update",
                "protocol-215-worker",
                f"--region={self.region}",
                f"--project={self.project}",
                "--min-instances=0",
                "--max-instances=0",
                "--quiet",
            ]
        )
        time.sleep(5)
        _gcloud_text(
            [
                "run",
                "services",
                "update",
                "protocol-215-worker",
                f"--region={self.region}",
                f"--project={self.project}",
                "--max-instances=2",
                "--min-instances=0",
                "--quiet",
            ]
        )
        self.mark("worker_cold_path_attempted", True)

    def step_approve(self, run_id: str, pre: dict[str, Any]) -> None:
        body = json.dumps(
            {
                "decision": "approved",
                "expected_state_version": pre["expected_state_version"],
                "comment": "cloud_e2e_test",
            }
        ).encode()
        code, resp = _http_json(
            "POST",
            f"{self.web}/api/runs/{run_id}/approvals/{pre['approval_id']}",
            data=body,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        self.mark(
            "approval_accepted",
            code in {200, 202} and (resp or {}).get("event_published") is not False,
            f"http={code} resp={str(resp)[:160]}",
        )
        self.ctx.pubsub_response_class = "amendment.resume_published"

    def step_poll_to_complete(self, run_id: str, pre: dict[str, Any]) -> dict[str, Any]:
        deadline = time.time() + self.args.poll_seconds
        last: dict[str, Any] = {}
        while time.time() < deadline:
            code, last = _http_json("GET", f"{self.web}/api/runs/{run_id}", timeout=15)
            if code != 200:
                time.sleep(3)
                continue
            status = last.get("status")
            cp = last.get("checkpoint")
            print(f"  resume-poll {status} @ {cp}")
            self.ctx.last_status = status
            self.ctx.last_checkpoint = cp
            self.ctx.state_version = last.get("state_version")
            if status in {"FAILED_RETRYABLE", "FAILED_TERMINAL", "FAILED"}:
                err = last.get("last_error_detail_safe") or last.get("error_summary")
                self.fail(f"resume failed: {err}")
            if status in {"COMPLETED", "COMPLETED_WITH_BLOCKS"}:
                self.mark("completed", True, status)
                # Same session / invocation resumed
                from google.cloud import firestore

                db = firestore.Client(project=self.project)
                meta = db.collection("workflow_sessions").document(run_id).get().to_dict() or {}
                if pre.get("session_id"):
                    self.mark(
                        "same_session_resumed",
                        meta.get("session_id") == pre["session_id"],
                        f"before={pre['session_id']} after={meta.get('session_id')}",
                    )
                if pre.get("invocation_id"):
                    # Invocation may advance; require session continuity at minimum.
                    self.mark(
                        "invocation_tracked",
                        bool(meta.get("invocation_id") or pre.get("invocation_id")),
                        f"after={meta.get('invocation_id')}",
                    )
                # GREEN ids/timestamps unchanged
                _, actions = _http_json(
                    "GET", f"{self.web}/api/runs/{run_id}/actions", timeout=30
                )
                after = {
                    a.get("execution_id"): a.get("executed_at")
                    for a in (actions or [])
                    if (a.get("authorized_tier") or "").upper() == "GREEN"
                }
                for g in pre.get("green") or []:
                    eid = g.get("execution_id")
                    if after.get(eid) != g.get("executed_at"):
                        self.fail(
                            f"GREEN action mutated after resume: {eid}",
                            last_safe_error=f"{g} vs {after.get(eid)}",
                        )
                self.mark("green_actions_immutable_across_resume", True)
                return last
            time.sleep(3)
        self.fail("timeout waiting for COMPLETED after approval")

    def step_manifest_invariants_audit(self, run_id: str, final: dict[str, Any]) -> None:
        code, manifest = _http_json("GET", f"{self.web}/api/runs/{run_id}/manifest", timeout=30)
        self.mark("manifest_exists", code == 200 and isinstance(manifest, dict))
        inv = (manifest or {}).get("invariants") or []
        failed = [i for i in inv if not i.get("passed")]
        self.mark(
            "all_invariants_pass",
            len(inv) > 0 and not failed,
            f"count={len(inv)} failed={[i.get('invariant_id') for i in failed]}",
        )
        code2, verify = _http_json(
            "GET", f"{self.web}/api/runs/{run_id}/audit/verify", timeout=30
        )
        self.mark(
            "audit_chain_verifies",
            code2 == 200 and (verify or {}).get("ok") is True,
            str(verify)[:160],
        )

    def _print_pass(self, payload: dict[str, Any]) -> None:
        print("\n======== CLOUD E2E PASS ========")
        for k in (
            "commit_sha",
            "web_revision",
            "worker_revision",
            "gemini_model",
            "run_id",
            "correlation_id",
            "elapsed_seconds",
        ):
            print(f"{k}: {payload.get(k)}")
        print("assertions:")
        for name, ok in payload.get("assertions", {}).items():
            print(f"  {'PASS' if ok else 'FAIL'} {name}")
        print(f"results written: {RESULTS_MD}")
        print("================================\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--web-url", default=os.environ.get("WEB_URL", ""))
    p.add_argument("--worker-url", default=os.environ.get("WORKER_URL", ""))
    p.add_argument(
        "--project",
        default=os.environ.get("GOOGLE_CLOUD_PROJECT")
        or os.environ.get("PROJECT_ID")
        or "protocol-215-demo",
    )
    p.add_argument("--region", default=os.environ.get("REGION", "us-central1"))
    p.add_argument(
        "--bucket",
        default=os.environ.get("GCS_BUCKET", ""),
    )
    p.add_argument(
        "--dlq-subscription",
        default=os.environ.get("DLQ_SUBSCRIPTION", "protocol-215-dead-letter-pull"),
    )
    p.add_argument("--confirm-reset", default=os.environ.get("CONFIRM_RESET", ""))
    p.add_argument("--poll-seconds", type=int, default=int(os.environ.get("POLL_SECONDS", "600")))
    p.add_argument(
        "--allow-one-retry",
        action="store_true",
        default=os.environ.get("ALLOW_ONE_RETRY", "1") not in {"0", "false", "no"},
    )
    p.add_argument(
        "--cold-resume",
        action="store_true",
        default=os.environ.get("COLD_RESUME", "") in {"1", "true", "yes"},
    )
    args = p.parse_args(argv)
    if not args.web_url:
        # Try terraform output
        tf = ROOT / "infra/terraform"
        if tf.is_dir():
            out = subprocess.run(
                ["terraform", "output", "-raw", "web_url"],
                cwd=tf,
                capture_output=True,
                text=True,
                check=False,
            )
            args.web_url = out.stdout.strip()
            wout = subprocess.run(
                ["terraform", "output", "-raw", "worker_url"],
                cwd=tf,
                capture_output=True,
                text=True,
                check=False,
            )
            if not args.worker_url:
                args.worker_url = wout.stdout.strip()
            bout = subprocess.run(
                ["terraform", "output", "-raw", "gcs_bucket"],
                cwd=tf,
                capture_output=True,
                text=True,
                check=False,
            )
            if not args.bucket:
                args.bucket = bout.stdout.strip()
    if not args.web_url:
        p.error("WEB_URL is required")
    if not args.bucket:
        p.error("GCS_BUCKET (or terraform output gcs_bucket) is required")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        CloudE2E(args).run()
        return 0
    except E2EError as exc:
        _print_failure(exc)
        fail_payload = {
            "result": "FAIL",
            "completed_at": _now(),
            "web_url": args.web_url,
            "run_id": exc.ctx.run_id,
            "error": str(exc),
            "last_status": exc.ctx.last_status,
            "last_checkpoint": exc.ctx.last_checkpoint,
            "correlation_id": exc.ctx.correlation_id,
            "elapsed_seconds": exc.ctx.elapsed_seconds,
            "assertions": {},
            "checkpoints_seen": [],
        }
        try:
            _write_results_md(fail_payload)
            _persist_e2e_result(args.project, fail_payload)
        except Exception as write_exc:  # noqa: BLE001
            print(f"could not persist failure result: {write_exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
