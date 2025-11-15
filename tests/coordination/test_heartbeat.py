"""Tests for heartbeat mechanism."""

import asyncio

import pytest

from hitl_mcp_cli.coordination.heartbeat import HeartbeatManager


@pytest.mark.asyncio
async def test_heartbeat_initial():
    """Test first heartbeat from agent."""
    manager = HeartbeatManager(heartbeat_interval=30)

    result = await manager.heartbeat("agent-a")

    assert result["acknowledged"] is True
    assert result["status"] == "alive"
    assert "next_heartbeat_by" in result


@pytest.mark.asyncio
async def test_heartbeat_multiple():
    """Test multiple heartbeats increment count."""
    manager = HeartbeatManager(heartbeat_interval=30)

    await manager.heartbeat("agent-a")
    await manager.heartbeat("agent-a")
    await manager.heartbeat("agent-a")

    status = await manager.get_agent_status("agent-a")

    assert status["total_heartbeats"] == 3
    assert status["status"] == "alive"


@pytest.mark.asyncio
async def test_heartbeat_with_metadata():
    """Test heartbeat with metadata."""
    manager = HeartbeatManager(heartbeat_interval=30)

    await manager.heartbeat("agent-a", metadata={"load": 0.5, "version": "1.0"})

    status = await manager.get_agent_status("agent-a")

    assert status["metadata"]["load"] == 0.5
    assert status["metadata"]["version"] == "1.0"


@pytest.mark.asyncio
async def test_get_agent_status():
    """Test getting agent health status."""
    manager = HeartbeatManager(heartbeat_interval=30)

    await manager.heartbeat("agent-a")

    status = await manager.get_agent_status("agent-a")

    assert status is not None
    assert status["agent_id"] == "agent-a"
    assert status["status"] == "alive"
    assert status["missed_beats"] == 0
    assert status["seconds_since_heartbeat"] < 1


@pytest.mark.asyncio
async def test_get_status_nonexistent_agent():
    """Test getting status of non-existent agent."""
    manager = HeartbeatManager()

    status = await manager.get_agent_status("nonexistent")

    assert status is None


@pytest.mark.asyncio
async def test_list_agents():
    """Test listing all agents."""
    manager = HeartbeatManager()

    await manager.heartbeat("agent-a")
    await manager.heartbeat("agent-b")
    await manager.heartbeat("agent-c")

    agents = await manager.list_agents()

    assert len(agents) == 3
    agent_ids = {a["agent_id"] for a in agents}
    assert agent_ids == {"agent-a", "agent-b", "agent-c"}


@pytest.mark.asyncio
async def test_list_agents_filtered():
    """Test listing agents with status filter."""
    manager = HeartbeatManager(heartbeat_interval=1, missing_threshold=1)

    await manager.heartbeat("agent-a")

    # Wait for agent-a to go missing
    await asyncio.sleep(1.5)

    # Manually trigger check
    await manager._check_agents()

    agents_alive = await manager.list_agents(status_filter="alive")
    agents_missing = await manager.list_agents(status_filter="missing")

    assert len(agents_alive) == 0
    assert len(agents_missing) == 1


@pytest.mark.asyncio
async def test_missing_detection():
    """Test agent marked as missing after threshold."""
    manager = HeartbeatManager(heartbeat_interval=1, missing_threshold=1)

    await manager.heartbeat("agent-a")

    # Initially alive
    status = await manager.get_agent_status("agent-a")
    assert status["status"] == "alive"

    # Wait for missing threshold
    await asyncio.sleep(1.5)

    # Trigger check
    await manager._check_agents()

    status = await manager.get_agent_status("agent-a")
    assert status["status"] == "missing"


@pytest.mark.asyncio
async def test_dead_detection():
    """Test agent marked as dead after threshold."""
    manager = HeartbeatManager(heartbeat_interval=1, missing_threshold=1, dead_threshold=2)

    await manager.heartbeat("agent-a")

    # Wait for dead threshold
    await asyncio.sleep(2.5)

    # Trigger check
    await manager._check_agents()

    status = await manager.get_agent_status("agent-a")
    assert status["status"] == "dead"


@pytest.mark.asyncio
async def test_recovery_from_missing():
    """Test agent recovers from missing status."""
    manager = HeartbeatManager(heartbeat_interval=1, missing_threshold=1)

    await manager.heartbeat("agent-a")
    await asyncio.sleep(1.5)
    await manager._check_agents()

    # Should be missing
    status = await manager.get_agent_status("agent-a")
    assert status["status"] == "missing"

    # Send heartbeat to recover
    await manager.heartbeat("agent-a")

    status = await manager.get_agent_status("agent-a")
    assert status["status"] == "alive"


@pytest.mark.asyncio
async def test_missing_callback():
    """Test callback triggered when agent goes missing."""
    manager = HeartbeatManager(heartbeat_interval=1, missing_threshold=1)

    missing_agents = []

    def on_missing(agent_id: str):
        missing_agents.append(agent_id)

    manager.register_missing_callback(on_missing)

    await manager.heartbeat("agent-a")
    await asyncio.sleep(1.5)
    await manager._check_agents()

    assert "agent-a" in missing_agents


@pytest.mark.asyncio
async def test_dead_callback():
    """Test callback triggered when agent is marked dead."""
    manager = HeartbeatManager(heartbeat_interval=1, missing_threshold=1, dead_threshold=2)

    dead_agents = []

    def on_dead(agent_id: str):
        dead_agents.append(agent_id)

    manager.register_dead_callback(on_dead)

    await manager.heartbeat("agent-a")
    await asyncio.sleep(2.5)
    await manager._check_agents()

    assert "agent-a" in dead_agents


@pytest.mark.asyncio
async def test_start_stop():
    """Test starting and stopping heartbeat manager."""
    manager = HeartbeatManager()

    await manager.start()
    assert manager._running is True
    assert manager._monitor_task is not None

    await manager.stop()
    assert manager._running is False


def test_get_stats():
    """Test heartbeat manager statistics."""
    manager = HeartbeatManager(heartbeat_interval=30)

    stats = manager.get_stats()

    assert stats["heartbeat_interval"] == 30
    assert stats["total_agents"] == 0
    assert stats["alive"] == 0
    assert stats["missing"] == 0
    assert stats["dead"] == 0
