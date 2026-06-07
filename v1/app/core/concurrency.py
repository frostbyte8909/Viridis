import time
from app.core.redis import redis_manager

async def check_and_acquire_concurrency(
    key_id: str,
    max_concurrency: int,
    request_id: str,
    ttl_seconds: int = 30
) -> bool:
    """
    Uses a Redis ZSET to track active requests.
    Returns True if acquired, False if concurrency limit exceeded.
    """
    r = redis_manager.get_client()
    zset_key = f"viridis:inflight:{key_id}"
    now = time.time()
    
    # 1. Remove dead requests (score < now)
    await r.zremrangebyscore(zset_key, "-inf", now)
    
    # 2. Check current active count
    count = await r.zcard(zset_key)
    if count >= max_concurrency:
        return False
        
    # 3. Add current request with expiry
    expiry = now + ttl_seconds
    await r.zadd(zset_key, {request_id: expiry})
    await r.expire(zset_key, ttl_seconds + 5)
    
    return True

async def release_concurrency(key_id: str, request_id: str) -> None:
    """Removes a request from the concurrency ZSET."""
    r = redis_manager.get_client()
    zset_key = f"viridis:inflight:{key_id}"
    await r.zrem(zset_key, request_id)
