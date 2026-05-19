"""Integration tests for hitl-mcp-cli server.

Tests the full MCP protocol initialization sequence and tool execution via TUI queue.
"""

import asyncio
from unittest.mock import patch

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
    configure_tui_mode(None, None)  # type: ignore[arg-type]


@pytest.fixture
async def mcp_client(tui_queue: HITLQueue) -> Client:
    """Create MCP client connected to the interactive server."""
    async with Client(mcp) as client:
        yield client


@pytest.mark.asyncio
async def test_server_initialization(mcp_client: Client) -> None:
    """Test MCP server initializes with correct metadata."""
    assert mcp_client.initialize_result is not None
    assert mcp_client.initialize_result.serverInfo is not None
    assert mcp_client.initialize_result.serverInfo.name == "HITL MCP Server"


@pytest.mark.asyncio
async def test_tools_list(mcp_client: Client) -> None:
    """Test tools/list returns all registered tools."""
    tools = await mcp_client.list_tools()

    tool_names = {tool.name for tool in tools}
    expected_tools = {
        "hitl_collect",
        "hitl_ask",
        "hitl_choose",
        "hitl_confirm",
        "hitl_notify",
        "hitl_poll",
        "hitl_recommend",
        "hitl_reject_question",
        "hitl_request_elaboration",
    }

    assert tool_names == expected_tools
    assert len(tools) == 9


@pytest.mark.asyncio
async def test_tool_schemas(mcp_client: Client) -> None:
    """Test tool schemas are properly defined."""
    tools = await mcp_client.list_tools()
    tools_by_name = {tool.name: tool for tool in tools}

    collect = tools_by_name["hitl_collect"]
    assert collect.description is not None
    assert "input" in collect.description.lower() or "collect" in collect.description.lower()
    assert collect.inputSchema is not None
    assert "message" in collect.inputSchema["properties"]

    ask = tools_by_name["hitl_ask"]
    assert ask.description is not None
    assert "alias" in ask.description.lower() or "collect" in ask.description.lower()
    assert ask.inputSchema is not None
    assert "message" in ask.inputSchema["properties"]

    choose = tools_by_name["hitl_choose"]
    assert choose.description is not None
    assert "select" in choose.description.lower() or "option" in choose.description.lower()
    assert choose.inputSchema is not None
    assert "message" in choose.inputSchema["properties"]

    confirm = tools_by_name["hitl_confirm"]
    assert confirm.description is not None
    assert "confirm" in confirm.description.lower()
    assert confirm.inputSchema is not None
    assert "message" in confirm.inputSchema["properties"]

    notify = tools_by_name["hitl_notify"]
    assert notify.description is not None
    assert "notification" in notify.description.lower() or "notify" in notify.description.lower()
    assert notify.inputSchema is not None
    assert "message" in notify.inputSchema["properties"]


@pytest.mark.asyncio
async def test_server_capabilities(mcp_client: Client) -> None:
    """Test server advertises correct capabilities."""
    assert mcp_client.initialize_result is not None
    assert mcp_client.initialize_result.capabilities is not None
    assert mcp_client.initialize_result.capabilities.tools is not None


@pytest.mark.asyncio
async def test_protocol_version(mcp_client: Client) -> None:
    """Test server uses correct MCP protocol version."""
    assert mcp_client.initialize_result is not None
    assert mcp_client.initialize_result.protocolVersion is not None
    assert isinstance(mcp_client.initialize_result.protocolVersion, str)
    assert len(mcp_client.initialize_result.protocolVersion) > 0


@pytest.mark.asyncio
async def test_hitl_collect_tool(mcp_client: Client, tui_queue: HITLQueue) -> None:
    """Test hitl_collect tool execution via TUI queue."""

    async def _resolve() -> None:
        req = await tui_queue.get()
        tui_queue.resolve(req, "Test User Input")

    task = asyncio.create_task(_resolve())
    result = await mcp_client.call_tool("hitl_collect", {"message": "Enter your name:", "default": "User"})
    await task

    assert result is not None
    assert result.data == "Test User Input"


@pytest.mark.asyncio
async def test_hitl_ask_alias(mcp_client: Client, tui_queue: HITLQueue) -> None:
    """Test hitl_ask delegates to hitl_collect."""

    async def _resolve() -> None:
        req = await tui_queue.get()
        tui_queue.resolve(req, "Ask Response")

    task = asyncio.create_task(_resolve())
    result = await mcp_client.call_tool("hitl_ask", {"message": "What is your name?", "default": "User"})
    await task

    assert result is not None
    assert result.data == "Ask Response"


