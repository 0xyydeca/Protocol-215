# SCREENSHOT_CHECKLIST — Protocol 215 Devpost / README

Capture from a **reset** demo. Prefer 16:9 or Devpost-native aspect. Blur any project numbers if needed; never show keys.

## Required storyboard

| # | Shot | What to show | Source |
| --- | --- | --- | --- |
| 1 | Title / signature | 215-day problem → Protocol 215 brand | Launch view |
| 2 | Mode bar | Synthetic · Local/Cloud · Fake/Live · model · revision | Header |
| 3 | Upload start | v1+v2 selected, Start clicked / run created | Launch |
| 4 | Stages | Indicator past Upload / Compiling | Stage bar |
| 5 | Semantic redline | Five changes; one card with page evidence | Redline view |
| 6 | Impact (optional) | Layered graph | Impact view |
| 7 | 215-day timeline | Phoenix / Boston / Seattle tracks | Timeline |
| 8 | Phoenix conflict | P002 finding card (dose / sample / courier / storage) | Findings |
| 9 | Action ledger | GREEN completed + AMBER waiting | Actions |
| 10 | Approval | Approve panel before click | Actions |
| 11 | Post-resume | Status completed / amber executed | Actions or status |
| 12 | Manifest | Invariants PASS + download | Manifest |
| 13 | Architecture | `docs/architecture.png` | Docs |
| 14 | Cloud proof (≥2 if cloud) | `.run.app`, revision, Logging, Pub/Sub, Firestore, Vertex | Console / UI |

## Optional

- Audit verify success JSON
- Terraform resource list (no billing)
- Evaluation metrics table (label **measured** / **mocked**)

## Do not screenshot

- Billing console amounts / account IDs  
- Service-account JSON  
- `.env` with secrets  
- Unrelated personal browser content  

## After capture

- [ ] Filenames like `01-signature.png` … `14-cloud-logging.png`
- [ ] Store under `demo/screenshots/` (create folder; gitignore large binaries if needed)
- [ ] Match captions to `docs/DEVPOST_SUBMISSION.md`
