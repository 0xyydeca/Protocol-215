import { humanizePollStall } from "../api/errors";
import type { RunStatus } from "../api/types";

type Props = {
  status: RunStatus;
  elapsedMs: number;
  reason: "stale_progress" | "poll_failures";
  onRetryStatus: () => void;
  onReturnLaunch: () => void;
};

function formatElapsed(ms: number): string {
  const s = Math.max(0, Math.floor(ms / 1000));
  const m = Math.floor(s / 60);
  const rem = s % 60;
  return m > 0 ? `${m}m ${rem}s` : `${rem}s`;
}

export function StalledRunPanel({
  status,
  elapsedMs,
  reason,
  onRetryStatus,
  onReturnLaunch,
}: Props) {
  const checkpoint = status.checkpoint ?? status.current_stage ?? "unknown";
  const title = humanizePollStall(checkpoint);
  const diagnostics = {
    run_id: status.run_id,
    status: status.status,
    checkpoint,
    state_version: status.state_version,
    elapsed: formatElapsed(elapsedMs),
    correlation_id: status.correlation_id ?? status.run_id,
    updated_at: status.updated_at ?? null,
    last_checkpoint_at: status.last_checkpoint_at ?? null,
    last_worker_event_id: status.last_worker_event_id ?? null,
    last_error_code: status.last_error_code ?? null,
    last_error_detail_safe: status.last_error_detail_safe ?? null,
    web_revision: status.web_revision ?? null,
    worker_revision: status.worker_revision ?? null,
    actual_adapters: status.actual_adapters ?? null,
    compiler_model: status.compiler_model ?? null,
    stall_reason: reason,
  };

  async function copyDiagnostics() {
    const text = JSON.stringify(diagnostics, null, 2);
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      // Fallback for restrictive environments
      window.prompt("Copy diagnostics", text);
    }
  }

  return (
    <div className="state-panel error retryable stalled-run" role="alert" aria-live="assertive">
      <h3>{title}</h3>
      <p>
        {reason === "poll_failures"
          ? "Three consecutive status requests failed. The UI is not inventing progress — retry or return to launch."
          : "Status and state_version have not changed for 45+ seconds. Backend state was not modified by this panel."}
      </p>
      <dl className="stalled-meta">
        <div>
          <dt>Run ID</dt>
          <dd>
            <code>{status.run_id}</code>
          </dd>
        </div>
        <div>
          <dt>Checkpoint</dt>
          <dd>{checkpoint}</dd>
        </div>
        <div>
          <dt>Elapsed</dt>
          <dd>{formatElapsed(elapsedMs)}</dd>
        </div>
        <div>
          <dt>Correlation ID</dt>
          <dd>
            <code>{status.correlation_id ?? status.run_id}</code>
          </dd>
        </div>
      </dl>
      <div className="stalled-actions">
        <button type="button" className="btn secondary" onClick={() => void copyDiagnostics()}>
          Copy diagnostics
        </button>
        <button type="button" className="btn secondary" onClick={onRetryStatus}>
          Retry status
        </button>
        <button type="button" className="btn ghost" onClick={onReturnLaunch}>
          Return to launch
        </button>
      </div>
    </div>
  );
}
