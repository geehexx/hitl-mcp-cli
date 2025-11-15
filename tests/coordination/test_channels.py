"""Tests for coordination channels."""

import pytest

from hitl_mcp_cli.coordination.channels import ChannelStore
from hitl_mcp_cli.coordination.schema import ChannelFullError, MessageType


@pytest.mark.asyncio
async def test_create_channel():
    """Test channel creation."""
    store = ChannelStore()
    channel = await store.create_channel("test-channel")

    assert channel.name == "test-channel"
    assert len(channel.members) == 0
    assert channel.message_count == 0


@pytest.mark.asyncio
async def test_join_channel():
    """Test joining a channel."""
    store = ChannelStore()

    # Agent A joins
    result_a = await store.join_channel("test", "agent-a")
    assert result_a["agent_id"] == "agent-a"
    assert result_a["other_agents"] == []

    # Agent B joins
    result_b = await store.join_channel("test", "agent-b")
    assert result_b["agent_id"] == "agent-b"
    assert "agent-a" in result_b["other_agents"]


@pytest.mark.asyncio
async def test_message_ordering():
    """Test messages are returned in chronological order."""
    store = ChannelStore()

    # Send messages
    id1 = await store.append("test", "agent-a", MessageType.INIT, "First")
    id2 = await store.append("test", "agent-a", MessageType.SYNC, "Second")
    id3 = await store.append("test", "agent-a", MessageType.READY, "Third")

    # Read all messages
    messages = await store.read("test")

    assert len(messages) == 3
    assert messages[0].content == "First"
    assert messages[1].content == "Second"
    assert messages[2].content == "Third"


@pytest.mark.asyncio
async def test_per_agent_sequence_numbers():
    """Test per-agent FIFO ordering via sequence numbers."""
    store = ChannelStore()

    # Agent A sends 3 messages
    await store.append("test", "agent-a", MessageType.INIT, "A1")
    await store.append("test", "agent-a", MessageType.SYNC, "A2")
    await store.append("test", "agent-a", MessageType.READY, "A3")

    # Agent B sends 2 messages
    await store.append("test", "agent-b", MessageType.INIT, "B1")
    await store.append("test", "agent-b", MessageType.SYNC, "B2")

    # Read and verify sequences
    messages = await store.read("test")

    agent_a_msgs = [m for m in messages if m.from_agent == "agent-a"]
    agent_b_msgs = [m for m in messages if m.from_agent == "agent-b"]

    # Agent A's sequence: 0, 1, 2
    assert agent_a_msgs[0].sequence == 0
    assert agent_a_msgs[1].sequence == 1
    assert agent_a_msgs[2].sequence == 2

    # Agent B's sequence: 0, 1
    assert agent_b_msgs[0].sequence == 0
    assert agent_b_msgs[1].sequence == 1


@pytest.mark.asyncio
async def test_filter_by_type():
    """Test filtering messages by type."""
    store = ChannelStore()

    await store.append("test", "agent-a", MessageType.INIT, "Init message")
    await store.append("test", "agent-a", MessageType.QUESTION, "Question message")
    await store.append("test", "agent-a", MessageType.INIT, "Another init")

    # Filter for init messages
    init_msgs = await store.read("test", filter_type="init")

    assert len(init_msgs) == 2
    assert all(m.type == MessageType.INIT for m in init_msgs)


@pytest.mark.asyncio
async def test_read_since_message():
    """Test reading messages since specific ID."""
    store = ChannelStore()

    id1 = await store.append("test", "agent-a", MessageType.INIT, "First")
    id2 = await store.append("test", "agent-a", MessageType.SYNC, "Second")
    id3 = await store.append("test", "agent-a", MessageType.READY, "Third")

    # Read since second message
    messages = await store.read("test", since_message_id=id2)

    assert len(messages) == 1
    assert messages[0].id == id3
    assert messages[0].content == "Third"


@pytest.mark.asyncio
async def test_channel_capacity():
    """Test channel capacity limits."""
    store = ChannelStore(max_messages_per_channel=3)

    # Fill channel to capacity
    await store.append("test", "agent-a", MessageType.INIT, "1")
    await store.append("test", "agent-a", MessageType.SYNC, "2")
    await store.append("test", "agent-a", MessageType.READY, "3")

    # Next message should raise ChannelFullError
    with pytest.raises(ChannelFullError) as exc_info:
        await store.append("test", "agent-a", MessageType.DONE, "4")

    assert "full" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_get_specific_message():
    """Test retrieving specific message by ID."""
    store = ChannelStore()

    msg_id = await store.append("test", "agent-a", MessageType.INIT, "Hello")

    message = await store.get_message("test", msg_id)

    assert message is not None
    assert message.id == msg_id
    assert message.content == "Hello"


@pytest.mark.asyncio
async def test_message_validation():
    """Test message content validation against schema."""
    store = ChannelStore()

    # Valid message (TASK_ASSIGN requires "task" field)
    await store.append(
        "test",
        "agent-a",
        MessageType.TASK_ASSIGN,
        {"task": "Update README", "files": ["README.md"]},
    )

    # Invalid message (missing required "task" field)
    with pytest.raises(ValueError) as exc_info:
        await store.append(
            "test",
            "agent-a",
            MessageType.TASK_ASSIGN,
            {"files": ["README.md"]},  # Missing "task"
        )

    assert "invalid" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_subscriptions():
    """Test channel subscriptions."""
    import asyncio

    store = ChannelStore()

    # Subscribe to channel
    queue = await store.subscribe("test")

    # Send message
    await store.append("test", "agent-a", MessageType.INIT, "Hello")

    # Should receive message in queue
    message = await asyncio.wait_for(queue.get(), timeout=1.0)

    assert message.content == "Hello"
    assert message.type == MessageType.INIT


@pytest.mark.asyncio
async def test_leave_channel():
    """Test leaving a channel."""
    store = ChannelStore()

    # Join and verify
    await store.join_channel("test", "agent-a")
    channel = await store.get_channel("test")
    assert "agent-a" in channel.members

    # Leave and verify
    await store.leave_channel("test", "agent-a")
    channel = await store.get_channel("test")
    assert "agent-a" not in channel.members


@pytest.mark.asyncio
async def test_stats():
    """Test store statistics."""
    store = ChannelStore()

    await store.create_channel("channel-1")
    await store.create_channel("channel-2")
    await store.append("channel-1", "agent-a", MessageType.INIT, "msg1")
    await store.append("channel-1", "agent-a", MessageType.SYNC, "msg2")
    await store.append("channel-2", "agent-b", MessageType.INIT, "msg3")

    stats = store.get_stats()

    assert stats["channels"] == 2
    assert stats["total_messages"] == 3
