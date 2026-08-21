import { useEffect, useRef, useState } from "react";

export function usePoll<T>(
  loader: () => Promise<T>,
  {
    enabled = true,
    intervalMs = 1500,
    deps = [] as unknown[],
  }: { enabled?: boolean; intervalMs?: number; deps?: unknown[] },
): { data: T | null; error: Error | null; loading: boolean; reload: () => void } {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);
  const loaderRef = useRef(loader);
  loaderRef.current = loader;

  useEffect(() => {
    if (!enabled) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    async function load() {
      try {
        const next = await loaderRef.current();
        if (!cancelled) {
          setData(next);
          setError(null);
          setLoading(false);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err : new Error(String(err)));
          setLoading(false);
        }
      }
    }
    void load();
    const id = window.setInterval(() => void load(), intervalMs);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, intervalMs, tick, ...deps]);

  return {
    data,
    error,
    loading,
    reload: () => setTick((t) => t + 1),
  };
}
