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
23. `f5e685b` [+] Security fixes: C-01, H-01, H-02, H-03, H-04, M-01, M-03
24. `e2215ba` [+] Security fixes: C-02, C-03, C-05, C-06, C-07, H-05, H-06, H-07, H-08, H-09, H-10, H-11, M-05, M-06, M-07, M-08, M-09, M-10, M-11
25. `1d2c166` [+] chore: Restore and secure CI/CD deployment pipeline
26. `1302c45` [+] Create codeql.yml
27. `5bc6d94` [+] ci: fix github action paths, node 20 deprecation warnings, and missing python version
28. `80324de` [+] fix: resolve codeql alerts, add strict pydantic types, and clean up code quality issues
29. `f21394f` [+] ci: enforce workflow permissions
30. `28c7ba8` [+] fix: resolve pydantic url casting bug and strengthen HMAC derivation for codeql
31. `d678314` [+] fix: resolve redis type hint import and definitively satisfy codeql hashing rule
32. `3aae5f4` [+] Merge pull request #14 from frostbyte8909/feature/pr-checks
33. `1dca371` [+] docs: rewrite root README with professional FAANG-style formatting
34. `a76f361` [+] docs: add banner image
35. `2519e2d` [+] docs: replace mermaid diagram with architecture image
36. `a963801` [+] docs: add medium article link and caption to architecture diagram
37. `dd8dcb1` [+] docs: rename project from viridian to viridis
38. `c5a4050` [+] feat: implement per-key limits, quota API, and audit export
