# AGENTS.md — Non-negotiables for coding agents

Read before any implementation change: `PRODUCT.md`, `RULES.md`, `ARCHITECTURE.md`, `SECURITY.md`, `EVALUATION.md`, `ROADMAP.md`.

## Product

- Active product is **Protocol 215: Clinical Amendment Preflight** only.
- Do **not** implement or revive the abandoned schema-change / data-pipeline project.
- Optimize for one synthetic AURORA-101 demo, not feature breadth.

## Architecture

- Services: `protocol-215-web` and `protocol-215-worker` only (plus managed GCP).
- Start event: `amendment.received`. Resume event: `amendment.resume`.
- **Never** block a long-running HTTP request waiting for human approval.
- Extraction Gemini: **no tools**. Planner: **never** receives raw PDF bytes.
- Deterministic Python for impact graph, twin rehearsal math, policy, tools, invariants, audit, manifest assembly.

## Safety

- Model output is untrusted — Pydantic / JSON Schema validate everything.
- No uncited fact may cause an action.
- Model proposes; **code** authorizes (GREEN/AMBER/RED).
- RED never executes, even if UI approve is clicked.
- Mutations are idempotent; duplicate Pub/Sub must not duplicate work.
- Audit is append-only and hash-chained.
- Historical visits / consent / protocol version assignments are immutable.
- Synthetic data only — no real clinical systems, PHI, or employer docs.
- No auth, billing, multi-tenancy, or chatbot UX in MVP.
- Do not store or display hidden chain-of-thought.

## Process

- Follow `ROADMAP.md` stages; do not skip quality gates.
- No secrets in git.
- Do not claim clinical production readiness.
- Prefer smallest change that meets stage acceptance criteria.
