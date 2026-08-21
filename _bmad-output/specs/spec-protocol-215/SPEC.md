---
id: SPEC-protocol-215
companions:
  - stack.md
  - risk-policy.md
  - workflow-stages.md
  - aurora-101-scenario.md
  - ui-screens.md
  - architecture-diagrams.md
  - evaluation-and-tests.md
  - demo-script.md
sources:
  - ../../docs/PROTOCOL_215_INPUT.md
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# Protocol 215: Clinical Amendment Preflight

## Why

**Mandate + pain.** Deliver an August 31 **All Things Agentic Hackathon** submission in **The Taskmaster** category: a complete autonomous workflow, not a chatbot. Clinical-trial amendments fragment across sites for an average of **215 days**, cascading into consent, visits, labs, EDC, training, kits, and logistics—where contradictions surface too late. Protocol 215 is a production-minded **synthetic** proof of concept that rehearses amendment rollout before it reaches a patient, prioritizing one polished end-to-end vertical slice over breadth.

## Capabilities

- **CAP-1**
  - **intent:** Operator can upload prior and amended protocol PDFs plus the AURORA-101 scenario to create a registered amendment run.
  - **success:** Run has unique `run_id`, SHA-256 hashes for both files, objects in Cloud Storage, Firestore run record, and an `amendment.received` Pub/Sub publish; duplicate identical document pairs are detected.
- **CAP-2**
  - **intent:** System can compile each protocol into a schema-validated Protocol Intermediate Representation (Protocol IR).
  - **success:** Every IR fact includes protocol version, page, section, confidence, and extraction status; schema validation fails closed on malformed model output.
- **CAP-3**
  - **intent:** System can produce concept-level semantic amendment changes with evidence links (not word-level redline).
  - **success:** Primary AURORA fixture yields the five gold-standard changes with ≥0.95 confidence where INPUT specifies; each change cites source pages/sections.
- **CAP-4**
  - **intent:** System can trace each semantic change through the downstream study-artifact impact graph.
  - **success:** Added six-hour PK sample expands to the documented artifact fan-out (SoA, consent review, training, kits/labels, lab manual, processing/storage, courier, EDC/edit checks, bioanalytical transfer).
- **CAP-5**
  - **intent:** System can rehearse each applicable Change × Site × Participant × Visit × Effective date in the Synthetic Trial Twin.
  - **success:** Emits concrete findings including the Phoenix P002 courier/storage block and site activation blocks for Boston (training) and Seattle (approval).
- **CAP-6**
  - **intent:** System can propose operational actions only from the restricted tool allowlist.
  - **success:** Any model-proposed non-allowlisted tool is rejected before execution; allowlist matches `risk-policy.md`.
- **CAP-7**
  - **intent:** System can apply a deterministic Green/Amber/Red policy gate to every proposed action.
  - **success:** Final authorization decision is code-enforced; model suggestions never override the gate; Red actions never execute even if UI approve is clicked.
- **CAP-8**
  - **intent:** System can execute Green actions against synthetic trial-system collections with full audit metadata.
  - **success:** Demo path auto-completes lab contact update, training tasks, kit reservation, and draft EDC/lab-manual change specs; each write has run/action IDs, evidence ref, idempotency key, tool identity, timestamp, before/after state.
- **CAP-9**
  - **intent:** Operator can authorize or reject an Amber action and the workflow resumes the same ADK invocation.
  - **success:** Pause shows required approval fields; confirmation uses same `invocation_id`; completed Green actions are not replayed; rejection leaves sensitive mutation unexecuted and recorded on the manifest.
- **CAP-10**
  - **intent:** System can verify post-execution operational invariants before declaring success.
  - **success:** Invariants assert zero unauthorized high-risk actions, zero Red executions, zero duplicate mutations on replay, zero retroactive completed-visit changes, zero site-version conflicts, and 100% evidence linkage for executable actions.
- **CAP-11**
  - **intent:** Operator can obtain an Amendment Release Manifest summarizing the run.
  - **success:** Manifest includes versions/hashes, changes, evidence coverage, sites/participants, actions by outcome, invariant results, audit refs; downloadable as JSON and print-ready HTML.
- **CAP-12**
  - **intent:** Operator can drive the AURORA demo through the seven required non-chatbot UI screens.
  - **success:** Screens in `ui-screens.md` are present and wired to live run state for Launch → Redline → Impact → Timeline → Findings → Ledger/Approval → Manifest.
- **CAP-13**
  - **intent:** Team can demonstrate the vertical slice running on Google Cloud within a four-minute video.
  - **success:** Demo shows Cloud Run URL, Pub/Sub trigger, ADK/Gemini activity, Firestore mutations, approval resume, invariants, and manifest per `demo-script.md`.

## Constraints

- Synthetic-only data and systems; never real PHI, patients, employer protocols, or real clinical systems (EDC/CTMS/IRT/eTMF).
- Runtime stack mandatory: Gemini 3.5+ via Vertex (`GEMINI_MODEL` env, never hard-coded unverified ID), Google ADK orchestration, Cloud Run, Pub/Sub, Firestore, Cloud Storage, Cloud Logging — details in `stack.md`.
- No uncited Protocol IR fact may trigger an action.
- Action proposals limited to the allowlist in `risk-policy.md`; model cannot invent tools.
- Green/Amber/Red authorization is deterministic code; model cannot authorize or impersonate approver.
- Red actions remain prohibited even after UI approval.
- Amber resume must use the same ADK `invocation_id`; no new workflow that repeats completed work.
- All mutations idempotent; duplicate Pub/Sub delivery must not duplicate actions.
- Approvals single-use; reject if underlying state changed after request creation; re-run policy gate immediately before execution.
- Cloud Run min instances = 0; max instances capped; budget/cost controls required.
- One controlled synthetic scenario (AURORA-101) until the vertical slice works; no speculative feature expansion.
- Prompt-injection instructions embedded in uploaded PDFs must never be followed.
- Record evidence and outcomes, not hidden chain-of-thought, in the application audit trail.

## Non-goals

- Real clinical-trial data, PHI, medical recommendations, eligibility, dosing, treatment assignment, or consent activation.
- Real CTMS/EDC/IRT/eTMF/ethics/regulatory integrations or GxP qualification.
- Full CDISC USDM, multi-tenant SaaS, billing, enterprise auth, long-term cross-study memory.
- General-purpose clinical chatbot or multiple polished amendment scenarios.
- Claims that the prototype is safe for real clinical use.
- Product rediscovery or features not required by the AURORA vertical slice / INPUT exclusions (`PROTOCOL_215_INPUT.md` §12).

## Success signal

One operator uploads AURORA v1 and v2 synthetic protocols and observes an autonomous GCP workflow that extracts the five evidence-linked changes, traces impact, rehearses sites/participants, detects the Phoenix P002 courier/storage contradiction, completes Green admin actions, blocks Amber/Red appropriately, pauses for one meaningful approval, resumes the same invocation without duplicates, verifies invariants, and produces an auditable Amendment Release Manifest—demonstrable in ≤4 minutes on Google Cloud.

## Assumptions

- Vertex AI project, billing, and a qualifying Gemini 3.5+ model will be available before CAP-13.
- Synthetic protocol PDFs will be authored so gold-standard changes and cited pages match `aurora-101-scenario.md`.
- Cursor/BMAD are development aids only; they are not the submitted runtime architecture.

## Open Questions

- Which exact Gemini 3.5-or-newer model identifier should `GEMINI_MODEL` use at submission time?
- Which ADK language runtime (e.g. Python ADK) is the team standard for the worker?
