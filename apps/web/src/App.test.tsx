import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { FindingsView } from "./views/FindingsView";
import { ManifestView } from "./views/ManifestView";
import { ActionsView } from "./views/ActionsView";
import { ErrorState, LoadingState } from "./components/States";
import { ApiError } from "./api/client";
import type { Manifest, RehearsalFinding, RunStatus } from "./api/types";

afterEach(() => {
  vi.restoreAllMocks();
});

function jsonResponse(data: unknown, ok = true, status = 200) {
  return {
    ok,
    status,
    text: async () => JSON.stringify(data),
    json: async () => data,
  };
}

function mockApiHappyPath() {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (
      url.endsWith("/readyz") ||
      url.endsWith("/healthz") ||
      url.endsWith("/livez") ||
      url.endsWith("/api/healthz")
    ) {
      return jsonResponse({
        status: "ok",
        service: "protocol-215-api",
        version: "0.1.0",
        app_env: "local",
        backends: { gemini: "fake", gemini_model: "gemini-3.5-flash" },
      });
    }
    if (url.endsWith("/api/runs") && (!init || init.method === "GET" || !init.method)) {
      return jsonResponse([]);
    }
    if (url.endsWith("/api/runs") && init?.method === "POST") {
      return jsonResponse({
        run_id: "run-test-1",
        status: "CREATED",
        study_id: "AURORA-101",
        from_version: "1.0",
        to_version: "2.0",
        old_sha256: "a".repeat(64),
        new_sha256: "b".repeat(64),
        old_pages: 13,
        new_pages: 13,
        event_published: true,
        message: "ok",
      });
    }
    if (url.includes("/api/runs/run-test-1") && !url.includes("/")) {
      /* fallthrough */
    }
    if (url.endsWith("/api/runs/run-test-1")) {
      return jsonResponse({
        run_id: "run-test-1",
        study_id: "AURORA-101",
        from_version: "1.0",
        to_version: "2.0",
        status: "AWAITING_APPROVAL",
        current_stage: "ApprovalRouter",
        progress: 0.75,
        last_event: "tool.executed",
        pending_approval: {
          approval_id: "apr-1",
          action_id: "act-1",
          tool_name: "draft_participant_transition_plan",
          affected_site_id: "SITE-001",
          affected_participant_id: "P002",
          expected_state_version: 8,
          reason_approval_required: "AMBER required",
        },
        completed_action_count: 6,
        blocked_action_count: 0,
        error_summary: null,
        execution_mode: "local",
        state_version: 9,
        checkpoint: "ApprovalRouter",
        created_at: "2026-08-21T00:00:00Z",
        event_sequence: [],
      } satisfies RunStatus);
    }
    if (url.endsWith("/changes")) {
      return jsonResponse([
        {
          change_id: "CHG-001",
          concept_type: "lab_contact",
          operation: "update",
          before: { phone: "old" },
          after: { phone: "new" },
          candidate_risk: "GREEN",
          review_status: "accepted",
          old_evidence: [{ page: 2, section_id: "lab", quote: "old lab" }],
          new_evidence: [{ page: 2, section_id: "lab", quote: "new lab" }],
        },
      ]);
    }
    if (url.endsWith("/impact")) {
      return jsonResponse({
        nodes: [
          {
            node_id: "change:CHG-001",
            artifact_type: "semantic_change",
            label: "CHG-001",
            layer: "protocol_change",
          },
          {
            node_id: "artifact:lab",
            artifact_type: "lab_manual",
            label: "lab_manual",
            layer: "operational_artifact",
          },
        ],
        edges: [
          {
            edge_id: "e1",
            change_id: "CHG-001",
            from_node_id: "change:CHG-001",
            to_node_id: "artifact:lab",
            relationship: "affects",
          },
        ],
        node_count: 2,
        edge_count: 1,
      });
    }
    if (url.endsWith("/findings")) {
      return jsonResponse([
        {
          finding_id: "F-P002-COURIER",
          code: "FINDING_P002_COURIER_STORAGE_CONFLICT",
          severity: "blocker",
          summary: "P002 has a courier/storage conflict.",
          site_id: "SITE-001",
          participant_id: "P002",
          details: {
            dose_time: "12:00",
            sample_time: "18:00",
            courier_departure: "17:30",
            overnight_storage: false,
          },
        },
      ]);
    }
    if (url.endsWith("/actions")) {
      return jsonResponse([
        {
          execution_id: "ex-1",
          proposal_id: "p1",
          tool_name: "create_courier_exception_task",
          status: "executed",
          authorized_tier: "GREEN",
          executed: true,
          site_id: "SITE-001",
          participant_id: "P002",
        },
      ]);
    }
    if (url.endsWith("/approvals") && (!init || !init.method || init.method === "GET")) {
      return jsonResponse([
        {
          approval_id: "apr-1",
          run_id: "run-test-1",
          action_ids: ["act-1"],
          status: "pending",
          expected_state_version: 8,
          tool_name: "draft_participant_transition_plan",
          affected_site_id: "SITE-001",
          affected_participant_id: "P002",
          reason_approval_required: "AMBER required",
          consequences_of_approval: "Execute after re-check",
          consequences_of_rejection: "Remain blocked",
          before_state: { status: "pending" },
          proposed_after_state: { drafted: true },
          change_evidence: [{ page: 4, section_id: "pk", quote: "6h sample" }],
          operational_evidence: [],
        },
      ]);
    }
    if (url.includes("/approvals/apr-1") && init?.method === "POST") {
      return jsonResponse({
        approval_id: "apr-1",
        run_id: "run-test-1",
        decision: "approved",
        event_published: true,
        message: "ok",
      });
    }
    if (url.endsWith("/manifest")) {
      return jsonResponse({
        run_id: "run-test-1",
        study_id: "AURORA-101",
        from_version: "1.0",
        to_version: "2.0",
        changes: [{ change_id: "CHG-001", concept_type: "lab_contact", operation: "update" }],
        findings: [],
        actions: [],
        invariants: [{ invariant_id: "INV-1", name: "no_red", passed: true, message: "ok" }],
        generated_at: "2026-08-21T00:00:00Z",
      });
    }
    if (url.endsWith("/audit/verify")) {
      return jsonResponse({ ok: true, events_checked: 3, errors: [], message: "ok" });
    }
    return jsonResponse({ error_code: "not_found", message: `unmocked ${url}`, correlation_id: "x", retryable: false }, false, 404);
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("App shell", () => {
  it("shows Protocol 215 branding, synthetic banner, and mode pills", async () => {
    mockApiHappyPath();
    render(<App />);
    expect(screen.getByText(/Synthetic data only/i)).toBeInTheDocument();
    expect(screen.getByText(/different protocol versions/i)).toBeInTheDocument();
    expect(screen.getByText("215")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText("Protocol 215")).toBeInTheDocument();
      expect(screen.getByText("Fake Compiler")).toBeInTheDocument();
      expect(screen.getByText("Local")).toBeInTheDocument();
      expect(screen.getByText("Synthetic Study")).toBeInTheDocument();
    });
    expect(screen.getByLabelText("Workflow stages")).toBeInTheDocument();
  });
});

