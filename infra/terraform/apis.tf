locals {
  apis = [
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "storage.googleapis.com",
    "pubsub.googleapis.com",
    "firestore.googleapis.com",
    "aiplatform.googleapis.com",
    "logging.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "serviceusage.googleapis.com",
  ]

  artifact_repo_id = "${var.name_prefix}-images"
  bucket_name      = "${var.name_prefix}-artifacts-${var.bucket_suffix}"
  events_topic     = "${var.name_prefix}-events"
  dlq_topic        = "${var.name_prefix}-dead-letter"
  web_sa_id        = "${var.name_prefix}-web"
  worker_sa_id     = "${var.name_prefix}-worker"
  invoker_sa_id    = "${var.name_prefix}-pubsub-invoker"
  web_service      = "${var.name_prefix}-web"
  worker_service   = "${var.name_prefix}-worker"

  web_image = format(
    "%s-docker.pkg.dev/%s/%s/protocol-215-web:%s",
    var.region,
    var.project_id,
    local.artifact_repo_id,
    var.web_image_tag,
  )
  worker_image = format(
    "%s-docker.pkg.dev/%s/%s/protocol-215-worker:%s",
    var.region,
    var.project_id,
    local.artifact_repo_id,
    var.worker_image_tag,
  )
}

resource "google_project_service" "apis" {
  for_each = toset(local.apis)

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

data "google_project" "current" {
  project_id = var.project_id
}
