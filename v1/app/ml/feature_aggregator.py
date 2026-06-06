import time
import logging
from typing import Dict, Any, List
import asyncio
import heapq
import json
from app.core.redis import redis_manager

logger = logging.getLogger(__name__)

# Feature window state
# Key: client_ip -> incremental state dict
_ip_windows: Dict[str, Dict[str, Any]] = {}
_timestamp_heap = []

WINDOW_SIZE_SECONDS = 300  # 5 minutes
MAX_ACTIVE_IPS = 100_000

def cleanup_stale_windows() -> None:
    current_time = time.time()
    stale_cutoff = current_time - 600  # 10 minutes grace period
    
    while _timestamp_heap:
        oldest_ts, oldest_ip = _timestamp_heap[0]
        if oldest_ts < stale_cutoff:
            heapq.heappop(_timestamp_heap)
            state = _ip_windows.get(oldest_ip)
            if state and state.get("last_request_ts", 0) < stale_cutoff:
                del _ip_windows[oldest_ip]
        else:
            break

async def cleanup_task() -> None:
    """Background task to periodically clean up stale windows."""
    while True:
        try:
            cleanup_stale_windows()
        except Exception as e:
            logger.error(f"Cleanup task error: {e}")
            await asyncio.sleep(60)
        await asyncio.sleep(60)

def normalize_route(route: str) -> str:
    """Canonicalize routes by stripping query params and trailing slashes."""
    if "?" in route:
        route = route.split("?")[0]
    if route.endswith("/") and len(route) > 1:
        route = route.rstrip("/")
    return route.lower()

def _init_state() -> Dict[str, Any]:
    return {
        "request_count": 0,
        "error_401_count": 0,
        "error_403_count": 0,
        "error_404_count": 0,
        "error_5xx_count": 0,
        "distinct_endpoints": set(),
        "distinct_methods": set(),
        "temporal_ewma": 0.0,
        "temporal_ewma_var": 0.0,
        "last_request_ts": 0.0,
    }

def compute_features(client_ip: str, current_time: float) -> Dict[str, Any]:
    """Computes features for a client IP based on the sliding window."""
    state = _ip_windows.get(client_ip)
    if not state:
        return {}
        
    request_count = state["request_count"]
    error_count = state["error_401_count"] + state["error_403_count"] + state["error_404_count"] + state["error_5xx_count"]
    
    error_density = error_count / request_count if request_count > 0 else 0.0
    endpoint_spread = len(state["distinct_endpoints"])
    method_diversity = len(state["distinct_methods"])
    temporal_variance = state["temporal_ewma_var"]

    return {
        "client_ip": client_ip,
        "request_count": request_count,
        "error_density": error_density,
        "endpoint_spread": endpoint_spread,
        "method_diversity": method_diversity,
        "temporal_variance": temporal_variance,
        "window_end": current_time
    }

async def add_event(event: Dict[str, Any]) -> None:
    """Adds a validated event to the aggregation window."""
    client_ip = event.get("client_ip")
    if not client_ip:
        return
        
    if client_ip not in _ip_windows:
        _ip_windows[client_ip] = _init_state()
        now_ts = time.time()
        heapq.heappush(_timestamp_heap, (now_ts, client_ip))
        
    state = _ip_windows[client_ip]
    state["request_count"] += 1
    
    # Track errors based on decision or status
    decision = event.get("decision", "allow").lower()
    if decision != "allow":
        state["error_403_count"] += 1
    else:
        status = str(event.get("status_code", "200"))
        if status == "401":
            state["error_401_count"] += 1
        elif status == "403":
            state["error_403_count"] += 1
        elif status == "404":
            state["error_404_count"] += 1
        elif status.startswith("5"):
            state["error_5xx_count"] += 1
            
    if len(state["distinct_endpoints"]) < 100:
        state["distinct_endpoints"].add(normalize_route(event.get("endpoint_path", "")))
    state["distinct_methods"].add(event.get("method", ""))
    
    now_ts = time.time()
    if state["last_request_ts"] > 0:
        delta = now_ts - state["last_request_ts"]
        alpha = 0.1
        state["temporal_ewma"] = (alpha * delta) + (1 - alpha) * state["temporal_ewma"]
        state["temporal_ewma_var"] = (alpha * (delta - state["temporal_ewma"])**2) + (1 - alpha) * state["temporal_ewma_var"]
    state["last_request_ts"] = now_ts
    
    feat = compute_features(client_ip, now_ts)
    if feat:
        r = redis_manager.get_client()
        await r.setex(f"viridis:waf:features:{client_ip}", 600, json.dumps(feat))
    
def get_active_windows() -> int:
    return len(_ip_windows)

def get_all_features() -> List[Dict[str, Any]]:
    """Returns the computed features for all active windows."""
    current_time = time.time()
    features = []
    # Using list() to avoid dictionary changed size during iteration
    for ip in list(_ip_windows.keys()):
        feat = compute_features(ip, current_time)
        if feat:
            features.append(feat)
    return features
