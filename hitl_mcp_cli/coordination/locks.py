"""Distributed lock management for multi-agent coordination."""

import asyncio
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from .schema import LockQuotaExceeded


@dataclass
class Lock:
    """Lock metadata."""

    id: str
    name: str  # Resource being locked (e.g., "file:/path/to/file")
    held_by: str  # Agent ID
    acquired_at: float
    expires_at: float
    auto_release_seconds: int


class LockManager:
    """Manage distributed locks for coordination.

    Features:
    - Timeout-based acquisition (fail fast or wait)
    - Auto-release to prevent deadlocks
    - Per-agent lock quotas
    - Heartbeat extension (future)
    """

    MAX_LOCKS_PER_AGENT = 10  # Prevent lock hoarding

    def __init__(self):
        """Initialize lock manager."""
        self.locks: dict[str, Lock] = {}  # lock_name -> Lock
        self.lock_mutex: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self.agent_locks: dict[str, set[str]] = defaultdict(set)  # agent_id -> set of lock_names

        # Background task for auto-release
        self._cleanup_task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start background cleanup task."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self) -> None:
        """Stop background cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

    async def acquire(
        self, lock_name: str, agent_id: str, timeout_seconds: int = 30, auto_release_seconds: int = 300
    ) -> dict[str, Any]:
        """Acquire lock on resource.

        Args:
            lock_name: Resource identifier (e.g., "file:/path")
            agent_id: Agent requesting lock
            timeout_seconds: How long to wait (0 = fail immediately)
            auto_release_seconds: Auto-release after this duration

        Returns:
            {
                "acquired": bool,
                "lock_id": str | None,
                "held_by": str | None,
                "expires_at": float | None
            }

        Raises:
            LockQuotaExceeded: If agent already holds too many locks
        """
        # Check quota
        current_locks = len(self.agent_locks[agent_id])
        if current_locks >= self.MAX_LOCKS_PER_AGENT:
            raise LockQuotaExceeded(agent_id, current_locks, self.MAX_LOCKS_PER_AGENT)

        start_time = time.time()
        async with self.lock_mutex[lock_name]:
            # Try to acquire
            while True:
                # Check if lock is available or expired
                existing = self.locks.get(lock_name)
                if existing is None or time.time() >= existing.expires_at:
                    # Lock is available, acquire it
                    lock_id = str(uuid.uuid4())
                    lock = Lock(
                        id=lock_id,
                        name=lock_name,
                        held_by=agent_id,
                        acquired_at=time.time(),
                        expires_at=time.time() + auto_release_seconds,
                        auto_release_seconds=auto_release_seconds,
                    )
                    self.locks[lock_name] = lock
                    self.agent_locks[agent_id].add(lock_name)

                    return {
                        "acquired": True,
                        "lock_id": lock_id,
                        "held_by": agent_id,
                        "expires_at": lock.expires_at,
                    }

                # Lock held by someone else
                elapsed = time.time() - start_time
                if elapsed >= timeout_seconds:
                    # Timeout reached, fail
                    return {
                        "acquired": False,
                        "lock_id": None,
                        "held_by": existing.held_by if existing else None,
                        "expires_at": existing.expires_at if existing else None,
                    }

                # Wait a bit and retry
                await asyncio.sleep(0.1)

    async def release(self, lock_id: str, agent_id: str) -> dict[str, bool]:
        """Release a previously acquired lock.

        Args:
            lock_id: Lock ID from acquire
            agent_id: Agent releasing lock (must match acquirer)

        Returns:
            {"released": bool}

        Raises:
            ValueError: If lock doesn't exist or agent doesn't own it
        """
        # Find lock by ID
        lock_name = None
        for name, lock in self.locks.items():
            if lock.id == lock_id:
                lock_name = name
                break

        if not lock_name:
            raise ValueError(f"Lock {lock_id} not found")

        async with self.lock_mutex[lock_name]:
            lock = self.locks.get(lock_name)
            if not lock:
                raise ValueError(f"Lock {lock_id} not found")

            if lock.held_by != agent_id:
                raise ValueError(f"Lock {lock_id} is held by {lock.held_by}, not {agent_id}")

            # Release lock
            del self.locks[lock_name]
            self.agent_locks[agent_id].discard(lock_name)

            return {"released": True}

    async def release_all(self, agent_id: str) -> int:
        """Release all locks held by agent.

        Args:
            agent_id: Agent whose locks to release

        Returns:
            Number of locks released
        """
        lock_names = list(self.agent_locks[agent_id])
        count = 0

        for lock_name in lock_names:
            async with self.lock_mutex[lock_name]:
                lock = self.locks.get(lock_name)
                if lock and lock.held_by == agent_id:
                    del self.locks[lock_name]
                    count += 1

        self.agent_locks[agent_id].clear()
        return count

    async def get_lock_status(self, lock_name: str) -> dict[str, Any] | None:
        """Get lock status.

        Args:
            lock_name: Lock to query

        Returns:
            Lock metadata if held, None if available
        """
        lock = self.locks.get(lock_name)
        if not lock:
            return None

        # Check if expired
        if time.time() >= lock.expires_at:
            return None

        return {
            "lock_id": lock.id,
            "name": lock.name,
            "held_by": lock.held_by,
            "acquired_at": lock.acquired_at,
            "expires_at": lock.expires_at,
            "seconds_remaining": int(lock.expires_at - time.time()),
        }

    async def list_locks(self) -> list[dict[str, Any]]:
        """List all active locks.

        Returns:
            List of lock metadata
        """
        now = time.time()
        return [
            {
                "lock_id": lock.id,
                "name": lock.name,
                "held_by": lock.held_by,
                "acquired_at": lock.acquired_at,
                "expires_at": lock.expires_at,
                "seconds_remaining": int(lock.expires_at - now),
            }
            for lock in self.locks.values()
            if now < lock.expires_at
        ]

    async def _cleanup_loop(self) -> None:
        """Background task to clean up expired locks."""
        while True:
            try:
                await asyncio.sleep(10)  # Check every 10 seconds
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                # Log error but continue
                print(f"Error in lock cleanup: {e}")

    async def _cleanup_expired(self) -> None:
        """Remove expired locks."""
        now = time.time()
        expired = []

        for lock_name, lock in list(self.locks.items()):
            if now >= lock.expires_at:
                expired.append((lock_name, lock.held_by))

        for lock_name, agent_id in expired:
            async with self.lock_mutex[lock_name]:
                if lock_name in self.locks:  # Double-check still exists
                    del self.locks[lock_name]
                    self.agent_locks[agent_id].discard(lock_name)

    def get_stats(self) -> dict[str, Any]:
        """Get lock manager statistics.

        Returns:
            Statistics: active locks, agents with locks, etc.
        """
        return {
            "active_locks": len(self.locks),
            "agents_with_locks": len([locks for locks in self.agent_locks.values() if locks]),
        }
