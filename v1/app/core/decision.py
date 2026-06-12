import time
from typing import Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.policy_cache import get_policy
from app.core.token_bucket import check_token_bucket
from app.core.sliding_window import check_sliding_window
from app.core.concurrency import check_and_acquire_concurrency
from app.core.redis import redis_manager
from app.services.audit import publish_audit_event
import asyncio

async def make_decision(
    key_hash: str,
    endpoint_path: str,
    method: str,
    client_ip: str,
    request_id: str,
    db: AsyncSession
) -> Dict[str, Any]:
    """
    Orchestrates the fail-fast enforcement logic.
    Returns the structured response dict.
    """
    start_time = time.perf_counter()
    r = redis_manager.get_client()
    
    def finalize(decision: str, code: str, **kwargs: Any) -> Dict[str, Any]:
        processing_ms = round((time.perf_counter() - start_time) * 1000, 2)
        event = {
            "decision": decision,
            "reason_code": code,
            "processing_ms": processing_ms,
            "trace_id": request_id,
            "api_key_id": policy.get("key_id", "") if policy else "",
            "tenant_id": policy.get("tenant_id", "") if policy else "",
            "endpoint_path": endpoint_path,
            "method": method,
            "client_ip": client_ip,
            **kwargs
        }
        asyncio.create_task(publish_audit_event(event))
        
        return {
            "decision": decision,
            "reason_code": code,
            "processing_ms": processing_ms,
            "trace_id": request_id,
            **kwargs
        }

    # 1. Fetch Policy
    policy = await get_policy(key_hash, db)
    if not policy:
        return finalize("DENY", "KEY_INVALID")
    
    if policy["is_active"] != "true":
        return finalize("DENY", "KEY_REVOKED")
        
    expires_at = float(policy.get("expires_at", 0))
    if expires_at > 0 and time.time() > expires_at:
        return finalize("DENY", "KEY_EXPIRED")

    # 2. Hard Overrides
    override = policy.get("override", "NONE")
    if override == "HARD_DENY":
        return finalize("DENY", "HARD_OVERRIDE")
    if override == "HARD_ALLOW":
        return finalize("ALLOW", "HARD_OVERRIDE_ALLOW")

    key_id = policy["key_id"]

    # 3. Cooldown
    cooldown_key = f"viridis:cooldown:{key_id}"
    if await r.exists(cooldown_key):
        return finalize("DENY", "COOLDOWN_ACTIVE")

    # 4. Concurrency Guard
    max_concurrency = int(policy["max_concurrency"])
    acquired = await check_and_acquire_concurrency(key_id, max_concurrency, request_id)
    if not acquired:
        return finalize("THROTTLE", "CONCURRENCY_EXCEEDED")

    # 5. Token Bucket (Burst)
    burst_capacity = int(policy["burst_capacity"])
    burst_refill_rate = float(policy["burst_refill_rate"])
    
    # Simplified weight: assume weight = 1.0 for now
    tokens_to_consume = 1.0
    
    tb_allowed, tb_remaining, tb_retry = await check_token_bucket(
        key_id, burst_capacity, burst_refill_rate, tokens_to_consume
    )
    if not tb_allowed:
        return finalize("THROTTLE", "BURST_EXHAUSTED", retry_after_seconds=tb_retry)

    # 6. Sliding Window (Sustained)
    sustained_limit = int(policy["requests_per_minute"])
    sw_allowed, sw_remaining, sw_retry = await check_sliding_window(
        key_id, 60, sustained_limit, request_id
    )
    
    current_usage = sustained_limit - sw_remaining
    tenant_id = policy.get("tenant_id", "unknown")
    
    # Threshold Alert Logic
    if sustained_limit > 0:
        threshold_crossed = None
        if current_usage >= sustained_limit:
            threshold_crossed = "100"
        elif current_usage >= sustained_limit * 0.8:
            threshold_crossed = "80"
            
        if threshold_crossed:
            alert_key = f"viridis:alert:{tenant_id}:{threshold_crossed}"
            # Atomically set NX (only set if not exists), with 60s expiration
            is_new_alert = await r.set(alert_key, "1", nx=True, ex=60)
            if is_new_alert:
                from app.services.alert_manager import dispatch_quota_alert
                asyncio.create_task(dispatch_quota_alert(
                    tenant_id=tenant_id,
                    email="", # Configured implicitly or fetched if tenant details had email
                    threshold=threshold_crossed,
                    current_usage=current_usage,
                    limit=sustained_limit
                ))

    if not sw_allowed:
        return finalize("THROTTLE", "QUOTA_EXCEEDED", retry_after_seconds=sw_retry)

    # 7. Abuse Heuristics (Impossible burst)
    # Check if >50% quota consumed in <2s (naive implementation)
    if sw_remaining < (sustained_limit / 2):
        # We could add an atomic fast-counter here to check the 2s burst rate
        pass

    # Success
    return finalize("ALLOW", "OK", tokens_remaining=tb_remaining, concurrency_remaining=(max_concurrency - 1))
