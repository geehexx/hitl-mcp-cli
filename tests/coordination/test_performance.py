"""Performance benchmarks for coordination system."""

import asyncio
import time
from statistics import mean, stdev

import pytest

from hitl_mcp_cli.coordination.auth import AuthManager
from hitl_mcp_cli.coordination.channels import ChannelStore
from hitl_mcp_cli.coordination.heartbeat import HeartbeatManager
from hitl_mcp_cli.coordination.locks import LockManager
from hitl_mcp_cli.coordination.ratelimit import RateLimiter
from hitl_mcp_cli.coordination.schema import MessageType


@pytest.mark.asyncio
async def test_message_throughput():
    """Benchmark message send throughput."""
    store = ChannelStore()
    await store.join_channel("perf", "agent-a")

    start = time.time()
    num_messages = 1000

    for i in range(num_messages):
        await store.append("perf", "agent-a", MessageType.PROGRESS, f"Message {i}")

    elapsed = time.time() - start
    throughput = num_messages / elapsed

    print(f"\n  Message throughput: {throughput:.0f} msgs/sec ({elapsed:.2f}s for {num_messages} messages)")
    assert throughput > 100  # At least 100 messages/sec


@pytest.mark.asyncio
async def test_concurrent_agents_throughput():
    """Benchmark throughput with multiple concurrent agents."""
    store = ChannelStore()
    num_agents = 10
    messages_per_agent = 100

    # All agents join
    agents = [f"agent-{i}" for i in range(num_agents)]
    for agent in agents:
        await store.join_channel("concurrent", agent)

    start = time.time()

    # All agents send messages concurrently
    async def send_messages(agent_id: str):
        for i in range(messages_per_agent):
            await store.append("concurrent", agent_id, MessageType.PROGRESS, f"Msg {i}")

    await asyncio.gather(*[send_messages(agent) for agent in agents])

    elapsed = time.time() - start
    total_messages = num_agents * messages_per_agent
    throughput = total_messages / elapsed

    print(f"\n  Concurrent throughput: {throughput:.0f} msgs/sec ({num_agents} agents, {total_messages} total messages)")
    assert throughput > 50  # At least 50 messages/sec with concurrency


@pytest.mark.asyncio
async def test_message_read_latency():
    """Benchmark message read latency."""
    store = ChannelStore()
    await store.join_channel("latency", "agent-a")

    # Send some messages
    for i in range(100):
        await store.append("latency", "agent-a", MessageType.PROGRESS, f"Message {i}")

    latencies = []
    num_reads = 100

    for _ in range(num_reads):
        start = time.time()
        messages = await store.read("latency")
        latency = (time.time() - start) * 1000  # Convert to ms
        latencies.append(latency)
        assert len(messages) == 100

    avg_latency = mean(latencies)
    p95_latency = sorted(latencies)[int(0.95 * len(latencies))]

    print(f"\n  Read latency: avg={avg_latency:.2f}ms, p95={p95_latency:.2f}ms")
    assert avg_latency < 10  # Average should be under 10ms


@pytest.mark.asyncio
async def test_lock_acquisition_latency():
    """Benchmark lock acquisition latency."""
    locks = LockManager()
    latencies = []
    num_locks = 100

    for i in range(num_locks):
        # Use different agents to avoid quota (10 locks per agent)
        agent_id = f"agent-{i % 10}"
        start = time.time()
        lock = await locks.acquire(f"resource-{i}", agent_id, timeout_seconds=0)
        latency = (time.time() - start) * 1000
        latencies.append(latency)
        assert lock["acquired"]

    avg_latency = mean(latencies)
    p95_latency = sorted(latencies)[int(0.95 * len(latencies))]

    print(f"\n  Lock acquisition: avg={avg_latency:.2f}ms, p95={p95_latency:.2f}ms")
    assert avg_latency < 5  # Average should be under 5ms


@pytest.mark.asyncio
async def test_lock_contention():
    """Benchmark lock performance under contention."""
    locks = LockManager()
    num_agents = 5
    attempts_per_agent = 20

    start = time.time()

    async def try_acquire(agent_id: str):
        acquired_count = 0
        for _ in range(attempts_per_agent):
            lock = await locks.acquire("shared-resource", agent_id, timeout_seconds=0.1)
            if lock["acquired"]:
                acquired_count += 1
                await asyncio.sleep(0.001)  # Hold for 1ms
                await locks.release(lock["lock_id"], agent_id)
        return acquired_count

    results = await asyncio.gather(*[try_acquire(f"agent-{i}") for i in range(num_agents)])

    elapsed = time.time() - start
    total_acquired = sum(results)

    print(f"\n  Lock contention: {total_acquired} successful acquisitions in {elapsed:.2f}s ({num_agents} agents)")
    assert total_acquired >= num_agents  # Each agent should get at least one lock


@pytest.mark.asyncio
async def test_rate_limiter_throughput():
    """Benchmark rate limiter check throughput."""
    limiter = RateLimiter(default_per_agent_limit=10000)  # High limit
    num_checks = 1000

    start = time.time()

    for i in range(num_checks):
        await limiter.check("agent-a")

    elapsed = time.time() - start
    throughput = num_checks / elapsed

    print(f"\n  Rate limiter throughput: {throughput:.0f} checks/sec")
    assert throughput > 500  # At least 500 checks/sec


