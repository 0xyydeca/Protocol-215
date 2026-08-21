# Protocol 215 — Implementation Plan (Hackathon)

> **SUPERSEDED (Prompt 0).** Runtime and stage contracts now live at repo root: `ARCHITECTURE.md`, `ROADMAP.md`, `PRODUCT.md`, `SECURITY.md`, `DECISIONS.md`. Resume is via Pub/Sub `amendment.resume` (not long-held HTTP / single blocked ADK wait). Keep this file for history only.

**Status:** Plan only. No implementation until this plan is accepted.  
**Category:** The Taskmaster  
**Repo:** `protocol-215/` only  
**Source inputs:** `docs/PROTOCOL_215_INPUT.md`, `_bmad-output/specs/spec-protocol-215/`

## Confirmation: prior plan superseded

- **No schema-change / data-pipeline project exists on disk.** Nothing named schema-first-responder, pipeline sentinel, or similar was created.
- Matches for `*schema*` under this tree are **BMAD skill assets** (`headless-schemas.md`, `stories-schema.md`) only — not the cancelled project.
- This document **fully replaces** the chat-only schema-change plan. That plan is abandoned. Do not implement it.

---

## 1. Updated repository structure

```text
protocol-215/
├── README.md                          # Local + Cloud spin-up (submission requirement)
├── ARCHITECTURE.md                    # Diagram + stack (submission requirement)
├── pyproject.toml
├── .env.example                       # GEMINI_MODEL, GCP project, buckets, topics
├── Makefile
│
├── apps/
│   ├── api/                           # Cloud Run: upload, run status, approval, artifacts
│   │   └── main.py
│   ├── worker/                        # Cloud Run: Pub/Sub → Google ADK workflow
│   │   ├── main.py
│   │   └── adk/
│   │       ├── agent.py               # Root ADK agent / workflow composition
│   │       ├── nodes/                 # Deterministic + Gemini nodes
│   │       ├── tools.py               # Allowlisted tools only
│   │       └── prompts.py
│   └── web/                           # Single-page judge-facing UI (7 screens)
│       └── ...
│
├── packages/
│   ├── models/                        # Pydantic domain + Gemini I/O schemas
│   ├── pdf_intake/                     # Hash, validate, GCS put (deterministic)
│   ├── protocol_ir/                   # IR schema + validators
│   ├── semantic_diff/                 # Post-process / normalize model diffs
│   ├── impact_graph/                  # Deterministic artifact fan-out
│   ├── trial_twin/                    # Load/rehearse synthetic sites & participants
│   ├── policy/                        # GREEN / AMBER / RED gate (code owns authz)
│   ├── tools_runtime/                 # Tool executors → Firestore mutations
│   ├── audit/                         # Append-only audit events
│   ├── invariants/                    # Post-execution checks
│   └── manifest/                      # Amendment Release Manifest builder
│
├── fixtures/
│   ├── protocols/                     # Synthetic AURORA-101 v1.0 / v2.0 PDFs
│   ├── twin/                          # Sites, participants, inventory, couriers
│   └── gold/                          # Five gold-standard semantic changes
│
├── scripts/
│   ├── run_local.sh                   # Fixtures/emulators + api + worker + web
│   ├── seed_twin.py
│   └── demo_trigger.py
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/                           # Full AURORA path + approval resume + replay
│
├── deploy/                            # Cloud Run, Pub/Sub, IAM (minimal)
│
├── docs/
│   ├── PROTOCOL_215_INPUT.md          # Product source input
│   └── PROTOCOL_215_PLAN.md           # This plan
│
└── _bmad-output/specs/spec-protocol-215/   # BMAD SPEC + companions + stories
```

---

## 2. Component architecture diagram

```text
┌────────────────────────────┐
│  Web UI (Cloud Run)        │  7 screens · single-page approval
│  Amendment Launch → … →    │
│  Manifest                  │
└──────────────┬─────────────┘
               │ HTTPS
               ▼
┌────────────────────────────┐     put PDFs      ┌─────────────────┐
│  API (Cloud Run)           │──────────────────►│ Cloud Storage   │
│  upload · runs · approve   │                   │ protocols/      │
│  artifacts · manifest      │                   │ artifacts/      │
└──────────────┬─────────────┘                   └─────────────────┘
               │ write run
               ▼
        ┌────────────┐   publish amendment.received   ┌──────────┐
        │ Firestore  │◄───────────────────────────────│ Pub/Sub  │
        └─────▲──────┘                                └────┬─────┘
              │                                            │ push/pull
              │ read/write state · audit · twin            ▼
              │                               ┌────────────────────────┐
              │                               │ Worker (Cloud Run)     │
              └───────────────────────────────│ Google ADK workflow    │
                                              │  ├─ deterministic nodes│
                                              │  ├─ Gemini 3.5+ nodes  │
                                              │  └─ allowlisted tools  │
                                              └───────────┬────────────┘
                                                          │
                                              ┌───────────▼────────────┐
                                              │ Vertex AI / Gemini     │
                                              │ GEMINI_MODEL env       │
                                              └────────────────────────┘
                                              ┌────────────────────────┐
                                              │ Cloud Logging          │
                                              └────────────────────────┘
```

