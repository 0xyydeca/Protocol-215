/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Cloud Run / API origin for hosted UI. Empty = same-origin (Vite proxy / Vercel rewrite). */
  readonly VITE_API_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
