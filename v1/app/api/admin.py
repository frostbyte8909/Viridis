from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.db.session import get_db
from app.config import settings
from app.services.key_service import issue_raw_key, create_api_key_record
from app.core.policy_cache import invalidate_policy
from app.models.db import Tenant, Plan

router = APIRouter(prefix="/admin", tags=["Admin"])

def require_admin_token(authorization: str = Header(None)) -> None:
    if not authorization or authorization != f"Bearer {settings.admin_token}":
        raise HTTPException(status_code=401, detail="Invalid admin token")

class CreateTenantReq(BaseModel):
    name: str
    tier: str

from app.core.circuit_breaker import db_circuit_breaker, execute_with_circuit_breaker, CircuitBreakerError

@router.post("/tenants", dependencies=[Depends(require_admin_token)])
async def create_tenant(req: CreateTenantReq, db: AsyncSession = Depends(get_db)):
    try:
        async with execute_with_circuit_breaker(db_circuit_breaker):
            tenant = Tenant(name=req.name, tier=req.tier)
            db.add(tenant)
            await db.commit()
            await db.refresh(tenant)
            return {"id": tenant.id, "name": tenant.name}
    except CircuitBreakerError:
        raise HTTPException(status_code=503, detail="Database is temporarily unavailable")

from fastapi.responses import StreamingResponse
from app.models.db import ApiKey, Plan
from sqlalchemy.future import select
from app.services.audit_export import generate_audit_export_stream

class AssignPlanReq(BaseModel):
    plan_id: str

@router.put("/keys/{api_key_id}/plan", dependencies=[Depends(require_admin_token)])
async def assign_key_plan(api_key_id: str, req: AssignPlanReq, db: AsyncSession = Depends(get_db)):
    try:
        async with execute_with_circuit_breaker(db_circuit_breaker):
            result = await db.execute(select(ApiKey).where(ApiKey.id == api_key_id))
            api_key = result.scalar_one_or_none()
            if not api_key:
                raise HTTPException(status_code=404, detail="API Key not found")
                
            plan_result = await db.execute(select(Plan).where(Plan.id == req.plan_id))
            plan = plan_result.scalar_one_or_none()
            if not plan:
                raise HTTPException(status_code=404, detail="Plan not found")
                
            api_key.plan_id = plan.id
            await db.commit()
            
            # Invalidate cache
            await invalidate_policy(api_key.key_hash)
            return {"status": "success", "api_key_id": api_key_id, "plan_id": req.plan_id}
    except CircuitBreakerError:
        raise HTTPException(status_code=503, detail="Database is temporarily unavailable")

@router.get("/tenants/{tenant_id}/quotas", dependencies=[Depends(require_admin_token)])
async def get_tenant_quotas(tenant_id: str, db: AsyncSession = Depends(get_db)):
    try:
        async with execute_with_circuit_breaker(db_circuit_breaker):
            result = await db.execute(
                select(ApiKey, Plan)
                .join(Plan, ApiKey.plan_id == Plan.id)
                .where(ApiKey.tenant_id == tenant_id)
            )
            quotas = []
            for api_key, plan in result.all():
                quotas.append({
                    "api_key_id": str(api_key.id),
                    "plan_name": plan.name,
                    "requests_per_minute": plan.requests_per_minute,
                    "burst_capacity": plan.burst_capacity,
                    "max_concurrency": plan.max_concurrency
                })
            return {"tenant_id": tenant_id, "quotas": quotas}
    except CircuitBreakerError:
        raise HTTPException(status_code=503, detail="Database is temporarily unavailable")

@router.get("/export/audit/{tenant_id}", dependencies=[Depends(require_admin_token)])
async def export_audit_log(tenant_id: str):
    """
    Streams a cryptographic hash chain of audit logs for offline verification.
    """
    generator = generate_audit_export_stream(tenant_id, limit=50000)
    return StreamingResponse(generator, media_type="application/x-ndjson")
