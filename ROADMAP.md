# ROADMAP.md — Vertical implementation stages

Implement in order. Each stage ends with the reusable quality gate (PASS required before next). No schema-change work.

## Stage 0 — Contract lock (this prompt)

**Done when:** Root contract docs exist (`PRODUCT`, `RULES`, `ARCHITECTURE`, `SECURITY`, `EVALUATION`, `AGENTS`, `DECISIONS`, `ROADMAP`) and schema-change is documented as abandoned.

## Stage 1 — Monorepo scaffold and AURORA fixtures

- Python 3.12 / uv workspace, FastAPI/Vite stubs, fixture twin (3 sites, 5 participants), gold-change JSON.
- **Acceptance:** Local health endpoints; fixtures load; no GCP required.

## Stage 2 — Amendment intake

- Upload PDFs → validate → SHA-256 → GCS (or local adapter) → Firestore run → publish `amendment.received`.
- **Acceptance:** Deterministic; duplicate pair detection; no Gemini.

## Stage 3 — Protocol IR compilation

- Tool-less Gemini → Pydantic IR with page/section/confidence; fail closed.
- **Acceptance:** v1 and v2 IR validate; uncited facts cannot be marked executable.

## Stage 4 — Semantic gold diff

- Five AURORA changes with evidence; not word-only redline.
- **Acceptance:** 100% gold recall on primary fixture.

## Stage 5 — Deterministic impact graph

- Fan-out including training, EDC, lab, kits, consent, activation, courier, storage, schedules.
- **Acceptance:** PK sample maps to required artifact set.

## Stage 6 — Trial Twin rehearsal

- Emit Phoenix P002 conflict; Boston/Seattle activation blocks; P001 Day 1 immutable.
- **Acceptance:** Findings match `EVALUATION.md` primary conflict.

## Stage 7 — Planner + policy gate

- Allowlisted proposals; GREEN/AMBER/RED in code; planner never sees PDF bytes.
- **Acceptance:** Unknown tools rejected; RED non-executable.

## Stage 8 — GREEN execution + hash-chained audit

- Contact, training tasks, kits, EDC/lab specs; idempotent mutations.
- **Acceptance:** Replay Pub/Sub does not duplicate; audit chain links.

## Stage 9 — Approval UI + `amendment.resume`

- Screen 6 fields; approve/reject; publish resume; worker continues without GREEN replay.
- **Acceptance:** No long-held HTTP; single-use approval; stale state rejected.

## Stage 10 — Invariants + Release Manifest

- All invariant checks; JSON + HTML manifest to GCS/Firestore.
- **Acceptance:** Happy path invariants pass; manifest fields complete.

## Stage 11 — UI Launch, Redline, Impact Graph

- Screens 1–3 wired to live run state + evidence navigation.
- **Acceptance:** Start Amendment Preflight works end-to-end into worker.

## Stage 12 — UI Timeline, Findings, Ledger

- Screens 4–6 (ledger hosts approval).
- **Acceptance:** Timeline shows PHX/BOS/SEA fragmentation; P002 finding visible.

## Stage 13 — UI Manifest

- Screen 7 + downloads.
- **Acceptance:** JSON/HTML download matches stored manifest.

## Stage 14 — Resilience and safety test suite

- Cover `EVALUATION.md` required tests (replay, injection, crashes, RED, reject).
- **Acceptance:** CI-local suite green for listed cases.

## Stage 15 — Deploy and four-minute demo dry-run

- Deploy `protocol-215-web` and `protocol-215-worker`; capture Cloud proof; rehearse demo script ≤4 min.
- **Acceptance:** Demo evidence map satisfied; min instances 0; README spin-up complete.

## Explicit MVP exclusions

See `PRODUCT.md` Non-goals. Additionally: no CLI primary approval; no multi-scenario polish; no real clinical connectors; no chatbot shell.

## Quality gate reminder

After every stage: stop features; audit against contract docs + stage acceptance; run applicable format/lint/type/test/build; PASS or FAIL with fixes only — never soft-pass skipped commands.
