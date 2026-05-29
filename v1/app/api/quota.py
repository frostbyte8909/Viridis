import time
import uuid
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.sql import text
import hashlib

from app.api.admin import require_admin_token
from app.config import settings
from app.core.redis import redis_manager
from app.db.session import get_db
from app.core.policy_cache import get_policy
from typing import Dict, Any

router = APIRouter(tags=["Quota"])

def _hash_key_sync(raw_key: str, pepper: str) -> str:
    return hashlib.sha256(f"{raw_key}{pepper}".encode()).hexdigest()

async def get_current_quota(key_id: str, key_hash: str, db: AsyncSession) -> Dict[str, Any]:
    policy = await get_policy(key_hash, db)
    if not policy:
        raise HTTPException(status_code=404, detail="Key not found or disabled")

    r = redis_manager.get_client()
    now = time.time()
    
    # 1. Token Bucket
    bucket_key = f"viridis:bucket:{key_id}"
    bucket_data = await r.hmget(bucket_key, ["tokens", "last_refill"])
    capacity = float(policy["burst_capacity"])
    refill_rate = float(policy["burst_refill_rate"])
    
    tokens = capacity
    if bucket_data[0] is not None and bucket_data[1] is not None:
        stored_tokens = float(bucket_data[0])
        last_refill = float(bucket_data[1])
        elapsed = now - last_refill
        tokens = min(capacity, stored_tokens + (elapsed * refill_rate))
    
    # 2. Sliding Window (Fixed Window implementation check)
    window_key = f"viridis:window:{key_id}:{int(now / 60)}"
    window_count = await r.zcard(window_key) or 0
    limit = int(policy["requests_per_minute"])
    
    # 3. Concurrency
    inflight_key = f"viridis:inflight:{key_id}"
    await r.zremrangebyscore(inflight_key, "-inf", now)
    inflight_count = await r.zcard(inflight_key) or 0
    max_concurrency = int(policy["max_concurrency"])

    return {
        "key_id": key_id,
        "tenant_id": policy["tenant_id"],
        "snapshot_at": now,
        "token_bucket": {
            "remaining": round(tokens, 2),
            "capacity": capacity,
            "refill_rate_per_second": refill_rate,
            "percent_remaining": round((tokens / capacity) * 100, 2) if capacity > 0 else 0.0
        },
        "sliding_window": {
            "requests_in_current_minute": window_count,
            "limit": limit,
            "percent_used": round((window_count / limit) * 100, 2) if limit > 0 else 0.0,
        },
        "concurrency": {
            "in_flight": inflight_count,
            "limit": max_concurrency
        }
    }

@router.get("/v1/quota")
async def get_my_quota(
    authorization: str = Header(None),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    raw_key = authorization.split(" ")[1]
    key_hash = _hash_key_sync(raw_key, settings.server_pepper)
    
    policy = await get_policy(key_hash, db)
    if not policy:
        raise HTTPException(status_code=403, detail="Invalid API Key")
        
    return await get_current_quota(policy["key_id"], key_hash, db)

@router.get("/admin/keys/{key_id}/quota", dependencies=[Depends(require_admin_token)])
async def get_tenant_quota(
    key_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    from app.models.db import ApiKey
    result = await db.execute(select(ApiKey).where(ApiKey.id == key_id))
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise HTTPException(status_code=404, detail="Key not found")
        
    return await get_current_quota(str(key_id), api_key.key_hash, db)

@router.get("/admin/keys/{key_id}/usage/history", dependencies=[Depends(require_admin_token)])
async def get_usage_history(
    key_id: uuid.UUID,
    page: int = 1,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    offset = (page - 1) * limit
    
    query = text("""
        SELECT 
            date_trunc('minute', created_at) AS timestamp,
            COUNT(*) as requests,
            SUM(CASE WHEN decision = 'ALLOW' THEN 1 ELSE 0 END) as allowed,
            SUM(CASE WHEN decision = 'THROTTLE' THEN 1 ELSE 0 END) as throttled
        FROM audit_log
        WHERE api_key_id = :key_id
        GROUP BY 1
        ORDER BY 1 DESC
        LIMIT :limit OFFSET :offset
    """)
    
    result = await db.execute(query, {"key_id": key_id, "limit": limit, "offset": offset})
    
    buckets = []
    for row in result:
        buckets.append({
            "timestamp": row[0].isoformat() if row[0] else None,
            "requests": row[1],
            "allowed": row[2],
            "throttled": row[3]
        })
        
    return {
        "key_id": str(key_id),
        "buckets": buckets,
        "page": page
    }
