# DEVPOST_SUBMISSION — Protocol 215

Copy fields into Devpost. Do not paste secrets or billing IDs.

## Project title

**Protocol 215: Clinical Amendment Preflight**

## Selected category

**The Taskmaster**

## One-sentence hook

Protocol 215 rehearses a clinical-trial protocol amendment against a synthetic Trial Twin—detecting operational conflicts, executing only safe actions, and gating the rest—before anything reaches a patient.

## Problem

Protocol amendments cascade across schedules, labs, EDC, training, kits, and logistics. Sites activate at different times; participants sit on different versions. Getz et al. (2024; PMID 38438658) reported fragmented rollouts on the order of **215 days**, and contradictions often surface too late.

## Solution

An event-driven agentic preflight on Google Cloud: upload synthetic old/new PDFs → GCS + Firestore → Pub/Sub `amendment.received` → ADK worker → Vertex Gemini Protocol IR → **deterministic** semantic diff → impact + Trial Twin → allowlisted plan → GREEN/AMBER/RED policy gate → human approval → `amendment.resume` → invariants → Amendment Release Manifest.

## Key features

- Evidence-linked semantic changes (not word-only redline)
- Synthetic Trial Twin (3 sites, 5 participants) with Phoenix P002 courier/storage conflict
- Deterministic GREEN/AMBER/RED authorization in code
- Idempotent tools + hash-chained audit
- Single-use web approval without holding HTTP open
- Judge UI: seven screens + Mode bar (Synthetic / Google Cloud / Live Gemini)
- **Deployed** Cloud Run demo with measured E2E pass

## How it works

1. Operator uploads AURORA-101 v1.0 and v2.0 PDFs at the hosted URL  
2. Web validates PDFs, stores objects in GCS, creates Firestore run, publishes start event  
3. Private worker (ADK graph) compiles IR via Vertex Gemini, diffs/rehearses in Python, executes GREEN, pauses on AMBER  
4. Operator approves on Action Ledger → resume event → worker continues with same session  
5. Invariants + downloadable Release Manifest  

Architecture: [`docs/architecture.png`](architecture.png).

## Technologies used

Python 3.12, FastAPI, Pydantic 2, Google ADK 2.x, Vertex Gemini 3.5 Flash, Cloud Run, GCS, Pub/Sub, Firestore, Cloud Logging, React, TypeScript, Vite, Terraform, pytest, Vitest.

## Synthetic data sources

Hand-authored synthetic **AURORA-101** protocol PDFs and twin JSON under `fixtures/` (sites Phoenix/Boston/Seattle; participants P001–P005). No real PHI or employer protocols.

## Findings and learnings

- Separating Gemini IR extraction from deterministic policy/tools made safety tests enforceable  
- Async resume (`amendment.resume`) is essential so approvals never block Cloud Run requests  
- Mode labeling (Fake vs Live) prevents overselling demo accuracy  
- Measured cloud E2E (`docs/CLOUD_E2E_RESULTS.md`) completed in ~97s wall time with live Vertex on five evidence-linked changes  

## Challenges encountered

- Keeping ADK resume/idempotency correct under duplicate Pub/Sub deliveries  
- Running ADK under uvicorn without blocking the event loop (`workflow/cloud_driver.py`)  
- Preventing prompt-injection text in PDFs from becoming tools or policy bypasses  
- Honest adapter labeling so judges can verify GCS/Firestore/Pub/Sub/Gemini from `/readyz`  

## Accomplishments

- **Live hosted demo** on Cloud Run with Vertex Gemini 3.5 Flash  
- End-to-end cloud E2E with 40+ assertions (`docs/CLOUD_E2E_RESULTS.md`)  
- 25 failure/hardening scenarios + evaluation harness  
- Judge UI fixes: approval pause vs stall, resume proof IDs, Trial Twin roster counts  

## Future work

- Broader synthetic protocol scenarios  
- Additional site capability models  
- Formal evaluation on heterogeneous protocol formats  
- Production regulatory validation (**explicitly not part of this prototype**)  

## Safety limitations

Synthetic proof of concept only. Not GxP validated. No PHI. No real trial integrations. No autonomous medical decisions — code authorizes GREEN/AMBER/RED. Not production-ready for real trials.

## Repository URL

https://github.com/0xyydeca/Protocol-215

## Hosted URL

https://protocol-215-web-u6nfupvmhq-uc.a.run.app

Recording mode: `?demo=1`

## Video URL

**Pending Devpost paste** — upload a **public** (not unlisted) YouTube or Vimeo demo **under 4 minutes**, then paste the URL into Devpost (not required in git).

Follow `demo/DEMO_SCRIPT.md`, `docs/VIDEO_EVIDENCE.md`, and `docs/SUBMISSION_CHECKLIST.md`.

## Built with (disclosure)

Newly created during the hackathon with **Cursor**, **Claude Code**, **ChatGPT** (architecture review, audit, troubleshooting, video scripting), **BMAD Method** planning assets, and standard open-source libraries (see README §23).

## Evidence links (for judges)

| Claim | Where |
| --- | --- |
| Cloud E2E PASS | `docs/CLOUD_E2E_RESULTS.md` |
| Architecture | `docs/architecture.png`, `ARCHITECTURE.md` |
| Deployment | `docs/DEPLOYMENT.md` |
| Video timestamp map | `docs/VIDEO_EVIDENCE.md` |
