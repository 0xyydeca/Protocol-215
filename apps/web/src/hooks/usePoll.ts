import { useEffect, useRef, useState } from "react";

export type PollLoader<T> = (signal: AbortSignal) => Promise<T>;

type PollOptions<T> = {
  enabled?: boolean;
  intervalMs?: number;
  /** Stop scheduling after a successful load when this returns true. */
  shouldStop?: (data: T) => boolean;
  deps?: unknown[];
  backoffBaseMs?: number;
  backoffMaxMs?: number;
  hiddenMultiplier?: number;
};

/**
 * Sequential recursive setTimeout polling.
 * - Never starts a second request until the prior completes
 * - Aborts in-flight requests on unmount / dep change
 * - Backs off after failures; slows down when the tab is hidden
 * - One loop per hook instance (no duplicate intervals)
 */
export function usePoll<T>(
  loader: PollLoader<T>,
  {
    enabled = true,
    intervalMs = 1500,
    shouldStop,
    deps = [] as unknown[],
    backoffBaseMs = 1000,
    backoffMaxMs = 15_000,
    hiddenMultiplier = 4,
  }: PollOptions<T>,
): {
  data: T | null;
  error: Error | null;
  loading: boolean;
  consecutiveFailures: number;
  reload: () => void;
} {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [loading, setLoading] = useState(true);
  const [consecutiveFailures, setConsecutiveFailures] = useState(0);
  const [tick, setTick] = useState(0);
  const loaderRef = useRef(loader);
  loaderRef.current = loader;
  const shouldStopRef = useRef(shouldStop);
  shouldStopRef.current = shouldStop;
  const inFlightRef = useRef(false);

  useEffect(() => {
    if (!enabled) {
      setLoading(false);
      return;
    }

    let cancelled = false;
    let timer: number | null = null;
    let failures = 0;
    let stopped = false;
    const abortRef = { current: new AbortController() };

    const clearTimer = () => {
      if (timer != null) {
        window.clearTimeout(timer);
        timer = null;
      }
    };

    const schedule = (delay: number) => {
      clearTimer();
      if (cancelled || stopped) return;
      timer = window.setTimeout(() => void tickOnce(), delay);
    };

    const nextDelay = () => {
      const hidden =
        typeof document !== "undefined" && document.visibilityState === "hidden";
      const base = hidden ? intervalMs * hiddenMultiplier : intervalMs;
      if (failures <= 0) return base;
      const backed = Math.min(backoffMaxMs, backoffBaseMs * 2 ** (failures - 1));
      return Math.max(base, backed);
    };

    async function tickOnce() {
      if (cancelled || stopped || inFlightRef.current) return;
      inFlightRef.current = true;
      abortRef.current = new AbortController();
      try {
        const next = await loaderRef.current(abortRef.current.signal);
        if (cancelled) return;
        setData(next);
        setError(null);
        setLoading(false);
        failures = 0;
        setConsecutiveFailures(0);
        if (shouldStopRef.current?.(next)) {
          stopped = true;
          return;
        }
      } catch (err) {
        if (cancelled) return;
        if (err instanceof DOMException && err.name === "AbortError") return;
        if (err instanceof Error && err.name === "AbortError") return;
        failures += 1;
        setConsecutiveFailures(failures);
        setError(err instanceof Error ? err : new Error(String(err)));
        setLoading(false);
      } finally {
        inFlightRef.current = false;
        if (!cancelled && !stopped) schedule(nextDelay());
      }
    }

    const onVisibility = () => {
      if (cancelled || stopped || inFlightRef.current) return;
      schedule(document.visibilityState === "visible" ? 0 : nextDelay());
    };

    void tickOnce();
    document.addEventListener("visibilitychange", onVisibility);

    return () => {
      cancelled = true;
      clearTimer();
      abortRef.current.abort();
      inFlightRef.current = false;
      document.removeEventListener("visibilitychange", onVisibility);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, intervalMs, tick, backoffBaseMs, backoffMaxMs, hiddenMultiplier, ...deps]);

  return {
    data,
    error,
    loading,
    consecutiveFailures,
    reload: () => setTick((t) => t + 1),
  };
}
