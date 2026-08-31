import { useMemo } from "react";
import type { AuditVerify, LaunchMeta, Manifest, RunStatus } from "../api/types";
import { ErrorState, LoadingState } from "../components/States";
import { shortHash } from "../lib/workflow";

type Props = {
  meta: LaunchMeta | null;
  status: RunStatus | null;
  manifest: Manifest | null;
  audit: AuditVerify | null;
  loading: boolean;
  error: Error | null;
  onRetry: () => void;
  recordingMode?: boolean;
};

function metricOrPending(ready: boolean, value: string | number): string {
  if (!ready) return "Pending backend confirmation";
  return String(value);
}

export function ManifestView({
  meta,
  status,
  manifest,
  audit,
  loading,
  error,
  onRetry,
  recordingMode = false,
}: Props) {
  const stats = useMemo(() => {
    if (!manifest) return null;
    const automatic = manifest.actions.filter((a) => a.status === "executed" && !a.approved);
    const approved = manifest.actions.filter((a) => a.approved && a.status === "executed");
    const blocked = manifest.actions.filter((a) => a.status === "blocked");
    const redUnauthorized = manifest.actions.filter(
      (a) => a.authorized_tier === "RED" && (a.executed || a.status === "executed"),
    );
    const amberWithoutApproval = manifest.actions.filter(
      (a) =>
        a.authorized_tier === "AMBER" &&
        (a.executed || a.status === "executed") &&
        !a.approved,
    );
    const sites =
      typeof manifest.sites_evaluated_count === "number"
        ? manifest.sites_evaluated_count
        : new Set(
            [...manifest.findings, ...manifest.actions]
              .map((x) => ("site_id" in x ? x.site_id : null))
              .filter(Boolean),
          ).size;
    const participants =
      typeof manifest.participants_evaluated_count === "number"
        ? manifest.participants_evaluated_count
        : new Set(
            [...manifest.findings, ...manifest.actions]
              .map((x) => ("participant_id" in x ? x.participant_id : null))
              .filter(Boolean),
          ).size;
    const withEvidence = manifest.changes.filter(
      (c) =>
        (c.old_evidence?.length ?? 0) +
          (c.new_evidence?.length ?? 0) +
          (c.evidence?.length ?? 0) >
        0,
    );
    const duplicateActions = (() => {
      const keys = new Map<string, number>();
      for (const a of manifest.actions) {
        const k = `${a.tool_name}|${a.site_id ?? ""}|${a.participant_id ?? ""}|${a.proposal_id}`;
        keys.set(k, (keys.get(k) ?? 0) + 1);
      }
      return [...keys.values()].filter((n) => n > 1).length;
    })();
    const completedVisitsAltered = manifest.invariants.filter(
      (i) =>
        /completed.?visit|immutable.?visit|historical.?visit/i.test(i.name + i.message) &&
        !i.passed,
    );
    const siteVersionConflicts = manifest.invariants.filter(
      (i) => /site.?version|activation|training|approval/i.test(i.name + i.message) && !i.passed,
    );
    return {
      automatic,
      approved,
      blocked,
      redUnauthorized: redUnauthorized.length,
      amberWithoutApproval: amberWithoutApproval.length,
      duplicateActions,
      completedVisitsAltered: completedVisitsAltered.length,
      siteVersionConflicts: siteVersionConflicts.length,
      sites,
      participants,
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
        h1{font-size:1.4rem} .meta{color:#4d606c}
      </style></head><body>
      <p><strong>SYNTHETIC DATA ONLY</strong></p>
      <h1>Amendment Release Manifest</h1>
      <p class="meta">Run ${manifest.run_id} · ${manifest.study_id}</p>
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
        Manifest not ready — complete Verify stage after approval (status:{" "}
        {status?.status ?? "—"}). No success metrics are shown until the backend confirms.
      </p>
    );
  }

  const ready = Boolean(manifest);

  return (
    <section
      className="view manifest-view"
      aria-labelledby="manifest-title"
      data-recording={recordingMode ? "true" : "false"}
    >
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

      <dl className="kv manifest-grid manifest-priority">
        <div>
          <dt>Sites evaluated</dt>
          <dd>{metricOrPending(ready, stats?.sites ?? 0)}</dd>
        </div>
        <div>
          <dt>Participants evaluated</dt>
          <dd>{metricOrPending(ready, stats?.participants ?? 0)}</dd>
        </div>
        <div>
          <dt>Changes detected</dt>
          <dd>{metricOrPending(ready, manifest.changes.length)}</dd>
        </div>
        <div>
          <dt>Evidence coverage</dt>
          <dd>{metricOrPending(ready, `${stats?.evidenceCoverage ?? 0}%`)}</dd>
        </div>
        <div>
          <dt>Unauthorized RED actions</dt>
          <dd>{metricOrPending(ready, stats?.redUnauthorized ?? 0)}</dd>
        </div>
        <div>
          <dt>AMBER actions without approval</dt>
          <dd>{metricOrPending(ready, stats?.amberWithoutApproval ?? 0)}</dd>
        </div>
        <div>
          <dt>Duplicate actions</dt>
          <dd>{metricOrPending(ready, stats?.duplicateActions ?? 0)}</dd>
        </div>
        <div>
          <dt>Completed visits altered</dt>
          <dd>{metricOrPending(ready, stats?.completedVisitsAltered ?? 0)}</dd>
        </div>
        <div>
          <dt>Site-version conflicts</dt>
          <dd>{metricOrPending(ready, stats?.siteVersionConflicts ?? 0)}</dd>
        </div>
        <div>
          <dt>Audit-chain verification</dt>
          <dd>
            {audit == null && "Checking…"}
            {audit && (
              <>
                {audit.ok ? "PASS · Intact" : "FAIL"} · {audit.events_checked} events
              </>
            )}
          </dd>
        </div>
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
          <dt>Final rollout status</dt>
          <dd>{status?.status ?? "—"}</dd>
        </div>
      </dl>
    </section>
  );
}
