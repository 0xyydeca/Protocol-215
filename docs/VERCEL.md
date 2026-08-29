# Vercel — Protocol 215 UI only

Vercel hosts the **React/Vite judge UI**. It does **not** run the FastAPI API, Google ADK worker, Pub/Sub, Firestore, or Vertex pipeline.

For the [All Things Agentic Hackathon](https://allthingsagentichackathon.devpost.com/), Google Cloud proof still comes from **Cloud Run** (and friends) via `scripts/deploy.sh` — not from Vercel.

## What works on Vercel

- Static SPA (`apps/web`)
- Optional link to a public API via `VITE_API_BASE_URL` (usually your Cloud Run web URL)

## Prerequisites

1. Deploy API + worker to **Google Cloud Run** (`./scripts/deploy.sh`) **or** another public HTTPS API that serves `/api`, `/readyz`, `/healthz`.
2. Add the Vercel origin to API `CORS_ORIGINS` (Cloud Run env), e.g.  
   `https://your-app.vercel.app,http://127.0.0.1:5173,http://localhost:5173`
3. Vercel project **Root Directory** = `apps/web` (if the Git repo root is `protocol-215/`).

## Env (Vercel → Project → Settings → Environment Variables)

| Name | Value |
| --- | --- |
| `VITE_API_BASE_URL` | `https://YOUR-CLOUD-RUN-WEB.run.app` (no trailing slash) |

Rebuild after changing this (Vite inlines it at build time).

## CLI deploy

```bash
cd apps/web
npm ci
npx vercel login          # once
npx vercel                # preview
npx vercel --prod         # production
```

Or connect the GitHub repo in the Vercel dashboard with root `apps/web`.

## Local still recommended for rehearsal

```bash
./scripts/run_local.sh
cd apps/web && npm run dev
# http://127.0.0.1:5173/?demo=1
```

## Mode bar honesty

- UI on Vercel + API on Cloud Run → Mode bar should show **Google Cloud** (from `/readyz`).
- UI on Vercel + no API / wrong URL → broken demo; do not claim Cloud.
- UI on Vercel + local API via tunnel → still **Local** unless the API itself runs on GCP.
