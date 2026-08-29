import { useEffect, useMemo, useState } from "react";
import { api, ApiError } from "../api/client";
import type { CreateRunResponse, LaunchMeta, RunListItem } from "../api/types";
import { ScenarioPreview, SignatureTitle } from "../components/RecordingChrome";
import { ErrorState, LoadingState } from "../components/States";
import { isTerminal, shortHash } from "../lib/workflow";

type Props = {
  recent: RunListItem[] | null;
  recentError: Error | null;
  onReloadRecent: () => void;
  onStarted: (meta: LaunchMeta, created: CreateRunResponse) => void;
  onReset?: () => void;
  recordingMode?: boolean;
  apiConfigOk?: boolean;
  apiHealthy?: boolean;
  cloudMode?: boolean;
};

const SCENARIOS = [
  {
    id: "aurora-101",
    label: "AURORA-101 · Phoenix PK courier conflict",
    studyId: "AURORA-101",
    from: "1.0",
    to: "2.0",
  },
];

export function LaunchView({
  recent,
  recentError,
  onReloadRecent,
  onStarted,
  onReset,
  recordingMode = false,
  apiConfigOk = true,
  apiHealthy = true,
  cloudMode = false,
}: Props) {
  const [scenarioId, setScenarioId] = useState(SCENARIOS[0].id);
  const [oldFile, setOldFile] = useState<File | null>(null);
  const [newFile, setNewFile] = useState<File | null>(null);
  const [oldHash, setOldHash] = useState<string | null>(null);
  const [newHash, setNewHash] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [confirmReset, setConfirmReset] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [introPhase, setIntroPhase] = useState<"problem" | "brand">("problem");

  useEffect(() => {
    const t = window.setTimeout(() => setIntroPhase("brand"), recordingMode ? 2800 : 2200);
    return () => window.clearTimeout(t);
  }, [recordingMode]);

  const scenario = useMemo(
    () => SCENARIOS.find((s) => s.id === scenarioId) ?? SCENARIOS[0],
    [scenarioId],
  );

  const uploadEnabled = apiConfigOk && apiHealthy && Boolean(oldFile && newFile) && !submitting;

  async function hashFile(file: File): Promise<string> {
    const buf = await file.arrayBuffer();
    const digest = await crypto.subtle.digest("SHA-256", buf);
    return Array.from(new Uint8Array(digest))
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("");
  }

  async function onOldChange(file: File | null) {
    setOldFile(file);
    setOldHash(file ? await hashFile(file) : null);
  }

  async function onNewChange(file: File | null) {
    setNewFile(file);
    setNewHash(file ? await hashFile(file) : null);
  }

  async function start() {
    if (!oldFile || !newFile || !uploadEnabled) return;
    setSubmitting(true);
    setError(null);
    try {
      const form = new FormData();
      form.append("old_protocol", oldFile);
      form.append("new_protocol", newFile);
      form.append("study_id", scenario.studyId);
      form.append("from_version", scenario.from);
      form.append("to_version", scenario.to);
      const created = await api.createRun(form);
      onStarted(
        {
          run_id: created.run_id,
          old_sha256: created.old_sha256,
          new_sha256: created.new_sha256,
          old_name: oldFile.name,
          new_name: newFile.name,
          study_id: created.study_id,
        },
        created,
      );
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setSubmitting(false);
    }
  }

  async function resetDemoConfirmed() {
    setResetting(true);
    setError(null);
    setConfirmReset(false);
    try {
      await api.demoReset(true);
      onReset?.();
      onReloadRecent();
      // Verify no non-terminal run remains (cloud honesty check).
      const listed = await api.listRuns();
      const lingering = listed.filter((r) => !isTerminal(r.status));
      if (lingering.length > 0) {
        setError(
          new Error(
            `Reset completed but ${lingering.length} non-terminal run(s) remain (e.g. ${lingering[0].run_id}).`,
          ),
        );
      }
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setResetting(false);
    }
  }

  function onResetClick() {
    if (cloudMode) {
      setConfirmReset(true);
      return;
    }
    void resetDemoConfirmed();
  }

  return (
    <section
      className="view launch-view"
      aria-labelledby="launch-title"
      data-recording={recordingMode ? "true" : "false"}
    >
      {recordingMode ? (
        <SignatureTitle phase={introPhase} />
      ) : (
        <div className="signature-opening" data-phase={introPhase} aria-live="polite">
          <p className="signature-problem">
            Clinical-trial sites can operate under different protocol versions for an average of{" "}
            <span className="days-215">215</span> days.
          </p>
          <div className="signature-brand">
            <p className="brand signature-brand-name">Protocol 215</p>
            <h2 id="launch-title" className="signature-tagline">
              Clinical Amendment Preflight
            </h2>
          </div>
        </div>
      )}

      {recordingMode && <ScenarioPreview />}

      <header className="view-header launch-subheader">
        <p id={recordingMode ? "launch-title" : undefined}>
          Register synthetic AURORA-101 protocol PDFs and start an asynchronous preflight run. The
          workflow executes on the backend — this screen does not hardcode outcomes.
        </p>
      </header>

      {!apiConfigOk && (
        <div className="state-panel error terminal" role="alert">
          <h3>API configuration failure</h3>
          <p>
            VITE_API_BASE_URL is missing or invalid for this host. Requests will not be sent to
            Vercel. Set the Cloud Run web URL and rebuild the Vite app.
          </p>
        </div>
      )}

      {apiConfigOk && !apiHealthy && (
        <div className="state-panel error retryable" role="alert">
          <h3>API not reachable</h3>
          <p>
            /healthz has not succeeded yet. Upload stays disabled until the Cloud Run API responds.
          </p>
        </div>
      )}

      <div className="launch-grid">
        <label className="field">
          <span>Synthetic scenario</span>
          <select
            value={scenarioId}
            onChange={(e) => setScenarioId(e.target.value)}
            aria-label="Synthetic scenario"
          >
            {SCENARIOS.map((s) => (
              <option key={s.id} value={s.id}>
                {s.label}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span>Old protocol (v{scenario.from})</span>
          <input
            type="file"
            accept="application/pdf,.pdf"
            aria-label="Old protocol PDF"
            onChange={(e) => void onOldChange(e.target.files?.[0] ?? null)}
          />
          {oldFile && (
            <span className="file-meta">
              {oldFile.name}
              {oldHash && <> · sha256 {shortHash(oldHash)}</>}
            </span>
          )}
        </label>

        <label className="field">
          <span>Amended protocol (v{scenario.to})</span>
          <input
            type="file"
            accept="application/pdf,.pdf"
            aria-label="Amended protocol PDF"
            onChange={(e) => void onNewChange(e.target.files?.[0] ?? null)}
          />
          {newFile && (
            <span className="file-meta">
              {newFile.name}
              {newHash && <> · sha256 {shortHash(newHash)}</>}
            </span>
          )}
        </label>
      </div>

      <div className="launch-actions">
        <button
          type="button"
          className="btn primary"
          disabled={!uploadEnabled}
          onClick={() => void start()}
        >
          {submitting ? "Starting…" : "Start Amendment Preflight"}
        </button>
        <button
          type="button"
          className="btn ghost"
          disabled={resetting || submitting || !apiConfigOk}
          onClick={onResetClick}
        >
          {resetting ? "Resetting…" : "Reset demo state"}
        </button>
      </div>

      {confirmReset && (
        <div className="modal-backdrop" role="presentation">
          <div
            className="modal-panel"
            role="dialog"
            aria-modal="true"
            aria-labelledby="reset-title"
          >
            <h3 id="reset-title">Reset synthetic demo state?</h3>
            <p>
              This removes only synthetic run state (runs, twin rehearsal scratch, audit for this
              demo). It does not touch real clinical systems — none are connected.
            </p>
            <div className="modal-actions">
              <button type="button" className="btn ghost" onClick={() => setConfirmReset(false)}>
                Cancel
              </button>
              <button
                type="button"
                className="btn danger"
                onClick={() => void resetDemoConfirmed()}
              >
                Confirm reset
              </button>
            </div>
          </div>
        </div>
      )}

      {submitting && <LoadingState label="Uploading protocols and publishing amendment.received…" />}
      {error && (
        <ErrorState
          error={error}
          onRetry={error instanceof ApiError && error.retryable ? () => void start() : undefined}
        />
      )}

      <section className="recent-runs" aria-labelledby="recent-title">
        <div className="section-row">
          <h3 id="recent-title">Recent runs</h3>
          <button type="button" className="btn ghost" onClick={onReloadRecent}>
            Refresh
          </button>
        </div>
        {recentError && <ErrorState error={recentError} onRetry={onReloadRecent} />}
        {!recent && !recentError && <LoadingState label="Loading recent runs…" />}
        {recent && recent.length === 0 && (
          <p className="empty">No runs yet — ready for a clean demo.</p>
        )}
        {recent && recent.length > 0 && (
          <table className="data-table">
            <thead>
              <tr>
                <th scope="col">Run</th>
                <th scope="col">Study</th>
                <th scope="col">Status</th>
                <th scope="col">Stage</th>
              </tr>
            </thead>
            <tbody>
              {recent.map((r) => (
                <tr key={r.run_id}>
                  <td>
                    <button
                      type="button"
                      className="linkish"
                      onClick={() =>
                        onStarted(
                          {
                            run_id: r.run_id,
                            old_sha256: "",
                            new_sha256: "",
                            old_name: `v${r.from_version}.pdf`,
                            new_name: `v${r.to_version}.pdf`,
                            study_id: r.study_id,
                          },
                          {
                            run_id: r.run_id,
                            status: r.status,
                            study_id: r.study_id,
                            from_version: r.from_version,
                            to_version: r.to_version,
                            old_sha256: "",
                            new_sha256: "",
                            old_pages: 0,
                            new_pages: 0,
                            event_published: true,
                            message: "",
                          },
                        )
                      }
                    >
                      {r.run_id}
                    </button>
                  </td>
                  <td>{r.study_id}</td>
                  <td>{r.status}</td>
                  <td>{r.current_stage}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </section>
  );
}
