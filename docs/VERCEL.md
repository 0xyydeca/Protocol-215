# Vercel — Protocol 215 UI only (optional)

**Primary recording path:** open the **Cloud Run web URL** (same-origin SPA + API). No `VITE_API_BASE_URL` and no CORS needed for that path.

Vercel remains supported for a hosted UI shell. It does **not** run FastAPI, ADK worker, Pub/Sub, Firestore, or Vertex.

## Changing `VITE_API_BASE_URL` requires a rebuild

Vite inlines `VITE_*` at **build time**. Updating the env var in the Vercel dashboard without redeploying leaves the old API origin in the JS bundle.

## Prerequisites (Vercel only)

1. Deploy API + worker to **Google Cloud Run** (`./scripts/deploy.sh`).
2. Set `VITE_API_BASE_URL` to the Cloud Run **web** URL (HTTPS, no trailing slash).
3. Add the exact Vercel production and preview origins to API `CORS_ORIGINS` (Terraform `var.cors_origins`), e.g.  
   `https://protocol-215.vercel.app,https://protocol-215-git-main-….vercel.app,http://127.0.0.1:5173,http://localhost:5173`
4. Do **not** set `CORS_ORIGINS=*`. The API uses `allow_credentials=False` and allows `GET`, `POST`, `OPTIONS` with `Content-Type`, `Idempotency-Key`, and `X-Correlation-ID`.
5. Vercel project **Root Directory** = `apps/web` (repo root `protocol-215/`).

## Env (Vercel → Project → Settings → Environment Variables)

| Name | Value |
| --- | --- |
| `VITE_API_BASE_URL` | `https://YOUR-CLOUD-RUN-WEB.run.app` (no trailing slash) |

Production builds **fail** when this is missing or not HTTPS (`scripts/check-vite-api-base.mjs`).

At startup the UI shows the resolved API origin and gates upload on `/healthz`. It will not silently send `/api` to Vercel.

## CLI deploy

```bash
cd apps/web
npm ci
npx vercel login
npx vercel --prod
```

## Local rehearsal

```bash
./scripts/run_local.sh
cd apps/web && npm run dev
# http://127.0.0.1:5173/?demo=1
```
