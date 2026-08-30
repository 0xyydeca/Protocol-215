import { ApiError } from "./apiError";

const SECRET_HEADER_RE = /authorization|api[_-]?key|x-api-key|bearer|token|cookie|set-cookie/i;

/** Never include secret header values in diagnostics. */
export function sanitizeHeaders(headers: HeadersInit | undefined): Record<string, string> {
  if (!headers) return {};
  const out: Record<string, string> = {};
  const entries =
    headers instanceof Headers
      ? [...headers.entries()]
      : Array.isArray(headers)
        ? headers
        : Object.entries(headers);
  for (const [key, value] of entries) {
    out[key] = SECRET_HEADER_RE.test(key) ? "[redacted]" : String(value);
  }
  return out;
}

export type RequestDiagnostics = {
  method: string;
  path: string;
  apiBaseUrl: string;
  correlationId?: string;
  status?: number;
  errorCode?: string;
};

export function formatNetworkError(err: unknown, diagnostics: RequestDiagnostics): Error {
  if (err instanceof ApiError) {
    return mapApiError(err, diagnostics);
  }

  const name = err instanceof Error ? err.name : "";
  const message = err instanceof Error ? err.message : String(err);
  const lower = message.toLowerCase();

  if (name === "AbortError" || lower.includes("aborted")) {
    return new ApiError(408, {
      error_code: "request_timeout",
      message: `Request timed out (${diagnostics.method} ${diagnostics.path}). The API did not respond in time — retry.`,
      correlation_id: diagnostics.correlationId ?? "unknown",
      retryable: true,
      details: { ...diagnostics },
    });
  }

  if (
    lower.includes("failed to fetch") ||
    lower.includes("networkerror") ||
    lower.includes("load failed")
  ) {
    const origin = diagnostics.apiBaseUrl || "(same-origin)";
    return new ApiError(0, {
      error_code: "network_unreachable",
      message: `API origin not reachable (${origin}). Check Cloud Run /livez (or /api/healthz), CORS, and that VITE_API_BASE_URL points at the API — not Vercel.`,
      correlation_id: diagnostics.correlationId ?? "unknown",
      retryable: true,
      details: { ...diagnostics, hint: "cors_or_network" },
    });
  }

  return new ApiError(0, {
    error_code: "network_error",
    message: `Network error on ${diagnostics.method} ${diagnostics.path}: ${message}`,
    correlation_id: diagnostics.correlationId ?? "unknown",
    retryable: true,
    details: { ...diagnostics },
  });
}

export function mapApiError(err: ApiError, diagnostics?: RequestDiagnostics): ApiError {
  const code = err.body.error_code;
  const status = err.status;
  let message = err.body.message;

  if (status === 503) {
    message = `Cloud Run API returned 503${
      diagnostics ? ` (${diagnostics.method} ${diagnostics.path})` : ""
    }. Service may be starting or backends are not ready.`;
  } else if (
    status === 404 &&
    (code === "not_found" || message.toLowerCase().includes("not found"))
  ) {
    message =
      "Run not found in persistent state. The worker may not have written this run, or Reset cleared it.";
  } else if (code === "gemini_timeout" || /gemini.*timed?\s*out/i.test(message)) {
    message =
      "Gemini request timed out. The compile step exceeded its deadline — retry the run.";
  } else if (code === "pubsub_publish_failed" || /pub\/?sub/i.test(message)) {
    message = "Pub/Sub delivery failed. The amendment event was not published to the worker.";
  } else if (/cors/i.test(message) || err.body.details?.hint === "cors_or_network") {
    message = `CORS preflight rejected or blocked. Allow this UI origin on the API (CORS_ORIGINS) for ${
      diagnostics?.method ?? "GET"
    } ${diagnostics?.path ?? "/api"}.`;
  } else if (code === "worker_stale" || /worker has not updated/i.test(message)) {
    message =
      "Worker has not updated the run. Pub/Sub may not be delivering or the worker handler is down.";
  }

  return new ApiError(err.status, {
    ...err.body,
    message,
    details: {
      ...(err.body.details ?? {}),
      ...(diagnostics ?? {}),
    },
  });
}

export function humanizePollStall(checkpoint: string | null | undefined): string {
  const cp = checkpoint?.trim() || "unknown checkpoint";
  return `Run appears stalled at ${cp}`;
}
