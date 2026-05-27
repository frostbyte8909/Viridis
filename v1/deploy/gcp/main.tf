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
  password = var.db_password
}

# 5. Secrets Manager (Secure credentials hosting)
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

# 6. Cloud Run Service (Gateway Container Hosting)
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
        
        env {
          name  = "DATABASE_URL"
          value = "postgresql+asyncpg://postgres:${var.db_password}@${google_sql_database_instance.postgres.private_ip_address}:5432/viridis"
        }
        env {
          name  = "REDIS_URL"
          value = "redis://${google_redis_instance.redis.host}:6379/0"
        }
        env {
          name  = "ADMIN_TOKEN"
          value = var.admin_token
        }
        env {
          name  = "SERVER_PEPPER"
          value = google_secret_manager_secret_version.pepper_version.secret_data
        }
      }
    }

    metadata {
      annotations = {
        "run.googleapis.com/vpc-access-connector" = google_vpc_access_connector.vpc_connector.id
        "run.googleapis.com/vpc-access-egress"    = "all-traffic"
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
}

# IAM Policy to allow unauthenticated public requests to Cloud Run (API Gateways must be open)
resource "google_cloud_run_service_iam_member" "public_access" {
  service  = google_cloud_run_service.api_gateway.name
  location = google_cloud_run_service.api_gateway.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}
