# Workflow stages

## High-level flow

See `architecture-diagrams.md`.

## Stage 1 — Amendment intake (deterministic)

Accept prior protocol PDF, amended protocol PDF, synthetic scenario. Verify file type; enforce size/page limits; SHA-256 hash; create `run_id`; store in Cloud Storage; detect previously processed identical pair; publish `amendment.received`.

## Stage 2 — Protocol compilation

Gemini → schema-validated Protocol IR including: study id; protocol version/date; arms/cohorts; visits; procedures; timing windows; PK samples; lab tests; ECG/vitals; eligibility; treatment instructions; objectives/endpoints; participant restrictions; consent-relevant procedures; explicit operational requirements.

Every fact: source version, page, section, confidence, extraction status. No uncited fact may trigger an action.

## Stage 3 — Semantic amendment diff

Concept-level changes (ADD/MODIFY/REMOVE) with evidence array and confidence. Example shape:

```json
{
  "change_id": "CHG-002",
  "concept_type": "scheduled_activity",
  "operation": "ADD",
  "activity": "PK blood sample",
  "visit": "Day 1",
  "time_after_dose_hours": 6,
  "risk_candidate": "AMBER",
  "evidence": [{"protocol_version": "2.0", "page": 17, "section": "Schedule of Activities"}],
  "confidence": 0.98
}
```

## Stage 4 — Impact tracing (deterministic)

Dependency engine maps each change to downstream artifacts (SoA, consent review, training, kits/labels, lab manual, processing/storage, courier, EDC/edit checks, bioanalytical transfer, etc.).

## Stage 5 — Trial Twin rehearsal

Load synthetic sites, participants, approvals, training, active protocol/consent versions, visits, equipment, inventory, courier, lab capabilities. Evaluate Change × Site × Participant × Visit × Effective date.

## Stage 6 — Action planning

Gemini proposes only allowlisted tools (`risk-policy.md`).

## Stage 7 — Deterministic policy gate

Classify Green / Amber / Red in code.

## Stage 8 — Safe execution

Mutate synthetic Firestore collections with run/action IDs, evidence ref, idempotency key, timestamp, tool identity, before/after state.

## Stage 9 — Pause and resume

Create approval request; no restricted mutation; preserve invocation/state; return approve/reject to same invocation; resume from suspended stage.

## Stage 10 — Verification

Invariants: no activation before approval/training; no retroactive completed-visit alteration; no unauthorized participant-affecting action; feasible sample path for new samples; evidence-linked actions; no duplicate actions from duplicate events; no Red executed; no unresolved operational contradiction in successful final state.

## Stage 11 — Amendment Release Manifest

Versions/hashes; changes; evidence coverage; affected artifacts; sites/participants; actions completed/approved/blocked; unresolved items; verification results; audit-event refs.
