import type { ReadyzResponse, RunStatus } from "../api/types";
import { STAGES, stageFromStatus } from "../lib/workflow";

type Props = {
  status?: RunStatus | null;
};

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
        </p>
      )}
    </nav>
  );
}

type ModeProps = {
  ready?: ReadyzResponse | null;
  executionMode?: string;
};

export function ModeBar({ ready, executionMode }: ModeProps) {
  const env = ready?.app_env ?? "local";
  const gemini = ready?.backends?.gemini ?? ready?.compiler_mode ?? "fake";
  const isFake = gemini === "fake" || ready?.compiler_mode === "fake";
  const cloud =
    executionMode === "cloud" ||
    ready?.execution_mode === "cloud" ||
    env === "cloud";
  const modelId = ready?.gemini_model ?? ready?.backends?.gemini_model ?? "gemini-3.5-flash";
  const revision = ready?.cloud_run_revision ?? ready?.demo_mode?.cloud_run_revision;

  return (
    <div className="mode-bar" role="status" aria-label="Demo mode indicators">
      <span className="mode-pill" data-tone="synthetic">
        Synthetic Study
      </span>
      <span className="mode-pill" data-tone={cloud ? "cloud" : "local"}>
        {cloud ? "Google Cloud" : "Local"}
      </span>
      <span className="mode-pill" data-tone={isFake ? "fake" : "live"}>
        {isFake ? "Fake Compiler" : "Live Gemini"}
      </span>
      <span className="mode-pill muted" title="Configured model ID">
        Model: {modelId}
      </span>
      {cloud && revision && (
        <span className="mode-pill muted" title="Cloud Run revision">
          Revision: {revision}
        </span>
      )}
    </div>
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
