# Viridis — API Admission & Abuse Governance Engine

Viridis is a production-grade, real-time, policy-driven admission control microservice designed to make API enforcement decisions in under 15ms. It enforces multi-dimensional rate limiting via Redis Lua scripts and decouples audit logging using Redis Streams and background workers.

## Architecture
- **API Framework**: FastAPI
- **Database**: PostgreSQL (SQLAlchemy + Alembic)
- **Hot-Path Cache & Rate Limiting**: Redis
- **Message Broker (Audit)**: Redis Streams

## Features
- Atomic Token Bucket and Sliding Window limits enforced via Redis Lua.
- ZSET-based precise concurrency guarding.
- Instant cache invalidation on policy changes.
- Append-only immutable audit log (enforced via DB triggers).

## Setup
```bash
docker-compose up -d --build
```

Run tests:
```bash
k6 run k6/smoke.js
```
