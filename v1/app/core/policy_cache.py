import logging
from typing import Optional, Dict, Any

from app.core.circuit_breaker import db_circuit_breaker
from app.core.redis import redis_manager
from app.models.db import ApiKey, Plan, Override, ApiKeyLimitOverride
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

logger = logging.getLogger(__name__)

async def get_policy(key_hash: str, db: AsyncSession) -> Optional[Dict[str, Any]]:
    """
    Lazy-loads policy from PostgreSQL and caches in Redis.
    Uses key_hash (SHA-256) since raw key is never stored.
    """
    r = redis_manager.get_client()
    cache_key = f"viridis:policy:{key_hash}"
    
    # 1. Try cache
    cached = await r.hgetall(cache_key)
    if cached:
        return cached


    if not await db_circuit_breaker.allow_request():
        logger.warning(f"Database circuit breaker is OPEN. Skipping DB fallback for key: {key_hash}")
        return None

    try:
        result = await db.execute(
            select(ApiKey, Plan, ApiKeyLimitOverride)
            .join(Plan, ApiKey.plan_id == Plan.id)
            .outerjoin(ApiKeyLimitOverride, ApiKey.id == ApiKeyLimitOverride.api_key_id)
            .where(ApiKey.key_hash == key_hash)
        )
        row = result.first()
        
        if not row:
            await db_circuit_breaker.record_success()
            return None
            
        api_key, plan, limit_override = row
    
        # Gather hard overrides
        overrides = await db.execute(
            select(Override)
            .where(Override.api_key_id == api_key.id)
        )
        await db_circuit_breaker.record_success()
    except SQLAlchemyError as e:
        await db_circuit_breaker.record_failure()
        logger.error(f"Database fallback query failed: {e}")
        raise
    active_override = "NONE"
    for override in overrides.scalars():
        active_override = override.override_type # e.g. HARD_DENY or HARD_ALLOW
        break

    rpm = limit_override.requests_per_minute if limit_override and limit_override.requests_per_minute is not None else plan.requests_per_minute
    burst = limit_override.burst_capacity if limit_override and limit_override.burst_capacity is not None else plan.burst_capacity
    refill = limit_override.burst_refill_rate if limit_override and limit_override.burst_refill_rate is not None else plan.burst_refill_rate
    conc = limit_override.max_concurrency if limit_override and limit_override.max_concurrency is not None else plan.max_concurrency
    cool = limit_override.cooldown_seconds if limit_override and limit_override.cooldown_seconds is not None else plan.cooldown_seconds

    policy = {
        "key_id": str(api_key.id),
        "tenant_id": str(api_key.tenant_id),
        "is_active": str(api_key.is_active).lower(),
        "expires_at": str(api_key.expires_at.timestamp()) if api_key.expires_at else "0",
        "requests_per_minute": str(rpm),
        "burst_capacity": str(burst),
        "burst_refill_rate": str(refill),
        "max_concurrency": str(conc),
        "cooldown_seconds": str(cool),
        "tier": plan.tier,
        "override": active_override
    }
    
    # 3. Write to cache
    await r.hset(cache_key, mapping=policy)
    await r.expire(cache_key, 300) # 5 minutes TTL
    
    return policy

async def invalidate_policy(key_hash: str) -> None:
    """Invalidates the policy cache for a given key hash."""
    r = redis_manager.get_client()
    await r.delete(f"viridis:policy:{key_hash}")
