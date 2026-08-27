import type { RunStatus } from "../api/types";
import { STAGES, stageFromStatus } from "../lib/workflow";

type Props = {
  status?: RunStatus | null;
};

/**
 * Stage indicator advances only from persisted backend workflow status — never timers.
 */
export function StageIndicator({ status }: Props) {
  const current = stageFromStatus(status?.status);
  const idx = STAGES.indexOf(current);
  return (
    <nav className="stage-indicator" aria-label="Workflow stages">
      <ol>
        {STAGES.map((stage, i) => {
          const state = i < idx ? "done" : i === idx ? "current" : "upcoming";
          return (
            <li key={stage} data-state={state}>
              <span className="stage-dot" aria-hidden="true" />
              <span className="stage-label">
                {state === "current" ? (
                  <strong>
                    <span className="sr-only">Current stage: </span>
                    {stage}
                  </strong>
                ) : (
                  stage
                )}
              </span>
            </li>
          );
        })}
      </ol>
      {status && (
        <p className="stage-meta" aria-live="polite">
          {status.current_stage} · {Math.round(status.progress * 100)}%
          {status.last_event ? ` · ${status.last_event}` : ""}
          {status.status ? ` · ${status.status}` : ""}
        </p>
      )}
    </nav>
  );
}

export function SyntheticBanner() {
  return (
    <aside className="synthetic-banner" role="note">
      <strong>Synthetic data only.</strong> AURORA-101 proof of concept — not validated for real
      clinical use. No PHI, patients, or production trial systems.
    </aside>
  );
}

/** Visible resume identity strip — values only from backend. */
export function ResumeProofBanner({
  runId,
  status,
  sessionId,
  invocationId,
}: {
  runId: string | null;
  status: string | null;
  sessionId?: string | null;
  invocationId?: string | null;
}) {
  if (!status) return null;
  const highlight =
    status === "AWAITING_APPROVAL" ||
    status === "RESUMING" ||
    status === "VERIFYING" ||
    status === "EXECUTING_APPROVED_AMBER";
  if (!highlight && status !== "COMPLETED" && status !== "COMPLETED_WITH_BLOCKS") {
    return null;
  }
  return (
    <aside className="resume-proof" aria-live="polite" data-status={status}>
      <strong>Resume proof</strong>
      <span className="resume-flow" aria-label="Status transitions">
        AWAITING_APPROVAL → RESUMING → VERIFYING
      </span>
      <span>
        Now: <code>{status}</code>
      </span>
      <span>
        Run: <code>{runId ?? "—"}</code>
      </span>
      <span>
        Session: <code>{sessionId ?? "—"}</code>
      </span>
      <span>
        Invocation: <code>{invocationId ?? "—"}</code>
      </span>
    </aside>
  );
}
