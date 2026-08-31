/** Shared API types matching Protocol 215 FastAPI contract. */

export type WorkflowStatus =
  | "CREATED"
  | "ARTIFACTS_REGISTERED"
  | "COMPILING"
  | "ANALYZING"
  | "REHEARSING"
  | "PLANNING"
  | "EXECUTING_SAFE_ACTIONS"
  | "AWAITING_APPROVAL"
  | "RESUMING"
  | "VERIFYING"
  | "COMPLETED"
  | "COMPLETED_WITH_BLOCKS"
  | "FAILED_RETRYABLE"
  | "FAILED_TERMINAL"
  | string;

export type ViewId =
  | "launch"
  | "redline"
  | "impact"
  | "timeline"
  | "findings"
  | "actions"
  | "manifest";

export type ApiErrorBody = {
  error_code: string;
  message: string;
  correlation_id: string;
  retryable: boolean;
  details?: Record<string, unknown>;
};

export type ReadyzResponse = {
  status: string;
  service?: string;
  version?: string;
  app_env?: string;
  execution_mode?: string;
  synthetic_study?: boolean;
  study_id?: string;
  compiler_mode?: "fake" | "live_gemini" | string;
  gemini_model?: string;
  cloud_run_revision?: string | null;
  backends?: {
    object_store?: string;
    state_store?: string;
    event_bus?: string;
    gemini?: string;
    gemini_model?: string;
  };
  demo_mode?: {
    synthetic_study?: string;
    runtime?: string;
    compiler?: string;
    model_id?: string;
    cloud_run_revision?: string | null;
  };
};

export type CreateRunResponse = {
  run_id: string;
  status: WorkflowStatus;
  study_id: string;
  from_version: string;
  to_version: string;
  old_sha256: string;
  new_sha256: string;
  old_pages: number;
  new_pages: number;
  event_published: boolean;
  message: string;
};

export type PendingApprovalSummary = {
  approval_id: string;
  action_id?: string | null;
  tool_name?: string | null;
  affected_site_id?: string | null;
  affected_participant_id?: string | null;
  expected_state_version: number;
  reason_approval_required: string;
  session_id?: string | null;
  interrupt_id?: string | null;
  invocation_id?: string | null;
};

export type RunStatus = {
  run_id: string;
  study_id: string;
  from_version: string;
  to_version: string;
  status: WorkflowStatus;
  current_stage: string;
  progress: number;
  last_event: string | null;
  pending_approval: PendingApprovalSummary | null;
  completed_action_count: number;
  blocked_action_count: number;
  error_summary: string | null;
  execution_mode: string;
  state_version: number;
  checkpoint: string | null;
  created_at: string;
  event_sequence: string[];
  /** Persisted ADK session / invocation identity for resume proof. */
  session_id?: string | null;
  invocation_id?: string | null;
  /** Diagnostic fields for stalled-run detection (backend-authored). */
  updated_at?: string | null;
  last_checkpoint_at?: string | null;
  last_worker_event_id?: string | null;
  last_error_code?: string | null;
  last_error_detail_safe?: string | null;
  correlation_id?: string | null;
  web_revision?: string | null;
  worker_revision?: string | null;
  actual_adapters?: Record<string, string> | null;
  compiler_model?: string | null;
};

export type RunListItem = {
  run_id: string;
  study_id: string;
  status: WorkflowStatus;
  from_version: string;
  to_version: string;
  created_at: string;
  current_stage: string;
};

export type EvidenceReference = {
  page: number;
  section_id: string;
  quote?: string | null;
  confidence?: number;
  review_status?: string;
  protocol_version?: string | null;
};

export type SemanticChange = {
  change_id: string;
  concept_type: string;
  operation: string;
  before?: Record<string, unknown> | null;
  after?: Record<string, unknown> | null;
  evidence?: EvidenceReference[];
  old_evidence?: EvidenceReference[];
  new_evidence?: EvidenceReference[];
  candidate_risk?: string | null;
  expected_risk_tier?: string | null;
  affected_artifact_ids?: string[];
  explanation?: string;
  review_status?: string;
};

export type ImpactNode = {
  node_id: string;
  artifact_type: string;
  label: string;
  layer: string;
  ref_id?: string | null;
};

export type ImpactEdge = {
  edge_id: string;
  change_id: string;
  from_node_id: string;
  to_node_id: string;
  relationship: string;
};

export type ImpactGraph = {
  nodes: ImpactNode[];
  edges: ImpactEdge[];
  node_count: number;
  edge_count: number;
};

export type RehearsalFinding = {
  finding_id: string;
  code: string;
  severity: string;
  summary: string;
  site_id?: string | null;
  participant_id?: string | null;
  change_ids?: string[];
  details?: Record<string, unknown>;
};

export type ActionExecution = {
  execution_id: string;
  proposal_id: string;
  tool_name: string;
  status: string;
  authorized_tier: string;
  evidence?: EvidenceReference[];
  site_id?: string | null;
  participant_id?: string | null;
  before?: Record<string, unknown> | null;
  after?: Record<string, unknown> | null;
  approved?: boolean;
  executed?: boolean;
  executed_at?: string | null;
};

export type ApprovalRequest = {
  approval_id: string;
  run_id: string;
  action_ids: string[];
  status: string;
  expected_state_version: number;
  action_id?: string | null;
  tool_name?: string | null;
  affected_site_id?: string | null;
  affected_participant_id?: string | null;
  change_evidence?: EvidenceReference[];
  operational_evidence?: EvidenceReference[];
  before_state?: Record<string, unknown>;
  proposed_after_state?: Record<string, unknown>;
  reason_approval_required?: string;
  consequences_of_approval?: string;
  consequences_of_rejection?: string;
  session_id?: string | null;
  invocation_id?: string | null;
  interrupt_id?: string | null;
};

export type InvariantResult = {
  invariant_id: string;
  name: string;
  passed: boolean;
  message: string;
  details?: Record<string, unknown>;
};

export type Manifest = {
  run_id: string;
  study_id: string;
  from_version: string;
  to_version: string;
  changes: SemanticChange[];
  findings: RehearsalFinding[];
  actions: ActionExecution[];
  invariants: InvariantResult[];
  generated_at: string;
  /** Trial Twin roster sizes (not derived from finding/action references). */
  sites_evaluated_count?: number | null;
  participants_evaluated_count?: number | null;
};

export type AuditVerify = {
  ok: boolean;
  events_checked: number;
  errors: string[];
  message: string;
};

export type LaunchMeta = {
  run_id: string;
  old_sha256: string;
  new_sha256: string;
  old_name: string;
  new_name: string;
  study_id: string;
};
