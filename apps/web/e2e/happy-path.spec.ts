import { expect, test } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const shotDir = path.join(__dirname, "screenshots");

const statusAwaiting = {
  run_id: "run-e2e-1",
  study_id: "AURORA-101",
  from_version: "1.0",
  to_version: "2.0",
  status: "AWAITING_APPROVAL",
  current_stage: "ApprovalRouter",
  progress: 0.75,
  last_event: "tool.executed",
  pending_approval: {
    approval_id: "apr-e2e",
    action_id: "prop-p002",
    tool_name: "draft_participant_transition_plan",
    affected_site_id: "SITE-001",
    affected_participant_id: "P002",
    expected_state_version: 8,
    reason_approval_required: "AMBER authorization required",
  },
  completed_action_count: 6,
  blocked_action_count: 0,
  error_summary: null,
  execution_mode: "local",
  state_version: 9,
  checkpoint: "ApprovalRouter",
  created_at: "2026-08-21T00:00:00Z",
  event_sequence: ["SemanticDiff", "ApprovalRouter"],
};

const changes = [
  {
    change_id: "CHG-001",
    concept_type: "central_lab_contact",
    operation: "update",
    before: { email: "lab-v1@example.com" },
    after: { email: "lab-v2@example.com" },
    candidate_risk: "GREEN",
    review_status: "accepted",
    old_evidence: [{ page: 3, section_id: "lab", quote: "Contact v1" }],
    new_evidence: [{ page: 3, section_id: "lab", quote: "Contact v2" }],
    affected_artifact_ids: ["lab_manual"],
  },
  {
    change_id: "CHG-002",
    concept_type: "pk_timepoint",
    operation: "add",
    before: null,
    after: { hours_post_dose: 6 },
    candidate_risk: "AMBER",
    review_status: "accepted",
    old_evidence: [],
    new_evidence: [{ page: 8, section_id: "pk", quote: "6-hour PK sample" }],
  },
];

async function installFakeBackend(page: import("@playwright/test").Page) {
  let approved = false;
  await page.route("**/readyz", async (route) => {
    await route.fulfill({
      json: {
        status: "ok",
        app_env: "local",
        backends: { gemini: "fake", gemini_model: "gemini-3.5-flash", object_store: "local" },
      },
    });
  });
  await page.route("**/healthz", async (route) => {
    await route.fulfill({ json: { status: "ok", service: "protocol-215-api" } });
  });
  await page.route("**/api/runs", async (route) => {
    if (route.request().method() === "POST") {
      await route.fulfill({
        status: 202,
        json: {
          run_id: "run-e2e-1",
          status: "CREATED",
          study_id: "AURORA-101",
          from_version: "1.0",
          to_version: "2.0",
          old_sha256: "11".repeat(32),
          new_sha256: "22".repeat(32),
          old_pages: 13,
          new_pages: 13,
          event_published: true,
          message: "accepted",
        },
      });
      return;
    }
    await route.fulfill({
      json: [
        {
          run_id: "run-e2e-1",
          study_id: "AURORA-101",
          status: approved ? "COMPLETED" : "AWAITING_APPROVAL",
          from_version: "1.0",
          to_version: "2.0",
          created_at: "2026-08-21T00:00:00Z",
          current_stage: approved ? "CompleteRun" : "ApprovalRouter",
        },
      ],
    });
  });
  await page.route("**/api/runs/run-e2e-1", async (route) => {
    const body = {
      ...statusAwaiting,
      status: approved ? "COMPLETED" : "AWAITING_APPROVAL",
      progress: approved ? 1 : 0.75,
      pending_approval: approved ? null : statusAwaiting.pending_approval,
      current_stage: approved ? "CompleteRun" : "ApprovalRouter",
    };
    await route.fulfill({ json: body });
  });
  await page.route("**/api/runs/run-e2e-1/changes", async (route) => {
    await route.fulfill({ json: changes });
  });
  await page.route("**/api/runs/run-e2e-1/impact", async (route) => {
    await route.fulfill({
      json: {
        nodes: [
          { node_id: "c1", artifact_type: "semantic_change", label: "CHG-002", layer: "protocol_change" },
          { node_id: "a1", artifact_type: "pk_schedule", label: "pk_schedule", layer: "operational_artifact" },
          { node_id: "s1", artifact_type: "site", label: "Phoenix", layer: "site", ref_id: "SITE-001" },
          { node_id: "p1", artifact_type: "participant", label: "P002", layer: "participant" },
          { node_id: "f1", artifact_type: "finding", label: "courier", layer: "finding" },
          { node_id: "x1", artifact_type: "action", label: "transition", layer: "proposed_action" },
        ],
        edges: [
          { edge_id: "e1", change_id: "CHG-002", from_node_id: "c1", to_node_id: "a1", relationship: "affects" },
          { edge_id: "e2", change_id: "CHG-002", from_node_id: "a1", to_node_id: "s1", relationship: "affects" },
          { edge_id: "e3", change_id: "CHG-002", from_node_id: "s1", to_node_id: "p1", relationship: "affects" },
          { edge_id: "e4", change_id: "CHG-002", from_node_id: "p1", to_node_id: "f1", relationship: "produces" },
          { edge_id: "e5", change_id: "CHG-002", from_node_id: "f1", to_node_id: "x1", relationship: "requires" },
        ],
        node_count: 6,
        edge_count: 5,
      },
    });
  });
  await page.route("**/api/runs/run-e2e-1/findings", async (route) => {
    await route.fulfill({
      json: [
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
      ],
    });
  });
  await page.route("**/api/runs/run-e2e-1/actions", async (route) => {
    await route.fulfill({
      json: [
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
        {
          execution_id: "ex-2",
          proposal_id: "p2",
          tool_name: "draft_participant_transition_plan",
          status: approved ? "executed" : "authorized",
          authorized_tier: "AMBER",
          executed: approved,
          approved,
          site_id: "SITE-001",
          participant_id: "P002",
        },
      ],
    });
  });
  await page.route("**/api/runs/run-e2e-1/approvals**", async (route) => {
    if (route.request().method() === "POST") {
      approved = true;
      await route.fulfill({
        status: 202,
        json: {
          approval_id: "apr-e2e",
          run_id: "run-e2e-1",
          decision: "approved",
          event_published: true,
          message: "ok",
        },
      });
      return;
    }
    await route.fulfill({
      json: [
        {
          approval_id: "apr-e2e",
          run_id: "run-e2e-1",
          action_ids: ["prop-p002"],
          status: approved ? "approved" : "pending",
          expected_state_version: 8,
          tool_name: "draft_participant_transition_plan",
          affected_site_id: "SITE-001",
          affected_participant_id: "P002",
          reason_approval_required: "AMBER authorization required",
          consequences_of_approval: "Resume workflow",
          consequences_of_rejection: "Remain blocked",
          before_state: { plan: null },
          proposed_after_state: { plan: "drafted" },
          change_evidence: [{ page: 8, section_id: "pk", quote: "6h sample" }],
          operational_evidence: [],
        },
      ],
    });
  });
  await page.route("**/api/runs/run-e2e-1/manifest", async (route) => {
    await route.fulfill({
      json: {
        run_id: "run-e2e-1",
        study_id: "AURORA-101",
        from_version: "1.0",
        to_version: "2.0",
        changes,
        findings: [],
        actions: [],
        invariants: [{ invariant_id: "INV-NO-RED", name: "no_red", passed: true, message: "ok" }],
        generated_at: "2026-08-21T00:00:00Z",
      },
    });
  });
  await page.route("**/api/runs/run-e2e-1/audit/verify", async (route) => {
    await route.fulfill({
      json: { ok: true, events_checked: 12, errors: [], message: "Audit chain intact." },
    });
  });
}

