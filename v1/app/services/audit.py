import logging
from typing import Dict, Any
from app.core.redis import redis_manager
from redis.exceptions import RedisError
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

STREAM_NAME = "viridis:audit:stream"

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5), reraise=True)
async def _do_publish(r, payload):
    await r.xadd(STREAM_NAME, payload, maxlen=100000)

async def publish_audit_event(event: Dict[str, Any]) -> None:
    """
    Publishes an audit event to a Redis Stream asynchronously.
    Fails silently (with log) to protect the hot path.
    Retries up to 3 times before failing.
    """
    r = redis_manager.get_client()
    try:
        # Convert all values to strings for Redis Hash format required by Streams
        payload = {k: str(v) for k, v in event.items()}
        await _do_publish(r, payload)
    except RedisError as e:
        logger.error(f"Failed to publish audit event to stream after retries: {e}")
