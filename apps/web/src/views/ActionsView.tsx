import { useState } from "react";
import { api, ApiError } from "../api/client";
import type { ActionExecution, ApprovalRequest, RunStatus } from "../api/types";
import { formatJson } from "../lib/workflow";
import { ErrorState, LoadingState } from "../components/States";

type Props = {
  runId: string | null;
  status: RunStatus | null;
  actions: ActionExecution[] | null;
  approvals: ApprovalRequest[] | null;
  loading: boolean;
  error: Error | null;
  onRetry: () => void;
  onDecision: () => void;
};

export function ActionsView({
  runId,
  status,
  actions,
  approvals,
  loading,
  error,
  onRetry,
  onDecision,
}: Props) {
  const [busy, setBusy] = useState(false);
  const [decisionError, setDecisionError] = useState<Error | null>(null);

  if (loading && !actions) return <LoadingState label="Loading action ledger…" />;
  if (error && !actions) return <ErrorState error={error} onRetry={onRetry} />;

  const completed = (actions ?? []).filter((a) => a.status === "executed" || a.executed);
  const blocked = (actions ?? []).filter((a) => a.status === "blocked" || a.authorized_tier === "RED");
  const pendingApproval =
    (approvals ?? []).find((a) => a.status === "pending") ??
    (status?.pending_approval
      ? ({
          approval_id: status.pending_approval.approval_id,
          run_id: status.run_id,
          action_ids: status.pending_approval.action_id
            ? [status.pending_approval.action_id]
            : [],
          status: "pending",
          expected_state_version: status.pending_approval.expected_state_version,
          tool_name: status.pending_approval.tool_name,
          affected_site_id: status.pending_approval.affected_site_id,
          affected_participant_id: status.pending_approval.affected_participant_id,
          reason_approval_required: status.pending_approval.reason_approval_required,
          consequences_of_approval: "AMBER actions execute after policy re-check.",
          consequences_of_rejection: "AMBER actions remain blocked.",
          before_state: {},
          proposed_after_state: {},
          change_evidence: [],
          operational_evidence: [],
        } as ApprovalRequest)
      : null);

  async function decide(decision: "approved" | "rejected") {
    if (!runId || !pendingApproval) return;
    setBusy(true);
    setDecisionError(null);
    try {
      await api.submitApproval(runId, pendingApproval.approval_id, {
        decision,
        expected_state_version: pendingApproval.expected_state_version,
      });
      onDecision();
    } catch (err) {
      setDecisionError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="view actions-view" aria-labelledby="actions-title">
      <header className="view-header">
        <h2 id="actions-title">Action Ledger & Approval</h2>
        <p>GREEN completes automatically. AMBER waits. RED never executes.</p>
      </header>

      <div className="ledger-columns">
        <div className="ledger-col">
          <h3>Completed automatically</h3>
          <ul className="ledger-list">
            {completed.map((a) => (
              <li key={a.execution_id}>
                <strong>{a.tool_name}</strong>
                <span>
                  {a.authorized_tier}
                  {a.site_id ? ` · ${a.site_id}` : ""}
                  {a.participant_id ? ` · ${a.participant_id}` : ""}
                </span>
              </li>
            ))}
            {!completed.length && <li className="empty">None confirmed yet.</li>}
          </ul>
        </div>

        <div className="ledger-col waiting">
          <h3>Waiting for approval</h3>
          {!pendingApproval && <p className="empty">No pending approval.</p>}
          {pendingApproval && (
            <div className="approval-panel" aria-label="Human approval panel">
              <p>
                <strong>{pendingApproval.tool_name ?? "AMBER action"}</strong>
              </p>
              <p>{pendingApproval.reason_approval_required}</p>
              <dl className="kv dense">
                <div>
                  <dt>Site</dt>
                  <dd>{pendingApproval.affected_site_id ?? "—"}</dd>
                </div>
                <div>
                  <dt>Participant</dt>
                  <dd>{pendingApproval.affected_participant_id ?? "—"}</dd>
                </div>
                <div>
                  <dt>Source evidence</dt>
                  <dd>
                    {(pendingApproval.change_evidence ?? [])
                      .concat(pendingApproval.operational_evidence ?? [])
                      .map((e) => `p.${e.page} ${e.section_id}`)
                      .join("; ") || "Linked from change evidence"}
                  </dd>
                </div>
                <div>
                  <dt>Before</dt>
                  <dd>
                    <pre>{formatJson(pendingApproval.before_state)}</pre>
                  </dd>
                </div>
                <div>
                  <dt>Proposed after</dt>
                  <dd>
                    <pre>{formatJson(pendingApproval.proposed_after_state)}</pre>
                  </dd>
                </div>
                <div>
                  <dt>If approved</dt>
                  <dd>{pendingApproval.consequences_of_approval}</dd>
                </div>
                <div>
                  <dt>If rejected</dt>
                  <dd>{pendingApproval.consequences_of_rejection}</dd>
                </div>
              </dl>
              <div className="approval-actions">
                <button
                  type="button"
                  className="btn primary"
                  disabled={busy}
                  onClick={() => void decide("approved")}
                >
                  Approve
                </button>
                <button
                  type="button"
                  className="btn danger"
                  disabled={busy}
                  onClick={() => void decide("rejected")}
                >
                  Reject
                </button>
              </div>
              {busy && <LoadingState label="Recording decision and publishing amendment.resume…" />}
              {decisionError && (
                <ErrorState
                  error={decisionError}
                  onRetry={
                    decisionError instanceof ApiError && decisionError.retryable
                      ? () => void decide("approved")
                      : undefined
                  }
                />
              )}
            </div>
          )}
        </div>

        <div className="ledger-col">
          <h3>Blocked</h3>
          <ul className="ledger-list">
            {blocked.map((a) => (
              <li key={a.execution_id}>
                <strong>{a.tool_name}</strong>
                <span>
                  {a.authorized_tier} · {a.status}
                </span>
              </li>
            ))}
            {!blocked.length && <li className="empty">No blocked actions.</li>}
          </ul>
        </div>
      </div>
    </section>
  );
}