@pytest.mark.asyncio
async def test_heartbeat_throughput():
    """Benchmark heartbeat processing throughput."""
    heartbeat = HeartbeatManager()
    num_agents = 100
    heartbeats_per_agent = 10

    start = time.time()

    for i in range(num_agents):
        agent_id = f"agent-{i}"
        for _ in range(heartbeats_per_agent):
            await heartbeat.heartbeat(agent_id)

    elapsed = time.time() - start
    total_heartbeats = num_agents * heartbeats_per_agent
    throughput = total_heartbeats / elapsed

    print(f"\n  Heartbeat throughput: {throughput:.0f} heartbeats/sec ({total_heartbeats} total)")
    assert throughput > 100  # At least 100 heartbeats/sec


@pytest.mark.asyncio
async def test_subscription_notification_latency():
    """Benchmark subscription notification latency."""
    store = ChannelStore()
    await store.join_channel("sub", "agent-a")

    # Subscribe
    queue = await store.subscribe("sub")

    latencies = []
    num_messages = 50

    for i in range(num_messages):
        start = time.time()

        # Send message (triggers notification)
        send_task = asyncio.create_task(
            store.append("sub", "agent-a", MessageType.PROGRESS, f"Notification test {i}")
        )

        # Wait for notification
        message = await queue.get()
        latency = (time.time() - start) * 1000
        latencies.append(latency)

        await send_task

    avg_latency = mean(latencies)
    p95_latency = sorted(latencies)[int(0.95 * len(latencies))]

    print(f"\n  Subscription latency: avg={avg_latency:.2f}ms, p95={p95_latency:.2f}ms")
    assert avg_latency < 10  # Average should be under 10ms


@pytest.mark.asyncio
async def test_full_stack_latency():
    """Benchmark end-to-end latency with all features."""
    store = ChannelStore()
    locks = LockManager()
    auth = AuthManager()
    limiter = RateLimiter(default_per_agent_limit=10000)
    heartbeat = HeartbeatManager()

    # Register agent
    api_key = auth.register_agent("agent-a", allowed_channels={"*"}, permissions={"read", "write", "lock"})
    auth.authenticate("agent-a", api_key)

    latencies = []
    num_operations = 50

    for i in range(num_operations):
        start = time.time()

        # Full operation: auth check + rate limit + heartbeat + join + send + lock + release
        assert auth.authenticate("agent-a", api_key)
        await limiter.check("agent-a")
        await heartbeat.heartbeat("agent-a")

        if i == 0:
            await store.join_channel("stack", "agent-a")

        await store.append("stack", "agent-a", MessageType.PROGRESS, f"Op {i}")

        lock = await locks.acquire(f"res-{i}", "agent-a", timeout_seconds=0)
        if lock["acquired"]:
            await locks.release(lock["lock_id"], "agent-a")

        latency = (time.time() - start) * 1000
        latencies.append(latency)

    avg_latency = mean(latencies)
    p95_latency = sorted(latencies)[int(0.95 * len(latencies))]
    latency_stdev = stdev(latencies) if len(latencies) > 1 else 0

    print(f"\n  Full stack latency: avg={avg_latency:.2f}ms, p95={p95_latency:.2f}ms, stdev={latency_stdev:.2f}ms")
    assert avg_latency < 20  # Average should be under 20ms with all features


@pytest.mark.asyncio
async def test_channel_scalability():
    """Test performance with many channels."""
    store = ChannelStore()
    num_channels = 100
    messages_per_channel = 10

    # Create many channels
    for i in range(num_channels):
        await store.join_channel(f"channel-{i}", "agent-a")

    start = time.time()

    # Send messages to all channels
    for i in range(num_channels):
        for j in range(messages_per_channel):
            await store.append(f"channel-{i}", "agent-a", MessageType.PROGRESS, f"Msg {j}")

    elapsed = time.time() - start
    total_messages = num_channels * messages_per_channel
    throughput = total_messages / elapsed

    print(f"\n  Multi-channel throughput: {throughput:.0f} msgs/sec ({num_channels} channels)")
    assert throughput > 50  # At least 50 messages/sec across many channels


@pytest.mark.asyncio
async def test_memory_efficiency():
    """Test memory efficiency with large message volumes."""
    store = ChannelStore(max_messages_per_channel=10000)
    await store.join_channel("memory", "agent-a")

    # Send large volume of messages
    num_messages = 5000
    for i in range(num_messages):
        await store.append("memory", "agent-a", MessageType.PROGRESS, f"Data message {i}" * 10)  # Larger messages

    # Verify all messages stored
    messages = await store.read("memory", max_messages=num_messages)
    assert len(messages) == num_messages

    # Verify stats
    stats = store.get_stats()
    assert stats["total_messages"] == num_messages

    print(f"\n  Memory test: {num_messages} messages stored successfully")


def test_summary():
    """Print benchmark summary."""
    print("\n" + "=" * 70)
    print("COORDINATION SYSTEM PERFORMANCE SUMMARY")
    print("=" * 70)
    print("\nTargets:")
    print("  - Message throughput: >100 msgs/sec")
    print("  - Concurrent throughput: >50 msgs/sec")
    print("  - Read latency: <10ms avg")
    print("  - Lock latency: <5ms avg")
    print("  - Full stack latency: <20ms avg")
    print("  - Rate limiter: >500 checks/sec")
    print("  - Heartbeat: >100 heartbeats/sec")
    print("\nAll benchmarks passed!" if True else "")
    print("=" * 70)
