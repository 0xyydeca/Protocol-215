# CHANGELOG.md

All notable changes to Protocol 215 are documented here. Dates are hackathon-local.

## [0.1.0] — 2026-08-21

### Added

- Product contract and architecture (`PRODUCT.md`, `ARCHITECTURE.md`, `SECURITY.md`, `EVALUATION.md`)
- FastAPI Event API with PDF validation, async runs, approvals, audit verify, demo reset
- Google ADK resumable workflow (compile → diff → twin → GREEN/AMBER → resume → manifest)
- React judge UI (seven views, Mode bar, signature opening, demo reset control)
- Cloud adapters: GCS, Firestore, Pub/Sub push worker (optional deps)
- Terraform + `scripts/deploy.sh` / `destroy_demo_resources.sh` (confirm-gated)
- Failure hardening tests (1–25) and evaluation harness (`evaluation/`)
- Demo reset (`scripts/reset_demo.sh`), rehearsal (`scripts/demo_rehearsal.py`)
- Submission docs: README, Devpost package, deployment, security review, checklists

### Measured (local / fake)

- Primary AURORA gold recall/evidence accuracy 1.0 on deterministic IR path (`docs/EVALUATION_RESULTS.md`)
- Demo rehearsal path checks all passed (`demo/rehearsal_results.json`)
- Safety blockers: 0 RED exec, 0 AMBER without approval (local measured)

### Not claimed

- Live Vertex extraction quality as proven
- Terraform applied / hosted URL (until operator deploys)
- Production / GxP readiness
