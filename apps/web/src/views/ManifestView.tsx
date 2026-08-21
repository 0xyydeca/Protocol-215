import { useMemo } from "react";
import type { AuditVerify, LaunchMeta, Manifest, RunStatus } from "../api/types";
import { shortHash } from "../lib/workflow";
import { ErrorState, LoadingState } from "../components/States";

type Props = {
  meta: LaunchMeta | null;
  status: RunStatus | null;
  manifest: Manifest | null;
  audit: AuditVerify | null;
  loading: boolean;
  error: Error | null;
  onRetry: () => void;
};

export function ManifestView({
  meta,
  status,
  manifest,
  audit,
  loading,
  error,
  onRetry,
}: Props) {
  const stats = useMemo(() => {
    if (!manifest) return null;
    const automatic = manifest.actions.filter((a) => a.status === "executed" && !a.approved);
    const approved = manifest.actions.filter((a) => a.approved && a.status === "executed");
    const blocked = manifest.actions.filter((a) => a.status === "blocked");
    const sites = new Set(
      [...manifest.findings, ...manifest.actions]
        .map((x) => ("site_id" in x ? x.site_id : null))
        .filter(Boolean),
    );
    const participants = new Set(
      [...manifest.findings, ...manifest.actions]
        .map((x) => ("participant_id" in x ? x.participant_id : null))
        .filter(Boolean),
    );
    const withEvidence = manifest.changes.filter(
      (c) => (c.old_evidence?.length ?? 0) + (c.new_evidence?.length ?? 0) + (c.evidence?.length ?? 0) > 0,
    );
    return {
      automatic,
      approved,
      blocked,
      sites: sites.size,
      participants: participants.size,
      evidenceCoverage: manifest.changes.length
        ? Math.round((withEvidence.length / manifest.changes.length) * 100)
        : 0,
    };
  }, [manifest]);

  function downloadJson() {
    if (!manifest) return;
    const blob = new Blob([JSON.stringify(manifest, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `amendment-manifest-${manifest.run_id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function printHtml() {
    if (!manifest) return;
    const w = window.open("", "_blank", "noopener,noreferrer,width=900,height=1000");
    if (!w) return;
    w.document.write(`<!doctype html><html><head><title>Manifest ${manifest.run_id}</title>
      <style>
        body{font-family:Georgia,serif;padding:2rem;color:#0b1f2a}
        h1{font-size:1.4rem} .meta{color:#4d606c} table{width:100%;border-collapse:collapse;margin:1rem 0}
        th,td{border:1px solid #c5d0d6;padding:.4rem;text-align:left;font-size:.9rem}
      </style></head><body>
      <p><strong>SYNTHETIC DATA ONLY</strong></p>
      <h1>Amendment Release Manifest</h1>
      <p class="meta">Run ${manifest.run_id} · ${manifest.study_id} · v${manifest.from_version}→v${manifest.to_version}</p>
      <h2>Changes (${manifest.changes.length})</h2>
      <ul>${manifest.changes.map((c) => `<li>${c.change_id}: ${c.concept_type} (${c.operation})</li>`).join("")}</ul>
      <h2>Actions</h2>
      <ul>${manifest.actions.map((a) => `<li>${a.tool_name} — ${a.status} / ${a.authorized_tier}</li>`).join("")}</ul>
      <h2>Invariants</h2>
      <ul>${manifest.invariants.map((i) => `<li>${i.name}: ${i.passed ? "PASS" : "FAIL"} — ${i.message}</li>`).join("")}</ul>
      </body></html>`);
    w.document.close();
    w.focus();
    w.print();
  }

  if (loading && !manifest) return <LoadingState label="Waiting for release manifest…" />;
  if (error && !manifest) return <ErrorState error={error} onRetry={onRetry} />;
  if (!manifest) {
    return (
      <p className="empty">
        Manifest not ready — complete Verify stage after approval (status: {status?.status ?? "—"}).
      </p>
    );
  }

  return (
    <section className="view manifest-view" aria-labelledby="manifest-title">
      <header className="view-header row">
        <div>
          <h2 id="manifest-title">Amendment Release Manifest</h2>
          <p>Evidence-linked rollout record for synthetic AURORA-101.</p>
        </div>
        <div className="manifest-actions">
          <button type="button" className="btn secondary" onClick={downloadJson}>
            Download JSON
          </button>
          <button type="button" className="btn secondary" onClick={printHtml}>
            Print-ready HTML
          </button>
        </div>
      </header>

      <dl className="kv manifest-grid">
        <div>
          <dt>Run ID</dt>
          <dd>{manifest.run_id}</dd>
        </div>
        <div>
          <dt>Protocol hashes</dt>
          <dd>
            v{manifest.from_version}: {shortHash(meta?.old_sha256 ?? "")}
            <br />
            v{manifest.to_version}: {shortHash(meta?.new_sha256 ?? "")}
          </dd>
        </div>
        <div>
          <dt>Detected changes</dt>
          <dd>
            {manifest.changes.length}
            <ul className="compact">
              {manifest.changes.map((c) => (
                <li key={c.change_id}>
                  {c.change_id} — {c.concept_type}
                </li>
              ))}
            </ul>
          </dd>
        </div>
        <div>
          <dt>Evidence coverage</dt>
          <dd>{stats?.evidenceCoverage ?? 0}%</dd>
        </div>
        <div>
          <dt>Sites evaluated</dt>
          <dd>{stats?.sites ?? 0}</dd>
        </div>
        <div>
          <dt>Participants evaluated</dt>
          <dd>{stats?.participants ?? 0}</dd>
        </div>
        <div>
          <dt>Automatic actions</dt>
          <dd>{stats?.automatic.length ?? 0}</dd>
        </div>
        <div>
          <dt>Approved actions</dt>
          <dd>{stats?.approved.length ?? 0}</dd>
        </div>
        <div>
          <dt>Blocked actions</dt>
          <dd>{stats?.blocked.length ?? 0}</dd>
        </div>
        <div>
          <dt>Invariant results</dt>
          <dd>
            <ul className="compact invariant-list">
              {manifest.invariants.map((inv) => (
                <li key={inv.invariant_id}>
                  <span className={inv.passed ? "invariant-pass" : "invariant-fail"}>
                    {inv.passed ? "PASS" : "FAIL"}
                  </span>{" "}
                  — {inv.name}: {inv.message}
                </li>
              ))}
              {!manifest.invariants.length && <li>None recorded</li>}
            </ul>
          </dd>
        </div>
        <div>
          <dt>Audit-chain verification</dt>
          <dd>
            {audit == null && "Checking…"}
            {audit && (
              <>
                {audit.ok ? "Intact" : "Failed"} · {audit.events_checked} events
                {!audit.ok && audit.errors.length > 0 && (
                  <ul className="compact">
                    {audit.errors.map((e) => (
                      <li key={e}>{e}</li>
                    ))}
                  </ul>
                )}
              </>
            )}
          </dd>
        </div>
        <div>
          <dt>Final rollout status</dt>
          <dd>{status?.status ?? "—"}</dd>
        </div>
      </dl>
    </section>
  );
}