**LLM vs deterministic**

| Concern | Owner |
| --- | --- |
| Upload validation, hash, GCS, run create, Pub/Sub | Deterministic |
| Protocol IR extraction, semantic diff narrative, action proposals, conflict copy | Gemini (schema-validated) |
| Impact graph edges, twin rehearsal math, policy classification, tool execution, invariants, manifest assembly, idempotency | Deterministic |

---

## 3. End-to-end data flow

1. Operator uploads synthetic old + amended PDFs; selects AURORA-101 scenario → **Amendment Launch**.
2. API validates type/size/pages → SHA-256 → GCS → Firestore `runs/{run_id}` → publish `amendment.received`.
3. Worker consumes event (idempotent on `run_id` + delivery key).
4. Gemini compiles each PDF → **Protocol IR** (Pydantic); reject/retry on schema failure.
5. Gemini (+ normalize) → **semantic amendment diff** with evidence; assert five gold changes in demo fixture.
6. Deterministic **impact graph** maps each change → training, EDC, lab manual, kits, consent review, activation, courier, storage, schedules, etc.
7. Load **Trial Twin** (3 sites, 5 participants, approvals, training, versions, visits, inventory, courier, storage).
8. Rehearse Change × Site × Participant × Visit × Effective date → **findings** (primary: Phoenix P002 18:00 PK vs 17:30 courier / no overnight storage).
9. Gemini proposes tools from **allowlist only**.
10. **Policy engine** classifies GREEN / AMBER / RED (code is authoritative).
11. Execute GREEN → synthetic Firestore systems + append-only **audit**.
12. Pause on Phoenix PK conflict → **Action Ledger + Approval** UI (same ADK `invocation_id`).
13. On approve: resume; do not replay completed GREEN; re-run policy before any gated mutation.
14. Run **invariants**; on success build **Amendment Release Manifest** (JSON + HTML to GCS/Firestore).
15. UI surfaces Screens 2–7 from live run state; Cloud Logging shows Pub/Sub → worker → tools.

---

## 4. Domain models (Pydantic)

Core types (illustrative names; exact fields in `packages/models`):

- `ProtocolDocument` — `gcs_uri`, `sha256`, `version`, `page_count`
- `Run` — `run_id`, `status`, `scenario_id`, `invocation_id`, `created_at`, `protocol_v1`, `protocol_v2`
- `EvidenceRef` — `protocol_version`, `page`, `section`, `quote_span?`
- `IRFact` — typed fact + `evidence: list[EvidenceRef]` + `confidence` + `extraction_status`
- `ProtocolIR` — study metadata, visits, procedures, PK samples, labs, ECG, eligibility, restrictions, …
- `SemanticChange` — `change_id`, `concept_type`, `operation`, before/after, `risk_candidate`, `evidence`, `confidence`
- `ImpactEdge` — `change_id` → `artifact_type` / `artifact_id`
- `Site`, `Participant`, `Visit`, `InventoryItem`, `CourierWindow`, `StorageCapability`
- `Finding` — severity, site, participant, visit, conflict, protocol_evidence, operational_evidence, recommendation
- `ProposedAction` — `action_id`, `tool_name`, `args`, `change_ids`, `evidence`
- `PolicyDecision` — `tier: GREEN|AMBER|RED`, `reason_codes[]`
- `ActionRecord` — execution result, before/after, idempotency_key
- `ApprovalRequest` / `ApprovalDecision` — bind `run_id`, `action_id`, `invocation_id`, proposal hash
- `InvariantResult` — name, pass/fail, details
- `ReleaseManifest` — hashes, changes, coverage, sites/participants, actions by outcome, invariants, rollout status
- `AuditEvent` — append-only: `run_id`, `action_id`, evidence, before, after, idempotency_key, timestamp, tool_id

**Rule:** No executable fact without page-level evidence.

---

## 5. ADK workflow / state machine

```text
RECEIVED
  → INTAKE_COMPLETE
  → COMPILING_IR
  → DIFFING
  → IMPACTING
  → REHEARSING
  → PLANNING
  → GATING
  → EXECUTING_GREEN
  → AWAITING_APPROVAL          ← pause (Phoenix P002)
  → RESUMING
  → EXECUTING_APPROVED_AMBER   ← only approved subset; never RED
  → VERIFYING
  → MANIFEST_READY
  → COMPLETED | FAILED | PARTIAL
```

