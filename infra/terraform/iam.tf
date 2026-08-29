resource "google_service_account" "web" {
  account_id   = local.web_sa_id
  display_name = "Protocol 215 Web"
  description  = "Least-privilege SA for protocol-215-web Cloud Run"
}

resource "google_service_account" "worker" {
  account_id   = local.worker_sa_id
  display_name = "Protocol 215 Worker"
  description  = "Least-privilege SA for protocol-215-worker Cloud Run"
}

resource "google_service_account" "pubsub_invoker" {
  account_id   = local.invoker_sa_id
  display_name = "Protocol 215 Pub/Sub Invoker"
  description  = "OIDC identity used by Pub/Sub to invoke the private worker only"
}

# --- Web IAM: GCS object R/W on designated bucket, Firestore, Pub/Sub publish, logs ---

resource "google_storage_bucket_iam_member" "web_object_user" {
  bucket = google_storage_bucket.artifacts.name
  role   = "roles/storage.objectUser"
  member = "serviceAccount:${google_service_account.web.email}"
}

resource "google_project_iam_member" "web_datastore_user" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.web.email}"
}

resource "google_pubsub_topic_iam_member" "web_events_publisher" {
  topic  = google_pubsub_topic.events.name
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:${google_service_account.web.email}"
}

resource "google_project_iam_member" "web_log_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.web.email}"
}

# Web readiness probe calls Vertex when GEMINI_BACKEND=vertex.
resource "google_project_iam_member" "web_aiplatform_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.web.email}"
}

# --- Worker IAM: GCS, Firestore, Vertex AI, logs ---

resource "google_storage_bucket_iam_member" "worker_object_user" {
  bucket = google_storage_bucket.artifacts.name
  role   = "roles/storage.objectUser"
  member = "serviceAccount:${google_service_account.worker.email}"
}

resource "google_project_iam_member" "worker_datastore_user" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.worker.email}"
}

resource "google_project_iam_member" "worker_aiplatform_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.worker.email}"
}

resource "google_project_iam_member" "worker_log_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.worker.email}"
}

# --- Pub/Sub invoker: run.invoker on worker only (bound in cloud_run.tf) ---

# Allow Pub/Sub service agent to mint OIDC tokens as the invoker SA.
resource "google_project_service_identity" "pubsub" {
  provider = google-beta
  project  = var.project_id
  service  = "pubsub.googleapis.com"

  depends_on = [google_project_service.apis]
}

resource "google_service_account_iam_member" "pubsub_token_creator" {
  service_account_id = google_service_account.pubsub_invoker.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:service-${data.google_project.current.number}@gcp-sa-pubsub.iam.gserviceaccount.com"

  depends_on = [google_project_service_identity.pubsub]
}

# Dead-letter: Pub/Sub must publish to DLQ topic.
resource "google_pubsub_topic_iam_member" "pubsub_dlq_publisher" {
  topic  = google_pubsub_topic.dead_letter.name
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:service-${data.google_project.current.number}@gcp-sa-pubsub.iam.gserviceaccount.com"

  depends_on = [google_project_service_identity.pubsub]
}

# Artifact Registry writers for Cloud Build / local deploy identity are granted
# outside Terraform (user/CI SA). Runtime SAs only need to pull via Cloud Run.
resource "google_artifact_registry_repository_iam_member" "web_ar_reader" {
  location   = google_artifact_registry_repository.images.location
  repository = google_artifact_registry_repository.images.name
  role       = "roles/artifactregistry.reader"
  member     = "serviceAccount:${google_service_account.web.email}"
}

resource "google_artifact_registry_repository_iam_member" "worker_ar_reader" {
  location   = google_artifact_registry_repository.images.location
  repository = google_artifact_registry_repository.images.name
  role       = "roles/artifactregistry.reader"
  member     = "serviceAccount:${google_service_account.worker.email}"
}
