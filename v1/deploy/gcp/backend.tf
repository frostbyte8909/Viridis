terraform {
  backend "gcs" {
    bucket = "viridis-terraform-state"
    prefix = "terraform/state"
  }
}

# The bucket itself must be created manually or in a separate bootstrapping state,
# but we document the ideal configuration for it here:
# resource "google_storage_bucket" "terraform_state" {
#   name          = "viridis-terraform-state"
#   location      = "US"
#   force_destroy = false
#   versioning {
#     enabled = true
#   }
#   lifecycle_rule {
#     action {
#       type = "Delete"
#     }
#     condition {
#       num_newer_versions = 5
#     }
#   }
# }
