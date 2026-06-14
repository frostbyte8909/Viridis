import pytest
import time
from app.core.token_bucket import check_token_bucket
from app.core.sliding_window import check_sliding_window

@pytest.mark.asyncio
async def test_token_bucket_allows_under_limit(test_client, redis_client):
    """Token bucket allows requests under limit."""
    api_key = "test_token_bucket_key"
    
    # Initialize token bucket (capacity 10, refill 1/s, consuming 1)
    allowed, remaining, retry = await check_token_bucket(
        api_key, 10, 1.0, 1.0
    )
    
    # First request should succeed, 9 tokens remaining
    assert allowed is True
    assert remaining == 9.0

@pytest.mark.asyncio
async def test_token_bucket_denies_over_limit(test_client, redis_client):
    """Token bucket denies requests over limit."""
    api_key = "test_token_bucket_over"
    
    # Send 2 requests (capacity 2)
    for _ in range(2):
        allowed, remaining, retry = await check_token_bucket(
            api_key, 2, 1.0, 1.0
        )
        assert allowed is True
    
    # 3rd request should fail
    allowed, remaining, retry = await check_token_bucket(
        api_key, 2, 1.0, 1.0
    )
    assert allowed is False
    assert retry > 0

@pytest.mark.asyncio
async def test_sliding_window_counts_requests(test_client, redis_client):
    """Sliding window tracks request count."""
    api_key = "test_sliding_window"
    
    # First 5 requests succeed
    for i in range(5):
        allowed, remaining, retry = await check_sliding_window(
            api_key, 60, 5, f"req-{i}"
        )
        assert allowed is True
        assert remaining == 5 - (i + 1)
    
    # 6th request should fail
    allowed, remaining, retry = await check_sliding_window(
        api_key, 60, 5, "req-6"
    )
    assert allowed is False
    assert retry > 0
