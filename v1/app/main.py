from fastapi import FastAPI, Depends

from app.config import settings

app = FastAPI(
    title="Viridis API Admission Engine",
    description="Real-time, policy-driven admission control microservice.",
    version="1.0.0",
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
async def readiness_check() -> dict[str, str]:
    # TODO: Add real Redis and DB connection checks here
    return {"status": "ready"}
