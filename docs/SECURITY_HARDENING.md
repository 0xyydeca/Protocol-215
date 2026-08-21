# SECURITY_HARDENING — Prompt 13 review

Evidence classes: **measured** | **mocked** | **live** | **not tested**

This document records security checks run for demo readiness. It does **not** claim production certification.

## 1. Secret scan — measured

Pattern scan over `src/`, `apps/`, `fixtures/`, `infra/`, `scripts/`, `evaluation/`, `docs/` for private keys, AWS-style access keys, Google API key prefixes, and PEM blocks.

**Result:** no matches.

`.env` / service-account JSON are gitignored; fixtures are synthetic.

## 2. Dependency vulnerability scan (Python) — measured

```text
pip-audit --cache-dir .cache/pip-audit
→ No known vulnerabilities found
(protocol215 local package skipped — not on PyPI)
```

## 3. Python static checks — measured (partial)

- `ruff check` on Prompt 13 touched modules: residual style/import nits in broader `tests/` remain; core policy/normalize changes are small.
- `mypy` available in venv; spot-check on `approval.py` / `normalize.py` shows existing `list` type-arg nit in normalize (pre-existing pattern).

Full-repo ruff clean is **not claimed**.

## 4. Frontend dependency audit — measured

`npm audit` in `apps/web`:

- **5** advisories (3 moderate, 1 high, 1 critical) via transitive `esbuild` / `vite` / `vitest` (dev-server request forgery class).
- Affects **dev tooling**, not the production static SPA serve path used in Cloud Run web image.
- Remediation would require Vite major bump (`npm audit fix --force`) — **not applied** in this hardening pass (no product feature / dependency churn beyond evaluation).

## 5. Container image scan — not tested

`trivy` / `grype` not installed in this environment. Local Docker images from Prompt 12A were not rescanned here.

## 6. File-upload validation review — measured

Intake (`api/pdf_validation.py` + unit tests):

- PDF signature required
- size / page limits
- encrypted PDF rejected
- empty/corrupt rejected before Pub/Sub publish
- SHA-256 stored on run

## 7. IAM review — mocked

Terraform (`infra/terraform/`) reviewed for least privilege:

- Separate web vs worker service accounts
- Worker not publicly invokable (`allUsers` absent on worker)
- GCS private; Pub/Sub OIDC push to worker
- No project-owner keys in runtime config

**Live apply / IAM policy fetch:** not tested (no GCP project in this run).

## 8. Logging review — measured

- Cloud log helper redacts credentials / large blobs (unit coverage in cloud adapter tests)
- Audit events store decision summaries + hashes, not chain-of-thought
- Fixtures contain no PHI

## 9. Prompt-injection review — measured

- Compiler system instruction treats PDF as untrusted data; tool-less extraction
- Planner never receives raw PDF bytes
- Dataset `06_prompt_injection` + failure test 16: injection text does not make RED tools executable
- Unknown tools → RED / non-executable

## 10. Authorization-boundary review — measured

- GREEN/AMBER/RED decided in code (`policy/matrix.py`)
- RED never executable even if approved
- AMBER requires approval flag
- **Hardening (Prompt 13):** `validate_approval_not_stale` now rejects already `APPROVED` / `REJECTED` requests (single-use at API decision time, not only `CONSUMED`)
- **Hardening:** `normalize_synonymous_changes` retains primary concept types that were previously dropped when not gold-mapped

## Residual risks (honest)

| Risk | Class |
| --- | --- |
| Live Vertex / GCP not exercised | not tested |
| Frontend npm audit (vite/esbuild) open | measured |
| Container CVE scan missing | not tested |
| Full-repo ruff debt | measured |
