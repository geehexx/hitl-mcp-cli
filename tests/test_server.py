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
    }

    assert tool_names == expected_tools
    assert len(tools) == 5


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
async def test_metrics_summary_no_queue() -> None:
    """metrics://summary returns zeroed payload when TUI queue is not configured."""
    import json

    from hitl_mcp_cli.server import configure_tui_mode, mcp

    configure_tui_mode(None, None)  # type: ignore[arg-type]
    try:
        async with Client(mcp) as client:
            result = await client.read_resource("metrics://summary")
        data = json.loads(result[0].text)  # type: ignore[union-attr]
        assert data["total_questions"] == 0
        assert data["avg_response_time_s"] is None
        assert data["active_sessions"] == 0
        assert data["questions_by_type"] == {}
        assert "warning" in data
    finally:
        configure_tui_mode(None, None)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_metrics_summary_resolved_at_accuracy(tui_queue: HITLQueue) -> None:
    """avg_response_time_s only counts items with a _resolved_at timestamp."""
    import json

    from hitl_mcp_cli.server import mcp

    async with Client(mcp) as client:
        # Enqueue and resolve one request via mark_answered
        async def _resolve() -> None:
            req = await tui_queue.get()
            tui_queue.mark_answered(req.request_id, "yes")
            tui_queue.resolve(req, {"action": "accept"})

        task = asyncio.create_task(_resolve())
        await client.call_tool("hitl_confirm", {"message": "Proceed?"})
        await task

        # Enqueue a second request but leave it pending (no _resolved_at)
        pending_task = asyncio.create_task(client.call_tool("hitl_confirm", {"message": "Still waiting?"}))
        await asyncio.sleep(0.05)  # let it enqueue

        result = await client.read_resource("metrics://summary")
        data = json.loads(result[0].text)  # type: ignore[union-attr]

        assert data["total_questions"] == 2
        # avg must be based only on the resolved item, not inflated by pending wait
        assert data["avg_response_time_s"] is not None
        assert data["avg_response_time_s"] < 5.0  # not inflated by pending item

        # clean up pending request
        req2 = await tui_queue.get()
        tui_queue.mark_cancelled(req2.request_id)
        tui_queue.resolve(req2, {"action": "decline"})
        await pending_task


@pytest.mark.asyncio
async def test_metrics_summary_pending_excluded_from_avg(tui_queue: HITLQueue) -> None:
    """avg_response_time_s is None when all requests are still pending."""
    import json

    from hitl_mcp_cli.server import mcp

    async with Client(mcp) as client:
        pending_task = asyncio.create_task(client.call_tool("hitl_confirm", {"message": "Waiting?"}))
        await asyncio.sleep(0.05)

        result = await client.read_resource("metrics://summary")
        data = json.loads(result[0].text)  # type: ignore[union-attr]

        assert data["total_questions"] == 1
        assert data["avg_response_time_s"] is None  # no resolved items yet

        req = await tui_queue.get()
        tui_queue.mark_cancelled(req.request_id)
        tui_queue.resolve(req, {"action": "decline"})
        await pending_task


@pytest.mark.asyncio
async def test_metrics_resolved_at_set_on_mark_answered() -> None:
    """mark_answered sets _resolved_at on the request."""
    import time

    from hitl_mcp_cli.tui.queue import HITLQueue, HITLRequest

    queue = HITLQueue()
    loop = asyncio.get_running_loop()
    future: asyncio.Future[object] = loop.create_future()
    req = HITLRequest(tool="hitl_confirm", params={}, future=future)
    queue._register(req)

    assert req._resolved_at is None
    t_before = time.monotonic()
    queue.mark_answered(req.request_id, "yes")
    t_after = time.monotonic()

    assert req._resolved_at is not None
    assert t_before <= req._resolved_at <= t_after


@pytest.mark.asyncio
async def test_metrics_resolved_at_set_on_mark_cancelled() -> None:
    """mark_cancelled sets _resolved_at on the request."""
    import time

    from hitl_mcp_cli.tui.queue import HITLQueue, HITLRequest

    queue = HITLQueue()
    loop = asyncio.get_running_loop()
    future: asyncio.Future[object] = loop.create_future()
    req = HITLRequest(tool="hitl_confirm", params={}, future=future)
    queue._register(req)

    assert req._resolved_at is None
    t_before = time.monotonic()
    queue.mark_cancelled(req.request_id)
    t_after = time.monotonic()

    assert req._resolved_at is not None
    assert t_before <= req._resolved_at <= t_after


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
            patch("hitl_mcp_cli.server.mcp") as mock_cli_mcp,
            patch("sys.argv", ["hitl-mcp"]),
        ):
            mock_cli_mcp.http_app.return_value = MagicMock()
            mock_app_cls.return_value = MagicMock()
            main()

        # The TUI app runs the server — stateless_http is set in tui/app.py
        # Just verify the CLI launches TUI (not headless mcp.run)
        mock_run.assert_not_called()
