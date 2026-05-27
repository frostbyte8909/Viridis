terraform {
  backend "gcs" {
    bucket = "viridis-tf-state"
    prefix = "terraform/state"
  }
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# 1. VPC Network & Private Services Access
resource "google_compute_network" "vpc_network" {
  name                    = "viridis-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "subnet" {
  name          = "viridis-subnet"
  ip_cidr_range = "10.0.0.0/24"
  network       = google_compute_network.vpc_network.id
  region        = var.region
}

resource "google_compute_global_address" "private_ip_alloc" {
  name          = "viridis-private-ip-alloc"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.vpc_network.id
}

resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.vpc_network.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_alloc.name]
}

resource "google_vpc_access_connector" "vpc_connector" {
  name          = "viridis-vpc-conn"
  region        = var.region
  ip_cidr_range = "10.8.0.0/28"
  network       = google_compute_network.vpc_network.name
}

# 2. Secure Cloud Memorystore (Redis)
resource "google_redis_instance" "redis" {
  name                    = "viridis-redis"
  tier                    = "STANDARD_HA"
  memory_size_gb          = 1
  region                  = var.region
  authorized_network      = google_compute_network.vpc_network.id
  connect_mode            = "PRIVATE_SERVICE_ACCESS"
  auth_enabled            = true
  transit_encryption_mode = "SERVER_AUTHENTICATION"
  depends_on              = [google_service_networking_connection.private_vpc_connection]
}

# 3. Secure Cloud SQL (PostgreSQL)
resource "google_sql_database_instance" "postgres" {
  name                = "viridis-db"
  database_version    = "POSTGRES_15"
  region              = var.region
  deletion_protection = true

  depends_on = [google_service_networking_connection.private_vpc_connection]

  lifecycle {
    prevent_destroy = true
  }

  settings {
    tier = "db-custom-1-3840"
    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.vpc_network.id
    }
    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
    }
  }
}

resource "google_sql_database" "database" {
  name     = "viridis"
  instance = google_sql_database_instance.postgres.name
}

resource "google_sql_user" "db_user" {
  name     = "postgres"
  instance = google_sql_database_instance.postgres.name
  password = var.db_password
}

# 4. Secrets Manager
resource "google_secret_manager_secret" "pepper" {
  secret_id = "viridis-server-pepper"
  replication {
    automatic = true
  }
}

resource "google_secret_manager_secret_version" "pepper_version" {
  secret      = google_secret_manager_secret.pepper.id
  secret_data = var.server_pepper
}

resource "google_secret_manager_secret" "admin_token" {
  secret_id = "viridis-admin-token"
  replication {
    automatic = true
  }
}

resource "google_secret_manager_secret_version" "admin_token_version" {
  secret      = google_secret_manager_secret.admin_token.id
  secret_data = var.admin_token
}

resource "google_secret_manager_secret" "db_url" {
  secret_id = "viridis-db-url"
  replication {
    automatic = true
  }
}

resource "google_secret_manager_secret_version" "db_url_version" {
  secret      = google_secret_manager_secret.db_url.id
  secret_data = "postgresql+asyncpg://postgres:${var.db_password}@${google_sql_database_instance.postgres.private_ip_address}:5432/viridis"
}

resource "google_secret_manager_secret" "redis_url" {
  secret_id = "viridis-redis-url"
  replication {
    automatic = true
  }
}

resource "google_secret_manager_secret_version" "redis_url_version" {
  secret      = google_secret_manager_secret.redis_url.id
  secret_data = "rediss://:${google_redis_instance.redis.auth_string}@${google_redis_instance.redis.host}:${google_redis_instance.redis.port}/0"
}


# 5. Cloud Run Service (Gateway Container Hosting)
resource "google_cloud_run_service" "api_gateway" {
  name     = "viridis-gateway"
  location = var.region

  template {
    spec {
      containers {
        image = var.container_image
        ports {
          container_port = 8000
        }
        resources {
          limits = {
            memory = "512Mi"
            cpu    = "1"
          }
        }
        
        env {
          name = "DATABASE_URL"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.db_url.secret_id
              key  = "latest"
            }
          }
        }
        env {
          name = "REDIS_URL"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.redis_url.secret_id
              key  = "latest"
            }
          }
        }
        env {
          name = "ADMIN_TOKEN"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.admin_token.secret_id
              key  = "latest"
            }
          }
        }
        env {
          name = "SERVER_PEPPER"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.pepper.secret_id
              key  = "latest"
            }
          }
        }
      }
    }

    metadata {
      annotations = {
        "run.googleapis.com/vpc-access-connector" = google_vpc_access_connector.vpc_connector.id
        "run.googleapis.com/vpc-access-egress"    = "all-traffic"
        "run.googleapis.com/ingress"              = "internal-and-cloud-load-balancing"
        "run.googleapis.com/timeout"              = "60"
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
}
