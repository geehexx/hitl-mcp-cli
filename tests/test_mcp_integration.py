"""Integration tests for MCP protocol interaction.

Tests the full MCP request/response cycle via TUI queue.
"""

from __future__ import annotations

import asyncio
from typing import Any

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


def _resolve(queue: HITLQueue, value: Any) -> asyncio.Task[None]:
    async def _r() -> None:
        req = await queue.get()
        queue.resolve(req, value)

    return asyncio.create_task(_r())


class TestMCPProtocol:
    """Test MCP protocol compliance and behavior."""

    @pytest.mark.asyncio
    async def test_initialize_handshake(self, mcp_client: Client) -> None:
        assert mcp_client.initialize_result is not None
        assert mcp_client.initialize_result.serverInfo is not None
        assert mcp_client.initialize_result.serverInfo.name == "HITL MCP Server"
        assert mcp_client.initialize_result.protocolVersion is not None

    @pytest.mark.asyncio
    async def test_server_capabilities(self, mcp_client: Client) -> None:
        assert mcp_client.initialize_result is not None
        assert mcp_client.initialize_result.capabilities is not None
        assert mcp_client.initialize_result.capabilities.tools is not None

    @pytest.mark.asyncio
    async def test_tools_list_response(self, mcp_client: Client) -> None:
        tools = await mcp_client.list_tools()
        assert len(tools) == 6
        tool_names = {tool.name for tool in tools}
        assert tool_names == {
            "hitl_collect",
            "hitl_ask",
            "hitl_choose",
            "hitl_confirm",
            "hitl_notify",
            "hitl_poll",
        }
        for tool in tools:
            assert tool.name is not None
            assert tool.description is not None
            assert tool.inputSchema is not None
            assert "properties" in tool.inputSchema


class TestToolExecution:
    """Test tool execution through MCP protocol."""

    @pytest.mark.asyncio
    async def test_hitl_collect_execution(self, mcp_client: Client, tui_queue: HITLQueue) -> None:
        task = _resolve(tui_queue, "User Response")
        result = await mcp_client.call_tool(
            "hitl_collect",
            {"message": "Enter text:", "default": "default", "input_type": "text"},
        )
        await task
        assert result is not None
        assert result.data == "User Response"
        assert not result.is_error

    @pytest.mark.asyncio
    async def test_hitl_collect_multiline(self, mcp_client: Client, tui_queue: HITLQueue) -> None:
        task = _resolve(tui_queue, "line1\nline2")
        result = await mcp_client.call_tool(
            "hitl_collect",
            {"message": "Enter text:", "input_type": "multiline"},
        )
        await task
        assert result is not None
        assert result.data == "line1\nline2"
        assert not result.is_error

    @pytest.mark.asyncio
    async def test_hitl_collect_path(self, mcp_client: Client, tui_queue: HITLQueue) -> None:
        task = _resolve(tui_queue, "/home/user/config.yaml")
        result = await mcp_client.call_tool(
            "hitl_collect",
            {"message": "Select file:", "input_type": "path"},
        )
        await task
        assert result is not None
        assert result.data == "/home/user/config.yaml"
        assert not result.is_error

    @pytest.mark.asyncio
    async def test_hitl_choose_single(self, mcp_client: Client, tui_queue: HITLQueue) -> None:
        task = _resolve(tui_queue, "Choice B")
        result = await mcp_client.call_tool(
            "hitl_choose",
            {
                "message": "Select one:",
                "choices": ["Choice A", "Choice B", "Choice C"],
                "default": "Choice A",
                "multiple": False,
            },
        )
        await task
        assert result is not None
        assert result.data == "Choice B"
        assert not result.is_error

    @pytest.mark.asyncio
    async def test_hitl_choose_multiple(self, mcp_client: Client, tui_queue: HITLQueue) -> None:
        task = _resolve(tui_queue, ["Choice A", "Choice C"])
        result = await mcp_client.call_tool(
            "hitl_choose",
            {
                "message": "Select multiple:",
                "choices": ["Choice A", "Choice B", "Choice C"],
                "multiple": True,
            },
        )
        await task
        assert result is not None
        assert result.data == ["Choice A", "Choice C"]
        assert not result.is_error

    @pytest.mark.asyncio
    async def test_hitl_choose_with_options(self, mcp_client: Client, tui_queue: HITLQueue) -> None:
        task = _resolve(tui_queue, "Fast: Quick but uses more memory")
        result = await mcp_client.call_tool(
            "hitl_choose",
            {
                "message": "Select approach:",
                "options": [
                    {"value": "fast", "label": "Fast", "description": "Quick but uses more memory"},
                    {"value": "safe", "label": "Safe", "description": "Slower but reliable"},
                ],
            },
        )
        await task
        assert result is not None
        assert result.data == "fast"
        assert not result.is_error

    @pytest.mark.asyncio
    async def test_hitl_confirm_true(self, mcp_client: Client, tui_queue: HITLQueue) -> None:
        task = _resolve(tui_queue, {"action": "accept"})
        result = await mcp_client.call_tool("hitl_confirm", {"message": "Confirm action?", "default": False})
        await task
        assert result is not None
        assert result.data == {"action": "accept", "timed_out": False}
        assert not result.is_error

    @pytest.mark.asyncio
    async def test_hitl_confirm_false(self, mcp_client: Client, tui_queue: HITLQueue) -> None:
        task = _resolve(tui_queue, {"action": "decline"})
        result = await mcp_client.call_tool("hitl_confirm", {"message": "Confirm action?", "default": True})
        await task
        assert result is not None
        assert result.data == {"action": "decline", "timed_out": False}
        assert not result.is_error

    @pytest.mark.asyncio
    async def test_hitl_notify_execution(self, mcp_client: Client, tui_queue: HITLQueue) -> None:
        result = await mcp_client.call_tool(
            "hitl_notify",
            {"message": "Operation complete", "level": "success", "title": "Success"},
        )
        assert result is not None
        assert result.data == {"acknowledged": True}
        assert not result.is_error

    @pytest.mark.asyncio
    async def test_hitl_notify_default_title(self, mcp_client: Client, tui_queue: HITLQueue) -> None:
        result = await mcp_client.call_tool("hitl_notify", {"message": "Something happened"})
        assert result is not None
        assert result.data == {"acknowledged": True}

    @pytest.mark.asyncio
    async def test_hitl_ask_execution(self, mcp_client: Client, tui_queue: HITLQueue) -> None:
        task = _resolve(tui_queue, "Ask Response")
        result = await mcp_client.call_tool("hitl_ask", {"message": "What is your name?"})
        await task
        assert result is not None
        assert result.data == "Ask Response"

    @pytest.mark.asyncio
    async def test_hitl_confirm_with_timeout(self, mcp_client: Client, tui_queue: HITLQueue) -> None:
        task = _resolve(tui_queue, {"action": "accept"})
        result = await mcp_client.call_tool("hitl_confirm", {"message": "Deploy?", "timeout_seconds": 30})
        await task
        assert result is not None
        assert result.data["action"] == "accept"
        assert result.data["timed_out"] is False

    @pytest.mark.asyncio
    async def test_hitl_confirm_declined(self, mcp_client: Client, tui_queue: HITLQueue) -> None:
        task = _resolve(tui_queue, {"action": "decline"})
        result = await mcp_client.call_tool(
            "hitl_confirm", {"message": "Deploy to production?", "timeout_seconds": 0}
        )
        await task
        assert result is not None
        assert result.data == {"action": "decline", "timed_out": False}


