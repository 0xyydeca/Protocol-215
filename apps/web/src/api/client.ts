import type {
  ApiErrorBody,
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

export class ApiError extends Error {
  readonly body: ApiErrorBody;
  readonly status: number;

  constructor(status: number, body: ApiErrorBody) {
    super(body.message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }

  get retryable(): boolean {
    return this.body.retryable;
  }
}

/** API origin for hosted UI (Vercel). Empty = same-origin / Vite proxy. */
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

function apiUrl(path: string): string {
  return `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}

async function parse<T>(res: Response): Promise<T> {
  const text = await res.text();
  let data: unknown = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { message: text };
  }
  if (!res.ok) {
    const body = (data ?? {}) as Partial<ApiErrorBody>;
    throw new ApiError(res.status, {
      error_code: body.error_code ?? "http_error",
      message: body.message ?? `HTTP ${res.status}`,
      correlation_id: body.correlation_id ?? "unknown",
      retryable: Boolean(body.retryable),
      details: body.details,
    });
  }
  return data as T;
}

export const api = {
  async healthz(): Promise<ReadyzResponse> {
    return parse(await fetch(apiUrl("/healthz")));
  },

  async readyz(): Promise<ReadyzResponse> {
    return parse(await fetch(apiUrl("/readyz")));
  },

  async listRuns(): Promise<RunListItem[]> {
    return parse(await fetch(apiUrl("/api/runs")));
  },

  async createRun(form: FormData): Promise<CreateRunResponse> {
    return parse(
      await fetch(apiUrl("/api/runs"), {
        method: "POST",
        body: form,
      }),
    );
  },

  async getRun(runId: string): Promise<RunStatus> {
    return parse(await fetch(apiUrl(`/api/runs/${encodeURIComponent(runId)}`)));
  },

  async getChanges(runId: string): Promise<SemanticChange[]> {
    return parse(await fetch(apiUrl(`/api/runs/${encodeURIComponent(runId)}/changes`)));
  },

  async getImpact(runId: string): Promise<ImpactGraph> {
    return parse(await fetch(apiUrl(`/api/runs/${encodeURIComponent(runId)}/impact`)));
  },

  async getFindings(runId: string): Promise<RehearsalFinding[]> {
    return parse(await fetch(apiUrl(`/api/runs/${encodeURIComponent(runId)}/findings`)));
  },

  async getActions(runId: string): Promise<ActionExecution[]> {
    return parse(await fetch(apiUrl(`/api/runs/${encodeURIComponent(runId)}/actions`)));
  },

  async getApprovals(runId: string): Promise<ApprovalRequest[]> {
    return parse(await fetch(apiUrl(`/api/runs/${encodeURIComponent(runId)}/approvals`)));
  },

  async submitApproval(
    runId: string,
    approvalId: string,
    body: {
      decision: "approved" | "rejected";
      expected_state_version: number;
      comment?: string;
    },
  ): Promise<{ approval_id: string; event_published: boolean }> {
    return parse(
      await fetch(
        apiUrl(
          `/api/runs/${encodeURIComponent(runId)}/approvals/${encodeURIComponent(approvalId)}`,
        ),
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
      ),
    );
  },

  async getManifest(runId: string): Promise<Manifest> {
    return parse(await fetch(apiUrl(`/api/runs/${encodeURIComponent(runId)}/manifest`)));
  },

  async verifyAudit(runId: string): Promise<AuditVerify> {
    return parse(await fetch(apiUrl(`/api/runs/${encodeURIComponent(runId)}/audit/verify`)));
  },

  async demoReset(confirm = false): Promise<{
    ok: boolean;
    message: string;
    sites_restored?: number;
    participants_restored?: number;
  }> {
    const q = confirm ? "?confirm=true" : "";
    return parse(await fetch(apiUrl(`/api/demo/reset${q}`), { method: "POST" }));
  },

  async recordingReadiness(): Promise<{
    overall: string;
    checks: { name: string; status: string; detail: string }[];
    failed_count: number;
    passed_count: number;
    observed: Record<string, unknown>;
  }> {
    return parse(await fetch(apiUrl("/api/demo/recording-readiness")));
  },
};
