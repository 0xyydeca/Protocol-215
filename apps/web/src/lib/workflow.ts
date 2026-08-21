import type { WorkflowStatus } from "../api/types";

export const STAGES = ["Compile", "Trace", "Rehearse", "Act", "Approve", "Verify"] as const;
export type StageName = (typeof STAGES)[number];

export function stageFromStatus(status: WorkflowStatus | undefined): StageName {
  switch (status) {
    case "CREATED":
    case "RECEIVED":
    case "ARTIFACTS_REGISTERED":
    case "COMPILING":
    case "COMPILING_IR":
    case "INTAKE_COMPLETE":
      return "Compile";
    case "ANALYZING":
    case "DIFFING":
    case "IMPACTING":
      return "Trace";
    case "REHEARSING":
      return "Rehearse";
    case "PLANNING":
    case "GATING":
    case "EXECUTING_SAFE_ACTIONS":
    case "EXECUTING_GREEN":
      return "Act";
    case "AWAITING_APPROVAL":
    case "RESUMING":
    case "EXECUTING_APPROVED_AMBER":
      return "Approve";
    case "VERIFYING":
    case "MANIFEST_READY":
    case "COMPLETED":
    case "COMPLETED_WITH_BLOCKS":
    case "PARTIAL":
      return "Verify";
    case "FAILED":
    case "FAILED_RETRYABLE":
    case "FAILED_TERMINAL":
      return "Verify";
    default:
      return "Compile";
  }
}

export function isTerminal(status: WorkflowStatus | undefined): boolean {
  return (
    status === "COMPLETED" ||
    status === "COMPLETED_WITH_BLOCKS" ||
    status === "FAILED" ||
    status === "FAILED_TERMINAL"
  );
}

export function isRetryableFailure(status: WorkflowStatus | undefined): boolean {
  return status === "FAILED_RETRYABLE";
}

export function shortHash(hash: string, n = 10): string {
  if (!hash) return "—";
  return hash.length <= n * 2 ? hash : `${hash.slice(0, n)}…${hash.slice(-n)}`;
}

export function formatJson(value: unknown): string {
  if (value == null) return "—";
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}
