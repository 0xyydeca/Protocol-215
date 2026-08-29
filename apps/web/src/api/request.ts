import type { ApiErrorBody } from "./types";
import { ApiError } from "./apiError";
import { formatNetworkError, sanitizeHeaders, type RequestDiagnostics } from "./errors";
import { resolveApiBaseUrl } from "./config";

export const TIMEOUTS = {
  poll: 10_000,
  upload: 60_000,
  approval: 30_000,
  default: 15_000,
  health: 8_000,
} as const;

export type RequestOptions = {
  method?: string;
  body?: BodyInit | null;
  headers?: HeadersInit;
  signal?: AbortSignal;
  timeoutMs?: number;
  /** Relative API path beginning with / */
  path: string;
};

function newCorrelationId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `corr-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function apiUrl(path: string, base = resolveApiBaseUrl()): string {
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${base}${p}`;
}

async function parseBody(res: Response): Promise<unknown> {
  const text = await res.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return { message: text };
  }
}

/**
 * Single request helper: AbortController, timeout, parsed errors, correlation ID,
 * configured base URL, and method/path in diagnostics. Never logs secret headers.
 */
export async function apiRequest<T>(options: RequestOptions): Promise<T> {
  const method = (options.method ?? "GET").toUpperCase();
  const path = options.path.startsWith("/") ? options.path : `/${options.path}`;
  const apiBaseUrl = resolveApiBaseUrl();
  const url = apiUrl(path, apiBaseUrl);
  const correlationId = newCorrelationId();
  const timeoutMs = options.timeoutMs ?? TIMEOUTS.default;

  const diagnostics: RequestDiagnostics = {
    method,
    path,
    apiBaseUrl,
    correlationId,
  };

  const controller = new AbortController();
  const onOuterAbort = () => controller.abort();
  if (options.signal) {
    if (options.signal.aborted) {
      controller.abort();
    } else {
      options.signal.addEventListener("abort", onOuterAbort, { once: true });
    }
  }
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);

  const headers = new Headers(options.headers);
  if (!headers.has("X-Correlation-ID")) {
    headers.set("X-Correlation-ID", correlationId);
  }
  void sanitizeHeaders(headers);

  try {
    const res = await fetch(url, {
      method,
      body: options.body,
      headers,
      signal: controller.signal,
    });
    diagnostics.status = res.status;
    const data = await parseBody(res);
    if (!res.ok) {
      const body = (data ?? {}) as Partial<ApiErrorBody>;
      const apiErr = new ApiError(res.status, {
        error_code: body.error_code ?? "http_error",
        message: body.message ?? `HTTP ${res.status}`,
        correlation_id: body.correlation_id ?? correlationId,
        retryable: Boolean(
          body.retryable ?? (res.status >= 500 || res.status === 408 || res.status === 429),
        ),
        details: { ...(body.details ?? {}), method, path, apiBaseUrl },
      });
      throw formatNetworkError(apiErr, {
        ...diagnostics,
        correlationId: apiErr.body.correlation_id,
        errorCode: apiErr.body.error_code,
      });
    }
    return data as T;
  } catch (err) {
    if (err instanceof ApiError) throw err;
    throw formatNetworkError(err, diagnostics);
  } finally {
    window.clearTimeout(timer);
    options.signal?.removeEventListener("abort", onOuterAbort);
  }
}
