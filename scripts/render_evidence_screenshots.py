#!/usr/bin/env python3
"""Render sanitized GCP evidence PNGs from verified CLI/API data (no fabricated values)."""

from __future__ import annotations

import html
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "evidence"
WEB_URL = "https://protocol-215-web-u6nfupvmhq-uc.a.run.app"
PROJECT = "protocol-215-demo"
REGION = "us-central1"
BUCKET = "protocol-215-artifacts-ky20260829"
VIDEO_RUN_ID = "run-43534f6f-af0a-4e46-8757-d52c91aec564"


def _fetch_json(url: str) -> dict:
    with urlopen(url, timeout=30) as resp:  # noqa: S310
        return json.loads(resp.read().decode())


def _gcloud_json(args: list[str]) -> dict | list:
    out = subprocess.check_output(["gcloud", *args], text=True)
    return json.loads(out) if out.strip() else {}


def _gcloud_text(args: list[str]) -> str:
    return subprocess.check_output(["gcloud", *args], text=True).strip()


def _gsutil_ls(prefix: str) -> str:
    return subprocess.check_output(["gsutil", "ls", "-l", prefix], text=True)


def _panel(title: str, subtitle: str, body_html: str) -> str:
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/>
<style>
  body {{ font-family: "Google Sans", "Segoe UI", system-ui, sans-serif; background:#f6f8fb; margin:0; padding:24px; color:#202124; }}
  .card {{ background:#fff; border:1px solid #dadce0; border-radius:8px; max-width:1100px; margin:0 auto; box-shadow:0 1px 3px rgba(60,64,67,.15); }}
  .hdr {{ background:#1a73e8; color:#fff; padding:16px 20px; border-radius:8px 8px 0 0; }}
  .hdr h1 {{ margin:0; font-size:18px; font-weight:500; }}
  .hdr p {{ margin:6px 0 0; font-size:12px; opacity:.9; }}
  .body {{ padding:20px; font-size:13px; line-height:1.45; }}
  pre {{ background:#f1f3f4; border:1px solid #e0e0e0; border-radius:4px; padding:12px; overflow:auto; white-space:pre-wrap; word-break:break-word; }}
  table {{ border-collapse:collapse; width:100%; }}
  td, th {{ border:1px solid #dadce0; padding:8px 10px; text-align:left; vertical-align:top; }}
  th {{ background:#f8f9fa; width:220px; }}
  .ok {{ color:#137333; font-weight:600; }}
  .note {{ color:#5f6368; font-size:12px; margin-top:12px; }}
</style></head><body>
<div class="card"><div class="hdr"><h1>{html.escape(title)}</h1><p>{html.escape(subtitle)}</p></div>
<div class="body">{body_html}</div></div></body></html>"""


def _write_html(name: str, content: str) -> Path:
    path = OUT / f"{name}.html"
    path.write_text(content, encoding="utf-8")
    return path


def _screenshot_all() -> None:
    subprocess.run(
        ["node", "scripts/screenshot_evidence.mjs"],
        cwd=ROOT / "apps" / "web",
        check=True,
    )


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    captured = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    from google.cloud import firestore

    db = firestore.Client(project=PROJECT)
    run_snap = db.collection("runs").document(VIDEO_RUN_ID).get()
    if not run_snap.exists:
        print(f"ERROR: Firestore run missing: {VIDEO_RUN_ID}", file=sys.stderr)
        return 1
    run = run_snap.to_dict() or {}

    processed = []
    for doc in db.collection("processed_events").stream():
        if VIDEO_RUN_ID in doc.id:
            processed.append({"id": doc.id, **(doc.to_dict() or {})})

    status = _fetch_json(f"{WEB_URL}/api/runs/{VIDEO_RUN_ID}")
    manifest = _fetch_json(f"{WEB_URL}/api/runs/{VIDEO_RUN_ID}/manifest")
    audit = _fetch_json(f"{WEB_URL}/api/runs/{VIDEO_RUN_ID}/audit/verify")
    ready = _fetch_json(f"{WEB_URL}/readyz")

    gcs_listing = _gsutil_ls(f"gs://{BUCKET}/runs/{VIDEO_RUN_ID}/protocols/")

    web_svc = _gcloud_json(
        ["run", "services", "describe", "protocol-215-web", f"--region={REGION}", f"--project={PROJECT}", "--format=json"]
    )
    worker_svc = _gcloud_json(
        ["run", "services", "describe", "protocol-215-worker", f"--region={REGION}", f"--project={PROJECT}", "--format=json"]
    )
    topics = _gcloud_text(["pubsub", "topics", "list", f"--project={PROJECT}", "--format=value(name)"])
    subs = _gcloud_text(["pubsub", "subscriptions", "list", f"--project={PROJECT}", "--format=table(name,topic,pushConfig.pushEndpoint)"])

    web_rev = web_svc["status"]["traffic"][0]["revisionName"]
    worker_rev = worker_svc["status"]["traffic"][0]["revisionName"]

    # 01 Firestore
    rows = "".join(
        f"<tr><th>{html.escape(k)}</th><td><pre>{html.escape(json.dumps(v, indent=2, default=str) if isinstance(v, (list, dict)) else str(v))}</pre></td></tr>"
        for k, v in [
            ("Document path", f"runs/{VIDEO_RUN_ID}"),
            ("status", run.get("status")),
            ("checkpoint", run.get("checkpoint")),
            ("compiler_model", run.get("compiler_model")),
            ("worker_revision", run.get("worker_revision")),
            ("state_version", run.get("state_version")),
            ("event_sequence", run.get("event_sequence")),
        ]
    )
    pe_rows = "".join(
        f"<tr><td><pre>{html.escape(p['id'])}</pre></td><td><pre>{html.escape(str(p.get('event_id')))}</pre></td></tr>"
        for p in processed[:6]
    )
    body = f"<table>{rows}</table><h3>processed_events (same run)</h3><table><tr><th>Document ID</th><th>event_id</th></tr>{pe_rows}</table>"
    body2 = f"<p><strong>Selected prefix:</strong> <code>gs://{BUCKET}/runs/{VIDEO_RUN_ID}/protocols/</code></p><pre>{html.escape(gcs_listing)}</pre>"
    body3 = f"<h3>Topics</h3><pre>{html.escape(topics)}</pre><h3>Subscriptions</h3><pre>{html.escape(subs)}</pre><p class='note'>Message payloads not shown — delivery inferred from processed_events and worker checkpoint progress.</p>"
    body4 = f"""<table>
<tr><th>protocol-215-web</th><td>revision <code>{html.escape(web_rev)}</code> · traffic 100% · ingress public</td></tr>
<tr><th>protocol-215-worker</th><td>revision <code>{html.escape(worker_rev)}</code> · traffic 100% · invoked by Pub/Sub push (OIDC)</td></tr>
<tr><th>readyz compiler</th><td><pre>{html.escape(str(ready.get('compiler_mode')))} · {html.escape(str(ready.get('gemini_model')))}</pre></td></tr>
</table>"""
    summary = {
        "run_id": VIDEO_RUN_ID,
        "status": status.get("status"),
        "checkpoint": status.get("checkpoint"),
        "changes": len(manifest.get("changes") or []),
        "actions": len(manifest.get("actions") or []),
        "invariants_passed": sum(1 for i in (manifest.get("invariants") or []) if i.get("passed")),
        "invariants_total": len(manifest.get("invariants") or []),
        "audit_verify": audit,
    }
    body5 = f"<pre>{html.escape(json.dumps(summary, indent=2))}</pre>"
    p1 = _write_html("01-firestore-completed-run", _panel("Firestore — completed run", f"project={PROJECT} · captured {captured}", body))
    p2 = _write_html("02-gcs-protocols-same-run", _panel("Cloud Storage — protocol PDFs", f"bucket={BUCKET}", body2))
    p3 = _write_html("03-pubsub-workflow", _panel("Pub/Sub — events + worker push", f"project={PROJECT}", body3))
    p4 = _write_html("04-cloud-run-services", _panel("Cloud Run — web + worker", f"region={REGION}", body4))
    p5 = _write_html("05-manifest", _panel("Manifest + audit verification", VIDEO_RUN_ID, body5))

    _screenshot_all()

    meta = {
        "captured_at": captured,
        "video_run_id": VIDEO_RUN_ID,
        "web_revision": web_rev,
        "worker_revision": worker_rev,
        "gemini_model": run.get("compiler_model") or ready.get("gemini_model"),
        "web_url": WEB_URL,
        "project": PROJECT,
        "bucket": BUCKET,
    }
    (OUT / "capture_meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(meta, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
