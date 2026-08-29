/**
 * Vercel production builds must set VITE_API_BASE_URL (Cloud Run web URL).
 * Cloud Run same-origin builds leave it unset — that is intentional.
 * Changing VITE_API_BASE_URL requires rebuilding the Vite app.
 */
import { writeFileSync } from "node:fs";

const isVercel = process.env.VERCEL === "1";
const raw = (process.env.VITE_API_BASE_URL ?? "").trim().replace(/\/$/, "");

if (isVercel) {
  if (!raw) {
    console.error(
      "[protocol-215] VITE_API_BASE_URL is required for Vercel builds.\n" +
        "Set it to your Cloud Run web URL (https://…run.app) and redeploy.\n" +
        "Do not point /api at Vercel — the API is not hosted there.",
    );
    process.exit(1);
  }
  if (!/^https:\/\//i.test(raw)) {
    console.error(
      `[protocol-215] VITE_API_BASE_URL must be HTTPS for Vercel. Got: ${raw}`,
    );
    process.exit(1);
  }
  // Normalize env for Vite by writing a transient .env.production.local if needed —
  // Vercel already injects env; we only validate here.
  console.log(`[protocol-215] Vercel API base OK: ${raw}`);
} else if (raw) {
  console.log(`[protocol-215] VITE_API_BASE_URL=${raw}`);
} else {
  console.log("[protocol-215] same-origin API base (Cloud Run / Vite proxy)");
}

// Touch stamp so CI can prove the gate ran.
writeFileSync(
  new URL("./.api-base-check.json", import.meta.url),
  JSON.stringify({ vercel: isVercel, apiBaseConfigured: Boolean(raw) }, null, 2),
);
