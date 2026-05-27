import asyncio
import logging
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import redis_manager
from app.db.session import AsyncSessionLocal
from app.models.db import AuditLog

logger = logging.getLogger(__name__)

STREAM_NAME = "viridis:audit:stream"
GROUP_NAME = "viridis:audit:group"
CONSUMER_NAME = "worker-1"

async def setup_consumer_group() -> None:
    r = redis_manager.get_client()
    try:
        await r.xgroup_create(STREAM_NAME, GROUP_NAME, id="0", mkstream=True)
    except Exception as e:
        if "BUSYGROUP" not in str(e):
            logger.error(f"Error creating consumer group: {e}")

async def batch_write_audit_logs(events: List[Dict[str, Any]]) -> None:
    async with AsyncSessionLocal() as session:
        for event in events:
            # We skip fields like tokens_consumed for simplicity if not in payload
            audit = AuditLog(
                decision_id=event.get("decision_id", ""),
                api_key_id=event.get("api_key_id", ""),
                tenant_id=event.get("tenant_id", ""),
                endpoint_path=event.get("endpoint_path", ""),
                method=event.get("method", ""),
                decision=event.get("decision", ""),
                reason_code=event.get("reason_code", ""),
                processing_ms=float(event.get("processing_ms", 0.0)),
                client_ip=event.get("client_ip", ""),
                trace_id=event.get("trace_id", "")
            )
            session.add(audit)
        try:
            await session.commit()
        except Exception as e:
            logger.error(f"Failed to write audit batch to DB: {e}")
            await session.rollback()
            raise

async def run_audit_consumer() -> None:
    """Runs continuously in the background to consume from Redis Streams."""
    await setup_consumer_group()
    r = redis_manager.get_client()
    
    logger.info("Started audit consumer worker")
    while True:
        try:
            # Read up to 100 events, block for 2 seconds max
            messages = await r.xreadgroup(GROUP_NAME, CONSUMER_NAME, {STREAM_NAME: ">"}, count=100, block=2000)
            if not messages:
                continue
                
            stream_name, records = messages[0]
            events = []
            message_ids = []
            
            for msg_id, payload in records:
                events.append(payload)
                message_ids.append(msg_id)
                
            if events:
                await batch_write_audit_logs(events)
                await r.xack(STREAM_NAME, GROUP_NAME, *message_ids)
                
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Audit consumer error: {e}")
            await asyncio.sleep(1)
