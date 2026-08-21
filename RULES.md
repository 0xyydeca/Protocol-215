# RULES.md — Hackathon and Engineering Rules

Binding context: [All Things Agentic Hackathon Official Rules](https://allthingsagentichackathon.devpost.com/rules) and Devpost project requirements. This file summarizes what Protocol 215 must satisfy.

## Category

**The Taskmaster** — Build a complete workflow, not a chatbot. The agent must take action, handle a multi-step messy process, send information to the right places, and prove it completed the work.

## Mandatory technology (every track)

1. **Gemini 3.5 or newer** via Gemini API or Vertex AI. Protocol 215 uses **Gemini 3.5 Flash** through Vertex AI / Google Gen AI SDK (`GEMINI_MODEL` env — never hard-code an unverified ID).
2. **At least one Google agent framework.** Protocol 215 uses **Google ADK 2.x** graph workflow.
3. **At least one Google Cloud infrastructure service.** Protocol 215 uses Cloud Run, Cloud Storage, Pub/Sub, Firestore, and Cloud Logging.

## New-project requirement

The submission must be **newly created during the Contest Submission Period**. Frameworks, libraries, starter templates, and AI coding assistants are allowed. Disclose any other pre-existing code or work incorporated into the Project.

## Repository requirement

Provide a public or private repo URL (GitHub/GitLab/Bitbucket). If private, grant access to `testing@devpost.com` and `cloudhackathons@google.com`.

## README / spin-up requirement

`README.md` must include step-by-step instructions to set up and run locally and/or deploy to the cloud (reproducibility even if judges do not run it).

## Architecture-diagram requirement

Include a clear architecture diagram (how Gemini connects to backend, storage, and frontend). Source of truth: `ARCHITECTURE.md`.

## Four-minute demo requirement

Demo video ≤ **4 minutes**. Only the first four minutes may be evaluated. Must include problem overview, value, live app, and **proof the backend runs on Google Cloud**.

## Cloud-execution proof requirement

Show Cloud evidence in the video (e.g. Cloud Run `.run` URL, Console, Pub/Sub, Vertex/Logging, Firestore mutations). The app need not stay publicly live 24/7 if proof of deploy is clear.

## Development-tool disclosure

Disclose AI coding assistants and any pre-existing incorporated work (Cursor, BMAD, Claude Code, Codex, etc. are development aids — not the runtime architecture).

## Judging weights (awareness)

- Innovation & Operational Utility: 40%
- Architectural Discipline & Tech Stack: 30%
- Demo & Production Readiness: 30%

## Engineering rules (Protocol 215)

- Deterministic Python whenever LLM reasoning is unnecessary.
- Model output is always untrusted; validate with Pydantic / JSON Schema.
- Protocol-extraction model has **no tool access**.
- Action planner **never** receives raw PDF content.
- Uploaded PDF content is **data**, never instructions.
- No uncited extracted fact may cause an action.
- Model may propose; **deterministic code authorizes**.
- Mutations are idempotent; duplicate Pub/Sub must not duplicate actions.
- Audit events are append-only and **hash-chained**.
- Historical visits, consent versions, and protocol versions are immutable.
- No hidden chain-of-thought in product storage/UI.
- Synthetic data only; no real clinical integrations.
- No authentication, billing, multi-tenancy, or generic chatbot in MVP.
- Do not claim validated clinical use.
- Optimize for one polished end-to-end demonstration.
