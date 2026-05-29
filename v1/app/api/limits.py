import logging
import uuid
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.admin import require_admin_token
from app.core.policy_cache import invalidate_policy
from app.db.session import get_db
from app.models.db import ApiKey, ApiKeyLimitOverride
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/keys", tags=["Limits"])


class LimitOverridePatchReq(BaseModel):
    requests_per_minute: Optional[int] = None
    burst_capacity: Optional[int] = None
    burst_refill_rate: Optional[float] = None
    max_concurrency: Optional[int] = None
    cooldown_seconds: Optional[int] = None


@router.patch("/{key_id}/limits", dependencies=[Depends(require_admin_token)])
async def update_key_limits(
    key_id: uuid.UUID,
    req: LimitOverridePatchReq,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    try:
        # Check if key exists
        result = await db.execute(select(ApiKey).where(ApiKey.id == key_id))
        api_key = result.scalar_one_or_none()
        if not api_key:
            raise HTTPException(status_code=404, detail="Key not found")

        # Fetch or create override
        override_result = await db.execute(
            select(ApiKeyLimitOverride).where(ApiKeyLimitOverride.api_key_id == key_id)
        )
        override = override_result.scalar_one_or_none()

        if not override:
            override = ApiKeyLimitOverride(api_key_id=key_id)
            db.add(override)

        updated_fields: List[str] = []
        for field, value in req.model_dump(exclude_unset=True).items():
            setattr(override, field, value)
            updated_fields.append(field)

        await db.commit()
        
        # Invalidate cache
        await invalidate_policy(api_key.key_hash)

        return {
            "key_id": str(key_id),
            "updated_fields": updated_fields,
            "cache_invalidated": True
        }
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Failed to update limits: {e}")
        raise HTTPException(status_code=500, detail="Database error")


@router.post("/{key_id}/reset", dependencies=[Depends(require_admin_token)])
async def reset_key_limits(
    key_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    try:
        result = await db.execute(select(ApiKey).where(ApiKey.id == key_id))
        api_key = result.scalar_one_or_none()
        if not api_key:
            raise HTTPException(status_code=404, detail="Key not found")

        override_result = await db.execute(
            select(ApiKeyLimitOverride).where(ApiKeyLimitOverride.api_key_id == key_id)
        )
        override = override_result.scalar_one_or_none()

        if override:
            await db.delete(override)
            await db.commit()
            await invalidate_policy(api_key.key_hash)
            return {"status": "ok", "message": "Limits reset to defaults"}
            
        return {"status": "ok", "message": "No overrides found"}
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Failed to reset limits: {e}")
        raise HTTPException(status_code=500, detail="Database error")
