variable "project_id" {
  description = "The GCP Project ID to deploy resources to"
  type        = string
}

variable "region" {
  description = "The target GCP region for all infrastructure resources"
  type        = string
  default     = "us-central1"
}

variable "container_image" {
  description = "The full Google Artifact Registry path to the built Viridis gateway image"
  type        = string
}

variable "db_password" {
  description = "Root password for the PostgreSQL instance"
  type        = string
  sensitive   = true
}

variable "admin_token" {
  description = "Secured administrative token for policy configuration endpoints"
  type        = string
  sensitive   = true
}

variable "server_pepper" {
  description = "Server-side pepper value used for API Key hash salting"
  type        = string
  sensitive   = true
}
