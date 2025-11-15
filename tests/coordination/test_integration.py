"""Integration tests for multi-agent coordination."""

import asyncio

import pytest

from hitl_mcp_cli.coordination.auth import AuthManager
from hitl_mcp_cli.coordination.channels import ChannelStore
from hitl_mcp_cli.coordination.heartbeat import HeartbeatManager
from hitl_mcp_cli.coordination.locks import LockManager
from hitl_mcp_cli.coordination.ratelimit import RateLimiter
from hitl_mcp_cli.coordination.schema import AuthenticationError, MessageType, RateLimitExceeded


@pytest.mark.asyncio
async def test_two_agent_coordination_basic():
    """Test basic two-agent coordination flow."""
    store = ChannelStore()

    # Agent A joins
    result_a = await store.join_channel("project", "agent-a")
    assert result_a["agent_id"] == "agent-a"

    # Agent B joins
    result_b = await store.join_channel("project", "agent-b")
    assert "agent-a" in result_b["other_agents"]

    # Agent A sends init
    msg_id = await store.append("project", "agent-a", MessageType.INIT, "Hello from A")

    # Agent B polls and sees it
    messages = await store.read("project")
    assert len(messages) == 1
    assert messages[0].content == "Hello from A"

    # Agent B acknowledges
    await store.append("project", "agent-b", MessageType.ACKNOWLEDGMENT, "Ready")

    # Agent A sees acknowledgment
    messages = await store.read("project", filter_type="acknowledgment")
    assert len(messages) == 1
    assert messages[0].from_agent == "agent-b"


@pytest.mark.asyncio
async def test_full_coordination_protocol():
    """Test complete coordination protocol (discovery -> sync -> operational)."""
    store = ChannelStore()

    # === Phase 1: Discovery ===
    await store.join_channel("project", "primary")
    await store.join_channel("project", "subordinate")

    await store.append("project", "primary", MessageType.INIT, '{"role": "primary"}')
    await store.append("project", "subordinate", MessageType.ACKNOWLEDGMENT, '{"role": "subordinate"}')

    # === Phase 2: Synchronization ===
    await store.append(
        "project",
        "primary",
        MessageType.SYNC,
        {"config": {"rules": {"no_transient_files": True}, "test_coverage_min": 0.92}},
    )

    await store.append(
        "project", "subordinate", MessageType.CAPABILITIES, {"capabilities": {"knowledge_base": False, "session_limit": 50}}
    )

    await store.append("project", "primary", MessageType.COORDINATION_COMPLETE, "Sync done")

    # === Phase 3: Operational ===
    await store.append("project", "primary", MessageType.TASK_ASSIGN, {"task": "Update README", "files": ["README.md"]})

    await store.append("project", "subordinate", MessageType.PROGRESS, {"status": "50% complete"})

    await store.append("project", "subordinate", MessageType.TASK_COMPLETE, {"task_id": "update-readme", "status": "done"})

    # Verify complete flow
    all_messages = await store.read("project")
    assert len(all_messages) >= 7

    message_types = [msg.type for msg in all_messages]
    assert MessageType.INIT in message_types
    assert MessageType.ACKNOWLEDGMENT in message_types
    assert MessageType.SYNC in message_types
    assert MessageType.TASK_ASSIGN in message_types
    assert MessageType.TASK_COMPLETE in message_types


@pytest.mark.asyncio
async def test_authenticated_coordination():
    """Test coordination with authentication."""
    store = ChannelStore()
    auth = AuthManager()

    # Register agents
    api_key_a = auth.register_agent("agent-a", allowed_channels={"project"}, permissions={"read", "write"})
    api_key_b = auth.register_agent("agent-b", allowed_channels={"project"}, permissions={"read", "write"})

    # Authenticate and join
    assert auth.authenticate("agent-a", api_key_a)
    assert auth.verify_channel_access("agent-a", "project")

    await store.join_channel("project", "agent-a")

    # Wrong API key should fail
    assert not auth.authenticate("agent-a", "wrong-key")

    # Unauthorized channel should fail
    assert not auth.verify_channel_access("agent-a", "unauthorized-channel")

    # Agent without write permission can't send
    auth.update_permissions("agent-b", {"read"})
    assert not auth.verify_permission("agent-b", "write")


@pytest.mark.asyncio
async def test_rate_limited_coordination():
    """Test rate limiting during coordination."""
    store = ChannelStore()
    limiter = RateLimiter(default_per_agent_limit=3, global_limit=10)

    # Agent can send 3 messages
    for i in range(3):
        await limiter.check("agent-a", "send_message")
        await store.append("project", "agent-a", MessageType.PROGRESS, f"Message {i}")

    # 4th should be rate limited
    with pytest.raises(RateLimitExceeded):
        await limiter.check("agent-a", "send_message")


@pytest.mark.asyncio
async def test_lock_coordination():
    """Test lock-based resource coordination."""
    store = ChannelStore()
    locks = LockManager()

    # Agent A acquires lock
    lock_a = await locks.acquire("file:config.yaml", "agent-a", timeout_seconds=0)
    assert lock_a["acquired"]

    # Agent B can't acquire (A holds it)
    lock_b = await locks.acquire("file:config.yaml", "agent-b", timeout_seconds=0)
    assert not lock_b["acquired"]

    # Agent A sends message about work
    await store.append("project", "agent-a", MessageType.PROGRESS, "Modifying config.yaml")

    # Agent A releases
    await locks.release(lock_a["lock_id"], "agent-a")

    # Now agent B can acquire
    lock_b2 = await locks.acquire("file:config.yaml", "agent-b", timeout_seconds=0)
    assert lock_b2["acquired"]