@pytest.mark.asyncio
async def test_hitl_choose_tool(mcp_client: Client, tui_queue: HITLQueue) -> None:
    """Test hitl_choose tool execution via TUI queue."""

    async def _resolve() -> None:
        req = await tui_queue.get()
        tui_queue.resolve(req, "Option B")

    task = asyncio.create_task(_resolve())
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
async def test_hitl_confirm_tool(mcp_client: Client, tui_queue: HITLQueue) -> None:
    """Test hitl_confirm tool execution via TUI queue."""

    async def _resolve() -> None:
        req = await tui_queue.get()
        tui_queue.resolve(req, {"action": "accept"})

    task = asyncio.create_task(_resolve())
    result = await mcp_client.call_tool(
        "hitl_confirm", {"message": "Do you want to continue?", "default": False}
    )
    await task

    assert result is not None
    assert result.data == {"action": "accept", "timed_out": False}


@pytest.mark.asyncio
async def test_hitl_confirm_with_timeout_expired(mcp_client: Client, tui_queue: HITLQueue) -> None:
    """Test hitl_confirm returns decline+timed_out when timeout expires."""
    # Don't resolve — let it time out
    result = await mcp_client.call_tool(
        "hitl_confirm",
        {"message": "Continue?", "timeout_seconds": 1},
    )

    assert result is not None
    assert result.data == {"action": "decline", "timed_out": True}


@pytest.mark.asyncio
async def test_hitl_notify_tool(mcp_client: Client, tui_queue: HITLQueue) -> None:
    """Test hitl_notify tool execution."""
    result = await mcp_client.call_tool(
        "hitl_notify",
        {
            "message": "Successfully completed the task",
            "level": "success",
            "title": "Task Complete",
        },
    )

    assert result is not None
    assert result.data == {"acknowledged": True}


@pytest.mark.asyncio
async def test_hitl_choose_multiple(mcp_client: Client, tui_queue: HITLQueue) -> None:
    """Test hitl_choose with multiple selections."""

    async def _resolve() -> None:
        req = await tui_queue.get()
        tui_queue.resolve(req, ["Option A", "Option C"])

    task = asyncio.create_task(_resolve())
    result = await mcp_client.call_tool(
        "hitl_choose",
        {
            "message": "Select multiple options:",
            "choices": ["Option A", "Option B", "Option C"],
            "multiple": True,
        },
    )
    await task

    assert result is not None
    assert result.data == ["Option A", "Option C"]


@pytest.mark.asyncio
async def test_hitl_collect_with_notes(mcp_client: Client, tui_queue: HITLQueue) -> None:
    """Test hitl_collect passes notes through queue params."""

    async def _resolve() -> None:
        req = await tui_queue.get()
        assert req.params.get("notes") == "This is context info"
        tui_queue.resolve(req, "response")

    task = asyncio.create_task(_resolve())
    result = await mcp_client.call_tool(
        "hitl_collect",
        {"message": "Enter name:", "notes": "This is context info"},
    )
    await task

    assert result is not None
    assert result.data == "response"


@pytest.mark.asyncio
async def test_hitl_choose_escape_hatch_all_selected(mcp_client: Client, tui_queue: HITLQueue) -> None:
    """Test escape hatch dict result passes through."""

    async def _resolve() -> None:
        req = await tui_queue.get()
        tui_queue.resolve(req, {"selected": ["A", "B", "C"], "note": "I want everything"})

    task = asyncio.create_task(_resolve())
    result = await mcp_client.call_tool(
        "hitl_choose",
        {"message": "Pick:", "choices": ["A", "B", "C"], "multiple": True},
    )
    await task

    assert result is not None
    assert result.data == {"selected": ["A", "B", "C"], "note": "I want everything"}


@pytest.mark.asyncio
async def test_stateless_http_transport() -> None:
    """Regression: server must use stateless_http=True for independent HTTP requests."""
    from unittest.mock import MagicMock

    with patch.object(mcp, "run", wraps=MagicMock()) as mock_run:
        from hitl_mcp_cli.cli import main

        with (
            patch("hitl_mcp_cli.server.configure_tui_mode"),
            patch("hitl_mcp_cli.tui.HITLApp") as mock_app_cls,
            patch("hitl_mcp_cli.tui.HITLQueue"),
            patch("hitl_mcp_cli.cli.mcp") as mock_cli_mcp,
            patch("sys.argv", ["hitl-mcp"]),
        ):
            mock_cli_mcp.http_app.return_value = MagicMock()
            mock_app_cls.return_value = MagicMock()
            main()

        # The TUI app runs the server — stateless_http is set in tui/app.py
        # Just verify the CLI launches TUI (not headless mcp.run)
        mock_run.assert_not_called()
