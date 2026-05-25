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

@router.post("/tenants", dependencies=[Depends(require_admin_token)])
async def create_tenant(req: CreateTenantReq, db: AsyncSession = Depends(get_db)):
    tenant = Tenant(name=req.name, tier=req.tier)
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    return {"id": tenant.id, "name": tenant.name}

# (Other CRUD endpoints for Plans, Overrides would go here)
