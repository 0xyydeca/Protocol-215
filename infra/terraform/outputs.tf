output "web_url" {
  description = "Public URL for protocol-215-web (judge-facing)."
  value       = google_cloud_run_v2_service.web.uri
}

output "worker_url" {
  description = "Private worker URL (internal / Pub/Sub push only — not for public browsing)."
  value       = google_cloud_run_v2_service.worker.uri
  sensitive   = false
}

output "artifact_registry_repository" {
  value = google_artifact_registry_repository.images.name
}

output "artifact_registry_url" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.images.repository_id}"
}

output "gcs_bucket" {
  value = google_storage_bucket.artifacts.name
}

output "pubsub_events_topic" {
  value = google_pubsub_topic.events.name
}

output "pubsub_dead_letter_topic" {
  value = google_pubsub_topic.dead_letter.name
}

output "pubsub_worker_subscription" {
  value = google_pubsub_subscription.worker_push.name
}

output "web_service_account" {
  value = google_service_account.web.email
}

output "worker_service_account" {
  value = google_service_account.worker.email
}

output "pubsub_invoker_service_account" {
  value = google_service_account.pubsub_invoker.email
}

output "web_image" {
  value = local.web_image
}

output "worker_image" {
  value = local.worker_image
}

output "gemini_model" {
  value = var.gemini_model
}

output "cost_notes" {
  value = <<-EOT
    Scale-to-zero: min_instances=${var.min_instances}. Max instances=${var.max_instances}.
    Destroy demo: ./scripts/destroy_demo_resources.sh
    Budget alerts: configure in Cloud Billing (do not store billing account IDs in git).
  EOT
}
