import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { STALL_THRESHOLD_MS, useStalledRun } from "./useStalledRun";
import type { RunStatus } from "../api/types";

afterEach(() => {
  vi.useRealTimers();
});

function status(partial: Partial<RunStatus> = {}): RunStatus {
  return {
    run_id: "run-1",
    study_id: "AURORA-101",
    from_version: "1.0",
    to_version: "2.0",
    status: "COMPILING",
    current_stage: "CompileOldProtocol",
    progress: 0.2,
    last_event: null,
    pending_approval: null,
    completed_action_count: 0,
    blocked_action_count: 0,
    error_summary: null,
    execution_mode: "cloud",
    state_version: 3,
    checkpoint: "CompileOldProtocol",
    created_at: "2026-08-29T00:00:00Z",
    event_sequence: [],
    correlation_id: "run-1",
    ...partial,
  };
}

describe("useStalledRun", () => {
  it("shows stalled message after 45 seconds without progress", () => {
    vi.useFakeTimers();
    const { result } = renderHook(() => useStalledRun(status(), 0));
    expect(result.current.stalled).toBe(false);

    act(() => {
      vi.advanceTimersByTime(STALL_THRESHOLD_MS + 1000);
    });

    expect(result.current.stalled).toBe(true);
    expect(result.current.reason).toBe("stale_progress");
  });

  it("still stalls on unchanged COMPILING after 45 seconds", () => {
    vi.useFakeTimers();
    const { result } = renderHook(() =>
      useStalledRun(
        status({ status: "COMPILING", checkpoint: "CompileOldProtocol", state_version: 2 }),
        0,
      ),
    );
    act(() => {
      vi.advanceTimersByTime(STALL_THRESHOLD_MS + 2000);
    });
    expect(result.current.stalled).toBe(true);
    expect(result.current.reason).toBe("stale_progress");
  });

  it("never treats AWAITING_APPROVAL as stale progress after 45 seconds", () => {
    vi.useFakeTimers();
    const { result } = renderHook(() =>
      useStalledRun(
        status({
          status: "AWAITING_APPROVAL",
          checkpoint: "ApprovalRouter",
          current_stage: "ApprovalRouter",
          state_version: 9,
        }),
        0,
      ),
    );
    act(() => {
      vi.advanceTimersByTime(STALL_THRESHOLD_MS + 10_000);
    });
    expect(result.current.stalled).toBe(false);
    expect(result.current.reason).toBeNull();
  });

  it("never treats COMPLETED / MANIFEST_READY / FAILED_TERMINAL as stale progress", () => {
    vi.useFakeTimers();
    for (const s of ["COMPLETED", "COMPLETED_WITH_BLOCKS", "MANIFEST_READY", "FAILED_TERMINAL"] as const) {
      const { result } = renderHook(() =>
        useStalledRun(status({ status: s, checkpoint: "VerifyInvariants" }), 0),
      );
      act(() => {
        vi.advanceTimersByTime(STALL_THRESHOLD_MS + 5000);
      });
      expect(result.current.stalled).toBe(false);
    }
  });

  it("stalls after three consecutive poll failures", () => {
    const { result } = renderHook(() => useStalledRun(status(), 3));
    expect(result.current.stalled).toBe(true);
    expect(result.current.reason).toBe("poll_failures");
  });

  it("reports poll_failures while awaiting approval (network diagnostic, not stall)", () => {
    const { result } = renderHook(() =>
      useStalledRun(
        status({
          status: "AWAITING_APPROVAL",
          checkpoint: "ApprovalRouter",
        }),
        3,
      ),
    );
    expect(result.current.stalled).toBe(true);
    expect(result.current.reason).toBe("poll_failures");
  });

  it("does not stall on terminal status", () => {
    vi.useFakeTimers();
    const { result } = renderHook(() =>
      useStalledRun(status({ status: "COMPLETED", checkpoint: "VerifyInvariants" }), 0),
    );
    act(() => {
      vi.advanceTimersByTime(STALL_THRESHOLD_MS + 5000);
    });
    expect(result.current.stalled).toBe(false);
  });
});
