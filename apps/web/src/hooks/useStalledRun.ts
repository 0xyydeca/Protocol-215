import { useEffect, useRef, useState } from "react";
import type { RunStatus } from "../api/types";
import { isTerminal } from "../lib/workflow";

const STALL_MS = 45_000;

/**
 * Detect stalled runs without mutating backend state.
 * Triggers when status+state_version are unchanged for 45s, or after 3 consecutive poll failures.
 */
export function useStalledRun(
  status: RunStatus | null,
  consecutiveFailures: number,
): {
  stalled: boolean;
  reason: "stale_progress" | "poll_failures" | null;
  elapsedMs: number;
} {
  const [now, setNow] = useState(() => Date.now());
  const anchor = useRef<{ key: string; at: number } | null>(null);

  const key =
    status == null
      ? ""
      : `${status.run_id}|${status.status}|${status.state_version}|${status.checkpoint ?? ""}`;

  useEffect(() => {
    if (!status || isTerminal(status.status)) {
      anchor.current = null;
      return;
    }
    if (!anchor.current || anchor.current.key !== key) {
      anchor.current = { key, at: Date.now() };
    }
  }, [key, status]);

  useEffect(() => {
    if (!status || isTerminal(status.status)) return;
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, [status?.run_id, status?.status]);

  if (!status || isTerminal(status.status)) {
    return { stalled: false, reason: null, elapsedMs: 0 };
  }

  if (consecutiveFailures >= 3) {
    const elapsed = anchor.current ? now - anchor.current.at : 0;
    return { stalled: true, reason: "poll_failures", elapsedMs: elapsed };
  }

  const started = anchor.current?.at ?? now;
  const elapsedMs = now - started;
  if (elapsedMs >= STALL_MS) {
    return { stalled: true, reason: "stale_progress", elapsedMs };
  }
  return { stalled: false, reason: null, elapsedMs };
}

export const STALL_THRESHOLD_MS = STALL_MS;
