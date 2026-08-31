# Cloud E2E Results

_Last updated: 2026-08-31T04:31:10.254958+00:00 (UTC)_

Automated acceptance for the hosted Google Cloud demo. The **Final release E2E** section is the authoritative PASS for the current submission commit and revisions.

## Final release E2E

**PASS**

| Field | Value |
| --- | --- |
| commit_sha | `1bdf964f893d1298f6595c5631a4df928d6f3110` |
| web_url | `https://protocol-215-web-u6nfupvmhq-uc.a.run.app` |
| web_revision | `protocol-215-web-00014-vjz` |
| worker_revision | `protocol-215-worker-00012-zvc` |
| gemini_model | `gemini-3.5-flash` |
| run_id | `run-27ad9b01-49f9-49ee-81da-96956508ccd3` |
| correlation_id | `run-27ad9b01-49f9-49ee-81da-96956508ccd3` |
| start_event_id | `evt-bf617a0b-a511-45ca-8074-70cbea182602` |
| session_id | `c162b07d-eb8f-4173-8891-018b2fa5b0c5` |
| invocation_id | `e-f10471b3-1e50-4d73-98c3-942975abe8f2` |
| elapsed_seconds | 120.7 |

### Adapter honesty

```json
{
  "object_store": "GCSObjectStore",
  "state_store": "FirestoreStateStore",
  "event_bus": "PubSubEventBus",
  "compiler": "VertexGeminiProtocolCompiler"
}
```

### Checkpoint path observed

```
CREATED → IntakeValidator → CompileOldProtocol → TrialTwinSimulator → SafeActionExecutor → ApprovalRouter
```

### Assertions

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

## Historical E2E runs

### E2E run (2026-08-30 — commit `6ee7f018`, revisions web-00010 / worker-00008)

**PASS** — superseded by Final release E2E above.

| Field | Value |
| --- | --- |
| commit_sha | `6ee7f018c6c30efc8f03cae4856285edd0568dd1` |
| web_revision | `protocol-215-web-00010-hnm` |
| worker_revision | `protocol-215-worker-00008-pz8` |
| run_id | `run-694ee197-0c66-4a26-9055-834572fac0ff` |
| elapsed_seconds | 97.4 |

Full assertion list preserved in git history for commit `6ee7f018`.
