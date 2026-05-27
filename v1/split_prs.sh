#!/bin/bash
set -e

# Unstage all files
git reset HEAD~1

# Create base branch
git checkout -b v1.1
git push origin v1.1

# PR 1: JWT & Config Hardening
git checkout v1.1
git checkout -b feature/jwt-hardening
git add .env.local docker-compose.yml app/main.py app/config.py app/middleware/jwt_auth.py
git commit -m "feat: implement jwt auth and config hardening"
git push origin feature/jwt-hardening
gh pr create --base v1.1 --title "feat: implement jwt auth and config hardening" --body "Adds JWT auth middleware and local environment overrides."

# PR 2: Circuit Breaker Engine
git checkout v1.1
git checkout -b feature/circuit-breaker
git add app/core/circuit_breaker.py app/core/policy_cache.py app/services/audit_consumer.py tests/unit/test_v2_features.py
git commit -m "feat: implement async circuit breaker"
git push origin feature/circuit-breaker
gh pr create --base v1.1 --title "feat: implement async circuit breaker" --body "Wraps database operations with a fail-fast context manager."

# PR 3: Alerts & Audit Exports
git checkout v1.1
git checkout -b feature/alerts-audit
git add app/services/alert_manager.py app/services/audit_export.py app/core/decision.py app/api/admin.py
git commit -m "feat: implement alerting and audit exports"
git push origin feature/alerts-audit
gh pr create --base v1.1 --title "feat: implement alerting and audit exports" --body "Adds debounced webhooks/SMTP and streaming SHA-256 exports."

# PR 4: GCP Infrastructure & CI/CD
git checkout v1.1
git checkout -b feature/gcp-deploy
git add deploy/gcp/backend.tf deploy/gcp/main.tf deploy/gcp/secrets.tf .github/workflows/deploy.yml Dockerfile CHANGELOG.md pyproject.toml uv.lock seed_k6_keys.py
# .github/workflows/ci.yml was deleted
git rm .github/workflows/ci.yml || true
git commit -m "feat: implement gcp terraform and ci/cd"
git push origin feature/gcp-deploy
gh pr create --base v1.1 --title "feat: implement gcp terraform and ci/cd" --body "Adds Terraform definitions for Cloud Run and GAR CI pipeline."

# Go back to v1.1
git checkout v1.1

echo "Done!"
