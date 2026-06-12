provider "google" {
  project = var.project_id
  region  = var.region
}

# 1. VPC Network & Private Services Access for DB/Redis
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

# Allocate an IP range for private services connection (Cloud SQL & Memorystore)
resource "google_compute_global_address" "private_ip_alloc" {
  name          = "viridis-private-ip-alloc"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.vpc_network.id
}

# Establish VPC Peering connection with Google services
resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.vpc_network.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_alloc.name]
}

# 2. Serverless VPC Access Connector (Allows Cloud Run to reach Redis/DB privately)
resource "google_vpc_access_connector" "vpc_connector" {
  name          = "viridis-vpc-conn"
  region        = var.region
  ip_cidr_range = "10.8.0.0/28"
  network       = google_compute_network.vpc_network.name
}

# 3. Cloud Memorystore (Redis)
resource "google_redis_instance" "redis" {
  name               = "viridis-redis"
  tier               = "BASIC"
  memory_size_gb     = 1
  region             = var.region
  authorized_network = google_compute_network.vpc_network.id
  connect_mode       = "PRIVATE_SERVICE_ACCESS"

  depends_on = [google_service_networking_connection.private_vpc_connection]
}

# 4. Cloud SQL (PostgreSQL)
resource "google_sql_database_instance" "postgres" {
  name             = "viridis-db"
  database_version = "POSTGRES_15"
  region           = var.region

  depends_on = [google_service_networking_connection.private_vpc_connection]

  settings {
    tier = "db-f1-micro" # Development tier, scale up for production
    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.vpc_network.id
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
  password = var.db_password # Provided initially, then ideally managed in Secret Manager
}

# 5. Service Account for Cloud Run (Least Privilege)
resource "google_service_account" "cloud_run_sa" {
  account_id   = "viridis-cloudrun-sa"
  display_name = "Viridis Cloud Run Service Account"
}

# Note: The Secret Manager definitions and IAM bindings are in secrets.tf

# 6. Cloud Run Service (Gateway Container Hosting)
resource "google_cloud_run_service" "api_gateway" {
  name     = "viridis-gateway"
  location = var.region

  template {
    spec {
      service_account_name = google_service_account.cloud_run_sa.email
      containers {
        image = var.container_image
        
        # We don't define port here directly, Cloud Run injects $PORT environment variable automatically (usually 8080).
        # We ensure the app listens to $PORT.
        
        # Plain text environment variables
        env {
          name  = "DATABASE_URL"
          value = "postgresql+asyncpg://postgres:${var.db_password}@${google_sql_database_instance.postgres.private_ip_address}:5432/viridis"
        }
        env {
          name  = "REDIS_URL"
          value = "redis://${google_redis_instance.redis.host}:6379/0"
        }

        # Secret Manager Environment Variables mappings
        # Cloud Run maps Secret Manager values into environment variables at runtime
        env {
          name = "JWKS_URL"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.secrets["viridis-jwks-url"].secret_id
              key  = "latest"
            }
          }
        }
        env {
          name = "JWT_STATIC_PEM"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.secrets["viridis-jwt-static-pem"].secret_id
              key  = "latest"
            }
          }
        }
        env {
          name = "SMTP_HOST"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.secrets["viridis-smtp-host"].secret_id
              key  = "latest"
            }
          }
        }
        env {
          name = "SMTP_USER"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.secrets["viridis-smtp-user"].secret_id
              key  = "latest"
            }
          }
        }
        env {
          name = "SMTP_PASSWORD"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.secrets["viridis-smtp-password"].secret_id
              key  = "latest"
            }
          }
        }
        env {
          name = "ALERT_WEBHOOK_URL"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.secrets["viridis-alert-webhook-url"].secret_id
              key  = "latest"
            }
          }
        }
        env {
          name = "ADMIN_TOKEN"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.secrets["viridis-admin-token"].secret_id
              key  = "latest"
            }
          }
        }
        env {
          name = "SERVER_PEPPER"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.secrets["viridis-server-pepper"].secret_id
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
        "autoscaling.knative.dev/minScale"        = "1" # Prevent cold starts
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  depends_on = [
    google_secret_manager_secret_iam_member.secret_accessor
  ]
}

# IAM Policy to allow unauthenticated public requests to Cloud Run (API Gateways must be open)
resource "google_cloud_run_service_iam_member" "public_access" {
  service  = google_cloud_run_service.api_gateway.name
  location = google_cloud_run_service.api_gateway.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}
