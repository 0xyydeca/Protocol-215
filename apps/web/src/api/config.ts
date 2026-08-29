/**
 * API origin configuration.
 * Empty base = same-origin (Cloud Run web serving SPA, or Vite proxy).
 * Vercel must set VITE_API_BASE_URL at build time — changing it requires a rebuild.
 */

export function resolveApiBaseUrl(
  raw: string | undefined = import.meta.env.VITE_API_BASE_URL,
): string {
  return (raw ?? "").trim().replace(/\/$/, "");
}

export type ApiConfigState =
  | { ok: true; apiBaseUrl: string; mode: "same-origin" | "cross-origin" }
  | { ok: false; reason: string; apiBaseUrl: string };

export function isVercelHost(
  hostname: string = typeof window !== "undefined" ? window.location.hostname : "",
): boolean {
  return hostname === "vercel.app" || hostname.endsWith(".vercel.app");
}

export function getApiConfig(): ApiConfigState {
  const apiBaseUrl = resolveApiBaseUrl();
  if (apiBaseUrl) {
    if (
      !/^https:\/\//i.test(apiBaseUrl) &&
      !/^http:\/\/(127\.0\.0\.1|localhost)(:\d+)?$/i.test(apiBaseUrl)
    ) {
      return {
        ok: false,
        reason: "VITE_API_BASE_URL must be HTTPS (or localhost HTTP for local rehearsal).",
        apiBaseUrl,
      };
    }
    return { ok: true, apiBaseUrl, mode: "cross-origin" };
  }

  if (typeof window !== "undefined" && isVercelHost(window.location.hostname)) {
    return {
      ok: false,
      reason:
        "VITE_API_BASE_URL is missing. Vercel cannot proxy /api to Cloud Run — set VITE_API_BASE_URL to the Cloud Run web URL and rebuild.",
      apiBaseUrl: "",
    };
  }

  return { ok: true, apiBaseUrl: "", mode: "same-origin" };
}

export function apiOriginLabel(base: string): string {
  if (!base) return "(same-origin)";
  return base;
}
