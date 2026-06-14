import time
from typing import Tuple

from app.core.redis import redis_manager

async def check_sliding_window(
    key_id: str,
    window_seconds: int,
    limit: int,
    request_id: str,
) -> Tuple[bool, int, int]:
    """
    Executes the sliding window Lua script in Redis.
    
    Returns:
        Tuple[allowed: bool, current_count: int, retry_after: int]
    """
    script = redis_manager.get_script("sliding_window")
    now = time.time()
    
    # Lua script returns [allowed (1/0), count_or_remaining, retry_after]
    # If allowed (1), index 1 is remaining quota.
    # If denied (0), index 1 is current count in window.
    result = await script(
        keys=[f"viridis:window:{key_id}"],
        args=[window_seconds, limit, now, request_id]
    )
    
    allowed = bool(result[0])
    val = int(result[1])
    retry_after = int(result[2])
    
    return allowed, val, retry_after
