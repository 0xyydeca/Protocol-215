resource "google_artifact_registry_repository" "images" {
  location      = var.region
  repository_id = local.artifact_repo_id
  description   = "Protocol 215 container images (web + worker)"
  format        = "DOCKER"
  labels        = var.labels

  depends_on = [google_project_service.apis]
}

resource "google_storage_bucket" "artifacts" {
  name                        = local.bucket_name
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = true # demo teardown convenience; not for production PHI
  public_access_prevention    = "enforced"
  labels                      = var.labels

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "Delete"
    }
  }

  depends_on = [google_project_service.apis]
}

resource "google_firestore_database" "native" {
  count = var.create_firestore_database ? 1 : 0

  project     = var.project_id
  name        = var.firestore_database_id
  location_id = var.firestore_location
  type        = "FIRESTORE_NATIVE"

  # Demo-friendly; enable deletion protection for longer-lived projects.
  delete_protection_state = "DELETE_PROTECTION_DISABLED"
  deletion_policy         = "DELETE"

  depends_on = [google_project_service.apis]
}
