# Protocol 215: Clinical Amendment Preflight

**Tagline:** Rehearse every protocol amendment before it reaches a patient.

**Hackathon category:** The Taskmaster — Google All Things Agentic Hackathon

**Status:** Synthetic proof of concept. Not validated for real clinical use.

---

## 1. Problem

Clinical-trial protocol amendments rarely affect only one document. A single added procedure can change consent, visit schedules, laboratory instructions, EDC forms, site training, kits, storage, courier logistics, and participant-specific instructions.

Sites do not activate amendments everywhere at once. They wait on ethics approval, training, supplies, EDC configuration, and logistics. Participants sit at different visit and consent versions. Teams often discover contradictions only after rollout has begun.

## 2. Why 215

A 2024 study reported investigative sites operated under different versions of the same protocol for an average of **215 days**. Protocol 215 names that fragmentation explicitly and models it in a synthetic Trial Twin (signature UI: 215-day rollout timeline). See `PRODUCT.md`.

## 3. Elevator pitch

Most tools tell you what changed. Protocol 215 shows what will break—and completes safe operational work, gates sensitive actions, and verifies the synthetic rollout before the amendment reaches a patient.

## 4. What the agent does

On synthetic **AURORA-101** protocol PDFs (v1.0 → v2.0):

1. Store uploads and create a run (`POST /api/runs` → `src/protocol215/api/routes.py`)
2. Publish `amendment.received` (local in-process bus or Pub/Sub)
3. Compile protocols into schema-validated, evidence-linked **Protocol IR** (Gemini tool-less path or Fake Compiler)
4. Deterministic **semantic diff** of five controlled changes (`application/semantic_diff.py`)
5. Build impact graph + Trial Twin rehearsal (`application/impact.py`, `simulator/twin.py`)
6. Propose allowlisted actions; authorize **GREEN / AMBER / RED** in code (`policy/matrix.py`)
7. Execute GREEN via idempotent tools; pause AMBER for web approval; never execute RED
8. On approve, publish `amendment.resume` and continue without replaying completed work
9. Run invariants and emit an **Amendment Release Manifest**

Seven UI views: Launch, Semantic Redline, Impact, 215-Day Timeline, Findings, Action Ledger + Approval, Manifest (`apps/web/src/`).

## 5. Why it is agentic rather than a chatbot

| Chatbot | Protocol 215 |
| --- | --- |
| Free-form Q&A | Event-driven workflow (`amendment.received` / `amendment.resume`) |
| Model decides authorization | Code decides GREEN/AMBER/RED |
| Tools often unrestricted | Strict allowlist (`tools/registry.py`) |
| Approval in chat | Single-use approval bound to state version (`policy/approval.py`) |
| Holds HTTP open | Web returns 202; worker resumes asynchronously |

Implementation: Google ADK graph (`workflow/`), FastAPI web + worker, Pub/Sub/in-process events.

## 6. Architecture diagram

![Protocol 215 architecture](docs/architecture.png)

Source: `docs/architecture.mmd`. Narrative topology: `ARCHITECTURE.md`.

Upload → Cloud Storage → Pub/Sub → Cloud Run ADK worker → Gemini → Trial Twin → policy gate → Firestore tools → human approval → resume → invariants → manifest.

## 7. Gemini role

- **Compiler:** tool-less PDF → Protocol IR with page-level evidence (`adapters/gemini/compiler.py`, `prompts.py`)
- **Not used for:** authorization, tool invention outside allowlist, or mutating twin state directly
- **Fake mode:** `GEMINI_BACKEND=fake` uses deterministic fixture IRs (`adapters/fakes.py`) — Mode bar must show **Fake Compiler**, never “live”

Configured model id: `GEMINI_MODEL` (default `gemini-3.5-flash`).

## 8. ADK role

Google ADK 2.x resumable graph runs intake → compile → analyze → rehearse → plan → GREEN exec → human approval interrupt → AMBER exec → verify → manifest (`workflow/graph.py`, `workflow/nodes.py`, `workflow/driver.py`). Checkpointed so restart/resume does not duplicate idempotent mutations.

## 9. Google Cloud services

