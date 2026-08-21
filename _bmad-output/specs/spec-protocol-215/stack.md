# Runtime stack

Mandatory submitted architecture (hackathon rules: Gemini 3.5+, approved Google agent framework, ≥1 GCP service).

## Gemini (Vertex AI)

- Model: Gemini 3.5 or newer via Vertex AI / Gemini API.
- Configure via `GEMINI_MODEL=<qualifying model id>` — do not hard-code an unverified identifier.
- Responsibilities: multimodal protocol interpretation; Protocol IR extraction; semantic amendment comparison; ambiguous impact reasoning; restricted action planning; human-readable conflict explanation.

## Google Agent Development Kit (ADK)

- Workflow orchestration; agent + deterministic-node composition; tool invocation; workflow state; human confirmation; pause/resume; event history.
- Confirmation responses must resume the **same** `invocation_id`.

## Cloud Run

- Hosts frontend, API, and asynchronous ADK worker.
- `min instances = 0`; cap `max instances`; turn off unused services after recording deploy evidence.

## Pub/Sub

- Topic/event: `amendment.received` from intake → async worker.
- Consumers must be idempotent under duplicate delivery.

## Firestore

Stores: runs, protocol versions, changes, sites, participants, actions, approvals, audit events, release manifests.

Synthetic system collections mutated by tools represent: CTMS-like state, site training, EDC change control, laboratory ops, trial supplies, site approval status, amendment actions.

## Cloud Storage

- Synthetic protocol PDFs, generated artifacts, optional HTML release-manifest output.

## Cloud Logging

- Visible evidence of Cloud execution, Pub/Sub delivery, ADK activity, tool execution, failures/retries.

## Development-only (not runtime architecture)

Cursor, Claude Code, Codex/ChatGPT, BMAD Method, GitHub, Terraform/scripts. Disclose any pre-existing incorporated work; project must be newly created in the submission period.
