import asyncio
import logging
from typing import Dict, Any

from app.core.redis import redis_manager
from app.ml.feature_aggregator import add_event

import os

logger = logging.getLogger(__name__)

STREAM_NAME = "viridis:audit:stream"
WAF_GROUP_NAME = "viridis:waf_cg"

async def setup_waf_consumer_group() -> None:
    r = redis_manager.get_client()
    try:
        await r.xgroup_create(STREAM_NAME, WAF_GROUP_NAME, id="0", mkstream=True)
    except Exception as e:
        if "BUSYGROUP" not in str(e):
            logger.error(f"Error creating WAF consumer group: {e}")

def validate_event(event: Dict[str, Any]) -> bool:
    required_keys = {"client_ip", "endpoint_path", "method"}
    if not all(event.get(k) is not None for k in required_keys):
        return False
    return True

async def run_waf_consumer() -> None:
    """Consumes audit events for the WAF ML pipeline."""
    await setup_waf_consumer_group()
    r = redis_manager.get_client()
    consumer_name = f"waf-worker-{os.getpid()}"
    
    logger.info(f"Started WAF consumer worker {consumer_name}")
    
    while True:
        try:
            # Check Stream Lag
            try:
                stream_info = await r.xinfo_stream(STREAM_NAME)
                lag = stream_info.get(b'length', stream_info.get('length', 0))
                # xinfo_stream length isn't exact lag for a consumer group, but serves as a rough proxy for uncompacted stream size
                # To get exact lag, we would check the group's pending or last-delivered-id. 
                # For simplicity as requested, we check stream length or use a try-except.
                if lag > 10000:
                    logger.warning(f"WAF consumer lagging: {lag} events in stream")
            except Exception:
                pass
            
            messages = await r.xreadgroup(WAF_GROUP_NAME, consumer_name, {STREAM_NAME: ">"}, count=100, block=2000)
            if not messages:
                continue
                
            stream_name, records = messages[0]
            message_ids = []
            
            for msg_id, payload in records:
                # Decoded payload is dict of bytes to bytes or string to string
                decoded_payload = {
                    k.decode('utf-8', errors='ignore') if isinstance(k, bytes) else k:
                    v.decode('utf-8', errors='ignore') if isinstance(v, bytes) else v
                    for k, v in payload.items()
                }
                
                if validate_event(decoded_payload):
                    await add_event(decoded_payload)
                    
                message_ids.append(msg_id)
                
            if message_ids:
                await r.xack(STREAM_NAME, WAF_GROUP_NAME, *message_ids)
                
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.exception(f"WAF consumer error: {e}")
            await asyncio.sleep(1)