| Service | Role in design | Local status |
| --- | --- | --- |
| Cloud Run (web + worker) | UI/API + ADK worker | Dockerfiles + Terraform present; **apply optional** |
| Cloud Storage | Protocol PDFs / artifacts | Local filesystem adapter or GCS |
| Pub/Sub | `amendment.received` / `amendment.resume` | In-process bus or Pub/Sub |
| Firestore | Run state, twin, audit, actions | Memory/SQLite or Firestore |
| Vertex AI / Gemini | IR compilation | Fake or Vertex |
| Cloud Logging | Demo evidence | Structured logs; live when deployed |

IaC: `infra/terraform/`. Deploy: `scripts/deploy.sh` (requires explicit `yes`). **Terraform has not been required to be applied for local demo readiness.**

## 10. Deterministic-versus-model responsibilities

| Deterministic (code) | Model-assisted |
| --- | --- |
| Semantic diff over Protocol IR | Protocol IR extraction (when live) |
| Impact graph, twin rehearsal | Constrained planner proposals (allowlisted) |
| GREEN/AMBER/RED authorization | — |
| Tool execution + idempotency | — |
| Approvals, invariants, audit hash chain | — |
| Manifest assembly | Optional concise explanations after graph exists |

## 11. Human-approval model

- AMBER actions require human approval in the Action Ledger UI
- Approval is single-use; stale state version / wrong invocation / already decided → rejected (`policy/approval.py`)
- RED remains non-executable even if UI approve is clicked
- Web handler stores decision + publishes resume; **does not** execute sensitive tools inline (`api/routes.py`)

## 12. Synthetic-data disclaimer

**Synthetic data only.** Fixtures under `fixtures/` (AURORA-101 PDFs, sites, participants). No PHI, real patients, employer protocols, or production EDC/CTMS/IRT/eTMF. Not a medical device; not GxP-qualified. Banner in UI: `apps/web/src/components/Chrome.tsx`.

## 13. Repository structure

```text
protocol-215/
  apps/web/           React + Vite judge UI
  apps/worker/        Worker entry (local/cloud)
  src/protocol215/    FastAPI, ADK workflow, tools, policy, cloud adapters
  fixtures/           Synthetic protocols + twin JSON
  evaluation/         Eval harness + datasets + results.json
  infra/terraform/    GCP demo IaC
  scripts/            bootstrap, local run, deploy, reset, rehearsal
  demo/               DEMO_SCRIPT, checklists, rehearsal_results.json
  docs/               Architecture, deployment, Devpost, security, eval
  tests/              Unit + integration
```

## 14. Prerequisites

- Python **3.12** (see `.python-version`, `pyproject.toml`)
- Node.js 20+ (for `apps/web`)
- `uv` (bundled bootstrap via `.tools/uv` or system)
- Optional: Docker, Terraform ≥ 1.5, `gcloud` (cloud deploy only)

## 15. Local setup

```bash
cd protocol-215
./scripts/bootstrap.sh          # or: make bootstrap
cp -n .env.example .env         # if bootstrap did not already
```

Default `.env`: `memory` / `local` / `inprocess` / `fake` — **no GCP credentials required**.

## 16. Local fake-mode run

```bash
# terminal 1
./scripts/run_local.sh          # or: make api   → http://127.0.0.1:8000

# terminal 2
cd apps/web && npm run dev      # or: make web   → http://127.0.0.1:5173
```

Confirm Mode bar: **Synthetic Study** · **Local** · **Fake Compiler** · model id.

Upload `fixtures/protocols/AURORA-101_Protocol_v1.0.pdf` and `…_v2.0.pdf`.

## 17. Live Gemini configuration

```bash
# .env
APP_ENV=local   # or cloud
GEMINI_BACKEND=vertex
GEMINI_MODEL=gemini-3.5-flash
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
```

Use Application Default Credentials / runtime SA — **never commit service-account JSON**. Mode bar must show **Live Gemini**. Optional: `RUN_LIVE_GEMINI_TESTS=1` for live tests (not CI default).

## 18. Google Cloud deployment

See **`docs/DEPLOYMENT.md`**. Summary:

```bash
PROJECT_ID=… BUCKET_SUFFIX=… ./scripts/deploy.sh   # types 'yes' to confirm
```

Destroy: `./scripts/destroy_demo_resources.sh` (type `destroy-protocol-215`).

## 19. Demo reset

