import hashlib
import json
from typing import AsyncGenerator, Dict, Any
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.admin import require_admin_token
from app.db.session import get_db
from app.models.db import AuditLog

router = APIRouter(prefix="/admin/audit", tags=["Audit"])

async def stream_audit_logs(db: AsyncSession, tenant_id: str, start: datetime, end: datetime) -> AsyncGenerator[str, None]:
    """
    Streams audit logs using server-side cursors and builds a SHA-256 hash chain.
    """
    query = select(AuditLog).where(
        AuditLog.tenant_id == uuid.UUID(tenant_id),
        AuditLog.created_at >= start,
        AuditLog.created_at <= end
    ).order_by(AuditLog.id.asc())

    # We use stream() to fetch rows iteratively (server-side cursor context)
    # Note: asyncpg supports server-side cursors naturally when using `stream()`
    result = await db.stream(query)

    prev_hash = "0" * 64
    
    async for row in result.scalars():
        row_dict = {
            "id": row.id,
            "decision_id": str(row.decision_id),
            "api_key_id": str(row.api_key_id),
            "tenant_id": str(row.tenant_id),
            "endpoint_path": row.endpoint_path,
            "method": row.method,
            "decision": row.decision,
            "reason_code": row.reason_code,
            "processing_ms": float(row.processing_ms),
            "created_at": row.created_at.isoformat(),
            "prev_hash": prev_hash
        }
        
        # Serialize deterministically
        row_json = json.dumps(row_dict, sort_keys=True)
        current_hash = hashlib.sha256(row_json.encode('utf-8')).hexdigest()
        
        row_dict["hash"] = current_hash
        prev_hash = current_hash
        
        # Yield NDJSON line
        yield json.dumps(row_dict) + "\n"


@router.get("/export", dependencies=[Depends(require_admin_token)])
async def export_audit_log(
    tenant_id: str,
    start: datetime,
    end: datetime,
    db: AsyncSession = Depends(get_db)
) -> StreamingResponse:
    """
    Exports a cryptographically verified hash-chained audit log.
    Uses NDJSON to stream large volumes of data securely.
    """
    return StreamingResponse(
        stream_audit_logs(db, tenant_id, start, end),
        media_type="application/x-ndjson",
        headers={
            "Content-Disposition": f"attachment; filename=audit_{tenant_id}.ndjson"
        }
    )

@router.post("/verify", dependencies=[Depends(require_admin_token)])
async def verify_audit_log(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Verifies the integrity of an exported NDJSON hash chain.
    """
    prev_hash = "0" * 64
    line_number = 0
    
    # Read line by line to support huge files
    while True:
        line = await file.read(65536) # Read chunks, wait NDJSON needs readline
        if not line:
            break
        # Fast streaming by splitting lines
        # In a production scenario, we use asynchronous file line iteration
        
    # Simplified line iteration for memory safety
    await file.seek(0)
    buffer = b""
    while chunk := await file.read(65536):
        buffer += chunk
        while b"\n" in buffer:
            line, buffer = buffer.split(b"\n", 1)
            if not line.strip():
                continue
                
            line_number += 1
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail=f"Invalid JSON at line {line_number}")
                
            stored_hash = row.pop("hash", None)
            if not stored_hash:
                raise HTTPException(status_code=400, detail=f"Missing hash at line {line_number}")
                
            if row.get("prev_hash") != prev_hash:
                return {"status": "INVALID", "detail": f"Chain broken at line {line_number}. Prev hash mismatch."}
                
            recomputed_hash = hashlib.sha256(json.dumps(row, sort_keys=True).encode('utf-8')).hexdigest()
            if recomputed_hash != stored_hash:
                return {"status": "INVALID", "detail": f"Tampering detected at line {line_number}. Hash mismatch."}
                
            prev_hash = stored_hash
            
    return {"status": "VALID", "detail": f"Verified {line_number} records successfully."}
