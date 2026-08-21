# DEVPOST_SUBMISSION — Protocol 215

Copy fields into Devpost. Replace placeholders before publish. Do not paste secrets or billing IDs.

## Project title

**Protocol 215: Clinical Amendment Preflight**

## Selected category

**The Taskmaster**

## One-sentence hook

Protocol 215 rehearses a clinical-trial protocol amendment against a synthetic Trial Twin—detecting operational conflicts, executing only safe actions, and gating the rest—before anything reaches a patient.

## Problem

Protocol amendments cascade across schedules, labs, EDC, training, kits, and logistics. Sites activate at different times; participants sit on different versions. Fragmented rollouts can last on the order of **215 days**, and contradictions often surface too late.

## Solution

An event-driven agentic preflight: upload synthetic old/new PDFs → store → `amendment.received` → compile Protocol IR → semantic diff → impact + Trial Twin rehearsal → allowlisted plan → GREEN/AMBER/RED policy gate → human approval → `amendment.resume` → invariants → Amendment Release Manifest.

## Key features

- Evidence-linked semantic changes (not word-only redline)
- Synthetic Trial Twin (3 sites, 5 participants) with Phoenix P002 courier/storage conflict
- Deterministic GREEN/AMBER/RED authorization in code
- Idempotent tools + hash-chained audit
- Single-use web approval without holding HTTP open
- Judge UI: seven screens + Mode bar (Synthetic / Local|Cloud / Fake|Live Gemini)
- Terraform + deploy scripts for Google Cloud demo (optional apply)

## How it works

1. Operator uploads AURORA-101 v1.0 and v2.0 PDFs in the web UI  
2. API validates PDFs, stores objects, creates run, publishes start event  
3. Worker (ADK graph) compiles IR, diffs, rehearses twin, executes GREEN, pauses on AMBER  
4. Operator approves on Action Ledger → resume event → worker continues  
5. Invariants + downloadable Release Manifest  

Architecture image: `docs/architecture.png`.

## Technologies used

Python 3.12, FastAPI, Pydantic 2, Google ADK 2.x, Google Gen AI / Vertex Gemini, Cloud Run, GCS, Pub/Sub, Firestore, Cloud Logging, React, TypeScript, Vite, Terraform, pytest, Vitest.

## Synthetic data sources

Hand-authored synthetic **AURORA-101** protocol PDFs and twin JSON under `fixtures/` (sites Phoenix/Boston/Seattle; participants P001–P005). No real PHI or employer protocols.

## Findings and learnings

- Separating model extraction from deterministic policy/tools made safety tests enforceable  
- Async resume (`amendment.resume`) is essential so approvals never block Cloud Run requests  
- Mode labeling (Fake vs Live) prevents overselling demo accuracy  
- Measured local rehearsal (`demo/rehearsal_results.json`) hit the demo path in ≪4 minutes of API wall time; narration still needs the full judge script  

## Challenges encountered

- Keeping ADK resume/idempotency correct under duplicate Pub/Sub deliveries  
- Preventing prompt-injection text in PDFs from becoming tools or policy bypasses  
- Shipping Terraform without applying billable resources until confirmed  
- Avoiding “perfect extraction” claims when evaluation used Fake Compiler / deterministic IR  

## Accomplishments

- End-to-end local fake-mode demo with required AURORA findings and approval path  
- 25 failure/hardening scenarios + evaluation harness with labeled evidence classes  
- Cloud adapters + Terraform/deploy automation ready for optional apply  
- Honest evaluation + security documentation  

## Future work

- Live Vertex measurement against gold fixtures  
- Applied GCP demo with recorded Cloud proof  
- Stronger planner grounding metrics  
- Broader synthetic scenarios (still synthetic-only)  

## Safety limitations

Not a validated clinical system; not production-ready for real trials; does not eliminate amendments; does not guarantee patient safety; extraction is not claimed perfect. Synthetic data only.

## Repository URL

`[REPOSITORY_URL]` — publish this repo and paste the public HTTPS URL.

## Hosted URL placeholder

`[HOSTED_URL]` — e.g. `https://protocol-215-web-….run.app` after `scripts/deploy.sh`.

## Video URL placeholder

`[VIDEO_URL]` — public YouTube or Vimeo, English audio or subtitles, **under 4 minutes**. Follow `demo/DEMO_SCRIPT.md` and `demo/RECORDING_CHECKLIST.md`.

## Built with (disclosure)

Newly created during the hackathon with **Cursor**, **Claude Code**, **BMAD Method** planning assets, and standard open-source libraries (see README §24).