test.describe("Protocol 215 happy path", () => {
  test("walks seven views with fake backend and captures screenshots", async ({ page }) => {
    await installFakeBackend(page);
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/");

    await expect(page.getByText("Protocol 215")).toBeVisible();
    await expect(page.getByText(/Synthetic data only/i)).toBeVisible();
    await page.screenshot({ path: path.join(shotDir, "01-launch.png"), fullPage: true });

    // Seed an active run via recent-runs path by posting then selecting through API-driven start:
    // Create a tiny PDF in browser and upload.
    const pdfBytes = Buffer.from(
      "%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n",
      "utf-8",
    );
    await page.getByLabel("Old protocol PDF").setInputFiles({
      name: "AURORA-101_Protocol_v1.0.pdf",
      mimeType: "application/pdf",
      buffer: pdfBytes,
    });
    await page.getByLabel("Amended protocol PDF").setInputFiles({
      name: "AURORA-101_Protocol_v2.0.pdf",
      mimeType: "application/pdf",
      buffer: pdfBytes,
    });
    await page.getByRole("button", { name: /Start Amendment Preflight/i }).click();

    await expect(page.getByText("Semantic Redline")).toBeVisible({ timeout: 10000 });
    await page.screenshot({ path: path.join(shotDir, "02-redline.png"), fullPage: true });

    await page.getByRole("button", { name: "Impact Graph" }).click();
    await expect(page.getByRole("heading", { name: "Impact Graph" })).toBeVisible();
    await page.screenshot({ path: path.join(shotDir, "03-impact.png"), fullPage: true });

    await page.getByRole("button", { name: "215-Day Timeline" }).click();
    await expect(page.getByRole("heading", { name: "215-Day Rollout Timeline" })).toBeVisible();
    await page.screenshot({ path: path.join(shotDir, "04-timeline.png"), fullPage: true });

    await page.getByRole("button", { name: "Rehearsal Findings" }).click();
    await expect(page.getByText(/No validated overnight storage/i)).toBeVisible();
    await page.screenshot({ path: path.join(shotDir, "05-findings.png"), fullPage: true });

    await page.getByRole("button", { name: "Action Ledger" }).click();
    await expect(page.getByLabel(/Human approval panel/i)).toBeVisible();
    await page.screenshot({ path: path.join(shotDir, "06-actions.png"), fullPage: true });

    await page.getByRole("button", { name: /^Approve$/i }).click();
    await page.getByRole("button", { name: "Release Manifest" }).click();
    await expect(page.getByRole("heading", { name: "Amendment Release Manifest" })).toBeVisible({
      timeout: 10000,
    });
    await page.screenshot({ path: path.join(shotDir, "07-manifest.png"), fullPage: true });
  });
});
