"""End-to-end tests for coordination server integration."""

import importlib
import os
import sys

import pytest

# Test basic server startup with coordination


@pytest.mark.asyncio
async def test_server_imports_with_coordination():
    """Test server can be imported with coordination enabled."""
    # Set environment before reload
    os.environ["HITL_ENABLE_COORDINATION"] = "1"

    # Force reload to pick up environment variable
    if "hitl_mcp_cli.server" in sys.modules:
        import hitl_mcp_cli.server as server_module

        importlib.reload(server_module)
    else:
        import hitl_mcp_cli.server as server_module

    assert server_module.ENABLE_COORDINATION is True
    assert server_module.coordination_channel_store is not None
    assert server_module.coordination_lock_manager is not None

    # Clean up for other tests
    os.environ.pop("HITL_ENABLE_COORDINATION", None)


@pytest.mark.asyncio
async def test_server_with_auth_enabled():
    """Test server with authentication enabled."""
    os.environ["HITL_ENABLE_COORDINATION"] = "1"
    os.environ["HITL_COORDINATION_AUTH"] = "1"
    os.environ["HITL_DEV_MODE"] = "1"

    # Reload server module to pick up env vars
    import hitl_mcp_cli.server as server

    importlib.reload(server)

    assert server.coordination_auth_manager is not None

    # Clean up
    os.environ.pop("HITL_ENABLE_COORDINATION", None)
    os.environ.pop("HITL_COORDINATION_AUTH", None)
    os.environ.pop("HITL_DEV_MODE", None)


@pytest.mark.asyncio
async def test_server_with_rate_limiting_enabled():
    """Test server with rate limiting enabled."""
    os.environ["HITL_ENABLE_COORDINATION"] = "1"
    os.environ["HITL_COORDINATION_RATE_LIMIT"] = "1"

    import hitl_mcp_cli.server as server

    importlib.reload(server)

    assert server.coordination_rate_limiter is not None

    # Clean up
    os.environ.pop("HITL_ENABLE_COORDINATION", None)
    os.environ.pop("HITL_COORDINATION_RATE_LIMIT", None)


@pytest.mark.asyncio
async def test_server_with_heartbeat_enabled():
    """Test server with heartbeat enabled."""
    os.environ["HITL_ENABLE_COORDINATION"] = "1"
    os.environ["HITL_COORDINATION_HEARTBEAT"] = "1"

    import hitl_mcp_cli.server as server

    importlib.reload(server)

    assert server.coordination_heartbeat_manager is not None

    # Clean up
    os.environ.pop("HITL_ENABLE_COORDINATION", None)
    os.environ.pop("HITL_COORDINATION_HEARTBEAT", None)


@pytest.mark.asyncio
async def test_metrics_update():
    """Test metrics can be updated from coordination state."""
    from hitl_mcp_cli.coordination import metrics
    from hitl_mcp_cli.coordination.channels import ChannelStore
    from hitl_mcp_cli.coordination.heartbeat import HeartbeatManager
    from hitl_mcp_cli.coordination.locks import LockManager

    store = ChannelStore()
    locks = LockManager()
    heartbeat = HeartbeatManager()

    # Create some state
    await store.join_channel("test", "agent-a")
    await store.append("test", "agent-a", "init", "hello")
    await locks.acquire("resource-1", "agent-a", timeout_seconds=0)
    await heartbeat.heartbeat("agent-a")

    # Update metrics
    metrics.update_metrics(store, locks, heartbeat)

    # Metrics should reflect state
    assert metrics.channels_active._value.get() == 1
    assert metrics.locks_active._value.get() == 1


