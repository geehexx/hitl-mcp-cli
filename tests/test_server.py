"""Integration tests for hitl-mcp-cli server.

Tests the full MCP protocol initialization sequence and tool execution.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastmcp import Client

from hitl_mcp_cli.server import mcp


@pytest.fixture
async def mcp_client() -> Client:
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

    # Verify hitl_collect schema
    collect = tools_by_name["hitl_collect"]
    assert collect.description is not None
    assert "input" in collect.description.lower() or "collect" in collect.description.lower()
    assert collect.inputSchema is not None
    assert "message" in collect.inputSchema["properties"]

    # Verify hitl_ask schema (alias for hitl_collect)
    ask = tools_by_name["hitl_ask"]
    assert ask.description is not None
    assert "alias" in ask.description.lower() or "collect" in ask.description.lower()
    assert ask.inputSchema is not None
    assert "message" in ask.inputSchema["properties"]

    # Verify hitl_choose schema
    choose = tools_by_name["hitl_choose"]
    assert choose.description is not None
    assert "select" in choose.description.lower() or "option" in choose.description.lower()
    assert choose.inputSchema is not None
    assert "message" in choose.inputSchema["properties"]

    # Verify hitl_confirm schema
    confirm = tools_by_name["hitl_confirm"]
    assert confirm.description is not None
    assert "confirm" in confirm.description.lower()
    assert confirm.inputSchema is not None
    assert "message" in confirm.inputSchema["properties"]

    # Verify hitl_notify schema
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
async def test_hitl_collect_tool(mcp_client: Client) -> None:
    """Test hitl_collect tool execution with mocked input."""
    with patch("hitl_mcp_cli.server.prompt_text", new_callable=AsyncMock) as mock_prompt:
        mock_prompt.return_value = "Test User Input"

        result = await mcp_client.call_tool(
            "hitl_collect", {"message": "Enter your name:", "default": "User"}
        )

        assert result is not None
        assert result.data == "Test User Input"
        mock_prompt.assert_called_once_with("Enter your name:", "User", False, None, None, None)


@pytest.mark.asyncio
async def test_hitl_ask_alias(mcp_client: Client) -> None:
    """Test hitl_ask delegates to hitl_collect."""
    with patch("hitl_mcp_cli.server.prompt_text", new_callable=AsyncMock) as mock_prompt:
        mock_prompt.return_value = "Ask Response"

        result = await mcp_client.call_tool("hitl_ask", {"message": "What is your name?", "default": "User"})

        assert result is not None
        assert result.data == "Ask Response"
        mock_prompt.assert_called_once_with("What is your name?", "User", False, None, None, None)


@pytest.mark.asyncio
async def test_hitl_choose_tool(mcp_client: Client) -> None:
    """Test hitl_choose tool execution with mocked input."""
    with patch("hitl_mcp_cli.server.prompt_select", new_callable=AsyncMock) as mock_select:
        mock_select.return_value = "Option B"

        result = await mcp_client.call_tool(
            "hitl_choose",
            {
                "message": "Choose an option:",
                "choices": ["Option A", "Option B", "Option C"],
                "default": "Option A",
                "multiple": False,
            },
        )

        assert result is not None
        assert result.data == "Option B"
        mock_select.assert_called_once()


@pytest.mark.asyncio
async def test_hitl_confirm_tool(mcp_client: Client) -> None:
    """Test hitl_confirm tool execution with mocked input."""
    with patch("hitl_mcp_cli.server.prompt_confirm", new_callable=AsyncMock) as mock_confirm:
        mock_confirm.return_value = True

        result = await mcp_client.call_tool(
            "hitl_confirm", {"message": "Do you want to continue?", "default": False}
        )

        assert result is not None
        assert result.data == {"action": "accept", "timed_out": False}
        mock_confirm.assert_called_once_with("Do you want to continue?", False, notes=None)


@pytest.mark.asyncio
async def test_hitl_confirm_with_context(mcp_client: Client) -> None:
    """Test hitl_confirm displays context panel before prompt."""
    with (
        patch("hitl_mcp_cli.server.prompt_confirm", new_callable=AsyncMock) as mock_confirm,
        patch("hitl_mcp_cli.server.display_notification") as mock_notify,
    ):
        mock_confirm.return_value = True

        result = await mcp_client.call_tool(
            "hitl_confirm",
            {"message": "Deploy?", "context": "Version 2.0 to production"},
        )

        assert result is not None
        assert result.data == {"action": "accept", "timed_out": False}
        mock_notify.assert_called_once_with("Context", "Version 2.0 to production", "info")


@pytest.mark.asyncio
async def test_hitl_confirm_with_timeout_success(mcp_client: Client) -> None:
    """Test hitl_confirm with timeout_seconds returns timed_out field."""
    with patch("hitl_mcp_cli.server.prompt_confirm", new_callable=AsyncMock) as mock_confirm:
        mock_confirm.return_value = True

        result = await mcp_client.call_tool(
            "hitl_confirm",
            {"message": "Continue?", "timeout_seconds": 30},
        )

        assert result is not None
        assert result.data == {"action": "accept", "timed_out": False}


@pytest.mark.asyncio
async def test_hitl_confirm_with_timeout_expired(mcp_client: Client) -> None:
    """Test hitl_confirm returns decline+timed_out when timeout expires."""
    with patch("hitl_mcp_cli.server.prompt_confirm", new_callable=AsyncMock) as mock_confirm:
        import asyncio

        async def slow_confirm(*args, **kwargs):
            await asyncio.sleep(2)
            return True

        mock_confirm.side_effect = slow_confirm

        result = await mcp_client.call_tool(
            "hitl_confirm",
            {"message": "Continue?", "timeout_seconds": 1},
        )

        assert result is not None
        assert result.data == {"action": "decline", "timed_out": True}


@pytest.mark.asyncio
async def test_hitl_collect_path_type(mcp_client: Client) -> None:
    """Test hitl_collect with input_type=path."""
    with patch("hitl_mcp_cli.server.prompt_path", new_callable=AsyncMock) as mock_path:
        mock_path.return_value = "/tmp/test.txt"

        result = await mcp_client.call_tool(
            "hitl_collect",
            {"message": "Enter file path:", "input_type": "path", "default": None},
        )

        assert result is not None
        assert result.data == "/tmp/test.txt"
        mock_path.assert_called_once()


@pytest.mark.asyncio
async def test_hitl_notify_tool(mcp_client: Client) -> None:
    """Test hitl_notify tool execution with mocked display."""
    with patch("hitl_mcp_cli.server.display_notification") as mock_notify:
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
        mock_notify.assert_called_once_with(
            "Task Complete", "Successfully completed the task", "success", None
        )


@pytest.mark.asyncio
async def test_hitl_choose_multiple(mcp_client: Client) -> None:
    """Test hitl_choose with multiple selections."""
    with patch("hitl_mcp_cli.server.prompt_checkbox", new_callable=AsyncMock) as mock_checkbox:
        mock_checkbox.return_value = ["Option A", "Option C"]

        result = await mcp_client.call_tool(
            "hitl_choose",
            {
                "message": "Select multiple options:",
                "choices": ["Option A", "Option B", "Option C"],
                "multiple": True,
            },
        )

        assert result is not None
        assert result.data == ["Option A", "Option C"]
        mock_checkbox.assert_called_once()


@pytest.mark.asyncio
async def test_stateless_http_transport() -> None:
    """Regression: server must use stateless_http=True for independent HTTP requests.

    Without stateless_http=True, MCP clients that make independent POST requests
    (like Kiro CLI) get ClientDisconnect errors because FastMCP expects persistent
    connection state.
    """
    from unittest.mock import MagicMock

    with patch.object(mcp, "run", wraps=MagicMock()) as mock_run:
        from hitl_mcp_cli.cli import main

        with patch("argparse.ArgumentParser.parse_args") as mock_args:
            mock_args.return_value = MagicMock(host="127.0.0.1", port=5555, no_banner=True, no_tui=True)
            main()

        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args[1]
        assert (
            call_kwargs.get("stateless_http") is True
        ), "mcp.run() must pass stateless_http=True for stateless HTTP clients"
        assert call_kwargs.get("transport") == "streamable-http"


@pytest.mark.asyncio
async def test_hitl_collect_with_notes(mcp_client: Client) -> None:
    """Test hitl_collect passes notes to prompt_text."""
    with patch("hitl_mcp_cli.server.prompt_text", new_callable=AsyncMock) as mock_prompt:
        mock_prompt.return_value = "response"

        result = await mcp_client.call_tool(
            "hitl_collect",
            {"message": "Enter name:", "notes": "This is context info"},
        )

        assert result is not None
        assert result.data == "response"
        mock_prompt.assert_called_once_with("Enter name:", None, False, None, None, "This is context info")


@pytest.mark.asyncio
async def test_hitl_choose_escape_hatch_all_selected(mcp_client: Client) -> None:
    """Test escape hatch triggers when all choices selected and note provided."""
    with patch("hitl_mcp_cli.server.prompt_checkbox", new_callable=AsyncMock) as mock_checkbox:
        mock_checkbox.return_value = {"selected": ["A", "B", "C"], "note": "I want everything"}

        result = await mcp_client.call_tool(
            "hitl_choose",
            {"message": "Pick:", "choices": ["A", "B", "C"], "multiple": True},
        )

        assert result is not None
        assert result.data == {"selected": ["A", "B", "C"], "note": "I want everything"}


@pytest.mark.asyncio
async def test_hitl_choose_escape_hatch_none_selected(mcp_client: Client) -> None:
    """Test escape hatch triggers when no choices selected and note provided."""
    with patch("hitl_mcp_cli.server.prompt_checkbox", new_callable=AsyncMock) as mock_checkbox:
        mock_checkbox.return_value = {"selected": [], "note": "None of these apply"}

        result = await mcp_client.call_tool(
            "hitl_choose",
            {"message": "Pick:", "choices": ["A", "B", "C"], "multiple": True},
        )

        assert result is not None
        assert result.data == {"selected": [], "note": "None of these apply"}


@pytest.mark.asyncio
async def test_hitl_choose_no_escape_hatch_partial(mcp_client: Client) -> None:
    """Test no escape hatch when partial selection (normal behavior)."""
    with patch("hitl_mcp_cli.server.prompt_checkbox", new_callable=AsyncMock) as mock_checkbox:
        mock_checkbox.return_value = ["A", "B"]

        result = await mcp_client.call_tool(
            "hitl_choose",
            {"message": "Pick:", "choices": ["A", "B", "C"], "multiple": True},
        )

        assert result is not None
        assert result.data == ["A", "B"]
