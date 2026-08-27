import type { ReadyzResponse, RunStatus, WorkflowStatus } from "../api/types";

type ModeProps = {
  ready?: ReadyzResponse | null;
  executionMode?: string;
  runId?: string | null;
  status?: RunStatus | null;
  recordingMode?: boolean;
};

/**
 * Mode bar — always displays values observed from the backend.
 * Never invents Google Cloud, Live Gemini, model ID, or revision.
 */
export function ModeBar({
  ready,
  executionMode,
  runId,
  status,
  recordingMode = false,
}: ModeProps) {
  const env = ready?.app_env;
  const geminiBackend = ready?.backends?.gemini ?? ready?.compiler_mode;
  const isFake =
    geminiBackend === "fake" ||
    ready?.compiler_mode === "fake" ||
    (!geminiBackend && ready != null);
  const isLive =
    geminiBackend === "vertex" || ready?.compiler_mode === "live_gemini";
  const cloud =
    executionMode === "cloud" ||
    ready?.execution_mode === "cloud" ||
    env === "cloud";
  // Never hardcode a model id — only show what readiness reported.
  const modelId =
    ready?.gemini_model ?? ready?.backends?.gemini_model ?? ready?.demo_mode?.model_id ?? null;
  const revision = ready?.cloud_run_revision ?? ready?.demo_mode?.cloud_run_revision ?? null;
  const workflowStatus: WorkflowStatus | null = status?.status ?? null;

  return (
    <div
      className="mode-bar"
      role="status"
      aria-label="Demo mode indicators"
      data-recording={recordingMode ? "true" : "false"}
    >
      <span className="mode-pill" data-tone="synthetic">
        Synthetic Study
      </span>
      <span className="mode-pill" data-tone={cloud ? "cloud" : "local"}>
        {ready == null ? "…" : cloud ? "Google Cloud" : "Local"}
      </span>
      <span
        className="mode-pill"
        data-tone={isLive ? "live" : isFake ? "fake" : "muted"}
      >
        {ready == null
          ? "…"
          : isLive
            ? "Live Gemini"
            : isFake
              ? "Fake Compiler"
              : "Compiler unknown"}
      </span>
      <span className="mode-pill muted" title="Configured model ID from backend">
        Model: {modelId ?? "—"}
      </span>
      <span className="mode-pill muted" title="Cloud Run revision (K_REVISION)">
        Revision: {revision ?? "—"}
      </span>
      <span className="mode-pill muted" title="Current run ID">
        Run: {runId ?? "—"}
      </span>
      <span className="mode-pill muted" title="Persisted workflow status">
        Status: {workflowStatus ?? "—"}
      </span>
    </div>
  );
}
