from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio
from typing import AsyncGenerator

from app.api.admin import router as admin_router
from app.api.enforce import router as enforce_router
from app.api.limits import router as limits_router
from app.api.quota import router as quota_router
from app.api.audit_export import router as audit_router
from fastapi.middleware.cors import CORSMiddleware
from app.core.redis import redis_manager
from app.services.audit_consumer import run_audit_consumer

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await redis_manager.connect()
    worker_task = asyncio.create_task(run_audit_consumer())
    yield
    worker_task.cancel()
    await redis_manager.disconnect()

app = FastAPI(
    title="Viridis API Admission Engine",
    description="Real-time, policy-driven admission control microservice.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(admin_router)
app.include_router(enforce_router)
app.include_router(limits_router)
app.include_router(quota_router)
app.include_router(audit_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://viridis.admin.dashboard"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
async def readiness_check() -> dict[str, str]:
    # TODO: Add real Redis and DB connection checks here
    return {"status": "ready"}
