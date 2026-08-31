import { useCallback, useEffect, useMemo, useState } from "react";
import { api, ApiError } from "./api/client";
import { getApiConfig } from "./api/config";
import type {
  ActionExecution,
  ApprovalRequest,
  AuditVerify,
  ImpactGraph,
  LaunchMeta,
  Manifest,
  ReadyzResponse,
  RehearsalFinding,
  RunStatus,
  SemanticChange,
  ViewId,
} from "./api/types";
import { ApiDiagnostics } from "./components/ApiDiagnostics";
import { AwaitingApprovalPanel } from "./components/AwaitingApprovalPanel";
import { ResumeProofBanner, StageIndicator, SyntheticBanner } from "./components/Chrome";
import { ModeBar } from "./components/ModeBar";
import { ErrorState } from "./components/States";
import { StalledRunPanel } from "./components/StalledRunPanel";
import { ViewNav } from "./components/ViewNav";
import { usePoll } from "./hooks/usePoll";
import { useStalledRun } from "./hooks/useStalledRun";
import { isRecordingMode } from "./lib/recordingMode";
import { isRetryableFailure, isTerminal } from "./lib/workflow";
import { ActionsView } from "./views/ActionsView";
import { FindingsView } from "./views/FindingsView";
import { ImpactGraphView } from "./views/ImpactGraphView";
import { LaunchView } from "./views/LaunchView";
import { ManifestView } from "./views/ManifestView";
import { RedlineView } from "./views/RedlineView";
import { TimelineView } from "./views/TimelineView";

function unlockedViews(_status: RunStatus | null, hasRun: boolean): Set<ViewId> {
  const all: ViewId[] = [
    "launch",
    "redline",
    "impact",
    "timeline",
    "findings",
    "actions",
    "manifest",
  ];
  if (!hasRun) return new Set<ViewId>(["launch"]);
  return new Set(all);
}

