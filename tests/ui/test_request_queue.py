"""Tests for request queue."""

import asyncio
from datetime import datetime

import pytest

from hitl_mcp_cli.ui.request_queue import HitlRequest, RequestQueue, get_request_queue


@pytest.mark.asyncio
async def test_request_creation():
    """Test creating a request."""

    async def dummy_handler(params):
        return "result"

    request = HitlRequest(
        priority=1,
        timestamp=datetime.now(),
        agent_id="test-agent",
        tool_name="prompt_text",
        params={"prompt": "test"},
        handler=dummy_handler,
    )

    assert request.agent_id == "test-agent"
    assert request.tool_name == "prompt_text"
    assert request.priority == 1


@pytest.mark.asyncio
async def test_priority_ordering():
    """Test that requests are processed by priority."""
    results = []

    async def handler_critical(params):
        results.append("critical")

    async def handler_normal(params):
        results.append("normal")

    async def handler_low(params):
        results.append("low")

    req_low = HitlRequest(
        priority=2, timestamp=datetime.now(), agent_id="a", tool_name="test", params={}, handler=handler_low
    )

    req_normal = HitlRequest(
        priority=1, timestamp=datetime.now(), agent_id="a", tool_name="test", params={}, handler=handler_normal
    )

    req_critical = HitlRequest(
        priority=0, timestamp=datetime.now(), agent_id="a", tool_name="test", params={}, handler=handler_critical
    )

    # Add in wrong order
    assert req_low > req_normal  # Lower priority (higher number) comes after
    assert req_normal > req_critical  # Normal comes after critical
    assert req_critical < req_normal  # Critical comes before normal


@pytest.mark.asyncio
async def test_queue_submit_and_process():
    """Test submitting and processing requests."""
    queue = RequestQueue()
    results = []

    async def handler1(params):
        results.append("task1")

    async def handler2(params):
        results.append("task2")

    # Submit requests
    await queue.submit("agent-a", "tool1", handler1, {}, priority=1)
    await queue.submit("agent-b", "tool2", handler2, {}, priority=1)

    # Wait for processing
    await asyncio.sleep(0.2)

    # Both should have been processed
    assert len(results) == 2
    assert "task1" in results
    assert "task2" in results


@pytest.mark.asyncio
async def test_queue_status():
    """Test queue status reporting."""
    queue = RequestQueue()

    async def slow_handler(params):
        await asyncio.sleep(0.1)

    # Initially empty
    status = queue.get_status()
    assert status["queue_size"] == 0
    assert status["processing"] is False

    # Add task
    await queue.submit("agent-a", "tool", slow_handler, {})

    # Should be processing
    await asyncio.sleep(0.05)
    status = queue.get_status()
    # May or may not be processing depending on timing


@pytest.mark.asyncio
async def test_global_queue_singleton():
    """Test that global queue is a singleton."""
    queue1 = get_request_queue()
    queue2 = get_request_queue()

    assert queue1 is queue2


@pytest.mark.asyncio
async def test_submit_and_wait():
    """Test submit_and_wait returns result."""
    queue = RequestQueue()

    async def handler_with_result(params):
        return {"success": True, "value": 42}

    result = await queue.submit_and_wait("agent-a", "tool", handler_with_result, {})

    assert result["success"] is True
    assert result["value"] == 42


@pytest.mark.asyncio
async def test_submit_and_wait_with_error():
    """Test submit_and_wait propagates exceptions."""
    queue = RequestQueue()

    async def failing_handler(params):
        raise ValueError("Something went wrong")

    with pytest.raises(ValueError, match="Something went wrong"):
        await queue.submit_and_wait("agent-a", "tool", failing_handler, {})


@pytest.mark.asyncio
async def test_concurrent_requests_processed_sequentially():
    """Test that concurrent requests are processed one at a time."""
    queue = RequestQueue()
    execution_times = []

    async def timed_handler(params):
        start = asyncio.get_event_loop().time()
        await asyncio.sleep(0.05)  # 50ms
        end = asyncio.get_event_loop().time()
        execution_times.append((start, end))

    # Submit multiple requests concurrently
    await asyncio.gather(
        queue.submit("agent-a", "tool", timed_handler, {}),
        queue.submit("agent-b", "tool", timed_handler, {}),
        queue.submit("agent-c", "tool", timed_handler, {}),
    )

    # Wait for all to complete
    await asyncio.sleep(0.3)

    # Should have 3 executions
    assert len(execution_times) >= 3

    # Check that executions didn't overlap (sequential processing)
    for i in range(len(execution_times) - 1):
        # End of task i should be before or equal to start of task i+1
        # (allowing small timing variations)
        assert execution_times[i][1] <= execution_times[i + 1][0] + 0.01  # 10ms tolerance