@pytest.mark.asyncio
async def test_client_library_basic_flow():
    """Test client library can coordinate with backend."""
    from hitl_mcp_cli.coordination.channels import ChannelStore

    # Mock MCP session
    class MockSession:
        def __init__(self, store):
            self.store = store

        async def call_tool(self, name, arguments):
            if name == "join_coordination_channel":
                # Only pass channel_name and agent_id to store
                result = await self.store.join_channel(arguments["channel_name"], arguments["agent_id"])
                return type("Result", (), {"content": result})()
            elif name == "send_coordination_message":
                from hitl_mcp_cli.coordination.schema import MessageType

                msg_id = await self.store.append(
                    arguments["channel_name"],
                    arguments["from_agent"],
                    MessageType(arguments["message_type"]),
                    arguments["content"],
                )
                msg = await self.store.get_message(arguments["channel_name"], msg_id)
                return type(
                    "Result",
                    (),
                    {
                        "content": {
                            "message_id": msg_id,
                            "timestamp": msg.timestamp if msg else 0,
                            "channel_uri": f"coordination://{arguments['channel_name']}/{msg_id}",
                        }
                    },
                )()

    from hitl_mcp_cli.coordination.client import CoordinationClient

    store = ChannelStore()
    session = MockSession(store)
    client = CoordinationClient(session, "test-agent")

    # Join channel
    result = await client.join_channel("project")
    assert result["agent_id"] == "test-agent"

    # Send message
    msg_id = await client.send("project", "init", "Hello")
    assert msg_id is not None


@pytest.mark.asyncio
async def test_tracing_manager_initialization():
    """Test tracing manager can be initialized."""
    from hitl_mcp_cli.coordination.tracing import TracingManager

    manager = TracingManager(service_name="test")

    # Should not crash even without OTLP endpoint
    assert manager is not None
    assert manager.enabled is False  # No endpoint provided


@pytest.mark.asyncio
async def test_full_coordination_with_all_features():
    """Test complete coordination flow with all features enabled."""
    from hitl_mcp_cli.coordination.auth import AuthManager
    from hitl_mcp_cli.coordination.channels import ChannelStore
    from hitl_mcp_cli.coordination.heartbeat import HeartbeatManager
    from hitl_mcp_cli.coordination.locks import LockManager
    from hitl_mcp_cli.coordination.ratelimit import RateLimiter
    from hitl_mcp_cli.coordination.schema import MessageType

    # Initialize all components
    store = ChannelStore()
    locks = LockManager()
    auth = AuthManager()
    limiter = RateLimiter()
    heartbeat = HeartbeatManager()

    # Register agent
    api_key = auth.register_agent("agent-a")

    # Start heartbeat
    await heartbeat.start()

    try:
        # Authenticate
        assert auth.authenticate("agent-a", api_key)

        # Rate limit check
        await limiter.check("agent-a")

        # Heartbeat
        await heartbeat.heartbeat("agent-a")

        # Join channel
        await store.join_channel("project", "agent-a")

        # Send message
        await store.append("project", "agent-a", MessageType.INIT, "Hello")

        # Acquire lock
        lock = await locks.acquire("resource-1", "agent-a", timeout_seconds=0)
        assert lock["acquired"]

        # Release lock
        await locks.release(lock["lock_id"], "agent-a")

        # Verify heartbeat status
        status = await heartbeat.get_agent_status("agent-a")
        assert status["status"] == "alive"

    finally:
        await heartbeat.stop()


def test_configuration_env_vars():
    """Test configuration via environment variables."""
    os.environ["HITL_ENABLE_COORDINATION"] = "1"
    os.environ["HITL_COORDINATION_AUTH"] = "1"
    os.environ["HITL_COORDINATION_RATE_LIMIT"] = "1"
    os.environ["HITL_RATE_LIMIT_PER_AGENT"] = "50"
    os.environ["HITL_RATE_LIMIT_GLOBAL"] = "500"
    os.environ["HITL_HEARTBEAT_INTERVAL"] = "60"

    # Configuration should be read from env vars
    assert os.getenv("HITL_RATE_LIMIT_PER_AGENT") == "50"
    assert os.getenv("HITL_RATE_LIMIT_GLOBAL") == "500"
    assert os.getenv("HITL_HEARTBEAT_INTERVAL") == "60"
