resource "google_cloud_run_v2_service" "web" {
  name     = local.web_service
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  labels = var.labels

  template {
    service_account = google_service_account.web.email

    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }

    timeout = "60s"

    containers {
      image = local.web_image

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "1Gi"
        }
      }

      env {
        name  = "APP_ENV"
        value = "cloud"
      }
      env {
        name  = "EXECUTION_MODE"
        value = "cloud"
      }
      env {
        name  = "OBJECT_STORE_BACKEND"
        value = "gcs"
      }
      env {
        name  = "STATE_STORE_BACKEND"
        value = "firestore"
      }
      env {
        name  = "EVENT_BUS_BACKEND"
        value = "pubsub"
      }
      env {
        name  = "GEMINI_BACKEND"
        value = "vertex"
      }
      env {
        name  = "GEMINI_MODEL"
        value = var.gemini_model
      }
      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }
      env {
        name  = "GOOGLE_CLOUD_LOCATION"
        value = var.gemini_location
      }
      env {
        name  = "GCS_BUCKET"
        value = google_storage_bucket.artifacts.name
      }
      env {
        name  = "PUBSUB_TOPIC_RECEIVED"
        value = google_pubsub_topic.events.name
      }
      env {
        name  = "PUBSUB_TOPIC_RESUME"
        value = google_pubsub_topic.events.name
      }
      env {
        name  = "STATIC_ASSETS_DIR"
        value = "/app/static"
      }
      env {
        name  = "CORS_ORIGINS"
        value = "*"
      }
    }
  }

  depends_on = [
    google_project_service.apis,
    google_artifact_registry_repository.images,
  ]

  lifecycle {
    ignore_changes = [
      # Image digests may be updated by deploy scripts between applies.
      client,
      client_version,
    ]
  }
}

resource "google_cloud_run_v2_service" "worker" {
  name     = local.worker_service
  location = var.region
  # Reachable URL for Pub/Sub HTTPS push, but NOT publicly invokable:
  # only the Pub/Sub invoker SA has roles/run.invoker (no allUsers).
  ingress = "INGRESS_TRAFFIC_ALL"

  labels = var.labels

  template {
    service_account = google_service_account.worker.email

    timeout = "${var.worker_timeout_seconds}s"

    max_instance_request_concurrency = var.worker_concurrency

    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }

    containers {
      image = local.worker_image

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "2"
          memory = "2Gi"
        }
      }

      env {
        name  = "APP_ENV"
        value = "cloud"
      }
      env {
        name  = "EXECUTION_MODE"
        value = "cloud"
      }
      env {
        name  = "OBJECT_STORE_BACKEND"
        value = "gcs"
      }
      env {
        name  = "STATE_STORE_BACKEND"
        value = "firestore"
      }
      env {
        name  = "EVENT_BUS_BACKEND"
        value = "pubsub"
      }
      env {
        name  = "GEMINI_BACKEND"
        value = "vertex"
      }
      env {
        name  = "GEMINI_MODEL"
        value = var.gemini_model
      }
      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }
      env {
        name  = "GOOGLE_CLOUD_LOCATION"
        value = var.gemini_location
      }
      env {
        name  = "GCS_BUCKET"
        value = google_storage_bucket.artifacts.name
      }
      env {
        name  = "WORKER_REQUIRE_OIDC"
        value = "true"
      }
      env {
        name  = "PUBSUB_TOPIC_RECEIVED"
        value = google_pubsub_topic.events.name
      }
      env {
        name  = "PUBSUB_TOPIC_RESUME"
        value = google_pubsub_topic.events.name
      }
    }
  }

  depends_on = [
    google_project_service.apis,
    google_artifact_registry_repository.images,
  ]
}

# Public invoker for judging (web only).
resource "google_cloud_run_v2_service_iam_member" "web_public" {
  project  = var.project_id
  location = google_cloud_run_v2_service.web.location
  name     = google_cloud_run_v2_service.web.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Worker: only the Pub/Sub invoker SA may invoke (no allUsers).
resource "google_cloud_run_v2_service_iam_member" "worker_invoker_pubsub" {
  project  = var.project_id
  location = google_cloud_run_v2_service.worker.location
  name     = google_cloud_run_v2_service.worker.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.pubsub_invoker.email}"
}
