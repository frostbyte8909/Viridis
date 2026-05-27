# Changelog

All notable changes to the Viridis project will be documented in this file in chronological order.

1. `43eefc2` [+] Initialize project structure and config files
2. `7204d1a` [+] Create FastAPI app factory and config
3. `1672577` [+] Set up PostgreSQL SQLAlchemy models
4. `0424baf` [+] Configure Alembic for async migrations
5. `f2912f3` [+] Set up Redis connection pool and Lua scripts
6. `8e09b30` [+] Implement core Redis Lua script wrappers and ZSET concurrency guard
7. `8bb5f62` [+] Implement decision engine orchestrator and enforce endpoint
8. `3f3c786` [+] Build management plane, API key issuance, and HMAC override verification
9. `49ec422` [+] Add PostgreSQL trigger migration for audit log immutability
10. `b21d659` [+] Integrate Redis Streams async audit pipeline and operational modes
11. `ebee56b` [+] Finalize CI/CD pipeline, k6 load testing, and project documentation
12. `5dbc6d4` [+] Fix docker build order, fix alembic graph, and add intensive load testing benchmarks
13. `c4d8d02` [+] Move README to repository root for visibility
14. `02ec4e8` [+] Add basic pytest framework for CI
15. `f838f91` [+] Add production docker-compose configuration
16. `608fecb` [+] Implement Azure IaC Bicep templates for Container Apps
17. `755c830` [+] Implement GitHub Actions CI/CD pipeline
18. `3cbe71d` [+] pre-fix commit before pytest issues fix
19. `37d3b79` [+] fix pytest import error and update status code assertion
20. `6e2edbc` [+] implement key hashing offloading, audit log partitioning migration, and DB fallback circuit breaker
21. `5936558` [+] add GCP IaC layer using Terraform (VPC, Memorystore Redis, Cloud SQL, Secret Manager, and Cloud Run)
22. `0e18f57` [+] Pre-change commit
