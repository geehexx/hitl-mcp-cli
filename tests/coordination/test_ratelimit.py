"""Tests for rate limiting."""


import pytest

from hitl_mcp_cli.coordination.ratelimit import RateLimiter, TokenBucket
from hitl_mcp_cli.coordination.schema import RateLimitExceeded


def test_token_bucket_consume():
    """Test token bucket consumption."""
    import time

    bucket = TokenBucket(capacity=10, refill_rate=1.0, tokens=10, last_refill=time.time())

    assert bucket.consume(5)
    assert bucket.tokens == 5

    assert bucket.consume(5)
    assert bucket.tokens < 0.001  # Nearly zero (account for floating point and refill)

    assert not bucket.consume(1)  # No tokens left


def test_token_bucket_refill():
    """Test token refill over time."""
    import time

    bucket = TokenBucket(capacity=10, refill_rate=10.0, tokens=0, last_refill=time.time())

    # Wait for refill
    time.sleep(0.5)

    bucket.refill()

    # Should have ~5 tokens (10 tokens/sec * 0.5 sec)
    assert bucket.tokens >= 4
    assert bucket.tokens <= 6


@pytest.mark.asyncio
async def test_rate_limiter_allows_within_limit():
    """Test rate limiter allows requests within limit."""
    limiter = RateLimiter(default_per_agent_limit=100)

    # Should succeed
    result = await limiter.check("agent-a")
    assert result is True


@pytest.mark.asyncio
async def test_rate_limiter_blocks_over_limit():
    """Test rate limiter blocks requests over limit."""
    limiter = RateLimiter(default_per_agent_limit=2)

    # First two should succeed
    await limiter.check("agent-a")
    await limiter.check("agent-a")

    # Third should fail
    with pytest.raises(RateLimitExceeded) as exc_info:
        await limiter.check("agent-a")

    assert "2/min" in str(exc_info.value)


@pytest.mark.asyncio
async def test_rate_limiter_global_limit():
    """Test global rate limit across agents."""
    limiter = RateLimiter(default_per_agent_limit=100, global_limit=3)

    # 3 requests across different agents should succeed
    await limiter.check("agent-a")
    await limiter.check("agent-b")
    await limiter.check("agent-c")

    # 4th should fail
    with pytest.raises(RateLimitExceeded) as exc_info:
        await limiter.check("agent-d")

    assert "global" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_rate_limiter_custom_limit():
    """Test custom per-agent limit."""
    limiter = RateLimiter(default_per_agent_limit=100)
    limiter.set_agent_limit("agent-a", 2)

    # Agent A limited to 2
    await limiter.check("agent-a")
    await limiter.check("agent-a")

    with pytest.raises(RateLimitExceeded):
        await limiter.check("agent-a")

    # Agent B should have default limit
    for _ in range(10):
        await limiter.check("agent-b")  # Should not raise


@pytest.mark.asyncio
async def test_rate_limiter_status():
    """Test getting rate limit status."""
    limiter = RateLimiter(default_per_agent_limit=10)

    status = await limiter.get_status("agent-a")

    assert status["agent_id"] == "agent-a"
    assert status["limit_per_minute"] == 10
    assert status["available_tokens"] > 0


@pytest.mark.asyncio
async def test_rate_limiter_reset():
    """Test resetting rate limits."""
    limiter = RateLimiter(default_per_agent_limit=1)

    # Exhaust limit
    await limiter.check("agent-a")

    with pytest.raises(RateLimitExceeded):
        await limiter.check("agent-a")

    # Reset
    await limiter.reset("agent-a")

    # Should work again
    result = await limiter.check("agent-a")
    assert result is True


@pytest.mark.asyncio
async def test_rate_limiter_reset_all():
    """Test resetting all rate limits."""
    limiter = RateLimiter(default_per_agent_limit=1, global_limit=2)

    # Exhaust both
    await limiter.check("agent-a")
    await limiter.check("agent-b")

    with pytest.raises(RateLimitExceeded):
        await limiter.check("agent-c")

    # Reset all
    await limiter.reset()

    # Should work again
    await limiter.check("agent-a")
    await limiter.check("agent-b")


def test_rate_limiter_stats():
    """Test rate limiter statistics."""
    limiter = RateLimiter(default_per_agent_limit=100, global_limit=1000)
    limiter.set_agent_limit("agent-special", 50)

    stats = limiter.get_stats()

    assert stats["global_limit"] == 1000
    assert stats["default_agent_limit"] == 100
    assert stats["custom_limits"] == 1
