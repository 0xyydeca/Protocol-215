import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { usePoll } from "./usePoll";

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("usePoll", () => {
  it("does not overlap in-flight requests", async () => {
    let active = 0;
    let maxActive = 0;
    let releases: Array<() => void> = [];

    const loader = vi.fn(
      () =>
        new Promise<number>((resolve) => {
          active += 1;
          maxActive = Math.max(maxActive, active);
          releases.push(() => {
            active -= 1;
            resolve(1);
          });
        }),
    );

    vi.useFakeTimers();
    const { unmount } = renderHook(() =>
      usePoll(loader, { intervalMs: 100, deps: [] }),
    );

    await act(async () => {
      await Promise.resolve();
    });
    expect(loader).toHaveBeenCalledTimes(1);

    await act(async () => {
      vi.advanceTimersByTime(500);
    });
    // Still waiting on first request — no second call.
    expect(loader).toHaveBeenCalledTimes(1);

    await act(async () => {
      releases[0]?.();
      await Promise.resolve();
    });
    expect(maxActive).toBe(1);
    unmount();
  });

  it("aborts in-flight request on unmount", async () => {
    const seenAborted: boolean[] = [];
    const loader = vi.fn(
      (signal: AbortSignal) =>
        new Promise<string>((_resolve, reject) => {
          signal.addEventListener("abort", () => {
            seenAborted.push(true);
            reject(new DOMException("Aborted", "AbortError"));
          });
        }),
    );

    const { unmount } = renderHook(() => usePoll(loader, { intervalMs: 5000 }));
    await waitFor(() => expect(loader).toHaveBeenCalled());
    unmount();
    await waitFor(() => expect(seenAborted.length).toBeGreaterThan(0));
  });

  it("stops polling at terminal status via shouldStop", async () => {
    const loader = vi.fn(async () => ({ status: "COMPLETED" as const }));
    vi.useFakeTimers();
    renderHook(() =>
      usePoll(loader, {
        intervalMs: 200,
        shouldStop: (d) => d.status === "COMPLETED",
      }),
    );

    await act(async () => {
      await Promise.resolve();
    });
    expect(loader).toHaveBeenCalledTimes(1);

    await act(async () => {
      vi.advanceTimersByTime(2000);
      await Promise.resolve();
    });
    expect(loader).toHaveBeenCalledTimes(1);
  });
});