export default function App() {
  const [recordingMode] = useState(() => isRecordingMode());
  const [apiConfig] = useState(() => getApiConfig());
  const [view, setView] = useState<ViewId>("launch");
  const [meta, setMeta] = useState<LaunchMeta | null>(null);
  const runId = meta?.run_id ?? null;

  const readyPoll = usePoll((signal) => api.readyz({ signal }), {
    intervalMs: 8000,
    enabled: apiConfig.ok,
  });
  const healthPoll = usePoll((signal) => api.healthz({ signal }), {
    intervalMs: 10_000,
    enabled: apiConfig.ok,
  });
  const recentPoll = usePoll((signal) => api.listRuns({ signal }), {
    intervalMs: 5000,
    enabled: apiConfig.ok,
  });

  const statusPoll = usePoll((signal) => api.getRun(runId!, { signal }), {
    enabled: Boolean(runId) && apiConfig.ok,
    intervalMs: 1200,
    shouldStop: (s) => isTerminal(s.status),
    deps: [runId],
  });

  const status: RunStatus | null = statusPoll.data;
  const terminal = isTerminal(status?.status);

  const changesPoll = usePoll((signal) => api.getChanges(runId!, { signal }), {
    enabled: Boolean(runId) && apiConfig.ok && !terminal,
    intervalMs: 2000,
    deps: [runId, status?.status],
  });

  const impactPoll = usePoll((signal) => api.getImpact(runId!, { signal }), {
    enabled: Boolean(runId) && apiConfig.ok && !terminal,
    intervalMs: 2500,
    deps: [runId, status?.status],
  });

  const findingsPoll = usePoll((signal) => api.getFindings(runId!, { signal }), {
    enabled: Boolean(runId) && apiConfig.ok && !terminal,
    intervalMs: 2000,
    deps: [runId, status?.status],
  });

  const actionsPoll = usePoll((signal) => api.getActions(runId!, { signal }), {
    enabled: Boolean(runId) && apiConfig.ok,
    intervalMs: 1500,
    shouldStop: () => terminal,
    deps: [runId, status?.status],
  });

  const approvalsPoll = usePoll((signal) => api.getApprovals(runId!, { signal }), {
    enabled: Boolean(runId) && apiConfig.ok,
    intervalMs: 1500,
    shouldStop: () => terminal,
    deps: [runId, status?.status],
  });

  const manifestPoll = usePoll(
    async (signal) => {
      try {
        return await api.getManifest(runId!, { signal });
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) return null;
        throw err;
      }
    },
    {
      enabled: Boolean(runId) && apiConfig.ok,
      intervalMs: 2000,
      deps: [runId, status?.status],
    },
  );

  const stall = useStalledRun(status, statusPoll.consecutiveFailures);

  const [audit, setAudit] = useState<AuditVerify | null>(null);
  useEffect(() => {
    if (!runId || !manifestPoll.data) return;
    let cancelled = false;
    const ac = new AbortController();
    void api.verifyAudit(runId, { signal: ac.signal }).then(
      (v) => {
        if (!cancelled) setAudit(v);
      },
      () => {
        if (!cancelled) {
          setAudit({
            ok: false,
            events_checked: 0,
            errors: ["verify failed"],
            message: "verify failed",
          });
        }
      },
    );
    return () => {
      cancelled = true;
      ac.abort();
    };
  }, [runId, manifestPoll.data]);

  const [approvalHinted, setApprovalHinted] = useState(false);
  useEffect(() => {
    if (
      !approvalHinted &&
      status?.status === "AWAITING_APPROVAL" &&
      view !== "actions" &&
      view !== "launch"
    ) {
      setView("actions");
      setApprovalHinted(true);
    }
  }, [status?.status, view, approvalHinted]);

  useEffect(() => {
    if (!recordingMode) return;
    const s = status?.status;
    if (s === "COMPLETED" || s === "COMPLETED_WITH_BLOCKS" || s === "MANIFEST_READY") {
      if (view !== "manifest" && view !== "launch") setView("manifest");
    }
  }, [recordingMode, status?.status, view]);

  const unlocked = useMemo(() => unlockedViews(status, Boolean(runId)), [status, runId]);

  const onStarted = useCallback((m: LaunchMeta) => {
    setMeta(m);
    setView("redline");
    setAudit(null);
    setApprovalHinted(false);
  }, []);

  const returnToLaunch = useCallback(() => {
    setMeta(null);
    setAudit(null);
    setView("launch");
  }, []);

  const ready: ReadyzResponse | null = readyPoll.data;
  const healthOk =
    healthPoll.data != null ? healthPoll.data.status === "ok" : healthPoll.error ? false : null;
  const changes: SemanticChange[] | null = changesPoll.data;
  const impact: ImpactGraph | null = impactPoll.data;
  const findings: RehearsalFinding[] | null = findingsPoll.data;
  const actions: ActionExecution[] | null = actionsPoll.data;
  const approvals: ApprovalRequest[] | null = approvalsPoll.data;
  const manifest: Manifest | null = manifestPoll.data;

  const pendingApproval = (approvals ?? []).find((a) => a.status === "pending") ?? null;

  const sessionId =
    status?.session_id ?? pendingApproval?.session_id ?? status?.pending_approval?.session_id ?? null;
  const invocationId =
    status?.invocation_id ??
    pendingApproval?.invocation_id ??
    status?.pending_approval?.invocation_id ??
    null;

  const cloudMode =
    ready?.execution_mode === "cloud" ||
    ready?.app_env === "cloud" ||
    status?.execution_mode === "cloud";

  const showAwaitingApprovalPanel =
    status?.status === "AWAITING_APPROVAL" && !(stall.stalled && stall.reason === "poll_failures");

  return (
    <div className="app" data-recording={recordingMode ? "true" : "false"}>
      <SyntheticBanner />
      <header className="app-header" data-compact={view === "launch" ? "true" : "false"}>
        <div className="brand-block">
          {view !== "launch" ? (
            <>
              <p className="brand">Protocol 215</p>
              <h1>Clinical Amendment Preflight</h1>
            </>
          ) : (
            <p className="brand-eyebrow">
              {recordingMode
                ? "Recording mode · ?demo=1 · synthetic AURORA-101"
                : "AURORA-101 · synthetic amendment rehearsal"}
            </p>
          )}
        </div>
        <ModeBar
          ready={ready}
          executionMode={status?.execution_mode ?? ready?.execution_mode}
          runId={runId}
          status={status}
          recordingMode={recordingMode}
        />
      </header>

      <ApiDiagnostics
        config={apiConfig}
        healthOk={apiConfig.ok ? healthOk : false}
        healthDetail={
          !apiConfig.ok
            ? apiConfig.reason
            : (healthPoll.error?.message ?? (healthOk === false ? "API /livez failed" : null))
        }
      />

      <StageIndicator status={status} />
      <ResumeProofBanner
        runId={runId}
        status={status?.status ?? null}
        sessionId={sessionId}
        invocationId={invocationId}
      />
      <ViewNav active={view} onChange={setView} unlocked={unlocked} />

      {showAwaitingApprovalPanel && status && <AwaitingApprovalPanel status={status} />}

      {stall.stalled && status && (
        <StalledRunPanel
          status={status}
          elapsedMs={stall.elapsedMs}
          reason={stall.reason ?? "stale_progress"}
          onRetryStatus={() => statusPoll.reload()}
          onReturnLaunch={returnToLaunch}
        />
      )}

      {statusPoll.error && !status && (
        <ErrorState error={statusPoll.error} onRetry={() => statusPoll.reload()} />
      )}

      {status && isRetryableFailure(status.status) && (
        <ErrorState
          error={new Error(status.error_summary ?? "Retryable workflow failure")}
          onRetry={() => statusPoll.reload()}
        />
      )}
      {status && status.status === "FAILED_TERMINAL" && (
        <ErrorState error={new Error(status.error_summary ?? "Terminal workflow failure")} />
      )}

      <main className="app-main" id="main">
        {view === "launch" && (
          <LaunchView
            recent={recentPoll.data}
            recentError={recentPoll.error}
            onReloadRecent={recentPoll.reload}
            onStarted={(m) => onStarted(m)}
            recordingMode={recordingMode}
            apiConfigOk={apiConfig.ok}
            apiHealthy={healthOk === true}
            cloudMode={Boolean(cloudMode)}
            onReset={returnToLaunch}
          />
        )}
        {view === "redline" && (
          <RedlineView
            changes={changes}
            impact={impact}
            loading={changesPoll.loading && !changes}
            error={changesPoll.error}
            onRetry={changesPoll.reload}
            recordingMode={recordingMode}
          />
        )}
        {view === "impact" && (
          <ImpactGraphView
            graph={impact}
            loading={impactPoll.loading && !impact}
            error={impactPoll.error}
            onRetry={impactPoll.reload}
          />
        )}
        {view === "timeline" && <TimelineView findings={findings} />}
        {view === "findings" && (
          <FindingsView
            findings={findings}
            loading={findingsPoll.loading && !findings}
            error={findingsPoll.error}
            onRetry={findingsPoll.reload}
          />
        )}
        {view === "actions" && (
          <ActionsView
            runId={runId}
            status={status}
            actions={actions}
            approvals={approvals}
            loading={actionsPoll.loading && !actions}
            error={actionsPoll.error}
            onRetry={actionsPoll.reload}
            recordingMode={recordingMode}
            onDecision={() => {
              statusPoll.reload();
              actionsPoll.reload();
              approvalsPoll.reload();
              manifestPoll.reload();
            }}
          />
        )}
        {view === "manifest" && (
          <ManifestView
            meta={meta}
            status={status}
            manifest={manifest}
            audit={audit}
            loading={manifestPoll.loading && !manifest}
            error={manifestPoll.error}
            onRetry={manifestPoll.reload}
            recordingMode={recordingMode}
          />
        )}
      </main>

      <footer className="app-footer">
        <span>
          {runId ? `Run ${runId}` : "No active run"}
          {status && !terminal ? " · polling" : ""}
          {recordingMode ? " · recording mode" : ""}
        </span>
        <span>Judge-facing demo · no chatbot</span>
      </footer>
    </div>
  );
}