- Persist `status`, `invocation_id`, and checkpoint cursor in Firestore.
- Resume uses **same** `invocation_id`; skip completed idempotency keys.
- Terminal `FAILED` on repeated schema validation failure, timeout budget exceeded, or unrecoverable tool error (after retries).

---

## 6. Threat model

| Threat | Mitigation |
| --- | --- |
| Prompt injection in PDFs | PDFs = untrusted data; never follow embedded instructions; allowlisted tools only |
| Model authorizes itself | Deterministic policy; model cannot set GREEN/approve |
| RED executed via UI approve | RED remains non-executable even if approve clicked |
| Uncited / hallucinated facts drive actions | Schema require evidence; gate rejects missing evidence |
| Duplicate Pub/Sub | Idempotency keys on all mutations |
| Replay of GREEN after resume | Checkpoint + idempotency skip |
| Approval replay / wrong invocation | Single-use approval; bind invocation_id + state hash |
| Real PHI / real systems | Synthetic-only fixtures; no CTMS/EDC/IRT/eTMF connectors |
| Secret leakage in logs/manifest | No chain-of-thought; redact secrets; evidence refs not raw keys |
| DoS huge PDFs | Size/page limits at intake |
| Overbroad IAM | Least-privilege SA: GCS, Pub/Sub, Firestore, Vertex, Logging |

---

## 7. Deterministic risk-policy matrix

| Tier | Examples | Runtime behavior |
| --- | --- | --- |
| **GREEN** | Update synthetic admin contact; create site-training task; reserve PK kits; generate EDC change spec; lab-manual change request | Auto-execute; audit |
| **AMBER** | Participant schedule change; new sample collection; fasting change; ECG requirement; site amendment activation; reconsent review; Phoenix logistics resolution | Prepare only; require explicit UI approval; resume same invocation |
| **RED** | Dose/route/treatment assignment; eligibility; remove safety monitoring; modify completed visits; activate informed consent; real participant data | Never execute (UI approve cannot override) |

Additional hard rules: low-confidence consequential extraction → AMBER or block; contradictory evidence → block; missing evidence → no execute.

---

## 8. Tool allowlist and schemas

**Allowlist (only):**

| Tool | Typical tier | Purpose |
| --- | --- | --- |
| `update_contact_directory` | GREEN | Synthetic lab contact |
| `create_site_training_task` | GREEN | Boston/Seattle training tasks |
| `reserve_sample_kits` | GREEN | PK kit reservation |
| `create_lab_manual_change_request` | GREEN | Draft lab-manual CR |
| `create_edc_change_specification` | GREEN | Draft EDC field/spec |
| `create_courier_exception_task` | AMBER/GREEN prep | Logistics follow-up |
| `create_reconsent_review` | AMBER | Reconsent review packet |
| `draft_participant_transition_plan` | AMBER | Per-participant plan |
| `request_human_approval` | — | Create approval object / pause |
| `generate_release_manifest` | GREEN | Final manifest |

Each tool: Pydantic `Args` + `Result`; executor writes Firestore + `AuditEvent` with before/after + idempotency key. Unknown tool name → reject.

---

## 9. Firestore collection design

| Collection | Key docs / fields |
| --- | --- |
| `runs` | `run_id`, status, scenario, hashes, gcs uris, invocation_id, timestamps |
| `protocol_irs` | `run_id` + version → IR blob/refs |
| `changes` | semantic changes per run |
| `impact_edges` | change → artifacts |
| `sites` | twin site state (or `twins/{scenario}/sites`) |
| `participants` | twin participant + visits/consent |
| `findings` | rehearsal findings |
| `proposed_actions` | tool proposals + policy tier |
| `actions` | executed action records |
| `approvals` | approval requests/decisions |
| `audit_events` | append-only audit (no updates/deletes in app logic) |
| `invariants` | verification results |
| `manifests` | release manifest docs + gcs links |

Synthetic “systems” (training, EDC change control, lab ops, supplies) may be subcollections under `runs/{id}/systems/...` or top-level `synthetic_*` keyed by `run_id`.

---

## 10. Implementation sequence (vertical stories)

Aligned with `_bmad-output/specs/spec-protocol-215/stories.yaml` (CAP mapping):

