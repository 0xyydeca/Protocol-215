import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AwaitingApprovalPanel } from "./AwaitingApprovalPanel";
import { ResumeProofBanner } from "./Chrome";
import { StalledRunPanel } from "./StalledRunPanel";
import type { RunStatus } from "../api/types";

function baseStatus(partial: Partial<RunStatus> = {}): RunStatus {
  return {
    run_id: "run-1",
    study_id: "AURORA-101",
    from_version: "1.0",
    to_version: "2.0",
    status: "AWAITING_APPROVAL",
    current_stage: "ApprovalRouter",
    progress: 0.75,
    last_event: null,
    pending_approval: {
      approval_id: "apr-1",
      action_id: "act-1",
      tool_name: "draft_participant_transition_plan",
      affected_site_id: "SITE-001",
      affected_participant_id: "P002",
      expected_state_version: 8,
      reason_approval_required: "AMBER",
      session_id: "sess-real",
      invocation_id: "inv-real",
    },
    completed_action_count: 6,
    blocked_action_count: 0,
    error_summary: null,
    execution_mode: "local",
    state_version: 9,
    checkpoint: "ApprovalRouter",
    created_at: "2026-08-29T00:00:00Z",
    event_sequence: [],
    session_id: "sess-real",
    invocation_id: "inv-real",
    ...partial,
  };
}

describe("AwaitingApprovalPanel", () => {
  it("shows required-approval information without failure language", () => {
    render(<AwaitingApprovalPanel status={baseStatus()} />);
    expect(screen.getByTestId("awaiting-approval-panel")).toBeInTheDocument();
    expect(screen.getByText("PAUSED FOR REQUIRED HUMAN APPROVAL")).toBeInTheDocument();
    expect(
      screen.getByText(/completed all permitted GREEN actions/i),
    ).toBeInTheDocument();
    expect(screen.getByText("ApprovalRouter")).toBeInTheDocument();
    expect(screen.getByText("run-1")).toBeInTheDocument();
    expect(screen.getByText("apr-1")).toBeInTheDocument();
    expect(screen.getByText("6")).toBeInTheDocument();
    expect(screen.getByText("SITE-001")).toBeInTheDocument();
    expect(screen.getByText("P002")).toBeInTheDocument();
    expect(screen.queryByText(/stalled/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/failed/i)).not.toBeInTheDocument();
  });
});

describe("StalledRunPanel poll failures", () => {
  it("shows network diagnostic rather than workflow stall language", () => {
    render(
      <StalledRunPanel
        status={baseStatus()}
        elapsedMs={12_000}
        reason="poll_failures"
        onRetryStatus={() => undefined}
        onReturnLaunch={() => undefined}
      />,
    );
    expect(screen.getByTestId("poll-failure-panel")).toBeInTheDocument();
    expect(screen.getByText("Status polling failed")).toBeInTheDocument();
    expect(
      screen.getByText(/workflow itself is not assumed stalled/i),
    ).toBeInTheDocument();
    expect(screen.queryByText(/Run appears stalled/i)).not.toBeInTheDocument();
  });
});

describe("ResumeProofBanner", () => {
  it("shows persisted session and invocation IDs", () => {
    render(
      <ResumeProofBanner
        runId="run-1"
        status="COMPLETED"
        sessionId="sess-real"
        invocationId="inv-real"
      />,
    );
    expect(screen.getByTestId("resume-proof")).toBeInTheDocument();
    expect(screen.getByText("sess-real")).toBeInTheDocument();
    expect(screen.getByText("inv-real")).toBeInTheDocument();
    expect(screen.getByText(/AWAITING_APPROVAL → RESUMING → VERIFYING → COMPLETED/)).toBeInTheDocument();
  });

  it("hides Session and Invocation rows when IDs are missing (no dash placeholders)", () => {
    render(
      <ResumeProofBanner runId="run-1" status="COMPLETED" sessionId={null} invocationId={undefined} />,
    );
    expect(screen.getByText(/Run:/)).toBeInTheDocument();
    expect(screen.queryByText(/Session:/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Invocation:/)).not.toBeInTheDocument();
    expect(screen.queryByText("—")).not.toBeInTheDocument();
  });

  it("does not display fake placeholder IDs", () => {
    render(
      <ResumeProofBanner runId="run-1" status="AWAITING_APPROVAL" sessionId="" invocationId="  " />,
    );
    expect(screen.queryByText(/Session:/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Invocation:/)).not.toBeInTheDocument();
  });
});
