# SECURITY_REVIEW.md — Protocol 215

This review summarizes controls implemented in code and measured in Prompt 13. It is **not** a formal penetration test or GxP validation.

Canonical policy: `SECURITY.md`. Scan notes: `docs/SECURITY_HARDENING.md`.

## Threat model (demo)

| Threat | Mitigation | Evidence |
| --- | --- | --- |
| Prompt injection in PDF | PDF treated as data; tool-less compiler; planner never gets raw PDF bytes | `adapters/gemini/prompts.py`; constrained planner |
| Model invents tools | Allowlist filter; unknown → RED | `tools/registry.py`; `policy/matrix.py` |
| Unauthorized AMBER/RED | Code authorization; RED never executable | `policy/matrix.py`; `tools/executor.py` |
| Stale / replayed approval | Single-use + state version + invocation checks | `policy/approval.py` |
| Duplicate mutations | Idempotency keys; processed-event dedupe | State stores; worker handler |
| Audit tampering | Hash chain verify | `adapters/audit_log.py`; `/api/runs/{id}/audit/verify` |
| Malicious PDF upload | Type/size/page/encrypt validation | `api/pdf_validation.py` |
| Secrets in git | `.gitignore` / `.env.example` only | Secret scan: clean (hardening doc) |
| Over-privileged cloud | Separate SAs; least privilege; private worker | `infra/terraform/iam.tf` |

## Authorization boundary

- GREEN: executable without human approval  
- AMBER: requires `approved=True` after valid approval  
- RED: never executable  

## Logging

Structured logs; credential redaction helpers in cloud logging adapter. Audit stores decision summaries and hashes—not hidden chain-of-thought.

## Measured checks (Prompt 13)

| Check | Class | Result |
| --- | --- | --- |
| Secret pattern scan | measured | No matches |
| pip-audit | measured | No known vulnerabilities |
| npm audit | measured | 5 vite/esbuild/vitest (dev) advisories |
| Container scan | not tested | No Trivy/Grype |
| Live IAM fetch | not tested | Terraform review only |

## Residual risks

- Unapplied / misconfigured live GCP  
- Claiming Fake Compiler results as live Vertex accuracy  
- Dev-server advisories if someone exposes Vite publicly (production serves built static assets)

## Synthetic-only commitment

No real PHI, patients, or production connectors. UI banner + README disclaimer required for demos.