describe("Loading and error states", () => {
  it("renders loading and retryable error panels", async () => {
    const user = userEvent.setup();
    render(<LoadingState label="Checking…" />);
    expect(screen.getByText("Checking…")).toBeInTheDocument();

    const onRetry = vi.fn();
    render(
      <ErrorState
        error={
          new ApiError(503, {
            error_code: "internal",
            message: "Temporary outage",
            correlation_id: "c-1",
            retryable: true,
          })
        }
        onRetry={onRetry}
      />,
    );
    expect(screen.getByText(/Temporary outage/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Retry/i }));
    expect(onRetry).toHaveBeenCalled();
  });
});

describe("FindingsView", () => {
  it("shows Phoenix P002 primary card details", () => {
    const findings: RehearsalFinding[] = [
      {
        finding_id: "F-P002-COURIER",
        code: "FINDING_P002_COURIER_STORAGE_CONFLICT",
        severity: "blocker",
        summary: "P002 has a courier/storage conflict.",
        participant_id: "P002",
        site_id: "SITE-001",
        details: {
          dose_time: "12:00",
          sample_time: "18:00",
          courier_departure: "17:30",
          overnight_storage: false,
        },
      },
    ];
    render(<FindingsView findings={findings} loading={false} error={null} onRetry={() => undefined} />);
    const card = screen.getByLabelText(/Phoenix P002 primary finding/i);
    expect(within(card).getByText("P002")).toBeInTheDocument();
    expect(within(card).getByText("12:00")).toBeInTheDocument();
    expect(within(card).getByText("18:00")).toBeInTheDocument();
    expect(within(card).getByText("17:30")).toBeInTheDocument();
    expect(within(card).getByText(/No validated overnight storage/i)).toBeInTheDocument();
    expect(within(card).getByText(/Activation blocked/i)).toBeInTheDocument();
  });
});

