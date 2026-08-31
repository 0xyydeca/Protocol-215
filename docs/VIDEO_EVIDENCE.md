# Video evidence map — Protocol 215

**Purpose:** Link each judge-visible moment in the demo video to a requirement, a persisted `run_id`, and repository evidence.

**Important:** Timestamps must be filled from the **final uploaded public video** only. Rows below list **expected** evidence from the recorded cloud demo script (`demo/DEMO_SCRIPT.md`) and the verified cloud E2E run in `docs/CLOUD_E2E_RESULTS.md`. Delete any row that does not appear in the final cut before Devpost submission.

## Reference run (cloud E2E — measured)

| Field | Value |
| --- | --- |
| Evidence file | `docs/CLOUD_E2E_RESULTS.md` |
| E2E commit | `6ee7f018c6c30efc8f03cae4856285edd0568dd1` |
| `run_id` | `run-694ee197-0c66-4a26-9055-834572fac0ff` |
| `session_id` | `550c56fc-003c-453b-883b-c0795d130fa8` |
| `invocation_id` | `e-c2a0da94-f004-40dc-9d3d-b4c2349c18e1` |
| Hosted URL | https://protocol-215-web-u6nfupvmhq-uc.a.run.app |

If the video uses a **new** run, replace the `run_id` column with that run’s ID from the Mode bar / Firestore.

## Evidence table

| Video timestamp | Visible evidence | Requirement / claim | `run_id` | Supporting repository file |
| --- | --- | --- | --- | --- |
| `[fill from final video]` | Public Cloud Run `.run.app` URL in browser | Live hosted deployment | `[video run]` | `docs/DEPLOYMENT.md`; `docs/CLOUD_E2E_RESULTS.md` |
| `[fill from final video]` | Mode bar: **Google Cloud** | Cloud Run + cloud adapters active | `[video run]` | `apps/web/src/components/ModeBar.tsx`; `src/protocol215/health.py` |
| `[fill from final video]` | Mode bar: **Live Gemini** | Vertex Gemini backend (not fake compiler) | `[video run]` | `src/protocol215/adapters/gemini/factory.py`; E2E `live_gemini_readyz` |
| `[fill from final video]` | Mode bar: **gemini-3.5-flash** | Gemini 3.5+ model id | `[video run]` | `docs/CLOUD_E2E_RESULTS.md`; `GEMINI_MODEL` in Terraform |
| `[fill from final video]` | Semantic Redline: **five** evidence-linked change cards | Controlled AURORA diff | `[video run]` | `fixtures/gold/amendment_v1_to_v2_expected.json`; E2E `exactly_five_changes` |
| `[fill from final video]` | Impact graph with dependency edges | Impact analysis | `[video run]` | `src/protocol215/application/impact.py`; `apps/web/src/views/ImpactGraphView.tsx` |
| `[fill from final video]` | 215-Day Timeline + Findings (e.g. Phoenix P002 conflict) | Trial Twin rehearsal | `[video run]` | `src/protocol215/simulator/twin.py`; `apps/web/src/data/auroraTimeline.ts` |
| `[fill from final video]` | Action Ledger: executed GREEN actions | GREEN auto-execution | `[video run]` | `src/protocol215/policy/matrix.py`; E2E `green_actions_completed` |
| `[fill from final video]` | Amber **PAUSED FOR REQUIRED HUMAN APPROVAL** (not “stalled”) | Intentional AMBER checkpoint | `[video run]` | `apps/web/src/components/AwaitingApprovalPanel.tsx`; E2E `reached_awaiting_approval` |
| `[fill from final video]` | Resume proof: same run + session IDs; status RESUMING → COMPLETED | Persistent ADK resume | `[video run]` | `apps/web/src/components/Chrome.tsx`; E2E `same_session_resumed` |
| `[fill from final video]` | Manifest + audit verify | Proof of execution | `[video run]` | `src/protocol215/application/services.py`; E2E `manifest_exists`, `audit_chain_verifies` |
| `[fill from final video]` | Console: Firestore `runs/{run_id}` | Persisted cloud state | `[video run]` | `src/protocol215/adapters/state_store_firestore.py`; E2E `firestore_run_exists` |
| `[fill from final video]` | Console: GCS objects under `runs/{run_id}/protocols/` | PDF storage | `[video run]` | `src/protocol215/adapters/object_store_gcs.py`; E2E `gcs_pdfs_exist` |
| `[fill from final video]` | Console: Pub/Sub topic `protocol-215-events` | Async Taskmaster events | `[video run]` | `infra/terraform/pubsub.tf`; E2E `pubsub_start_delivered` |
| `[fill from final video]` | Console: separate **web** and **worker** Cloud Run services | Two-service architecture | `[video run]` | `infra/terraform/cloud_run.tf`; `ARCHITECTURE.md` |

## Console cutaway notes

- Project used for verified E2E: `protocol-215-demo` (see deploy scripts / operator notes — do not paste secrets or SA keys in the video).
- Pub/Sub **topic** name is `protocol-215-events`; message **event types** are `amendment.received` and `amendment.resume` (same topic, typed envelope).
