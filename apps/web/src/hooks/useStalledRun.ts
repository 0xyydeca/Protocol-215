import { useEffect, useRef, useState } from "react";
import type { RunStatus, WorkflowStatus } from "../api/types";
import { isTerminal } from "../lib/workflow";

const STALL_MS = 45_000;

/**
 * Intentional waiting / terminal checkpoints — not stale computational progress.
 * AWAITING_APPROVAL is a human-input pause; completed/failed/manifest states are done.
 */
export const NON_COMPUTATIONAL_STATUSES: ReadonlySet<string> = new Set([
  "AWAITING_APPROVAL",
  "COMPLETED",
  "COMPLETED_WITH_BLOCKS",
  "MANIFEST_READY",
  "FAILED_TERMINAL",
]);

/** Statuses where an unchanged status+state_version for 45s indicates a real stall. */
export const COMPUTATIONAL_STALL_STATUSES: ReadonlySet<string> = new Set([
  "COMPILING",
  "ANALYZING",
  "REHEARSING",
  "PLANNING",
  "EXECUTING_SAFE_ACTIONS",
  "RESUMING",
  "VERIFYING",
]);

export function isNonComputationalStatus(status: WorkflowStatus | undefined): boolean {
  return status != null && NON_COMPUTATIONAL_STATUSES.has(status);
}

export function isComputationalStallCandidate(status: WorkflowStatus | undefined): boolean {
  if (status == null || isTerminal(status) || isNonComputationalStatus(status)) {
    return false;
  }
  // Prefer the explicit computational set; also allow other in-progress statuses
  // (e.g. COMPILING_IR, EXECUTING_GREEN) that are not intentional waits.
  if (COMPUTATIONAL_STALL_STATUSES.has(status)) return true;
  return !isNonComputationalStatus(status) && !isTerminal(status);
}

/**
 * Detect stalled runs without mutating backend state.
 * Stale-progress triggers only for computational statuses after 45s unchanged.
 * Three consecutive poll failures still surface a network diagnostic (including
 * while awaiting approval) — that is polling failure, not workflow stall.
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

  const trackProgress = Boolean(status && isComputationalStallCandidate(status.status));

  useEffect(() => {
    if (!status || !trackProgress) {
      anchor.current = null;
      return;
    }
    if (!anchor.current || anchor.current.key !== key) {
      anchor.current = { key, at: Date.now() };
    }
  }, [key, status, trackProgress]);

  useEffect(() => {
    // Keep a clock for poll-failure elapsed time even while awaiting approval.
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

  if (!trackProgress) {
    return { stalled: false, reason: null, elapsedMs: 0 };
  }

  const started = anchor.current?.at ?? now;
  const elapsedMs = now - started;
  if (elapsedMs >= STALL_MS) {
    return { stalled: true, reason: "stale_progress", elapsedMs };
  }
  return { stalled: false, reason: null, elapsedMs };
}

export const STALL_THRESHOLD_MS = STALL_MS;
