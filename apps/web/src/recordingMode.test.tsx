/**
 * Recording mode (?demo=1) — never fabricate cloud/live status;
 * stages from backend; double-approve blocked; manifest from persisted data.
 */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ModeBar } from "./components/ModeBar";
import { StageIndicator } from "./components/Chrome";
import { ActionsView } from "./views/ActionsView";
import { ManifestView } from "./views/ManifestView";
import { isRecordingMode } from "./lib/recordingMode";
import { stageFromStatus } from "./lib/workflow";
import type { Manifest, RunStatus } from "./api/types";
import { api } from "./api/client";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("recordingMode flag", () => {
  it("detects ?demo=1 and leaves normal mode unchanged otherwise", () => {
    expect(isRecordingMode("?demo=1")).toBe(true);
    expect(isRecordingMode("?demo=true")).toBe(true);
    expect(isRecordingMode("")).toBe(false);
    expect(isRecordingMode("?foo=1")).toBe(false);
  });
});

describe("ModeBar never fabricates cloud/live", () => {
  it("shows Local and Fake when readiness says so — not Google Cloud / Live Gemini", () => {
    render(
      <ModeBar
        ready={{
          status: "ok",
          app_env: "local",
          execution_mode: "local",
          compiler_mode: "fake",
          gemini_model: "gemini-3.5-flash",
          backends: { gemini: "fake", gemini_model: "gemini-3.5-flash" },
          cloud_run_revision: null,
        }}
        executionMode="local"
        runId={null}
        status={null}
        recordingMode
      />,
    );
    expect(screen.getByText("Local")).toBeInTheDocument();
    expect(screen.getByText("Fake Compiler")).toBeInTheDocument();
    expect(screen.queryByText("Google Cloud")).not.toBeInTheDocument();
    expect(screen.queryByText("Live Gemini")).not.toBeInTheDocument();
    expect(screen.getByText(/Model: gemini-3.5-flash/)).toBeInTheDocument();
    expect(screen.getByText(/Revision: —/)).toBeInTheDocument();
  });

  it("shows Google Cloud and Live Gemini only when backend reports them", () => {
    render(
      <ModeBar
        ready={{
          status: "ok",
          app_env: "cloud",
          execution_mode: "cloud",
          compiler_mode: "live_gemini",
          gemini_model: "gemini-3.5-flash",
          backends: { gemini: "vertex", gemini_model: "gemini-3.5-flash" },
          cloud_run_revision: "protocol-215-web-00042-abc",
        }}
        executionMode="cloud"
        runId="run-xyz"
        status={{ status: "AWAITING_APPROVAL" } as RunStatus}
        recordingMode
      />,
    );
    expect(screen.getByText("Google Cloud")).toBeInTheDocument();
    expect(screen.getByText("Live Gemini")).toBeInTheDocument();
    expect(screen.getByText(/Revision: protocol-215-web-00042-abc/)).toBeInTheDocument();
    expect(screen.getByText(/Run: run-xyz/)).toBeInTheDocument();
    expect(screen.getByText(/Status: AWAITING_APPROVAL/)).toBeInTheDocument();
  });

  it("does not invent a model id when readiness omits it", () => {
    render(
      <ModeBar
        ready={{ status: "ok", app_env: "local", backends: { gemini: "fake" } }}
        recordingMode
      />,
    );
    expect(screen.getByText(/Model: —/)).toBeInTheDocument();
  });
});

describe("stage progression from backend only", () => {
  it("maps statuses to stages without timers", () => {
    expect(stageFromStatus("COMPILING")).toBe("Compile");
    expect(stageFromStatus("ANALYZING")).toBe("Trace");
    expect(stageFromStatus("REHEARSING")).toBe("Rehearse");
    expect(stageFromStatus("EXECUTING_SAFE_ACTIONS")).toBe("Act");
    expect(stageFromStatus("AWAITING_APPROVAL")).toBe("Approve");
    expect(stageFromStatus("RESUMING")).toBe("Approve");
    expect(stageFromStatus("VERIFYING")).toBe("Verify");
    expect(stageFromStatus("COMPLETED")).toBe("Verify");
  });

  it("StageIndicator current label follows status prop", () => {
    const { rerender } = render(
      <StageIndicator
        status={
          {
            status: "COMPILING",
            current_stage: "CompileOldProtocol",
            progress: 0.2,
            last_event: null,
          } as RunStatus
        }
      />,
    );
    expect(screen.getByText("Compile").closest("li")).toHaveAttribute("data-state", "current");
    rerender(
      <StageIndicator
        status={
          {
            status: "AWAITING_APPROVAL",
            current_stage: "ApprovalRouter",
            progress: 0.75,
            last_event: null,
          } as RunStatus
        }
      />,
    );
    expect(screen.getByText("Approve").closest("li")).toHaveAttribute("data-state", "current");
  });
});

