# Cloud E2E Results

_Last updated: 2026-08-30T01:39:16.571115+00:00 (UTC)_

## Verdict

**PASS**

## Evidence

| Field | Value |
| --- | --- |
| commit_sha | `6ee7f018c6c30efc8f03cae4856285edd0568dd1` |
| web_url | `https://protocol-215-web-u6nfupvmhq-uc.a.run.app` |
| web_revision | `protocol-215-web-00010-hnm` |
| worker_revision | `protocol-215-worker-00008-pz8` |
| gemini_model | `gemini-3.5-flash` |
| run_id | `run-694ee197-0c66-4a26-9055-834572fac0ff` |
| correlation_id | `run-694ee197-0c66-4a26-9055-834572fac0ff` |
| start_event_id | `evt-fdae79a0-a7d3-4ab3-bd59-c57f28953d65` |
| session_id | `550c56fc-003c-453b-883b-c0795d130fa8` |
| invocation_id | `e-c2a0da94-f004-40dc-9d3d-b4c2349c18e1` |
| elapsed_seconds | 97.4 |

## Adapter honesty

```json
{
  "object_store": "GCSObjectStore",
  "state_store": "FirestoreStateStore",
  "event_bus": "PubSubEventBus",
  "compiler": "VertexGeminiProtocolCompiler"
}
```

## Checkpoint path observed

```
CREATED → IntakeValidator → SemanticDiff → ActionPlanner → SafeActionExecutor → ApprovalRouter
```

## Assertions

- [x] healthz
- [x] web_traffic_100
- [x] adapter_object_store
- [x] adapter_state_store
- [x] adapter_event_bus
- [x] live_gemini_readyz
- [x] gemini_3_5_plus
- [x] worker_readyz
- [x] worker_revision_observed
- [x] demo_reset
- [x] create_within_60s
- [x] create_202
- [x] reached_awaiting_approval
- [x] persisted_checkpoints
- [x] firestore_run_exists
- [x] gcs_pdfs_exist
- [x] pubsub_start_delivered
- [x] run_live_gemini_3_5
- [x] start_event_id_captured
- [x] exactly_five_changes
- [x] all_changes_have_page_evidence
- [x] finding_FINDING_BOSTON_TRAINING_REQUIRED
- [x] finding_FINDING_SEATTLE_APPROVAL_TRAINING_REQUIRED
- [x] finding_FINDING_P001_DAY1_IMMUTABLE
- [x] finding_FINDING_P002_COURIER_STORAGE_CONFLICT
- [x] green_actions_completed
- [x] green_ids_unique
- [x] approval_accepted
- [x] completed
- [x] same_session_resumed
- [x] invocation_tracked
- [x] green_actions_immutable_across_resume
- [x] manifest_exists
- [x] all_invariants_pass
- [x] audit_chain_verifies

