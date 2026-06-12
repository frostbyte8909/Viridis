import hashlib
import json
from typing import AsyncGenerator, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.db import AuditLog
from app.db.session import AsyncSessionLocal
import logging

logger = logging.getLogger(__name__)

async def generate_audit_export_stream(tenant_id: str, limit: int = 10000) -> AsyncGenerator[str, None]:
    """
    Yields JSON lines of audit logs with a rolling SHA-256 hash chain for integrity verification.
    """
    async with AsyncSessionLocal() as session:
        # Stream logs in chronological order
        query = (
            select(AuditLog)
            .where(AuditLog.tenant_id == tenant_id)
            .order_by(AuditLog.created_at.asc(), AuditLog.id.asc())
            .limit(limit)
        )
        
        # Use execution options for streaming if driver supports it (asyncpg does)
        result = await session.stream(query)
        
        previous_hash = "0" * 64  # Initial Genesis Hash
        
        async for row in result.scalars():
            record = {
                "id": str(row.id),
                "decision_id": row.decision_id,
                "api_key_id": str(row.api_key_id),
                "endpoint_path": row.endpoint_path,
                "method": row.method,
                "decision": row.decision,
                "reason_code": row.reason_code,
                "processing_ms": row.processing_ms,
                "client_ip": row.client_ip,
                "trace_id": row.trace_id,
                "created_at": row.created_at.isoformat()
            }
            
            record_json = json.dumps(record, sort_keys=True)
            
            # hash[i] = SHA256(record[i] + hash[i-1])
            current_hash = hashlib.sha256(f"{record_json}{previous_hash}".encode()).hexdigest()
            
            export_payload = {
                "record": record,
                "previous_hash": previous_hash,
                "hash": current_hash
            }
            
            previous_hash = current_hash
            
            yield json.dumps(export_payload) + "\n"

def verify_export_chain(export_lines: list[str]) -> bool:
    """
    Utility to verify the integrity of an offline exported JSONL hash chain.
    """
    previous_hash = "0" * 64
    for line_idx, line in enumerate(export_lines):
        if not line.strip():
            continue
            
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse line {line_idx}")
            return False
            
        record_json = json.dumps(payload["record"], sort_keys=True)
        expected_prev_hash = payload["previous_hash"]
        expected_hash = payload["hash"]
        
        if expected_prev_hash != previous_hash:
            logger.error(f"Hash chain broken at line {line_idx}: expected prev {previous_hash}, got {expected_prev_hash}")
            return False
            
        actual_hash = hashlib.sha256(f"{record_json}{previous_hash}".encode()).hexdigest()
        if actual_hash != expected_hash:
            logger.error(f"Hash mismatch at line {line_idx}: expected {expected_hash}, got {actual_hash}")
            return False
            
        previous_hash = actual_hash
        
    return True
