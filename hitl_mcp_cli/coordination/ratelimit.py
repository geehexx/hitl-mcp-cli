"""Rate limiting for multi-agent coordination."""

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass

from .schema import RateLimitExceeded


@dataclass
class TokenBucket:
    """Token bucket for rate limiting.

    Implements token bucket algorithm with configurable capacity and refill rate.
    """

    capacity: int  # Maximum tokens
    refill_rate: float  # Tokens added per second
    tokens: float  # Current token count
    last_refill: float  # Last refill timestamp

    def refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill

        # Add tokens based on elapsed time
        new_tokens = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + new_tokens)
        self.last_refill = now

    def consume(self, count: int = 1) -> bool:
        """Try to consume tokens.

        Args:
            count: Number of tokens to consume

        Returns:
            True if tokens consumed, False if insufficient
        """
        self.refill()

        if self.tokens >= count:
            self.tokens -= count
            return True

        return False

    def get_available(self) -> int:
        """Get available token count.

        Returns:
            Number of available tokens
        """
        self.refill()
        return int(self.tokens)

    def get_wait_time(self, count: int = 1) -> float:
        """Get time to wait for tokens to be available.

        Args:
            count: Number of tokens needed

        Returns:
            Seconds to wait
        """
        self.refill()
        deficit = count - self.tokens

        if deficit <= 0:
            return 0.0

        return deficit / self.refill_rate


class RateLimiter:
    """Multi-agent rate limiter with per-agent and global limits."""

    def __init__(
        self,
        default_per_agent_limit: int = 100,  # requests per minute
        global_limit: int = 1000,  # total requests per minute
    ):
        """Initialize rate limiter.

        Args:
            default_per_agent_limit: Default requests per minute per agent
            global_limit: Global requests per minute across all agents
        """
        self.default_per_agent_limit = default_per_agent_limit
        self.global_limit = global_limit

        # Per-agent buckets
        self.agent_buckets: dict[str, TokenBucket] = {}

        # Global bucket
        self.global_bucket = TokenBucket(
            capacity=global_limit, refill_rate=global_limit / 60.0, tokens=global_limit, last_refill=time.time()
        )

        # Per-agent custom limits
        self.agent_limits: dict[str, int] = {}

        # Lock for thread safety
        self.lock = asyncio.Lock()

    def set_agent_limit(self, agent_id: str, limit: int) -> None:
        """Set custom rate limit for agent.

        Args:
            agent_id: Agent identifier
            limit: Requests per minute
        """
        self.agent_limits[agent_id] = limit

        # Update bucket if exists
        if agent_id in self.agent_buckets:
            bucket = self.agent_buckets[agent_id]
            bucket.capacity = limit
            bucket.refill_rate = limit / 60.0
            bucket.tokens = min(bucket.tokens, limit)

    def _get_agent_bucket(self, agent_id: str) -> TokenBucket:
        """Get or create token bucket for agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Token bucket for agent
        """
        if agent_id not in self.agent_buckets:
            limit = self.agent_limits.get(agent_id, self.default_per_agent_limit)
            self.agent_buckets[agent_id] = TokenBucket(
                capacity=limit, refill_rate=limit / 60.0, tokens=limit, last_refill=time.time()
            )

        return self.agent_buckets[agent_id]

    async def check(self, agent_id: str, operation: str = "request") -> bool:
        """Check if agent is within rate limits.

        Args:
            agent_id: Agent identifier
            operation: Operation type (for logging)

        Returns:
            True if within limits, raises RateLimitExceeded otherwise
        """
        async with self.lock:
            # Check global limit first
            if not self.global_bucket.consume(1):
                wait_time = self.global_bucket.get_wait_time(1)
                raise RateLimitExceeded(
                    agent_id=agent_id, limit=f"{self.global_limit}/min (global)"
                ).add_details(
                    wait_seconds=wait_time,
                    suggested_action=f"Wait {wait_time:.1f}s for global rate limit to refill",
                )

            # Check per-agent limit
            bucket = self._get_agent_bucket(agent_id)
            if not bucket.consume(1):
                # Refund global token
                self.global_bucket.tokens += 1

                wait_time = bucket.get_wait_time(1)
                limit = self.agent_limits.get(agent_id, self.default_per_agent_limit)
                raise RateLimitExceeded(agent_id=agent_id, limit=f"{limit}/min").add_details(
                    wait_seconds=wait_time, suggested_action=f"Wait {wait_time:.1f}s for rate limit to refill"
                )

            return True

    async def get_status(self, agent_id: str) -> dict[str, int | float]:
        """Get rate limit status for agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Status dict with available tokens and limits
        """
        async with self.lock:
            bucket = self._get_agent_bucket(agent_id)
            limit = self.agent_limits.get(agent_id, self.default_per_agent_limit)

            return {
                "agent_id": agent_id,
                "limit_per_minute": limit,
                "available_tokens": bucket.get_available(),
                "global_available": self.global_bucket.get_available(),
                "global_limit": self.global_limit,
            }

    async def reset(self, agent_id: str | None = None) -> None:
        """Reset rate limits.

        Args:
            agent_id: Agent to reset (None for all agents)
        """
        async with self.lock:
            if agent_id:
                if agent_id in self.agent_buckets:
                    bucket = self.agent_buckets[agent_id]
                    bucket.tokens = bucket.capacity
                    bucket.last_refill = time.time()
            else:
                # Reset all
                for bucket in self.agent_buckets.values():
                    bucket.tokens = bucket.capacity
                    bucket.last_refill = time.time()

                self.global_bucket.tokens = self.global_bucket.capacity
                self.global_bucket.last_refill = time.time()

    def get_stats(self) -> dict[str, int]:
        """Get rate limiter statistics.

        Returns:
            Statistics dict
        """
        return {
            "agents_tracked": len(self.agent_buckets),
            "global_limit": self.global_limit,
            "default_agent_limit": self.default_per_agent_limit,
            "custom_limits": len(self.agent_limits),
        }


# Helper to add details to RateLimitExceeded
class RateLimitExceeded(RateLimitExceeded):
    """Extended rate limit exception with details."""

    def add_details(self, **kwargs):
        """Add additional details."""
        self.details.update(kwargs)
        return self