describe("double-click approval prevention", () => {
  it("disables Approve after one click", async () => {
    const user = userEvent.setup();
    const submit = vi.spyOn(api, "submitApproval").mockResolvedValue({
      approval_id: "apr-1",
      event_published: true,
    });
    const onDecision = vi.fn();
    render(
      <ActionsView
        runId="run-1"
        status={
          {
            run_id: "run-1",
            status: "AWAITING_APPROVAL",
            pending_approval: {
              approval_id: "apr-1",
              expected_state_version: 1,
              reason_approval_required: "AMBER",
            },
          } as RunStatus
        }
        actions={[]}
        approvals={[
          {
            approval_id: "apr-1",
            run_id: "run-1",
            action_ids: ["a1"],
            status: "pending",
            expected_state_version: 1,
            tool_name: "draft_participant_transition_plan",
            reason_approval_required: "AMBER",
            consequences_of_approval: "execute",
            consequences_of_rejection: "block",
            before_state: { status: "pending" },
            proposed_after_state: { tool: "draft" },
            change_evidence: [{ page: 8, section_id: "SEC-PK" }],
            operational_evidence: [{ page: 8, section_id: "SEC-PK" }],
            session_id: "sess-1",
            invocation_id: "inv-1",
          },
        ]}
        loading={false}
        error={null}
        onRetry={() => undefined}
        onDecision={onDecision}
        recordingMode
      />,
    );
    const approve = screen.getByRole("button", { name: "Approve" });
    await user.click(approve);
    await user.click(approve);
    await waitFor(() => expect(submit).toHaveBeenCalledTimes(1));
    expect(approve).toBeDisabled();
    expect(screen.getByText(/Run ID/i)).toBeInTheDocument();
    expect(screen.getByText("sess-1")).toBeInTheDocument();
    expect(screen.getByText("inv-1")).toBeInTheDocument();
  });
});

describe("manifest values from persisted results", () => {
  it("does not show success metrics before manifest exists", () => {
    render(
      <ManifestView
        meta={null}
        status={{ status: "VERIFYING" } as RunStatus}
        manifest={null}
        audit={null}
        loading={false}
        error={null}
        onRetry={() => undefined}
        recordingMode
      />,
    );
    expect(screen.getByText(/No success metrics are shown/i)).toBeInTheDocument();
  });

  it("renders measured counts from manifest payload only", () => {
    const manifest: Manifest = {
      run_id: "run-m",
      study_id: "AURORA-101",
      from_version: "1.0",
      to_version: "2.0",
      generated_at: "2026-01-01T00:00:00Z",
      changes: [
        { change_id: "CHG-1", concept_type: "lab", operation: "update", evidence: [{ page: 2, section_id: "s" }] },
        { change_id: "CHG-2", concept_type: "pk", operation: "add", evidence: [{ page: 8, section_id: "SEC-PK" }] },
      ],
      findings: [{ finding_id: "f1", code: "P002", severity: "blocker", summary: "conflict", site_id: "SITE-001", participant_id: "P002" }],
      actions: [
        {
          execution_id: "e1",
          proposal_id: "p1",
          tool_name: "update_contact_directory",
          status: "executed",
          authorized_tier: "GREEN",
          executed: true,
          site_id: "SITE-001",
        },
      ],
      invariants: [
        { invariant_id: "INV-1", name: "no completed visit alter", passed: true, message: "ok" },
      ],
    };
    render(
      <ManifestView
        meta={{ run_id: "run-m", old_sha256: "aa", new_sha256: "bb", old_name: "a", new_name: "b", study_id: "AURORA-101" }}
        status={{ status: "COMPLETED" } as RunStatus}
        manifest={manifest}
        audit={{ ok: true, events_checked: 3, errors: [], message: "ok" }}
        loading={false}
        error={null}
        onRetry={() => undefined}
        recordingMode
      />,
    );
    expect(screen.getByText("Changes detected").closest("div")?.querySelector("dd")).toHaveTextContent("2");
    expect(screen.getByText("Unauthorized RED actions").closest("div")?.querySelector("dd")).toHaveTextContent("0");
    expect(screen.getByText(/PASS · Intact/)).toBeInTheDocument();
  });
});
