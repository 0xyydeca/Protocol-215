# PRODUCT.md — Protocol 215: Clinical Amendment Preflight

**Tagline:** Rehearse every protocol amendment before it reaches a patient.  
**Category:** The Taskmaster (Google All Things Agentic Hackathon)  
**Status:** Product contract (Prompt 0). Synthetic proof of concept — not validated for real clinical use.

## Problem

Clinical-trial protocol amendments rarely affect only one document. A single added procedure can change consent requirements, visit schedules, laboratory instructions, EDC forms, site training, specimen kits, storage, courier logistics, and participant-specific instructions.

Sites do not activate amendments everywhere at once. They wait on ethics approval, training, supplies, EDC configuration, and logistics. Participants sit at different visit and consent versions. Teams often discover contradictions only after rollout has begun.

A 2024 study reported investigative sites operated under different versions of the same protocol for an average of **215 days**.

## Product

**Protocol 215** is an autonomous clinical-trial amendment rehearsal agent. It treats an amendment like a software release:

1. Register and store old and amended synthetic protocol PDFs.
2. Publish `amendment.received`.
3. Compile each protocol into a schema-validated, evidence-linked **Protocol IR** (Gemini 3.5 Flash; no tools).
4. Generate a **semantic** amendment diff (not a word-only redline).
5. Map each change to affected trial artifacts.
6. Load a synthetic **Trial Twin** (sites, participants, approvals, training, visits, inventory, courier, storage).
7. Rehearse the amendment across the twin.
8. Identify operational conflicts.
9. Propose actions from a **strict allowlist** (planner never sees raw PDF bytes).
10. Classify actions **GREEN / AMBER / RED** with deterministic code.
11. Execute GREEN in synthetic Firestore-backed systems.
12. Pause AMBER for human approval in a single-page web UI.
13. Never execute RED.
14. On approval, publish `amendment.resume` and continue without repeating completed work.
15. Run deterministic invariants.
16. Produce an evidence-linked **Amendment Release Manifest**.

## User

Primary demo user: clinical-operations / amendment lead (hackathon judge operating the web UI).

## Elevator pitch

Most tools tell you what changed. Protocol 215 shows what will break—and completes safe operational work, gates sensitive actions, and verifies the synthetic rollout before the amendment reaches a patient.

## Meaning of 215

**215** refers to the average days investigative sites spent under fragmented protocol versions. Protocol 215 models that fragmented transition explicitly (signature visual: 215-day rollout timeline).

## Primary scenario (AURORA-101)

Synthetic study only. Protocol v2.0 introduces five controlled changes. The primary demo conflict:

- A **6-hour PK sample** is added.
- Phoenix participant **P002** doses at **12:00** → sample at **18:00**.
- Courier departs **17:30**.
- Site lacks validated overnight sample storage.

Protocol 215 must detect that v2 cannot safely activate for this participant under current operational state.

Sites: Phoenix (approved + trained), Boston (approved, training incomplete), Seattle (approval pending). Five synthetic participants including P001 (completed Day 1 — immutable).

## Core workflow (summary)

Upload → GCS + run record → `amendment.received` → ADK worker → IR → semantic diff → impact graph → Trial Twin rehearsal → allowlisted plan → policy gate → GREEN exec + audit → AMBER pause (UI) → `amendment.resume` → invariants → Manifest.

Seven UI screens: Amendment Launch; Semantic Redline; Impact Graph; 215-Day Rollout Timeline; Rehearsal Findings; Action Ledger + Human Approval; Amendment Release Manifest.

## Success criteria

One operator uploads AURORA v1 and v2 PDFs and observes an autonomous Google Cloud workflow that extracts the five evidence-linked changes, traces impact, rehearses sites/participants, detects the Phoenix P002 conflict, completes GREEN actions, blocks AMBER/RED appropriately, resumes via `amendment.resume` after web approval, verifies invariants, and produces a downloadable Amendment Release Manifest — demonstrable in ≤4 minutes with visible Cloud proof.

## Non-goals

- Schema-change / data-pipeline first-responder product (abandoned; not this submission).
- Real PHI, patients, employer protocols, or real EDC/CTMS/IRT/eTMF/regulatory systems.
- Medical advice, dosing, eligibility, treatment assignment, consent activation.
- Auth, billing, multi-tenancy, SaaS packaging, generic chatbot.
- CLI as primary approval path.
- Multiple polished amendment scenarios.
- Claims of GxP qualification or real clinical safety.
