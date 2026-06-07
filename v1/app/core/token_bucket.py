import time
from typing import Tuple

from app.core.redis import redis_manager

async def check_token_bucket(
    key_id: str,
    capacity: int,
    refill_rate: float,
    tokens_to_consume: float = 1.0,
) -> Tuple[bool, float, int]:
    """
    Executes the token bucket Lua script in Redis.
    
    Returns:
        Tuple[allowed: bool, tokens_remaining: float, retry_after: int]
    """
    script = redis_manager.get_script("token_bucket")
    now = time.time()
    
    # Lua script returns [allowed (1/0), remaining_tokens, retry_after]
    result = await script(
        keys=[f"viridis:bucket:{key_id}"],
        args=[capacity, refill_rate, tokens_to_consume, now]
    )
    
    allowed = bool(result[0])
    remaining = float(result[1])
    retry_after = int(result[2])
    
    return allowed, remaining, retry_after
