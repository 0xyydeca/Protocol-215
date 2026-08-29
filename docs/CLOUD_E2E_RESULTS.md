# Cloud E2E Results

_Last updated: not run yet_

## Verdict

**NOT RUN** — deploy the cloud path repair + frontend reliability changes, then execute:

```bash
CONFIRM_RESET=yes ./scripts/cloud_e2e_test.sh
```

## Evidence

| Field | Value |
| --- | --- |
| commit_sha | — |
| web_revision | — |
| worker_revision | — |
| gemini_model | — |
| run_id | — |
| E2E result | NOT RUN |
| GitHub Actions | — |

## Notes

- Primary recording path: Cloud Run same-origin web URL.
- Recording readiness cannot PASS until this document/Firestore `cloud_e2e_results/latest` shows PASS for the currently deployed web and worker revisions.
- Do not claim PASS when adapters are fake/local or when any assertion is skipped.
