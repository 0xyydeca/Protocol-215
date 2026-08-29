variable "project_id" {
  description = "Google Cloud project ID (never commit real secrets; project ID is not a secret)."
  type        = string
}

variable "region" {
  description = "Primary region for Cloud Run, Artifact Registry, and related resources."
  type        = string
  default     = "us-central1"
}

variable "bucket_suffix" {
  description = "Suffix for globally unique GCS bucket name: protocol-215-artifacts-{suffix}."
  type        = string
}

variable "gemini_model" {
  description = "Vertex AI Gemini model id used by the worker."
  type        = string
  default     = "gemini-3.5-flash"
}

variable "gemini_location" {
  description = "Vertex AI / Gemini API location (gemini-3.5-flash typically requires global)."
  type        = string
  default     = "global"
}

variable "web_image_tag" {
  description = "Container image tag for protocol-215-web (e.g. git sha or semver)."
  type        = string
  default     = "latest"
}

variable "worker_image_tag" {
  description = "Container image tag for protocol-215-worker."
  type        = string
  default     = "latest"
}

variable "max_instances" {
  description = "Maximum Cloud Run instances per service (cost control)."
  type        = number
  default     = 2
}

variable "min_instances" {
  description = "Minimum Cloud Run instances (0 = scale to zero)."
  type        = number
  default     = 0
}

variable "worker_timeout_seconds" {
  description = "Bounded request timeout for the private worker Cloud Run service."
  type        = number
  default     = 600
}

variable "worker_concurrency" {
  description = "Max concurrent requests per worker instance (default 1 unless proven safe)."
  type        = number
  default     = 1
}

variable "firestore_location" {
  description = "Firestore database location (often nam5 or a regional location)."
  type        = string
  default     = "nam5"
}

variable "firestore_database_id" {
  description = "Firestore database id. Use (default) for the default Native database."
  type        = string
  default     = "(default)"
}

variable "create_firestore_database" {
  description = "If false, skip google_firestore_database (use when DB already exists)."
  type        = bool
  default     = true
}

variable "cors_origins" {
  description = "Comma-separated exact browser origins allowed for CORS (Vercel prod/preview + local Vite). Do not use * with credentials; app sets allow_credentials=false."
  type        = string
  default     = "http://127.0.0.1:5173,http://localhost:5173"
}

variable "name_prefix" {
  description = "Resource name prefix."
  type        = string
  default     = "protocol-215"
}

variable "labels" {
  description = "Labels applied to supported resources."
  type        = map(string)
  default = {
    app       = "protocol-215"
    purpose   = "hackathon-demo"
    synthetic = "true"
  }
}
