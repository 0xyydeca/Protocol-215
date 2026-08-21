# SECURITY.md — Protocol 215

## Synthetic-data-only policy

- Only synthetic protocols, sites, participants, and systems.
- No PHI, real patients, employer documents, or production clinical systems.
- No real EDC, CTMS, IRT, eTMF, or regulatory connectors.

## Prompt-injection protections

- PDF contents are **untrusted data**, never agent instructions.
- Extraction model has **no tools**.
- Action planner never receives raw PDF bytes — only validated IR, changes, findings, and twin operational facts.
- Tool names restricted to allowlist; unknown tools rejected.

## Strict model schemas

- All Gemini structured output validated with **Pydantic 2** and JSON Schema.
- Fail closed on malformed output (retry with budget → `FAILED`).
- No uncited `IRFact` may trigger an action.

## Tool allowlist

See `ARCHITECTURE.md`. Executors are deterministic Python writing Firestore + audit.

## Deterministic authorization

- Model may propose tiers; **code decides** GREEN / AMBER / RED.
- Model cannot authorize, impersonate approver, or mark approval complete.
- RED remains non-executable even if UI approve is clicked.
- Re-run policy gate immediately before any post-approval mutation.

## IAM boundaries

- Separate service accounts for `protocol-215-web` and `protocol-215-worker`.
- Least privilege: GCS object R/W (scoped buckets), Pub/Sub publish/consume, Firestore R/W, Vertex predict, Logging write.
- No project-owner keys in runtime; no secrets in source control (`.env` / Secret Manager only).

## Idempotency

- Every mutation carries an idempotency key.
- Duplicate `amendment.received` or `amendment.resume` deliveries must not duplicate actions.
- Resume skips completed keys from checkpoint.

## Audit hash chain

- `audit_events` are append-only (application never updates/deletes).
- Each event stores `prev_hash` and `event_hash` over canonical payload.
- Store decision summaries, evidence refs, tool inputs/outcomes — **not** hidden chain-of-thought.

## File-validation controls

- Allowed types: PDF only for protocols.
- Enforce size and page-count limits at intake.
- SHA-256 of each object stored on the run.
- Reject empty/corrupt uploads before Pub/Sub publish.

## Approvals

- Single-use `approval_id` bound to `run_id`, action set hash, and expected state.
- Reject if underlying state changed after request creation.
- Wrong or missing resume correlation → no mutation.

## No PHI / no secrets in source control

- Fixtures are clearly synthetic.
- No API keys, service-account JSON, or real protocol PDFs in git.
- Manifests and logs redact credentials.

## Immutability

- Completed visits, historical consent versions, and prior protocol-version assignments are immutable.
- P001 completed Day 1 must never be retroactively altered.