| Story | Vertical slice |
| --- | --- |
| 1 | Monorepo scaffold, AURORA twin fixtures, Cloud Run health stub |
| 2 | Intake: upload → hash → GCS → Firestore run → Pub/Sub |
| 3 | Protocol IR compilation (schema + evidence) |
| 4 | Semantic five-change gold diff |
| 5 | Deterministic impact graph |
| 6 | Trial Twin rehearsal + P002/Phoenix finding |
| 7 | Allowlisted planner + policy gate |
| 8 | GREEN tool execution + audit |
| 9 | AMBER approval UI + same-invocation resume |
| 10 | Invariants + Release Manifest |
| 11 | UI: Launch, Semantic Redline, Impact Graph |
| 12 | UI: Timeline, Findings, Ledger + Approval |
| 13 | UI: Manifest + downloads |
| 14 | Resilience/safety tests (replay, injection, RED, crashes) |
| 15 | GCP deploy evidence + 4-minute demo dry-run |

---

## 11. Acceptance criteria (every story)

**1 — Scaffold**  
- Repo builds; fixtures load 3 sites / 5 participants; health endpoint returns 200; README local stub documented.

**2 — Intake**  
- Both PDFs in GCS; SHA-256 stored; `runs` doc created; `amendment.received` published; duplicate identical pair detected; no Gemini.

**3 — IR**  
- v1 and v2 IR pass Pydantic; every fact has page+section+confidence; malformed Gemini output fails closed after retries.

**4 — Diff**  
- Exactly five gold AURORA changes recalled at 100% on primary fixture; each has evidence; not word-only redline.

**5 — Impact**  
- Added 6h PK expands to required artifact fan-out (training, EDC, lab, kits, consent, courier, storage, schedules, etc.).

**6 — Twin**  
- Emits P002 Phoenix courier/storage block; Boston blocked on training; Seattle blocked on approval; P001 completed Day 1 never altered.

**7 — Policy**  
- Unknown tools rejected; GREEN/AMBER/RED from code; model suggestion cannot override; RED non-executable.

**8 — GREEN exec**  
- Contact update, training tasks, kit reserve, EDC/lab specs written; audit has before/after + idempotency; Pub/Sub replay does not duplicate.

**9 — Approval**  
- UI shows conflict, protocol+ops evidence, site, participant, resolution, completed vs blocked; approve resumes same `invocation_id`; reject leaves sensitive mutation undone.

**10 — Verify + manifest**  
- All listed invariants pass on happy path; manifest JSON+HTML include hashes, changes, coverage, actions by outcome, invariants, rollout status.

**11–13 — UI**  
- Seven screens wired to live run; Launch CTA starts preflight; redline jumps to evidence; timeline shows 215-style fragmentation; ledger hosts approval; manifest downloadable.

**14 — Tests**  
- Suite covers duplicate delivery, crash after tool, crash before ack, bad Gemini JSON, missing evidence, contradictory passages, PDF injection, timeout, approval misuse, RED proposal, completed visit, double submit.

**15 — Deploy/demo**  
- `.run` URL, Pub/Sub, worker logs, Firestore mutations, approval resume, invariants, manifest visible in ≤4 minutes; min instances 0.

---

## 12. Explicit MVP exclusions

- Schema-change / data-pipeline first-responder product (cancelled)
- Real CTMS, EDC, IRT, eTMF, ethics/regulatory systems
- Real protocols, PHI, patients, employer data
- Medical advice, dosing, eligibility, treatment assignment
- Auth, billing, multi-tenancy, SaaS packaging
- Generic chatbot as primary UX
- CLI as primary approval path
- Multiple polished amendment scenarios
- Full CDISC USDM / GxP qualification
- Claims of clinical production readiness

---

## 13. Four-minute demo → backend evidence map

| Time | On screen | Backend evidence to show |
| --- | --- | --- |
| 0:00–0:20 | 215-day problem → Protocol 215 | — |
| 0:20–0:38 | Compile→Trace→Rehearse→Act→Approve→Verify | Architecture diagram |
| 0:38–1:00 | Upload + Start Preflight | Cloud Run `.run` URL; GCS objects; Firestore `runs`; Pub/Sub message |
| 1:00–1:35 | Five semantic change cards + PK evidence pages | Firestore `changes`; Vertex/Gemini logs; IR docs |
| 1:35–2:10 | 215-day timeline (PHX/BOS/SEA) | Twin `sites`/`participants`; findings |
| 2:10–2:40 | Ledger GREEN actions completing | Firestore `actions` + `audit_events`; Logging tool lines |
| 2:40–3:10 | P002 18:00 vs courier 17:30 / no storage | Finding doc with protocol + operational evidence |
| 3:10–3:30 | Approval UI → resume | `approvals` decision; same `invocation_id`; no duplicate GREEN audits |
| 3:30–3:48 | Invariants green | `invariants` results |
| 3:48–4:00 | Amendment Release Manifest | `manifests` + GCS HTML/JSON |

---

## Next step

When you accept this plan, implementation starts at **Story 1** inside `protocol-215/` only — still no schema-change work.
