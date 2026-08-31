# RECORDING_CHECKLIST — Protocol 215 demo video

Target: **under 4 minutes**, English audio or subtitles, public YouTube or Vimeo.

Follow narration in `demo/DEMO_SCRIPT.md`.

## Before record

- [ ] Run `./scripts/reset_demo.sh` (cloud: `--confirm`)
- [ ] Confirm Mode bar: **Synthetic Study**
- [ ] If claiming live model: Mode bar shows **Live Gemini** (not Fake Compiler)
- [ ] If claiming cloud: Mode bar shows **Google Cloud** + **Revision** (or visible `.run.app` URL)
- [ ] Close private / personal tabs
- [ ] Hide billing, IAM keys, `.env`, service-account JSON, project secrets
- [ ] Console / Logging font size readable on 1080p
- [ ] Capture resolution ≥ 1080p (or platform minimum)
- [ ] Microphone level check; reduce keyboard noise
- [ ] Fixture PDFs ready: `fixtures/protocols/AURORA-101_Protocol_v1.0.pdf` + v2.0
- [ ] Second monitor/tab ready for Cloud proof (optional but recommended)

## During record

- [ ] Signature problem line → Protocol 215 brand
- [ ] Upload + Start; show stage progress
- [ ] Five semantic changes with evidence
- [ ] Twin findings: Boston, Seattle, P001, Phoenix P002
- [ ] GREEN ledger activity
- [ ] One AMBER approve (single click)
- [ ] Manifest + invariants
- [ ] At least **two** cloud proofs if cloud demo: `.run.app` URL, revision, Pub/Sub, Vertex log, Firestore change, Logging entry

## After record

- [ ] Duration **&lt; 4:00**
- [ ] Public link works without login
- [ ] English audio **or** accurate subtitles
- [ ] Cloud Run proof visible (if cloud claim)
- [ ] Final manifest appears
- [ ] No exaggerated claims in voiceover (“validated clinical”, “guarantees safety”, “perfect extraction”)
- [ ] Paste public video URL into Devpost (≤4 min, public not unlisted)

## Fail / retake if

- Mode bar says Fake while voiceover says “live Gemini”
- Duplicate 409 on upload (forgot reset)
- Double approval error
- Secrets or billing UI on screen
