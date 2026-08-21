# DEMO_SCRIPT — Protocol 215 (≤4 minutes)

Synthetic AURORA-101 only. Do not claim live Vertex accuracy unless the Mode bar shows **Live Gemini**. Measured local evaluation (Prompt 13) used Fake Compiler + deterministic IR.

## Pre-flight (before recording)

1. `./scripts/reset_demo.sh` (cloud: add `--confirm`)
2. Confirm Mode bar: **Synthetic Study** · **Local** or **Google Cloud** · **Fake Compiler** or **Live Gemini** · model ID · Cloud Run revision (cloud only)
3. Open fixture PDFs ready: `fixtures/protocols/AURORA-101_Protocol_v1.0.pdf` and `…_v2.0.pdf`
4. Second browser tab ready for Cloud Logging / Pub/Sub / Firestore (cloud proof — no secrets)

---

## Timed narrative

### 0:00–0:20 — Problem

On the launch signature screen, read:

> Clinical-trial sites can operate under different protocol versions for an average of **215** days.

Pause for the brand reveal: **Protocol 215 · Clinical Amendment Preflight**.

### 0:20–0:38 — Concept

One sentence: most tools show what changed; Protocol 215 rehearses what will break, executes safe work, gates sensitive actions, and verifies before patients.

Point at Mode bar (Synthetic Study · runtime · compiler — never call Fake Compiler “live”).

### 0:38–1:00 — Cloud trigger

1. Select AURORA-101 scenario  
2. Upload v1 + v2 PDFs  
3. Click **Start Amendment Preflight**  
4. Note 202 response / run id; stage indicator moves past Upload  

**Cloud proof (pick ≥2 across the demo):** Cloud Run `.run.app` URL · revision pill · Pub/Sub `amendment.received` · Vertex/Gemini request · Firestore run doc · Logging entries.

### 1:00–1:35 — Semantic changes

Open **Semantic Redline**. Confirm **five** evidence-linked changes (lab contact, 6h PK, fasting, EDC temp, conditional ECG). Click one card; show page evidence.

### 1:35–2:10 — Trial Twin

Open **215-Day Timeline** (fragmented site activation), then **Findings**. Highlight Boston training, Seattle approval, P001 immutability, and the **Phoenix P002** courier/storage conflict card.

### 2:10–2:40 — Autonomous actions

Open **Action Ledger**. Show GREEN tools already executed (contact directory / EDC / training tasks as produced by the live workflow). Note RED never executes.

### 2:40–3:10 — Phoenix conflict

Return to Findings / Timeline if needed. State clearly: dose 12:00 → 6h sample 18:00; courier 17:30; no overnight storage → activation blocked for P002.

### 3:10–3:30 — Approval and resume

On Action Ledger, open the AMBER approval panel. Approve once. Watch status leave `AWAITING_APPROVAL` (resume event / stage progress). Do not double-click approve.

### 3:30–3:48 — Verification

Open **Manifest**. Show invariant results (all pass for the happy path). Optionally hit audit verify if shown.

### 3:48–4:00 — Manifest and close

Download or print manifest. Close on: evidence-linked release package, synthetic only, ready for judges’ questions.

---

## Click checklist (judge-facing)

1. Wait for signature brand reveal (or skip wait ~2s)  
2. Choose scenario (default OK)  
3. Choose old PDF  
4. Choose new PDF  
5. **Start Amendment Preflight**  
6. Nav → Semantic Redline (auto may land here)  
7. Optional: click a change chip  
8. Nav → Impact (optional)  
9. Nav → 215-Day Timeline  
10. Nav → Findings  
11. Nav → Actions  
12. **Approve** on AMBER panel  
13. Nav → Manifest  
14. Download JSON (optional)

**Minimum clicks if auto-nav works:** upload×2 → Start → wait → Actions Approve → Manifest ≈ **5 interactions** after files selected.

---

## Recording failure risks

| Risk | Mitigation |
| --- | --- |
| Duplicate PDF pair → 409 | Reset demo first |
| Still Fake Compiler while claiming Vertex | Read Mode bar; do not invent “live” |
| Approval double-submit | Single click; wait for resume |
| Background pipeline slow | Allow ≤30s; show stage indicator |
| Wrong PDFs / encrypted | Use fixtures only |
| Cloud reset without confirm | Use `--confirm` |
| UI shows empty findings | Wait for Rehearse stage; do not hardcode |
| Network blip on polling | Retry / refresh; do not refresh mid-approval |

---

## Cloud proof (visible, no secrets)

Show any **two** of:

- Browser URL `https://protocol-215-web-….run.app`
- Mode bar **Revision: …** (`K_REVISION`)
- Console: Pub/Sub message / push ACK for `amendment.received` or `amendment.resume`
- Vertex AI / Gemini request in Logging (model id only)
- Firestore `runs/{id}` status transitions
- Cloud Logging structured lines (`run_id`, `event_id`) — redact project numbers if sensitive

Never show service-account JSON, API keys, or billing pages.

---

## Measured local rehearsal (Prompt 14)

Ran `scripts/demo_rehearsal.py` against Fake Compiler + fixture PDFs (actual workflow, not hardcoded UI):

| Segment | Seconds |
| --- | ---: |
| Reset → upload | ~0.08 |
| Upload → AWAITING_APPROVAL | ~0.00–0.05 |
| Approve → manifest | ~0.00–0.05 |
| **Total API wall** | **~0.1** |

Judge-facing UI budget remains **≤240s** including narration. All demo-path checks passed (5 changes, GREEN actions, Boston/Seattle/P001/P002 findings, AMBER approval, resume, verified manifest). Results: `demo/rehearsal_results.json`.

**Mode:** Fake Compiler — do not call this live Gemini.
