from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio
from typing import AsyncGenerator

from app.api.admin import router as admin_router
from app.api.enforce import router as enforce_router
from app.api.limits import router as limits_router
from app.api.quota import router as quota_router
from app.api.audit_export import router as audit_router
from app.api.metrics import router as metrics_router
from fastapi.middleware.cors import CORSMiddleware
from app.core.redis import redis_manager
import os
from app.services.audit_consumer import run_audit_consumer
from app.ml.consumer import run_waf_consumer
from app.ml.feature_aggregator import _ip_windows, cleanup_task
from app.ml.scorer import run_waf_scorer
from app.ml.trainer import train_model_task
from app.api.waf_admin import router as waf_admin_router

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await redis_manager.connect()
    audit_task = asyncio.create_task(run_audit_consumer())
    waf_consumer_task = asyncio.create_task(run_waf_consumer())
    waf_scorer_task = asyncio.create_task(run_waf_scorer())
    waf_trainer_task = asyncio.create_task(train_model_task())
    cleanup_bg_task = asyncio.create_task(cleanup_task())
    yield
    audit_task.cancel()
    waf_consumer_task.cancel()
    waf_scorer_task.cancel()
    waf_trainer_task.cancel()
    cleanup_bg_task.cancel()
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
app.include_router(waf_admin_router)
app.include_router(metrics_router)

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

@app.get("/health/waf-consumer")
async def waf_health_check() -> dict:
    try:
        r = redis_manager.get_client()
        stream_info = await r.xinfo_stream("viridis:audit:stream")
        lag = stream_info.get(b'length', stream_info.get('length', 0))
    except Exception:
        lag = "unknown"
        
    return {
        "status": "healthy",
        "worker_id": os.getpid(),
        "active_windows": len(_ip_windows),
        "stream_length": lag
    }


@app.get("/ready")
async def readiness_check() -> dict[str, str]:
    # TODO: Add real Redis and DB connection checks here
    return {"status": "ready"}
