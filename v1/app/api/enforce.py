import asyncio
import hashlib
import uuid
from fastapi.responses import JSONResponse
from fastapi import APIRouter, Depends, Header, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Literal, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.decision import make_decision
from app.config import settings
from app.db.session import get_db
from app.core.policy_cache import get_policy
from app.core.concurrency import release_concurrency
from app.core.redis import redis_manager
from app.services.payload_scanner import scan_payload
from app.core.metrics import (
    emit_block,
    viridis_processing_latency_seconds,
    viridis_requests_total
)
from pytricia import PyTricia
import time
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["Enforcement"])

class AdmitRequest(BaseModel):
    endpoint_path: str = Field(..., max_length=2000)
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"]
    client_ip: Optional[str] = None
    trace_id: Optional[str] = None
    payload: Optional[str] = None

def _hash_key_sync(raw_key: str, pepper: str) -> str:
    return hashlib.sha256(f"{raw_key}{pepper}".encode()).hexdigest()

class CIDRAllowlistCache:
    def __init__(self):
        self._tree = PyTricia()
        self._lock = asyncio.Lock()
        self._last_update = 0.0
    
    async def is_in_allowlist(self, redis_client, ip: str) -> bool:
        now = time.time()
        if now > self._last_update:
            async with self._lock:
                if time.time() > self._last_update:
                    try:
                        self._tree = PyTricia()
                        cidrs = await redis_client.smembers("viridis:waf:cidr_allowlist")
                        for cidr in cidrs:
                            self._tree.insert(cidr, True)
                        self._last_update = time.time() + 10
                    except Exception as e:
                        logger.error(f"Error refreshing CIDR allowlist: {e}")
        
        return self._tree.has_key(ip)

_cidr_cache = CIDRAllowlistCache()

def parse_api_key(auth_header: str) -> str:
    if not auth_header or not auth_header.startswith("Bearer "):
        raise ValueError("Missing or invalid Authorization header")
    parts = auth_header.split(maxsplit=1)
    if len(parts) < 2 or not parts[1]:
        raise ValueError("Empty bearer token")
    return parts[1]


@router.post("/admit")
async def admit(
    req: AdmitRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    authorization: str = Header(None),
    db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    start_time = time.time()
    status_code = 500
    
    try:
        try:
            raw_key = parse_api_key(authorization)
        except ValueError as e:
            raise HTTPException(status_code=401, detail=str(e))
        
        # Hash key with pepper synchronously
        key_hash = _hash_key_sync(raw_key, settings.server_pepper)
        
        trace_id = req.trace_id or str(uuid.uuid4())
        client_ip = req.client_ip or (request.client.host if request.client else "unknown")
        
        async def check_waf_blocklist() -> bool:
            try:
                r = redis_manager.get_client()
                if client_ip != "unknown":
                    if await _cidr_cache.is_in_allowlist(r, client_ip):
                        return False
                    
                if client_ip != "unknown":
                    return await r.sismember("viridis:waf:blocklist", client_ip)
            except Exception:
                # PRD: Fail open if Redis degrades
                pass
            return False
            
        waf_blocked = await check_waf_blocklist()
        
        if waf_blocked:
            emit_block(reason="ML_WAF")
            status_code = 403
            return JSONResponse(
                content={
                    "decision": "DENY",
                    "reason_code": "ML_WAF_BLOCK",
                    "processing_ms": 0.0,
                    "tokens_consumed": 0,
                    "concurrency_count": 0,
                    "headers": {"X-Viridis-Blocked-By": "ML_WAF"}
                },
                status_code=403,
                headers={"X-Viridis-Blocked-By": "ML_WAF"}
            )
            
        if req.payload:
            is_safe, reason = scan_payload(req.payload)
            if not is_safe:
                emit_block(reason=f"L7_{reason}")
                status_code = 403
                return JSONResponse(
                    content={
                        "decision": "DENY",
                        "reason_code": reason,
                        "processing_ms": 0.0,
                        "tokens_consumed": 0,
                        "concurrency_count": 0,
                        "headers": {"X-Viridis-Blocked-By": "L7_INSPECTION"}
                    },
                    status_code=403,
                    headers={"X-Viridis-Blocked-By": "L7_INSPECTION"}
                )
            
        decision = await make_decision(
            key_hash=key_hash,
            endpoint_path=req.endpoint_path,
            method=req.method,
            client_ip=client_ip,
            request_id=trace_id,
            db=db,
            background_tasks=background_tasks
        )
        
        # HTTP Status mapping
        status_code = 200
        if decision["decision"] == "THROTTLE":
            status_code = 429
        elif decision["decision"] == "DENY":
            status_code = 403
        elif decision["decision"] == "CHALLENGE":
            status_code = 202
            
        return JSONResponse(content=decision, status_code=status_code)
    finally:
        latency = time.time() - start_time
        viridis_processing_latency_seconds.observe(latency)
        viridis_requests_total.labels(method=req.method, endpoint=req.endpoint_path, status=status_code).inc()

class ReleaseRequest(BaseModel):
    trace_id: str

@router.post("/release")
async def release(
    req: ReleaseRequest,
    authorization: str = Header(None),
    db: AsyncSession = Depends(get_db)
) -> dict:
    try:
        raw_key = parse_api_key(authorization)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    key_hash = _hash_key_sync(raw_key, settings.server_pepper)
    
    policy = await get_policy(key_hash, db)
    if not policy:
        raise HTTPException(status_code=403, detail="Invalid API Key")
        
    await release_concurrency(policy["key_id"], req.trace_id)
    return {"status": "ok", "message": "Concurrency slot released"}
