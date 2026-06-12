locals {
  secrets = [
    "viridis-jwks-url",
    "viridis-jwt-static-pem",
    "viridis-smtp-host",
    "viridis-smtp-user",
    "viridis-smtp-password",
    "viridis-alert-webhook-url",
    "viridis-db-password",
    "viridis-admin-token",
    "viridis-server-pepper"
  ]
}

resource "google_secret_manager_secret" "secrets" {
  for_each  = toset(local.secrets)
  secret_id = each.key
  replication {
    automatic = true
  }
}

# The Cloud Run service account needs permission to access these secrets
resource "google_secret_manager_secret_iam_member" "secret_accessor" {
  for_each  = google_secret_manager_secret.secrets
  secret_id = each.value.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}
