import type { RunStatus } from "../api/types";

type Props = {
  status: RunStatus;
};

/**
 * Amber informational panel for the intentional AWAITING_APPROVAL checkpoint.
 * Must not use failure / stall language.
 */
export function AwaitingApprovalPanel({ status }: Props) {
  const pending = status.pending_approval;
  const checkpoint = status.checkpoint ?? status.current_stage ?? "ApprovalRouter";

  return (
    <div
      className="state-panel awaiting-approval"
      role="status"
      aria-live="polite"
      data-testid="awaiting-approval-panel"
    >
      <h3>PAUSED FOR REQUIRED HUMAN APPROVAL</h3>
      <p>
        The autonomous workflow completed all permitted GREEN actions. Participant-sensitive AMBER
        actions remain blocked pending review.
      </p>
      <dl className="stalled-meta">
        <div>
          <dt>Current checkpoint</dt>
          <dd>{checkpoint}</dd>
        </div>
        <div>
          <dt>Run ID</dt>
          <dd>
            <code>{status.run_id}</code>
          </dd>
        </div>
        {pending?.approval_id ? (
          <div>
            <dt>Pending approval ID</dt>
            <dd>
              <code>{pending.approval_id}</code>
            </dd>
          </div>
        ) : null}
        <div>
          <dt>Completed GREEN actions</dt>
          <dd>{status.completed_action_count}</dd>
        </div>
        {pending?.affected_site_id ? (
          <div>
            <dt>Affected site</dt>
            <dd>{pending.affected_site_id}</dd>
          </div>
        ) : null}
        {pending?.affected_participant_id ? (
          <div>
            <dt>Affected participant</dt>
            <dd>{pending.affected_participant_id}</dd>
          </div>
        ) : null}
      </dl>
    </div>
  );
}
