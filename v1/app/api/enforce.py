import hashlib
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.decision import make_decision
from app.config import settings
from app.db.session import get_db

router = APIRouter(prefix="/v1", tags=["Enforcement"])

class AdmitRequest(BaseModel):
    endpoint_path: str
    method: str
    client_ip: Optional[str] = None
    trace_id: Optional[str] = None



import asyncio

def _hash_key_sync(raw_key: str, pepper: str) -> str:
    return hashlib.sha256(f"{raw_key}{pepper}".encode()).hexdigest()


@router.post("/admit")
async def admit(
    req: AdmitRequest,
    request: Request,
    authorization: str = Header(None),
    db: AsyncSession = Depends(get_db)
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    
    raw_key = authorization.split(" ")[1]
    
    # Hash key with pepper asynchronously in a worker thread
    key_hash = await asyncio.to_thread(_hash_key_sync, raw_key, settings.server_pepper)
    
    trace_id = req.trace_id or str(uuid.uuid4())
    client_ip = req.client_ip or request.client.host if request.client else "unknown"
    
    decision = await make_decision(
        key_hash=key_hash,
        endpoint_path=req.endpoint_path,
        method=req.method,
        client_ip=client_ip,
        request_id=trace_id,
        db=db
    )
    
    # HTTP Status mapping
    status_code = 200
    if decision["decision"] == "THROTTLE":
        status_code = 429
    elif decision["decision"] == "DENY":
        status_code = 403
    elif decision["decision"] == "CHALLENGE":
        status_code = 202
        
    return decision
