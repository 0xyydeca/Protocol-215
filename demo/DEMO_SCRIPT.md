# DEMO_SCRIPT — Protocol 215 (3:55 incident-driven storyboard)

Synthetic AURORA-101 only. Open the UI with **`?demo=1`** for judge-facing recording mode.

**Do not claim Google Cloud or Live Gemini unless the Mode bar shows those values from the backend.**

## Pre-flight (before recording)

```bash
./scripts/recording_preflight.sh --api https://YOUR-WEB-URL --web https://YOUR-WEB-URL --reset --confirm
```

Or locally (cloud checks will FAIL — expected for local rehearsal):

```bash
./scripts/recording_preflight.sh --api http://127.0.0.1:8000
./scripts/reset_demo.sh
```

Confirm Mode bar (backend-observed only):

- Synthetic Study
- Local **or** Google Cloud
- Fake Compiler **or** Live Gemini
- Model ID (actual)
- Revision (Cloud Run `K_REVISION`, or —)
- Run / Status (update as the run progresses)

Open: `https://…/?demo=1` (or `http://localhost:5173/?demo=1`).

Fixture PDFs: `fixtures/protocols/AURORA-101_Protocol_v1.0.pdf` and `…_v2.0.pdf`.

Second tab ready for Console proof (Pub/Sub / Logging / Firestore) — **no secrets**.

---

## Timed narrative (3:55)

### 0:00–0:28 — Phoenix conflict cold open

On Launch (`?demo=1`), the **scenario preview** is visible:

> Phoenix · P002  
> Dose: 12:00 · New 6-hour sample: 18:00 · Courier: 17:30 · Overnight storage: unavailable

Narrate: *“A six-hour PK draw after a noon dose lands after the courier leaves — and this site has no validated overnight storage.”*

This preview is **explanatory**, not a fabricated run result.

### 0:28–0:48 — Meaning of 215

Signature title on screen:

> **215 DAYS** of protocol-version fragmentation  
> **PROTOCOL 215** · Clinical Amendment Preflight  
> Rehearse every protocol amendment before it reaches a patient.

Narrate: *“Sites can run mismatched protocol versions for about 215 days. Protocol 215 rehearses the amendment before it reaches a patient.”*

### 0:48–1:05 — Cloud proof

Point at the Mode bar. Read **exactly** what it shows (Google Cloud · Live Gemini · model · Revision).

Optional cutaway (≤10s): Cloud Run `.run.app` URL, Pub/Sub topic, or Logging line — no keys.

### 1:05–1:25 — Upload and event

1. Scenario AURORA-101 (default)  
2. Upload v1 + v2 PDFs  
3. **Start Amendment Preflight**  
4. Note run ID; stage indicator leaves Launch/Compile as backend status advances  

Narrate: *“Upload publishes `amendment.received`. The worker runs asynchronously — the UI does not invent outcomes.”*

### 1:25–1:55 — Gemini semantic changes

Open **Semantic Redline**. Five evidence-linked change cards should be readable at 1080p.

Click the **6-hour PK** card → show **page 8 / SEC-PK** evidence.

### 1:55–2:20 — Trial Twin

**215-Day Timeline**: Phoenix, Boston, Seattle visible **without horizontal scrolling**.

**Findings**: Phoenix · P002 is the dominant card (dose / sample / courier / storage).

### 2:20–2:45 — Safe actions

**Action Ledger** three columns:

- Completed automatically (IDs + timestamps from backend)
- Waiting for approval
- Blocked (RED never executes)

### 2:45–3:20 — Approval and resume

Open the AMBER panel. Show:

- protocol evidence · operational evidence  
- before / proposed after  
- consequences of approval / rejection  
- run ID · session ID · invocation ID  

**Approve once** (button disables immediately).

Watch **Resume proof** strip: status moves **AWAITING_APPROVAL → RESUMING → VERIFYING** with the **same** run/session/invocation identity. Completed GREEN actions are **not** replayed.

### 3:20–3:45 — Manifest

**Amendment Release Manifest** — only after backend confirmation:

- sites / participants evaluated  
- changes detected · evidence coverage  
- unauthorized RED · AMBER without approval · duplicates  
- completed visits altered · site-version conflicts  
- audit-chain verification  

Do not announce “success” until values appear from the API.

### 3:45–3:55 — Final tagline

> Protocol 215 — rehearse every protocol amendment before it reaches a patient.  
> Synthetic data only.

---

## Click checklist

1. Open `?demo=1`  
2. Wait for signature / scenario preview  
3. Upload v1 + v2  
4. Start Amendment Preflight  
5. Redline → click 6h PK evidence  
6. Timeline → Findings (P002)  
7. Actions → Approve once  
8. Manifest  

---

## Failure risks

| Risk | Mitigation |
| --- | --- |
| Claiming Cloud/Live when Mode bar says Local/Fake | Read Mode bar only |
| `recording-readiness` FAIL | Fix cloud backends before official take |
| Double-approve | Button disables after first click |
| Stale prior run | `recording_preflight.sh --reset --confirm` |
| Empty redline/findings | Wait for backend stages — never hardcode |
| Horizontal timeline scroll | Use `?demo=1` CSS layout |

---

## Cloud proof (visible, no secrets)

Show any **two** of: `.run.app` URL · Mode bar Revision · Pub/Sub message · Vertex/Logging model id · Firestore run status · structured logs with `run_id`.