class TestErrorHandling:
    """Test error handling in MCP protocol."""

    @pytest.mark.asyncio
    async def test_missing_required_parameter(self, mcp_client: Client) -> None:
        result = await mcp_client.call_tool("hitl_collect", {}, raise_on_error=False)
        assert result is not None
        assert result.is_error

    @pytest.mark.asyncio
    async def test_hitl_choose_no_choices_or_options(self, mcp_client: Client) -> None:
        result = await mcp_client.call_tool("hitl_choose", {"message": "Choose:"}, raise_on_error=False)
        assert result is not None
        assert result.is_error


class TestParameterHandling:
    """Test parameter validation and handling."""

    @pytest.mark.asyncio
    async def test_optional_parameters_omitted(self, mcp_client: Client, tui_queue: HITLQueue) -> None:
        task = _resolve(tui_queue, "Response")
        result = await mcp_client.call_tool("hitl_collect", {"message": "Enter text:"})
        await task
        assert result is not None
        assert not result.is_error

    @pytest.mark.asyncio
    async def test_notification_level_values(self, mcp_client: Client, tui_queue: HITLQueue) -> None:
        for level in ["success", "info", "warning", "error"]:
            result = await mcp_client.call_tool("hitl_notify", {"message": "Message", "level": level})
            assert result is not None
            assert not result.is_error


class TestConcurrentRequests:
    """Test handling of concurrent tool calls."""

    @pytest.mark.asyncio
    async def test_multiple_sequential_calls(self, mcp_client: Client, tui_queue: HITLQueue) -> None:
        for i in range(3):
            task = _resolve(tui_queue, f"Response {i + 1}")
            result = await mcp_client.call_tool("hitl_collect", {"message": f"Prompt {i}:"})
            await task
            assert result is not None
            assert not result.is_error
            assert result.data == f"Response {i + 1}"

    @pytest.mark.asyncio
    async def test_different_tools_sequential(self, mcp_client: Client, tui_queue: HITLQueue) -> None:
        task1 = _resolve(tui_queue, "Text response")
        result1 = await mcp_client.call_tool("hitl_collect", {"message": "Enter text:"})
        await task1
        assert result1 is not None
        assert not result1.is_error

        task2 = _resolve(tui_queue, {"action": "accept"})
        result2 = await mcp_client.call_tool("hitl_confirm", {"message": "Confirm?"})
        await task2
        assert result2 is not None
        assert not result2.is_error

        result3 = await mcp_client.call_tool("hitl_notify", {"message": "Complete"})
        assert result3 is not None
        assert not result3.is_error
