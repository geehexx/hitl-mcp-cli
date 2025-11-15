"""Tests for coordination locks."""

import asyncio

import pytest

from hitl_mcp_cli.coordination.locks import LockManager
from hitl_mcp_cli.coordination.schema import LockQuotaExceeded


@pytest.mark.asyncio
async def test_acquire_lock():
    """Test acquiring a lock."""
    manager = LockManager()

    result = await manager.acquire("resource-1", "agent-a", timeout_seconds=0)

    assert result["acquired"] is True
    assert result["lock_id"] is not None
    assert result["held_by"] == "agent-a"


@pytest.mark.asyncio
async def test_lock_prevents_concurrent_access():
    """Test that lock prevents concurrent access."""
    manager = LockManager()

    # Agent A acquires lock
    lock1 = await manager.acquire("resource-1", "agent-a", timeout_seconds=0)
    assert lock1["acquired"] is True

    # Agent B tries to acquire same lock (should fail immediately)
    lock2 = await manager.acquire("resource-1", "agent-b", timeout_seconds=0)
    assert lock2["acquired"] is False
    assert lock2["held_by"] == "agent-a"


@pytest.mark.asyncio
async def test_release_lock():
    """Test releasing a lock."""
    manager = LockManager()

    # Acquire and release
    lock = await manager.acquire("resource-1", "agent-a", timeout_seconds=0)
    assert lock["acquired"] is True

    result = await manager.release(lock["lock_id"], "agent-a")
    assert result["released"] is True

    # Now another agent can acquire
    lock2 = await manager.acquire("resource-1", "agent-b", timeout_seconds=0)
    assert lock2["acquired"] is True


@pytest.mark.asyncio
async def test_release_wrong_agent():
    """Test that only lock owner can release."""
    manager = LockManager()

    lock = await manager.acquire("resource-1", "agent-a", timeout_seconds=0)

    # Agent B tries to release Agent A's lock
    with pytest.raises(ValueError) as exc_info:
        await manager.release(lock["lock_id"], "agent-b")

    assert "not agent-b" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_lock_timeout():
    """Test lock acquisition with timeout."""
    manager = LockManager()

    # Agent A holds lock
    await manager.acquire("resource-1", "agent-a", timeout_seconds=0)

    # Agent B waits for lock (should timeout after small delay)
    import time

    start = time.time()
    lock2 = await manager.acquire("resource-1", "agent-b", timeout_seconds=0.5)
    elapsed = time.time() - start

    assert lock2["acquired"] is False
    assert elapsed >= 0.5


@pytest.mark.asyncio
async def test_lock_auto_release():
    """Test locks auto-release after expiry."""
    manager = LockManager()

    # Acquire lock with 1 second auto-release
    lock = await manager.acquire("resource-1", "agent-a", timeout_seconds=0, auto_release_seconds=1)
    assert lock["acquired"] is True

    # Immediately, agent B can't acquire
    lock2 = await manager.acquire("resource-1", "agent-b", timeout_seconds=0)
    assert lock2["acquired"] is False

    # Wait for auto-release
    await asyncio.sleep(1.1)

    # Cleanup expired locks
    await manager._cleanup_expired()

    # Now agent B can acquire
    lock3 = await manager.acquire("resource-1", "agent-b", timeout_seconds=0)
    assert lock3["acquired"] is True


@pytest.mark.asyncio
async def test_lock_quota():
    """Test per-agent lock quota."""
    manager = LockManager()
    manager.MAX_LOCKS_PER_AGENT = 3  # Set quota to 3 for testing

    # Agent can acquire up to quota
    await manager.acquire("resource-1", "agent-a", timeout_seconds=0)
    await manager.acquire("resource-2", "agent-a", timeout_seconds=0)
    await manager.acquire("resource-3", "agent-a", timeout_seconds=0)

    # Exceeding quota raises error
    with pytest.raises(LockQuotaExceeded) as exc_info:
        await manager.acquire("resource-4", "agent-a", timeout_seconds=0)

    assert "quota" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_release_all_locks():
    """Test releasing all locks for an agent."""
    manager = LockManager()

    # Agent holds multiple locks
    await manager.acquire("resource-1", "agent-a", timeout_seconds=0)
    await manager.acquire("resource-2", "agent-a", timeout_seconds=0)
    await manager.acquire("resource-3", "agent-a", timeout_seconds=0)

    # Release all
    count = await manager.release_all("agent-a")
    assert count == 3

    # All locks now available
    lock1 = await manager.acquire("resource-1", "agent-b", timeout_seconds=0)
    lock2 = await manager.acquire("resource-2", "agent-b", timeout_seconds=0)
    lock3 = await manager.acquire("resource-3", "agent-b", timeout_seconds=0)

    assert all(lock["acquired"] for lock in [lock1, lock2, lock3])


@pytest.mark.asyncio
async def test_get_lock_status():
    """Test getting lock status."""
    manager = LockManager()

    # No lock held
    status = await manager.get_lock_status("resource-1")
    assert status is None

    # Acquire lock
    lock = await manager.acquire("resource-1", "agent-a", timeout_seconds=0, auto_release_seconds=300)

    # Get status
    status = await manager.get_lock_status("resource-1")
    assert status is not None
    assert status["held_by"] == "agent-a"
    assert status["seconds_remaining"] > 0


@pytest.mark.asyncio
async def test_list_locks():
    """Test listing all active locks."""
    manager = LockManager()

    # Acquire several locks
    await manager.acquire("resource-1", "agent-a", timeout_seconds=0)
    await manager.acquire("resource-2", "agent-b", timeout_seconds=0)

    # List locks
    locks = await manager.list_locks()

    assert len(locks) == 2
    lock_names = {lock["name"] for lock in locks}
    assert "resource-1" in lock_names
    assert "resource-2" in lock_names


@pytest.mark.asyncio
async def test_stats():
    """Test lock manager statistics."""
    manager = LockManager()

    await manager.acquire("resource-1", "agent-a", timeout_seconds=0)
    await manager.acquire("resource-2", "agent-a", timeout_seconds=0)
    await manager.acquire("resource-3", "agent-b", timeout_seconds=0)

    stats = manager.get_stats()

    assert stats["active_locks"] == 3
    assert stats["agents_with_locks"] == 2
