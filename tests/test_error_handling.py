"""Tests for error handling across the application."""

from __future__ import annotations

import asyncio

import pytest
from fastmcp import Client

from hitl_mcp_cli.server import configure_tui_mode, mcp
from hitl_mcp_cli.tui.queue import HITLQueue


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
async def test_hitl_collect_cancel_from_queue(mcp_client: Client, tui_queue: HITLQueue) -> None:
    """Test hitl_collect returns cancel dict when queue resolves with cancel."""

    async def _resolve() -> None:
        req = await tui_queue.get()
        tui_queue.resolve(req, {"action": "cancel"})

    task = asyncio.create_task(_resolve())
    result = await mcp_client.call_tool("hitl_collect", {"message": "Test:"})
    await task
    assert result is not None
    assert result.data == {"action": "cancel"}


@pytest.mark.asyncio
async def test_hitl_choose_cancel_from_queue(mcp_client: Client, tui_queue: HITLQueue) -> None:
    """Test hitl_choose returns cancel dict when queue resolves with cancel."""

    async def _resolve() -> None:
        req = await tui_queue.get()
        tui_queue.resolve(req, {"action": "cancel"})

    task = asyncio.create_task(_resolve())
    result = await mcp_client.call_tool("hitl_choose", {"message": "Choose:", "choices": ["A", "B"]})
    await task
    assert result is not None
    assert result.data == {"action": "cancel"}


@pytest.mark.asyncio
async def test_hitl_confirm_cancel_from_queue(mcp_client: Client, tui_queue: HITLQueue) -> None:
    """Test hitl_confirm returns cancel dict when queue resolves with cancel."""

    async def _resolve() -> None:
        req = await tui_queue.get()
        tui_queue.resolve(req, {"action": "cancel"})

    task = asyncio.create_task(_resolve())
    result = await mcp_client.call_tool("hitl_confirm", {"message": "Proceed?"})
    await task
    assert result is not None
    assert result.data == {"action": "cancel", "timed_out": False}


@pytest.mark.asyncio
async def test_hitl_notify_acknowledged(mcp_client: Client, tui_queue: HITLQueue) -> None:
    """Test hitl_notify always returns acknowledged."""
    result = await mcp_client.call_tool("hitl_notify", {"message": "Message"})
    assert result is not None
    assert result.data == {"acknowledged": True}


@pytest.mark.asyncio
async def test_hitl_choose_multiple_cancel(mcp_client: Client, tui_queue: HITLQueue) -> None:
    """Test multiple selection cancel from queue."""

    async def _resolve() -> None:
        req = await tui_queue.get()
        tui_queue.resolve(req, {"action": "cancel"})

    task = asyncio.create_task(_resolve())
    result = await mcp_client.call_tool(
        "hitl_choose",
        {"message": "Select:", "choices": ["A", "B"], "multiple": True},
    )
    await task
    assert result is not None
    assert result.data == {"action": "cancel"}


@pytest.mark.asyncio
async def test_hitl_collect_required_empty(mcp_client: Client, tui_queue: HITLQueue) -> None:
    """Test required=True with empty input returns cancel."""

    async def _resolve() -> None:
        req = await tui_queue.get()
        tui_queue.resolve(req, "")

    task = asyncio.create_task(_resolve())
    result = await mcp_client.call_tool("hitl_collect", {"message": "Name:", "required": True})
    await task
    assert result is not None
    assert isinstance(result.data, dict)
    assert result.data.get("action") == "cancel"


@pytest.mark.asyncio
async def test_hitl_confirm_timeout(mcp_client: Client, tui_queue: HITLQueue) -> None:
    """Test hitl_confirm returns timed_out when timeout expires."""
    result = await mcp_client.call_tool(
        "hitl_confirm",
        {"message": "Deploy?", "timeout_seconds": 1},
    )
    assert result is not None
    assert result.data == {"action": "decline", "timed_out": True}
