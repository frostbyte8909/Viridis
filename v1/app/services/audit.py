import json
import logging
from typing import Dict, Any
from app.core.redis import redis_manager

logger = logging.getLogger(__name__)

STREAM_NAME = "viridis:audit:stream"

async def publish_audit_event(event: Dict[str, Any]) -> None:
    """
    Publishes an audit event to a Redis Stream asynchronously.
    Fails silently (with log) to protect the hot path.
    """
    r = redis_manager.get_client()
    try:
        # Convert all values to strings for Redis Hash format required by Streams
        payload = {k: str(v) for k, v in event.items()}
        await r.xadd(STREAM_NAME, payload)
    except Exception as e:
        logger.error(f"Failed to publish audit event to stream: {e}")