```bash
./scripts/reset_demo.sh
# Cloud: CONFIRM_DEMO_RESET=yes ./scripts/reset_demo.sh --confirm
# or UI: Launch → Reset demo state → POST /api/demo/reset
```

Clears runs/actions/approvals/manifests; restores twin baseline from fixtures (3 sites, 5 participants); preserves `fixtures/` and infra. Implementation: `application/demo_reset.py`, `api/container.py`.

## 20. Testing

```bash
./scripts/check.sh              # or: make check
make test                       # pytest + web vitest
.venv/bin/python scripts/demo_rehearsal.py
```

Failure scenarios: `tests/unit/test_failure_hardening.py` (1–25).  
Measured rehearsal: `demo/rehearsal_results.json` (fake compiler; all demo-path checks passed).

## 21. Evaluation results

See **`docs/EVALUATION_RESULTS.md`** and `evaluation/results.json`.

Primary AURORA gold (deterministic IR path, **measured**): change recall / evidence-page accuracy **1.0**; safety blockers **0** RED executions, **0** AMBER without approval, resume + audit OK.

**Do not claim** live Vertex extraction accuracy or `EVALUATION.md` targets as achieved unless re-measured live.

## 22. Security boundaries

See `SECURITY.md`, `docs/SECURITY_REVIEW.md`, `docs/SECURITY_HARDENING.md`.

Highlights: PDF untrusted; tool-less extraction; allowlisted tools; code authorization; hash-chained audit; least-privilege Terraform SAs; no secrets in git.

## 23. Known limitations

- Live GCP deploy is **optional**; local demo uses fakes/adapters
- Live Gemini IR quality is **not** claimed from Prompt 13 measured results (fake/deterministic IR)
- Frontend `npm audit` reports vite/esbuild/vitest advisories (dev tooling)
- Container image CVE scan **not tested** in hardening pass
- Single synthetic amendment scenario for the polished demo
- Not for real PHI, real trials, or regulatory submission

## 24. Development-tool disclosure

This repository was **newly created during the hackathon** and developed with assistance from:

| Tool | Use |
| --- | --- |
| **Cursor** | Primary IDE / agent-assisted implementation |
| **Claude Code** | Additional agent/CLI assistance (`launch-claude.sh`, `.claude/`) |
| **BMAD Method** | Planning / method assets present under `_bmad/` |
| **Open-source stack** | Python, FastAPI, Pydantic, Google ADK, google-genai, React, Vite, Terraform, pytest, Vitest, Playwright |

**Not listed:** tools that were not used for this project (e.g. no claim of OpenAI Codex / ChatGPT unless separately used by an author).

## 25. License

Apache License 2.0 — see `LICENSE`.

## 26. Cleanup instructions

**Local:**

```bash
./scripts/reset_demo.sh
rm -rf data/object_store data/sqlite data/demo_rehearsal
```

**Cloud (after deploy):**

```bash
./scripts/destroy_demo_resources.sh
```

Then verify Console for leftover Artifact Registry images, logs, and billing alerts. Scale-to-zero does **not** eliminate all storage costs — see `infra/terraform/README.md`.

---

## Claim → evidence map

| Claim | Evidence |
| --- | --- |
| Five semantic changes on AURORA | `fixtures/gold/amendment_v1_to_v2_expected.json`; `demo/rehearsal_results.json` |
| GREEN / AMBER / RED gating | `src/protocol215/policy/matrix.py`; failure tests 17–18 |
| Phoenix P002 conflict | `simulator/twin.py`; Findings UI; rehearsal checks |
| Async approval / resume | `api/routes.py`; `workflow/nodes.py`; rehearsal |
| Fake vs live labeling | `health.py` readiness `demo_mode`; Mode bar |
| Eval metrics (measured) | `docs/EVALUATION_RESULTS.md`; `evaluation/results.json` |
| Terraform / deploy scripts | `infra/terraform/`; `scripts/deploy.sh` |
| Demo reset | `scripts/reset_demo.sh`; `tests/unit/test_demo_reset.py` |

## Placeholders (manual)

- `[REPOSITORY_URL]` — set after publishing git remote
- `[HOSTED_URL]` — Cloud Run web URL after deploy
- `[VIDEO_URL]` — public YouTube/Vimeo demo ≤4 minutes
- Live Gemini + cloud Mode bar proof screenshots for Devpost
