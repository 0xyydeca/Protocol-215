import type {
  ApprovalRequest,
  AuditVerify,
  CreateRunResponse,
  ImpactGraph,
  Manifest,
  ReadyzResponse,
  RehearsalFinding,
  RunListItem,
  RunStatus,
  SemanticChange,
  ActionExecution,
} from "./types";
import { apiRequest, TIMEOUTS } from "./request";
import { resolveApiBaseUrl } from "./config";

export { ApiError } from "./apiError";
export { apiUrl, TIMEOUTS, apiRequest } from "./request";
export { resolveApiBaseUrl, getApiConfig, apiOriginLabel } from "./config";

export type FetchOpts = { signal?: AbortSignal };

export const api = {
  apiBaseUrl(): string {
    return resolveApiBaseUrl();
  },

  async healthz(opts: FetchOpts = {}): Promise<ReadyzResponse> {
    return apiRequest({ path: "/healthz", signal: opts.signal, timeoutMs: TIMEOUTS.health });
  },

  async readyz(opts: FetchOpts = {}): Promise<ReadyzResponse> {
    return apiRequest({ path: "/readyz", signal: opts.signal, timeoutMs: TIMEOUTS.health });
  },

  async listRuns(opts: FetchOpts = {}): Promise<RunListItem[]> {
    return apiRequest({ path: "/api/runs", signal: opts.signal, timeoutMs: TIMEOUTS.poll });
  },

  async createRun(form: FormData, opts: FetchOpts = {}): Promise<CreateRunResponse> {
    return apiRequest({
      path: "/api/runs",
      method: "POST",
      body: form,
      signal: opts.signal,
      timeoutMs: TIMEOUTS.upload,
    });
  },

  async getRun(runId: string, opts: FetchOpts = {}): Promise<RunStatus> {
    return apiRequest({
      path: `/api/runs/${encodeURIComponent(runId)}`,
      signal: opts.signal,
      timeoutMs: TIMEOUTS.poll,
    });
  },

  async getChanges(runId: string, opts: FetchOpts = {}): Promise<SemanticChange[]> {
    return apiRequest({
      path: `/api/runs/${encodeURIComponent(runId)}/changes`,
      signal: opts.signal,
      timeoutMs: TIMEOUTS.poll,
    });
  },

  async getImpact(runId: string, opts: FetchOpts = {}): Promise<ImpactGraph> {
    return apiRequest({
      path: `/api/runs/${encodeURIComponent(runId)}/impact`,
      signal: opts.signal,
      timeoutMs: TIMEOUTS.poll,
    });
  },

  async getFindings(runId: string, opts: FetchOpts = {}): Promise<RehearsalFinding[]> {
    return apiRequest({
      path: `/api/runs/${encodeURIComponent(runId)}/findings`,
      signal: opts.signal,
      timeoutMs: TIMEOUTS.poll,
    });
  },

  async getActions(runId: string, opts: FetchOpts = {}): Promise<ActionExecution[]> {
    return apiRequest({
      path: `/api/runs/${encodeURIComponent(runId)}/actions`,
      signal: opts.signal,
      timeoutMs: TIMEOUTS.poll,
    });
  },

  async getApprovals(runId: string, opts: FetchOpts = {}): Promise<ApprovalRequest[]> {
    return apiRequest({
      path: `/api/runs/${encodeURIComponent(runId)}/approvals`,
      signal: opts.signal,
      timeoutMs: TIMEOUTS.poll,
    });
  },

  async submitApproval(
    runId: string,
    approvalId: string,
    body: {
      decision: "approved" | "rejected";
      expected_state_version: number;
      comment?: string;
    },
    opts: FetchOpts = {},
  ): Promise<{ approval_id: string; event_published: boolean }> {
    return apiRequest({
      path: `/api/runs/${encodeURIComponent(runId)}/approvals/${encodeURIComponent(approvalId)}`,
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: opts.signal,
      timeoutMs: TIMEOUTS.approval,
    });
  },

  async getManifest(runId: string, opts: FetchOpts = {}): Promise<Manifest> {
    return apiRequest({
      path: `/api/runs/${encodeURIComponent(runId)}/manifest`,
      signal: opts.signal,
      timeoutMs: TIMEOUTS.poll,
    });
  },

  async verifyAudit(runId: string, opts: FetchOpts = {}): Promise<AuditVerify> {
    return apiRequest({
      path: `/api/runs/${encodeURIComponent(runId)}/audit/verify`,
      signal: opts.signal,
      timeoutMs: TIMEOUTS.poll,
    });
  },

  async demoReset(
    confirm = false,
    opts: FetchOpts = {},
  ): Promise<{
    ok: boolean;
    message: string;
    sites_restored?: number;
    participants_restored?: number;
  }> {
    const q = confirm ? "?confirm=true" : "";
    return apiRequest({
      path: `/api/demo/reset${q}`,
      method: "POST",
      signal: opts.signal,
      timeoutMs: TIMEOUTS.default,
    });
  },

  async recordingReadiness(opts: FetchOpts = {}): Promise<{
    overall: string;
    checks: { name: string; status: string; detail: string }[];
    failed_count: number;
    passed_count: number;
    observed: Record<string, unknown>;
  }> {
    return apiRequest({
      path: "/api/demo/recording-readiness",
      signal: opts.signal,
      timeoutMs: TIMEOUTS.health,
    });
  },
};
