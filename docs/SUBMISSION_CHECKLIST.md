# Submission checklist — Protocol 215 (The Taskmaster)

Use before Devpost publish. Every checked item must be verifiable from code, the hosted app, or `docs/CLOUD_E2E_RESULTS.md`.

## Links (required)

- [x] **Repository:** https://github.com/0xyydeca/Protocol-215
- [x] **Hosted app:** https://protocol-215-web-u6nfupvmhq-uc.a.run.app
- [ ] **Video:** public YouTube/Vimeo URL pasted in **Devpost** (≤4 min, public not unlisted) — *not stored in git*

## Live deployment honesty

- [ ] Mode bar on hosted app shows **Google Cloud** and **Live Gemini** (backend `/readyz`, not UI fiction)
- [ ] Mode bar shows **gemini-3.5-flash** (or current `GEMINI_MODEL` from service env)
- [ ] Cloud E2E report present: `docs/CLOUD_E2E_RESULTS.md` (**PASS**)
- [ ] Adapter labels match runtime: `GCSObjectStore`, `FirestoreStateStore`, `PubSubEventBus`, `VertexGeminiProtocolCompiler`

## Demo path (AURORA-101 synthetic)

- [ ] Upload v1.0 + v2.0 PDFs from `fixtures/protocols/`
- [ ] Five evidence-linked semantic changes on Redline
- [ ] Impact graph + Trial Twin findings (incl. Phoenix P002 conflict)
- [ ] GREEN actions execute; AMBER pauses for approval (not “stalled”)
- [ ] Approve → resume → manifest + audit verify
- [ ] `run_id` / `session_id` visible in UI where persisted

## Architecture & documentation

- [ ] `docs/architecture.png` and `docs/architecture.svg` match deployed stack
- [x] README **Live Deployment** section URLs filled
- [ ] `docs/VIDEO_EVIDENCE.md` timestamps filled from final video; spurious rows removed
- [ ] No doc claims “Terraform not applied”, “cloud optional only”, or “live Gemini not demonstrated”

## Safety & scope (must appear in README / Devpost)

- [ ] Synthetic proof of concept — no PHI
- [ ] No real trial system integrations
- [ ] Not GxP validated
- [ ] No autonomous medical decisions; code authorizes GREEN/AMBER/RED

## Development-tool disclosure

- [ ] Cursor, Claude Code, BMAD, ChatGPT (review/scripting), and open-source stack listed
- [ ] No tools claimed that were not used

## CI & repo hygiene

- [ ] GitHub Actions green on submitted commit
- [ ] No secrets in git (`.env`, SA JSON, API keys)
- [ ] `LICENSE` (Apache-2.0) present

## Optional gallery assets

- [ ] Architecture diagram attached to Devpost
- [ ] Sanitized GCP screenshots in `docs/evidence/` (video run captured **before** demo reset)
- [ ] Firestore / Pub/Sub / Cloud Run console stills (no credentials visible)
