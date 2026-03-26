"""Regression tests for selection tools via TUI queue."""

import pytest
from fastmcp import Client

from hitl_mcp_cli.server import configure_tui_mode, mcp
from hitl_mcp_cli.tui.queue import HITLQueue


@pytest.fixture
async def tui_queue() -> HITLQueue:
    """Create a TUI queue and configure the server to use it."""
    queue = HITLQueue()
    configure_tui_mode(queue, None)  # type: ignore[arg-type]
    yield queue
    # Reset
    configure_tui_mode(None, None)  # type: ignore[arg-type]


@pytest.fixture
async def mcp_client(tui_queue: HITLQueue) -> Client:
    """Create MCP client connected to the interactive server."""
    async with Client(mcp) as client:
        yield client


@pytest.mark.asyncio
async def test_hitl_choose_short_list(mcp_client: Client, tui_queue: HITLQueue) -> None:
    """Test selection with short list routes through TUI queue."""

    async def _auto_resolve() -> None:
        req = await tui_queue.get()
        tui_queue.resolve(req, "Option B")

    import asyncio

    task = asyncio.create_task(_auto_resolve())

    result = await mcp_client.call_tool(
        "hitl_choose",
        {
            "message": "Choose an option:",
            "choices": ["Option A", "Option B", "Option C"],
            "default": "Option A",
            "multiple": False,
        },
    )
    await task

    assert result is not None
    assert result.data == "Option B"


@pytest.mark.asyncio
async def test_hitl_choose_multiple(mcp_client: Client, tui_queue: HITLQueue) -> None:
    """Test multiple selection routes through TUI queue."""
    import asyncio

    async def _auto_resolve() -> None:
        req = await tui_queue.get()
        tui_queue.resolve(req, ["Option A", "Option C"])

    task = asyncio.create_task(_auto_resolve())

    result = await mcp_client.call_tool(
        "hitl_choose",
        {
            "message": "Choose multiple:",
            "choices": ["Option A", "Option B", "Option C"],
            "multiple": True,
        },
    )
    await task

    assert result is not None
    assert result.data == ["Option A", "Option C"]


@pytest.mark.asyncio
async def test_hitl_choose_no_choices_raises(mcp_client: Client, tui_queue: HITLQueue) -> None:
    """Test hitl_choose raises when no choices provided."""
    from fastmcp.exceptions import ToolError

    with pytest.raises(ToolError):
        await mcp_client.call_tool(
            "hitl_choose",
            {"message": "Choose:", "multiple": False},
        )