describe("ActionsView approval state", () => {
  it("shows approve/reject for pending approval", async () => {
    const user = userEvent.setup();
    const onDecision = vi.fn();
    const fetchMock = mockApiHappyPath();
    render(
      <ActionsView
        runId="run-test-1"
        status={null}
        actions={[]}
        approvals={[
          {
            approval_id: "apr-1",
            run_id: "run-test-1",
            action_ids: ["a1"],
            status: "pending",
            expected_state_version: 8,
            tool_name: "draft_participant_transition_plan",
            affected_site_id: "SITE-001",
            affected_participant_id: "P002",
            reason_approval_required: "Needs human gate",
            consequences_of_approval: "Resume",
            consequences_of_rejection: "Stay blocked",
            before_state: { x: 1 },
            proposed_after_state: { x: 2 },
            change_evidence: [{ page: 4, section_id: "pk" }],
          },
        ]}
        loading={false}
        error={null}
        onRetry={() => undefined}
        onDecision={onDecision}
      />,
    );
    expect(screen.getByLabelText(/Human approval panel/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /^Approve$/i }));
    await waitFor(() => expect(onDecision).toHaveBeenCalled());
    expect(fetchMock).toHaveBeenCalled();
  });
});

describe("ManifestView", () => {
  it("renders manifest summary and actions", () => {
    const manifest: Manifest = {
      run_id: "run-x",
      study_id: "AURORA-101",
      from_version: "1.0",
      to_version: "2.0",
      changes: [
        { change_id: "CHG-001", concept_type: "lab_contact", operation: "update" },
        { change_id: "CHG-002", concept_type: "pk_timepoint", operation: "add" },
      ],
      findings: [],
      actions: [
        {
          execution_id: "e1",
          proposal_id: "p1",
          tool_name: "notify_site",
          status: "executed",
          authorized_tier: "GREEN",
          executed: true,
        },
      ],
      invariants: [{ invariant_id: "INV-1", name: "no_red", passed: true, message: "ok" }],
      generated_at: "2026-08-21T00:00:00Z",
      sites_evaluated_count: 3,
      participants_evaluated_count: 5,
    };
    render(
      <ManifestView
        meta={{
          run_id: "run-x",
          old_sha256: "aa",
          new_sha256: "bb",
          old_name: "v1.pdf",
          new_name: "v2.pdf",
          study_id: "AURORA-101",
        }}
        status={{ status: "COMPLETED" } as RunStatus}
        manifest={manifest}
        audit={{ ok: true, events_checked: 4, errors: [], message: "ok" }}
        loading={false}
        error={null}
        onRetry={() => undefined}
      />,
    );
    expect(screen.getByText("Amendment Release Manifest")).toBeInTheDocument();
    expect(screen.getByText(/Intact/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Download JSON/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Print-ready HTML/i })).toBeInTheDocument();
    expect(screen.getByText("Sites evaluated").closest("div")?.querySelector("dd")?.textContent).toBe(
      "3",
    );
    expect(
      screen.getByText("Participants evaluated").closest("div")?.querySelector("dd")?.textContent,
    ).toBe("5");
  });

  it("uses backend rehearsal roster counts rather than deriving from findings", () => {
    const manifest: Manifest = {
      run_id: "run-y",
      study_id: "AURORA-101",
      from_version: "1.0",
      to_version: "2.0",
      changes: [],
      findings: [
        {
          finding_id: "F1",
          code: "X",
          severity: "blocker",
          summary: "one",
          site_id: "SITE-001",
          participant_id: "P002",
        },
      ],
      actions: [],
      invariants: [],
      generated_at: "2026-08-21T00:00:00Z",
      sites_evaluated_count: 3,
      participants_evaluated_count: 5,
    };
    render(
      <ManifestView
        meta={null}
        status={{ status: "COMPLETED" } as RunStatus}
        manifest={manifest}
        audit={null}
        loading={false}
        error={null}
        onRetry={() => undefined}
      />,
    );
    expect(
      screen.getByText("Participants evaluated").closest("div")?.querySelector("dd")?.textContent,
    ).toBe("5");
  });
});
