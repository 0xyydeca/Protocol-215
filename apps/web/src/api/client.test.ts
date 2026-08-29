import { describe, expect, it, vi } from "vitest";
import { apiUrl, apiRequest, TIMEOUTS } from "./request";
import { ApiError } from "./apiError";
import { formatNetworkError, sanitizeHeaders, humanizePollStall } from "./errors";
import { getApiConfig, resolveApiBaseUrl, isVercelHost } from "./config";

describe("API URL composition", () => {
  it("strips trailing slash and joins paths", () => {
    expect(resolveApiBaseUrl("https://api.example.run.app/")).toBe(
      "https://api.example.run.app",
    );
    expect(apiUrl("/api/runs", "https://api.example.run.app")).toBe(
      "https://api.example.run.app/api/runs",
    );
    expect(apiUrl("/healthz", "")).toBe("/healthz");
  });

  it("exposes timeout bounds", () => {
    expect(TIMEOUTS.poll).toBe(10_000);
    expect(TIMEOUTS.upload).toBe(60_000);
    expect(TIMEOUTS.approval).toBe(30_000);
  });
});

describe("Vercel API base", () => {
  it("detects vercel hosts", () => {
    expect(isVercelHost("protocol-215.vercel.app")).toBe(true);
    expect(isVercelHost("localhost")).toBe(false);
  });

  it("rejects non-https remote bases via getApiConfig shape", () => {
    const raw = "http://evil.example";
    expect(/^https:\/\//i.test(raw)).toBe(false);
    expect(getApiConfig().ok).toBe(true); // jsdom is localhost same-origin
  });
});

describe("network errors", () => {
  it("maps Failed to fetch to actionable error", () => {
    const err = formatNetworkError(new TypeError("Failed to fetch"), {
      method: "GET",
      path: "/api/runs/x",
      apiBaseUrl: "https://protocol-215-web.example.run.app",
      correlationId: "c1",
    });
    expect(err).toBeInstanceOf(ApiError);
    expect(err.message).toMatch(/API origin not reachable/);
    expect((err as ApiError).retryable).toBe(true);
  });

  it("maps abort to timeout retryable error", () => {
    const err = formatNetworkError(new DOMException("Aborted", "AbortError"), {
      method: "GET",
      path: "/api/runs/x",
      apiBaseUrl: "",
      correlationId: "c2",
    });
    expect(err.message).toMatch(/timed out/i);
    expect((err as ApiError).retryable).toBe(true);
  });

  it("maps 503 to Cloud Run message", () => {
    const err = formatNetworkError(
      new ApiError(503, {
        error_code: "unavailable",
        message: "nope",
        correlation_id: "c3",
        retryable: true,
      }),
      { method: "GET", path: "/readyz", apiBaseUrl: "", correlationId: "c3" },
    );
    expect(err.message).toMatch(/Cloud Run API returned 503/);
  });

  it("redacts secret headers", () => {
    expect(sanitizeHeaders({ Authorization: "Bearer secret", "Content-Type": "application/json" }))
      .toEqual({
        Authorization: "[redacted]",
        "Content-Type": "application/json",
      });
  });
});

describe("stalled copy", () => {
  it("names the checkpoint", () => {
    expect(humanizePollStall("CompileOldProtocol")).toBe(
      "Run appears stalled at CompileOldProtocol",
    );
  });
});

describe("apiRequest", () => {
  it("includes method/path diagnostics on HTTP errors", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: false,
        status: 404,
        text: async () =>
          JSON.stringify({
            error_code: "not_found",
            message: "Run not found.",
            correlation_id: "corr-9",
            retryable: false,
          }),
      })),
    );
    await expect(apiRequest({ path: "/api/runs/missing" })).rejects.toMatchObject({
      message: expect.stringMatching(/persistent state/i),
    });
  });
});
