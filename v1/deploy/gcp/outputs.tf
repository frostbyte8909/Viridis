output "gateway_url" {
  description = "The publicly accessible endpoint URL for the Cloud Run admission gateway"
  value       = google_cloud_run_service.api_gateway.status[0].url
}

output "redis_host" {
  description = "The private IP address of the Memorystore Redis instance"
  value       = google_redis_instance.redis.host
}

output "postgres_private_ip" {
  description = "The private IP address of the Cloud SQL PostgreSQL instance"
  value       = google_sql_database_instance.postgres.private_ip_address
}
