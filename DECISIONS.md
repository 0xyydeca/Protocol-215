# DECISIONS.md — Architecture decision log

## D-001 — Active product is Protocol 215 only

**Decision:** The hackathon submission is Protocol 215: Clinical Amendment Preflight (Taskmaster).  
**Rejected:** Autonomous schema-change / data-pipeline first-responder (chat-only plan; never scaffolded).  
**Consequence:** All implementation and docs refer to clinical amendment preflight. Agents must refuse schema-change scope.

## D-002 — Approval resume via Pub/Sub, not held HTTP/ADK wait

**Decision:** Human approval is captured by `protocol-215-web`, persisted in Firestore, then published as `amendment.resume`. Worker consumes resume asynchronously.  
**Rejected:** Long-running HTTP request or single continuous ADK invocation that blocks until the operator clicks approve.  
**Conflict note:** Earlier drafts (`docs/PROTOCOL_215_PLAN.md`, BMAD SPEC companions) described “same ADK invocation_id resume.” That wording is **superseded** by this decision. BMAD SPEC should be updated in a later planning pass; runtime contract is this file + `ARCHITECTURE.md`.  
**Input doc:** `docs/PROTOCOL_215_INPUT.md` Stage 9 still mentions same-invocation ADK confirmation — treat INPUT as product narrative; **runtime resume mechanism is `amendment.resume`** per Prompt 0.

## D-003 — Two Cloud Run services

**Decision:** `protocol-215-web` (UI/API) and `protocol-215-worker` (ADK).  
**Rationale:** Separates request latency from async agent work; enables scale-to-zero and clear demo proof.

## D-004 — Extraction model is tool-less; planner never sees PDFs

**Decision:** Protocol IR compilation uses Gemini with **zero** tool access. Action planner receives only structured IR/changes/findings/twin facts.  
**Rationale:** Prompt-injection and confused-deputy resistance.

## D-005 — Hash-chained append-only audit

**Decision:** Every audit event includes `prev_hash` and `event_hash`. Application logic never updates/deletes audit rows.  
**Rationale:** Demo-visible integrity; supports replay investigations.

## D-006 — Contract docs live at repo root

**Decision:** `PRODUCT.md`, `RULES.md`, `ARCHITECTURE.md`, `SECURITY.md`, `EVALUATION.md`, `AGENTS.md`, `DECISIONS.md`, `ROADMAP.md` at `protocol-215/` root for quality-gate discovery. Detailed narrative remains in `docs/PROTOCOL_215_INPUT.md`.

## D-007 — Keep BMAD install; do not delete

**Decision:** Retain `_bmad/`, `.agents/`, `_bmad-output/` as development methodology. Runtime architecture is Google stack above, not BMAD.

## Assumptions requiring implementation validation

1. Exact Gemini 3.5 Flash model ID available on Vertex for `GEMINI_MODEL` at submission time.
2. Google ADK 2.x Python graph APIs support our node/checkpoint pattern with Pub/Sub-driven resume.
3. Synthetic PDF fixtures can be authored so gold five-change recall and cited pages are stable.
4. Firestore emulator + Pub/Sub emulator (or faithful fakes) suffice for local e2e.
5. Cloud Run min instances = 0 keeps demo cost within credit budget.
6. Nested `protocol-215/` git root is the submission repo content (parent `Protocol-215` may wrap it).
