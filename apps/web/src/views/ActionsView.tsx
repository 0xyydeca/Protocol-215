import { useRef, useState } from "react";
import { api, ApiError } from "../api/client";
import type { ActionExecution, ApprovalRequest, RunStatus } from "../api/types";
import { ErrorState, LoadingState } from "../components/States";
import { formatJson } from "../lib/workflow";

type Props = {
  runId: string | null;
  status: RunStatus | null;
  actions: ActionExecution[] | null;
  approvals: ApprovalRequest[] | null;
  loading: boolean;
  error: Error | null;
  onRetry: () => void;
  onDecision: () => void;
  recordingMode?: boolean;
};

function evidenceLines(
  list?: { page: number; section_id: string; quote?: string | null }[] | null,
): string {
  if (!list?.length) return "—";
  return list.map((e) => `page ${e.page} / ${e.section_id}`).join("; ");
}

export function ActionsView({
  runId,
  status,
  actions,
  approvals,
  loading,
  error,
  onRetry,
  onDecision,
  recordingMode = false,
}: Props) {
  const [busy, setBusy] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [decisionError, setDecisionError] = useState<Error | null>(null);
  const clickGuard = useRef(false);

  if (loading && !actions) return <LoadingState label="Loading action ledger…" />;
  if (error && !actions) return <ErrorState error={error} onRetry={onRetry} />;

  const completed = (actions ?? []).filter((a) => a.status === "executed" || a.executed);
  const blocked = (actions ?? []).filter(
    (a) => a.status === "blocked" || a.authorized_tier === "RED",
  );
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
          session_id: null,
          invocation_id: status.pending_approval.invocation_id,
        } as ApprovalRequest)
      : null);

  const approveDisabled = busy || submitted || clickGuard.current;

  async function decide(decision: "approved" | "rejected") {
    if (!runId || !pendingApproval) return;
    if (clickGuard.current || busy || submitted) return;
    clickGuard.current = true;
    setBusy(true);
    setSubmitted(true);
    setDecisionError(null);
    try {
      await api.submitApproval(runId, pendingApproval.approval_id, {
        decision,
        expected_state_version: pendingApproval.expected_state_version,
      });
      onDecision();
    } catch (err) {
      setDecisionError(err instanceof Error ? err : new Error(String(err)));
      // Keep button disabled after first click — do not allow double-submit.
    } finally {
      setBusy(false);
    }
  }

  return (
    <section
      className="view actions-view"
      aria-labelledby="actions-title"
      data-recording={recordingMode ? "true" : "false"}
    >
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
                <span className="ledger-meta">
                  ID: <code>{a.execution_id}</code>
                  {a.executed_at ? (
                    <>
                      {" "}
                      · {a.executed_at}
                    </>
                  ) : (
                    " · timestamp pending"
                  )}
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
                  <dt>Protocol evidence</dt>
                  <dd>{evidenceLines(pendingApproval.change_evidence)}</dd>
                </div>
                <div>
                  <dt>Operational evidence</dt>
                  <dd>{evidenceLines(pendingApproval.operational_evidence)}</dd>
                </div>
                <div>
                  <dt>Before state</dt>
                  <dd>
                    <pre>{formatJson(pendingApproval.before_state)}</pre>
                  </dd>
                </div>
                <div>
                  <dt>Proposed after state</dt>
                  <dd>
                    <pre>{formatJson(pendingApproval.proposed_after_state)}</pre>
                  </dd>
                </div>
                <div>
                  <dt>Consequences of approval</dt>
                  <dd>{pendingApproval.consequences_of_approval ?? "—"}</dd>
                </div>
                <div>
                  <dt>Consequences of rejection</dt>
                  <dd>{pendingApproval.consequences_of_rejection ?? "—"}</dd>
                </div>
                <div>
                  <dt>Run ID</dt>
                  <dd>
                    <code>{pendingApproval.run_id || runId || "—"}</code>
                  </dd>
                </div>
                <div>
                  <dt>Session ID</dt>
                  <dd>
                    <code>{pendingApproval.session_id ?? "—"}</code>
                  </dd>
                </div>
                <div>
                  <dt>Invocation ID</dt>
                  <dd>
                    <code>{pendingApproval.invocation_id ?? "—"}</code>
                  </dd>
                </div>
              </dl>
              <div className="approval-actions">
                <button
                  type="button"
                  className="btn primary"
                  disabled={approveDisabled}
                  aria-disabled={approveDisabled}
                  onClick={() => void decide("approved")}
                >
                  {submitted ? "Decision submitted" : "Approve"}
                </button>
                <button
                  type="button"
                  className="btn danger"
                  disabled={approveDisabled}
                  aria-disabled={approveDisabled}
                  onClick={() => void decide("rejected")}
                >
                  Reject
                </button>
              </div>
              {busy && (
                <LoadingState label="Recording decision and publishing amendment.resume…" />
              )}
              {decisionError && (
                <ErrorState
                  error={decisionError}
                  onRetry={
                    decisionError instanceof ApiError && decisionError.retryable
                      ? undefined
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
                <span className="ledger-meta">
                  ID: <code>{a.execution_id}</code>
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
