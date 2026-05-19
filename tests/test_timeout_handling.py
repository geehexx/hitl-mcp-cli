"""Tests for timeout handling and retry scenarios."""

from __future__ import annotations

import asyncio

import pytest
from fastmcp import Client

from hitl_mcp_cli.server import configure_tui_mode, mcp
from hitl_mcp_cli.tui.queue import HITLQueue


@pytest.fixture(autouse=True)
def _pin_timeout_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HITL_MIN_WAIT_MIN", "0")
    monkeypatch.setenv("HITL_DEFAULT_WAIT_MIN", "0.1")
    import hitl_mcp_cli.timeout_config as tc

    tc._config = None
    yield
    tc._config = None


@pytest.fixture
async def tui_queue() -> HITLQueue:
    queue = HITLQueue()
    configure_tui_mode(queue, None)  # type: ignore[arg-type]
    yield queue
    configure_tui_mode(None, None)  # type: ignore[arg-type]


@pytest.fixture
async def mcp_client(tui_queue: HITLQueue) -> Client:
    async with Client(mcp) as client:
        yield client


@pytest.mark.asyncio
async def test_hitl_confirm_timeout_returns_decline(mcp_client: Client, tui_queue: HITLQueue) -> None:
    """hitl_confirm with max_wait_minutes=0.02 and no resolution → timeout shape."""
    result = await mcp_client.call_tool("hitl_confirm", {"message": "Deploy?", "max_wait_minutes": 0.02})
    assert result.data["status"] == "timeout"
    assert "question_id" in result.data


@pytest.mark.asyncio
async def test_hitl_confirm_no_timeout_when_fast(mcp_client: Client, tui_queue: HITLQueue) -> None:
    """Fast response within timeout window → timed_out: false."""

    async def _resolve() -> None:
        req = await tui_queue.get()
        tui_queue.resolve(req, {"action": "accept"})

    task = asyncio.create_task(_resolve())
    result = await mcp_client.call_tool("hitl_confirm", {"message": "Continue?", "max_wait_minutes": 5})
    await task
    assert result.data == {"action": "accept", "timed_out": False}


@pytest.mark.asyncio
async def test_hitl_collect_resolves(mcp_client: Client, tui_queue: HITLQueue) -> None:
    """hitl_collect resolves when queue resolves."""

    async def _resolve() -> None:
        req = await tui_queue.get()
        tui_queue.resolve(req, "response")

    task = asyncio.create_task(_resolve())
    result = await mcp_client.call_tool("hitl_collect", {"message": "Name:"})
    await task
    assert result.data == "response"


@pytest.mark.asyncio
async def test_multiple_sequential_calls(mcp_client: Client, tui_queue: HITLQueue) -> None:
    """Test multiple sequential tool calls work correctly."""
    for expected in ["Response 1", "Response 2", "Response 3"]:

        async def _resolve(val: str = expected) -> None:
            req = await tui_queue.get()
            tui_queue.resolve(req, val)

        task = asyncio.create_task(_resolve())
        result = await mcp_client.call_tool("hitl_collect", {"message": "Prompt:"})
        await task
        assert result.data == expected


@pytest.mark.asyncio
async def test_server_healthy_after_timeout(mcp_client: Client, tui_queue: HITLQueue) -> None:
    """Server still accepts calls after a timeout."""
    r1 = await mcp_client.call_tool("hitl_confirm", {"message": "Slow?", "max_wait_minutes": 0.02})
    assert r1.data["status"] == "timeout"

    async def _resolve() -> None:
        req = await tui_queue.get()
        tui_queue.resolve(req, "healthy")

    task = asyncio.create_task(_resolve())
    r2 = await mcp_client.call_tool("hitl_collect", {"message": "Name:", "max_wait_minutes": 5})
    await task
    assert r2.data == "healthy"


@pytest.mark.asyncio
async def test_error_recovery_after_reject(mcp_client: Client, tui_queue: HITLQueue) -> None:
    """Server recovers after a queue rejection."""

    async def _reject_then_resolve() -> None:
        req1 = await tui_queue.get()
        tui_queue.reject(req1, RuntimeError("First call failed"))
        req2 = await tui_queue.get()
        tui_queue.resolve(req2, "Second call success")

    task = asyncio.create_task(_reject_then_resolve())

    with pytest.raises(Exception):
        await mcp_client.call_tool("hitl_collect", {"message": "Test 1:"})

    result = await mcp_client.call_tool("hitl_collect", {"message": "Test 2:"})
    await task
    assert result.data == "Second call success"
