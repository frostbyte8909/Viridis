# Changelog

All notable changes to the **Viridis** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] - GCP Readiness & v2 Engine Enhancements

This release marks the transition of Viridis from a proof-of-concept into a production-ready, compliance-grade API gateway, with full IaC support for Google Cloud Platform.

### Added
- **JWT Authentication Middleware**: Implemented `app/middleware/jwt_auth.py` to support RS256 JWT validation using a JWKS endpoint (production) or static PEM (local development).
- **Circuit Breaker**: Added a robust asynchronous circuit breaker (`app/core/circuit_breaker.py`) guarding all PostgreSQL interactions (policy caching, admin API, audit consumers) to fail-fast during database degradation.
- **Alert Manager**: Implemented `app/services/alert_manager.py` with SMTP and Webhook support to proactively notify tenants and administrators of quota exhaustion, with Redis-backed debouncing.
- **Cryptographic Audit Export**: Created `app/services/audit_export.py` enabling streaming downloads of SHA-256 hash-chained audit logs for compliance requirements.
- **GCP Infrastructure as Code**: Added robust Terraform definitions (`deploy/gcp/`) including:
  - Google Secret Manager integration (`secrets.tf`)
  - Serverless VPC Access Connector configurations.
  - GCS Backend setup (`backend.tf`) for safe CI/CD state sharing.
- **GitHub Actions Deployment**: Added `.github/workflows/deploy.yml` with Workload Identity Federation (WIF) authentication for secure, keyless deployments to Cloud Run.
- **Local Parity Features**: Created `.env.local` and updated `docker-compose.yml` to ensure local development behaves exactly like production without relying on active cloud credentials.

### Changed
- **Event Loop Optimization**: Offloaded CPU-bound key hashing (`hashlib.sha256`) to `asyncio.to_thread` in the `admit` endpoint to prevent blocking the FastAPI event loop during high-throughput bursts.
- **Environment Variable Contract**: Removed all hardcoded fallback secrets from `app/config.py`. The application now strictly enforces the runtime environment variable contract.
- **Dockerfile Hardening**: Updated the Dockerfile to run as a non-root user (`appuser`) and dynamically expose the `$PORT` environment variable mandated by Cloud Run.
- **Health Checks**: Simplified `/health` and `/ready` endpoints in `app/main.py` to perform shallow liveness checks, preventing brief dependency outages from cascading into container termination.

### Removed
- **Legacy CI Pipeline**: Removed the outdated `.github/workflows/ci.yml` in favor of the unified `deploy.yml`.

---
