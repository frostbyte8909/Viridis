import json
import logging
from typing import Optional, Dict, Any

from app.core.redis import redis_manager
from app.models.db import ApiKey, Plan, Override
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

    # 2. Fetch from DB (Guarded by Circuit Breaker)
    from app.core.circuit_breaker import db_circuit_breaker, execute_with_circuit_breaker, CircuitBreakerError
    
    try:
        async with execute_with_circuit_breaker(db_circuit_breaker):
            result = await db.execute(
                select(ApiKey, Plan)
                .join(Plan, ApiKey.plan_id == Plan.id)
                .where(ApiKey.key_hash == key_hash)
            )
            row = result.first()
            
            if not row:
                return None
                
            api_key, plan = row
        
            # Gather hard overrides
            overrides = await db.execute(
                select(Override)
                .where(Override.api_key_id == api_key.id)
            )
    except CircuitBreakerError:
        logger.warning(f"Database circuit breaker is OPEN. Skipping DB fallback for key: {key_hash}")
        return None
    except Exception as e:
        logger.error(f"Database fallback query failed: {e}")
        raise e
        
    active_override = "NONE"
    for override in overrides.scalars():
        active_override = override.override_type # e.g. HARD_DENY or HARD_ALLOW
        break

    policy = {
        "key_id": str(api_key.id),
        "tenant_id": str(api_key.tenant_id),
        "is_active": str(api_key.is_active).lower(),
        "expires_at": str(api_key.expires_at.timestamp()) if api_key.expires_at else "0",
        "requests_per_minute": str(plan.requests_per_minute),
        "burst_capacity": str(plan.burst_capacity),
        "burst_refill_rate": str(plan.burst_refill_rate),
        "max_concurrency": str(plan.max_concurrency),
        "cooldown_seconds": str(plan.cooldown_seconds),
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
