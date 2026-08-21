import { useCallback, useEffect, useMemo, useState } from "react";
import { api, ApiError } from "./api/client";
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
import { ModeBar, StageIndicator, SyntheticBanner } from "./components/Chrome";
import { ErrorState } from "./components/States";
import { ViewNav } from "./components/ViewNav";
import { usePoll } from "./hooks/usePoll";
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
  // Once a run exists, all judge views are navigable; empty/loading states show stage wait.
  return new Set(all);
}

export default function App() {
  const [view, setView] = useState<ViewId>("launch");
  const [meta, setMeta] = useState<LaunchMeta | null>(null);
  const runId = meta?.run_id ?? null;

  const readyPoll = usePoll(() => api.readyz(), { intervalMs: 8000 });
  const recentPoll = usePoll(() => api.listRuns(), { intervalMs: 5000 });

  const statusPoll = usePoll(() => api.getRun(runId!), {
    enabled: Boolean(runId),
    intervalMs: 1200,
    deps: [runId],
  });

  const changesPoll = usePoll(() => api.getChanges(runId!), {
    enabled: Boolean(runId),
    intervalMs: 2000,
    deps: [runId, statusPoll.data?.status],
  });

  const impactPoll = usePoll(() => api.getImpact(runId!), {
    enabled: Boolean(runId),
    intervalMs: 2500,
    deps: [runId, statusPoll.data?.status],
  });

  const findingsPoll = usePoll(() => api.getFindings(runId!), {
    enabled: Boolean(runId),
    intervalMs: 2000,
    deps: [runId, statusPoll.data?.status],
  });

  const actionsPoll = usePoll(() => api.getActions(runId!), {
    enabled: Boolean(runId),
    intervalMs: 1500,
    deps: [runId, statusPoll.data?.status],
  });

  const approvalsPoll = usePoll(() => api.getApprovals(runId!), {
    enabled: Boolean(runId),
    intervalMs: 1500,
    deps: [runId, statusPoll.data?.status],
  });

  const manifestPoll = usePoll(async () => {
    try {
      return await api.getManifest(runId!);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) return null;
      throw err;
    }
  }, {
    enabled: Boolean(runId),
    intervalMs: 2000,
    deps: [runId, statusPoll.data?.status],
  });

  const [audit, setAudit] = useState<AuditVerify | null>(null);
  useEffect(() => {
    if (!runId || !manifestPoll.data) return;
    let cancelled = false;
    void api.verifyAudit(runId).then(
      (v) => {
        if (!cancelled) setAudit(v);
      },
      () => {
        if (!cancelled) setAudit({ ok: false, events_checked: 0, errors: ["verify failed"], message: "verify failed" });
      },
    );
    return () => {
      cancelled = true;
    };
  }, [runId, manifestPoll.data]);

  // Hint once when approval becomes available (do not fight manual navigation).
  const [approvalHinted, setApprovalHinted] = useState(false);
  useEffect(() => {
    if (
      !approvalHinted &&
      statusPoll.data?.status === "AWAITING_APPROVAL" &&
      view !== "actions" &&
      view !== "launch"
    ) {
      setView("actions");
      setApprovalHinted(true);
    }
  }, [statusPoll.data?.status, view, approvalHinted]);

  const unlocked = useMemo(
    () => unlockedViews(statusPoll.data, Boolean(runId)),
    [statusPoll.data, runId],
  );

  const onStarted = useCallback((m: LaunchMeta) => {
    setMeta(m);
    setView("redline");
    setAudit(null);
    setApprovalHinted(false);
  }, []);

  const ready: ReadyzResponse | null = readyPoll.data;
  const status: RunStatus | null = statusPoll.data;
  const changes: SemanticChange[] | null = changesPoll.data;
  const impact: ImpactGraph | null = impactPoll.data;
  const findings: RehearsalFinding[] | null = findingsPoll.data;
  const actions: ActionExecution[] | null = actionsPoll.data;
  const approvals: ApprovalRequest[] | null = approvalsPoll.data;
  const manifest: Manifest | null = manifestPoll.data;

  return (
    <div className="app">
      <SyntheticBanner />
      <header className="app-header" data-compact={view === "launch" ? "true" : "false"}>
        <div className="brand-block">
          {view !== "launch" ? (
            <>
              <p className="brand">Protocol 215</p>
              <h1>Clinical Amendment Preflight</h1>
            </>
          ) : (
            <p className="brand-eyebrow">AURORA-101 · synthetic amendment rehearsal</p>
          )}
        </div>
        <ModeBar ready={ready} executionMode={status?.execution_mode ?? ready?.execution_mode} />
      </header>

      <StageIndicator status={status} />
      <ViewNav active={view} onChange={setView} unlocked={unlocked} />

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
            onReset={() => {
              setMeta(null);
              setAudit(null);
              setView("launch");
            }}
          />
        )}
        {view === "redline" && (
          <RedlineView
            changes={changes}
            impact={impact}
            loading={changesPoll.loading}
            error={changesPoll.error}
            onRetry={changesPoll.reload}
          />
        )}
        {view === "impact" && (
          <ImpactGraphView
            graph={impact}
            loading={impactPoll.loading}
            error={impactPoll.error}
            onRetry={impactPoll.reload}
          />
        )}
        {view === "timeline" && <TimelineView findings={findings} />}
        {view === "findings" && (
          <FindingsView
            findings={findings}
            loading={findingsPoll.loading}
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
            loading={actionsPoll.loading}
            error={actionsPoll.error}
            onRetry={actionsPoll.reload}
            onDecision={() => {
              statusPoll.reload();
              actionsPoll.reload();
              approvalsPoll.reload();
            }}
          />
        )}
        {view === "manifest" && (
          <ManifestView
            meta={meta}
            status={status}
            manifest={manifest}
            audit={audit}
            loading={manifestPoll.loading}
            error={manifestPoll.error}
            onRetry={manifestPoll.reload}
          />
        )}
      </main>

      <footer className="app-footer">
        <span>
          {runId ? `Run ${runId}` : "No active run"}
          {status && !isTerminal(status.status) ? " · polling" : ""}
        </span>
        <span>Judge-facing demo · no chatbot</span>
      </footer>
    </div>
  );
}
