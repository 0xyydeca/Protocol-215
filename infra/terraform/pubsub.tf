resource "google_pubsub_topic" "events" {
  name   = local.events_topic
  labels = var.labels

  message_retention_duration = "604800s" # 7 days

  depends_on = [google_project_service.apis]
}

resource "google_pubsub_topic" "dead_letter" {
  name   = local.dlq_topic
  labels = var.labels

  message_retention_duration = "1209600s" # 14 days

  depends_on = [google_project_service.apis]
}

resource "google_pubsub_subscription" "worker_push" {
  name  = "${var.name_prefix}-worker-push"
  topic = google_pubsub_topic.events.name

  ack_deadline_seconds = 600

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dead_letter.id
    max_delivery_attempts = 5
  }

  push_config {
    push_endpoint = "${google_cloud_run_v2_service.worker.uri}/pubsub/push"

    oidc_token {
      service_account_email = google_service_account.pubsub_invoker.email
      audience              = google_cloud_run_v2_service.worker.uri
    }

    attributes = {
      "x-goog-version" = "v1"
    }
  }

  depends_on = [
    google_cloud_run_v2_service.worker,
    google_cloud_run_v2_service_iam_member.worker_invoker_pubsub,
    google_service_account_iam_member.pubsub_token_creator,
    google_pubsub_topic_iam_member.pubsub_dlq_publisher,
  ]
}

# Optional pull subscription on DLQ for operators to inspect failed deliveries.
resource "google_pubsub_subscription" "dead_letter_pull" {
  name  = "${var.name_prefix}-dead-letter-pull"
  topic = google_pubsub_topic.dead_letter.name

  message_retention_duration = "604800s"
  retain_acked_messages      = false
  ack_deadline_seconds       = 30
}
