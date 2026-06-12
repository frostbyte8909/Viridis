from typing import List, Dict, Any
import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.admin import require_admin_token
from app.core.redis import redis_manager
from app.ml.scorer import get_thresholds, set_thresholds
import app.ml.trainer as trainer

router = APIRouter(prefix="/admin/waf", tags=["WAF Admin"], dependencies=[Depends(require_admin_token)])

@router.get("/model/status")
async def get_model_status() -> Dict[str, Any]:
    r = redis_manager.get_client()
    # Try fetching from Redis first if process just started, otherwise memory
    meta = await r.hgetall("viridis:waf:model:current")
    if meta:
        decoded = {
            k.decode('utf-8') if isinstance(k, bytes) else k:
            v.decode('utf-8') if isinstance(v, bytes) else v
            for k, v in meta.items()
        }
        if "sample_count" in decoded:
            decoded["sample_count"] = int(decoded["sample_count"])
        if "mean_anomaly_score" in decoded:
            decoded["mean_anomaly_score"] = float(decoded["mean_anomaly_score"])
        return decoded
    return trainer.model_metadata

@router.get("/blocked")
async def list_blocked_ips() -> List[Dict[str, Any]]:
    r = redis_manager.get_client()
    blocked_ips = await r.smembers("viridis:waf:blocklist")
    
    if not blocked_ips:
        return []
        
    blocked_ips_list = list(blocked_ips)
    pipe = r.pipeline()
    for ip in blocked_ips_list:
        pipe.get(f"viridis:waf:blockmeta:{ip}")
        pipe.ttl(f"viridis:waf:blockmeta:{ip}")
        
    results = await pipe.execute()
    
    result = []
    ips_to_remove = []
    for i in range(0, len(results), 2):
        meta_raw = results[i]
        ttl = results[i + 1]
        ip = blocked_ips_list[i // 2]
        
        meta = json.loads(meta_raw) if meta_raw else {}
        if ttl <= 0 and not meta_raw:
            ips_to_remove.append(ip)
            continue
            
        result.append({
            "ip": ip,
            "ttl": ttl,
            "metadata": meta
        })
        
    if ips_to_remove:
        await r.srem("viridis:waf:blocklist", *ips_to_remove)
        
    return result

class UnblockRequest(BaseModel):
    ip: str
    reason: str

@router.post("/unblock")
async def unblock_ip(req: UnblockRequest) -> Dict[str, str]:
    r = redis_manager.get_client()
    await r.srem("viridis:waf:blocklist", req.ip)
    await r.delete(f"viridis:waf:blockmeta:{req.ip}")
    # Log audit event
    audit_event = {
        "action": "unblock",
        "ip": req.ip,
        "reason": req.reason
    }
    await r.xadd("viridis:waf:admin:audit", audit_event)
    return {"status": "ok", "message": f"Unblocked {req.ip}"}

class ThresholdsUpdate(BaseModel):
    watch_threshold: float
    block_threshold: float
    reason: str

@router.get("/thresholds")
async def get_current_thresholds() -> Dict[str, float]:
    return await get_thresholds()

@router.put("/thresholds")
async def update_thresholds(req: ThresholdsUpdate) -> Dict[str, str]:
    await set_thresholds(req.watch_threshold, req.block_threshold)
    r = redis_manager.get_client()
    audit_event = {
        "action": "update_thresholds",
        "watch_threshold": str(req.watch_threshold),
        "block_threshold": str(req.block_threshold),
        "reason": req.reason
    }
    await r.xadd("viridis:waf:admin:audit", audit_event)
    return {"status": "ok"}

class CidrAllowlistUpdate(BaseModel):
    action: str  # "add" or "remove"
    cidr: str
    reason: str

@router.get("/cidr-allowlist")
async def get_cidr_allowlist() -> List[str]:
    r = redis_manager.get_client()
    cidrs = await r.smembers("viridis:waf:cidr_allowlist")
    return list(cidrs)

@router.post("/cidr-allowlist")
async def update_cidr_allowlist(req: CidrAllowlistUpdate) -> Dict[str, str]:
    r = redis_manager.get_client()
    if req.action == "add":
        await r.sadd("viridis:waf:cidr_allowlist", req.cidr)
    elif req.action == "remove":
        await r.srem("viridis:waf:cidr_allowlist", req.cidr)
    else:
        raise HTTPException(status_code=400, detail="Action must be 'add' or 'remove'")
        
    audit_event = {
        "action": f"cidr_allowlist_{req.action}",
        "cidr": req.cidr,
        "reason": req.reason
    }
    await r.xadd("viridis:waf:admin:audit", audit_event)
    return {"status": "ok"}
