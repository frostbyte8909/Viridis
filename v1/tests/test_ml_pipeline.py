import pytest
import time
from app.ml.feature_aggregator import add_event, compute_features, _ip_windows, normalize_route

@pytest.mark.asyncio
async def test_error_density_calculates_correctly(redis_client):
    """error_density = (401 + 403 + 404 + 5xx) / total_requests."""
    client_ip = "203.0.113.10"
    
    # Clear state
    if client_ip in _ip_windows:
        del _ip_windows[client_ip]
        
    # Add events: 10 total, 3 errors (401, 403, 404)
    for status in [200, 200, 401, 200, 403, 200, 200, 404, 200, 200]:
        event = {
            "client_ip": client_ip,
            "status_code": status,
            "decision": "allow",
            "endpoint_path": "/v1/test",
            "method": "GET",
        }
        await add_event(event)
    
    # Get features directly from memory
    features = compute_features(client_ip, time.time())
    
    # Assert error_density = 3/10 = 0.3
    assert features["error_density"] == 0.3

@pytest.mark.asyncio
async def test_endpoint_spread_counts_distinct_routes(redis_client):
    """endpoint_spread = number of distinct routes canonicalized."""
    client_ip = "203.0.113.11"
    
    if client_ip in _ip_windows:
        del _ip_windows[client_ip]
        
    # Add events: 5 requests, 3 distinct routes
    for route in ["/v1/a", "/v1/b/", "/v1/a?query=1", "/v1/c", "/v1/b"]:
        event = {
            "client_ip": client_ip,
            "status_code": 200,
            "decision": "allow",
            "endpoint_path": route,
            "method": "GET",
        }
        await add_event(event)
    
    features = compute_features(client_ip, time.time())
    
    # distinct routes normalized should be /v1/a, /v1/b, /v1/c -> 3
    assert features["endpoint_spread"] == 3

def test_normalize_route():
    assert normalize_route("/v1/test/") == "/v1/test"
    assert normalize_route("/v1/test?q=1") == "/v1/test"
    assert normalize_route("/V1/TEST/") == "/v1/test"