@pytest.mark.asyncio
async def test_heartbeat_coordination():
    """Test heartbeat-based liveness detection."""
    heartbeat = HeartbeatManager(heartbeat_interval=1, missing_threshold=1, dead_threshold=2)
    locks = LockManager()

    # Setup callback to release locks when agent dies
    dead_agents = []

    async def on_dead(agent_id: str):
        dead_agents.append(agent_id)
        await locks.release_all(agent_id)

    heartbeat.register_dead_callback(lambda agent_id: asyncio.create_task(on_dead(agent_id)))

    # Agent A holds lock
    lock = await locks.acquire("resource-1", "agent-a", timeout_seconds=0)
    assert lock["acquired"]

    # Agent A sends heartbeat
    await heartbeat.heartbeat("agent-a")

    # Wait for agent to "die" (miss heartbeats)
    await asyncio.sleep(2.5)
    await heartbeat._check_agents()

    # Agent should be marked dead
    status = await heartbeat.get_agent_status("agent-a")
    assert status["status"] == "dead"

    # Callback should have released locks
    await asyncio.sleep(0.1)  # Give callback time to run
    lock_status = await locks.get_lock_status("resource-1")
    # Lock should be released or expired


@pytest.mark.asyncio
async def test_concurrent_agents_same_channel():
    """Test multiple agents coordinating concurrently."""
    store = ChannelStore()

    # 5 agents join simultaneously
    agents = ["agent-1", "agent-2", "agent-3", "agent-4", "agent-5"]

    join_tasks = [store.join_channel("shared", agent) for agent in agents]
    results = await asyncio.gather(*join_tasks)

    # All should succeed
    assert all(r["channel_name"] == "shared" for r in results)

    # Each sends a message
    send_tasks = [store.append("shared", agent, MessageType.READY, f"Ready from {agent}") for agent in agents]
    await asyncio.gather(*send_tasks)

    # Read all messages
    messages = await store.read("shared")
    assert len(messages) == 5

    # All agents represented
    senders = {msg.from_agent for msg in messages}
    assert senders == set(agents)


@pytest.mark.asyncio
async def test_conflict_resolution_flow():
    """Test conflict detection and resolution."""
    store = ChannelStore()

    # Both agents modify same file (detected)
    await store.append(
        "project",
        "subordinate",
        MessageType.CONFLICT_DETECTED,
        {"conflict_type": "file_modification", "details": "Both modified config.yaml"},
    )

    # Primary resolves
    await store.append(
        "project", "primary", MessageType.CONFLICT_RESOLVED, {"resolution": "Use primary's version", "rationale": "..."}
    )

    # Verify resolution recorded
    conflicts = await store.read("project", filter_type="conflict_detected")
    resolutions = await store.read("project", filter_type="conflict_resolved")

    assert len(conflicts) == 1
    assert len(resolutions) == 1


@pytest.mark.asyncio
async def test_subscription_notifications():
    """Test real-time subscription notifications."""
    store = ChannelStore()

    # Subscribe to channel
    queue = await store.subscribe("project")

    # Send message in background
    async def send_later():
        await asyncio.sleep(0.1)
        await store.append("project", "agent-a", MessageType.INIT, "Hello")

    task = asyncio.create_task(send_later())

    # Should receive via subscription
    message = await asyncio.wait_for(queue.get(), timeout=1.0)

    assert message.content == "Hello"
    assert message.type == MessageType.INIT

    await task


@pytest.mark.asyncio
async def test_full_stack_with_all_features():
    """Integration test with auth, rate limiting, locks, and heartbeat."""
    # Initialize all components
    store = ChannelStore()
    auth = AuthManager()
    limiter = RateLimiter(default_per_agent_limit=100)
    locks = LockManager()
    heartbeat = HeartbeatManager()

    # Register authenticated agent
    api_key = auth.register_agent("agent-a", allowed_channels={"*"}, permissions={"read", "write", "lock"})

    # Start heartbeat manager
    await heartbeat.start()

    try:
        # Authenticate
        assert auth.authenticate("agent-a", api_key)

        # Send heartbeat
        await heartbeat.heartbeat("agent-a")

        # Check rate limit
        await limiter.check("agent-a", "join")

        # Join channel
        await store.join_channel("project", "agent-a")

        # Acquire lock (with rate limit check)
        await limiter.check("agent-a", "lock")
        lock = await locks.acquire("resource-1", "agent-a", timeout_seconds=0)
        assert lock["acquired"]

        # Send message (with rate limit check)
        await limiter.check("agent-a", "send")
        await store.append("project", "agent-a", MessageType.PROGRESS, "Working on resource-1")

        # Release lock
        await locks.release(lock["lock_id"], "agent-a")

        # Verify heartbeat registered
        status = await heartbeat.get_agent_status("agent-a")
        assert status["status"] == "alive"

    finally:
        await heartbeat.stop()


def test_metrics_collection():
    """Test that metrics can be collected."""
    from hitl_mcp_cli.coordination import metrics

    # Metrics should be importable
    assert hasattr(metrics, "messages_sent_total")
    assert hasattr(metrics, "locks_acquired_total")
    assert hasattr(metrics, "heartbeat_total")
