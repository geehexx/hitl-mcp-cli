"""Edge case tests for HITL MCP server.

Tests unusual inputs, boundary conditions, and error scenarios.
"""

from __future__ import annotations

import asyncio

import pytest
from fastmcp import Client

from hitl_mcp_cli.server import mcp
from hitl_mcp_cli.tui.queue import HITLQueue


@pytest.fixture
async def mcp_client(tui_queue: HITLQueue) -> Client:
    """Create MCP client connected to the server."""
    async with Client(mcp) as client:
        yield client


def _auto_resolve(queue: HITLQueue, value: object) -> asyncio.Task[None]:
    """Create a task that resolves the next queued request with value."""

    async def _resolve() -> None:
        req = await queue.get()
        queue.resolve(req, value)

    return asyncio.create_task(_resolve())


class TestInputEdgeCases:
    """Test edge cases for input handling."""

    @pytest.mark.asyncio
    async def test_empty_string_input(self, mcp_client: Client, tui_queue: HITLQueue) -> None:
        """Test empty string input is accepted."""
        task = _auto_resolve(tui_queue, "")
        result = await mcp_client.call_tool("hitl_collect", {"message": "Enter text:"})
        await task
        assert result is not None
        assert result.data == ""
        assert not result.is_error

    @pytest.mark.asyncio
    async def test_whitespace_only_input(self, mcp_client: Client, tui_queue: HITLQueue) -> None:
        """Test whitespace-only input is accepted."""
        task = _auto_resolve(tui_queue, "   \t\n  ")
        result = await mcp_client.call_tool("hitl_collect", {"message": "Enter text:"})
        await task
        assert result is not None
        assert result.data == "   \t\n  "
        assert not result.is_error

    @pytest.mark.asyncio
    async def test_unicode_emoji_input(self, mcp_client: Client, tui_queue: HITLQueue) -> None:
        """Test Unicode and emoji characters in input."""
        task = _auto_resolve(tui_queue, "Hello 世界 🌍 🚀 ñ é")
        result = await mcp_client.call_tool("hitl_collect", {"message": "Enter text:"})
        await task
        assert result is not None
        assert result.data == "Hello 世界 🌍 🚀 ñ é"
        assert not result.is_error

    @pytest.mark.asyncio
    async def test_very_long_input(self, mcp_client: Client, tui_queue: HITLQueue) -> None:
        """Test very long input (10KB+)."""
        long_text = "A" * 10000
        task = _auto_resolve(tui_queue, long_text)
        result = await mcp_client.call_tool("hitl_collect", {"message": "Enter text:"})
        await task
        assert result is not None
        assert result.data == long_text
        assert not result.is_error

    @pytest.mark.asyncio
    async def test_multiline_with_special_chars(self, mcp_client: Client, tui_queue: HITLQueue) -> None:
        """Test multiline input with special characters."""
        multiline_text = "Line 1\nLine 2\r\nLine 3\tTabbed\nLine 4 with \"quotes\" and 'apostrophes'"
        task = _auto_resolve(tui_queue, multiline_text)
        result = await mcp_client.call_tool(
            "hitl_collect", {"message": "Enter text:", "input_type": "multiline"}
        )
        await task
        assert result is not None
        assert result.data == multiline_text
        assert not result.is_error

    @pytest.mark.asyncio
    async def test_special_characters_in_prompt(self, mcp_client: Client, tui_queue: HITLQueue) -> None:
        """Test special characters in prompt text."""
        task = _auto_resolve(tui_queue, "response")
        result = await mcp_client.call_tool(
            "hitl_collect", {"message": 'Enter <value> with "quotes" & special chars: $#@!'}
        )
        await task
        assert result is not None
        assert not result.is_error


class TestSelectionEdgeCases:
    """Test edge cases for selection tools."""

    @pytest.mark.asyncio
    async def test_single_choice_in_list(self, mcp_client: Client, tui_queue: HITLQueue) -> None:
        """Test selection with only one choice."""
        task = _auto_resolve(tui_queue, "Only Option")
        result = await mcp_client.call_tool("hitl_choose", {"message": "Select:", "choices": ["Only Option"]})
        await task
        assert result is not None
        assert result.data == "Only Option"
        assert not result.is_error

    @pytest.mark.asyncio
    async def test_choices_with_special_characters(self, mcp_client: Client, tui_queue: HITLQueue) -> None:
        """Test choices containing special characters."""
        task = _auto_resolve(tui_queue, 'Option with "quotes" & <tags>')
        result = await mcp_client.call_tool(
            "hitl_choose",
            {
                "message": "Select:",
                "choices": ['Option with "quotes" & <tags>', "Normal option"],
            },
        )
        await task
        assert result is not None
        assert result.data == 'Option with "quotes" & <tags>'
        assert not result.is_error

    @pytest.mark.asyncio
    async def test_very_long_choice_text(self, mcp_client: Client, tui_queue: HITLQueue) -> None:
        """Test selection with very long choice text."""
        long_choice = "A" * 500
        task = _auto_resolve(tui_queue, long_choice)
        result = await mcp_client.call_tool(
            "hitl_choose", {"message": "Select:", "choices": [long_choice, "Short"]}
        )
        await task
        assert result is not None
        assert result.data == long_choice
        assert not result.is_error

    @pytest.mark.asyncio
    async def test_many_choices(self, mcp_client: Client, tui_queue: HITLQueue) -> None:
        """Test selection with many choices (100+)."""
        choices = [f"Option {i}" for i in range(100)]
        task = _auto_resolve(tui_queue, "Option 50")
        result = await mcp_client.call_tool("hitl_choose", {"message": "Select:", "choices": choices})
        await task
        assert result is not None
        assert result.data == "Option 50"
        assert not result.is_error

    @pytest.mark.asyncio
    async def test_empty_selection_multiple(self, mcp_client: Client, tui_queue: HITLQueue) -> None:
        """Test multiple selection with no items selected."""
        task = _auto_resolve(tui_queue, [])
        result = await mcp_client.call_tool(
            "hitl_choose",
            {"message": "Select:", "choices": ["A", "B", "C"], "multiple": True},
        )
        await task
        assert result is not None
        assert result.data == []
        assert not result.is_error

    @pytest.mark.asyncio
    async def test_all_items_selected_multiple(self, mcp_client: Client, tui_queue: HITLQueue) -> None:
        """Test multiple selection with all items selected."""
        task = _auto_resolve(tui_queue, ["A", "B", "C"])
        result = await mcp_client.call_tool(
            "hitl_choose",
            {"message": "Select:", "choices": ["A", "B", "C"], "multiple": True},
        )
        await task
        assert result is not None
        assert result.data == ["A", "B", "C"]
        assert not result.is_error


class TestNotificationEdgeCases:
    """Test edge cases for notifications."""

    @pytest.mark.asyncio
    async def test_empty_message(self, mcp_client: Client, tui_queue: HITLQueue) -> None:
        """Test notification with empty message."""
        result = await mcp_client.call_tool("hitl_notify", {"message": ""})
        assert result is not None
        assert result.data == {"acknowledged": True}
        assert not result.is_error

    @pytest.mark.asyncio
    async def test_very_long_message(self, mcp_client: Client, tui_queue: HITLQueue) -> None:
        """Test notification with very long message."""
        result = await mcp_client.call_tool("hitl_notify", {"message": "A" * 10000})
        assert result is not None
        assert result.data == {"acknowledged": True}
        assert not result.is_error

    @pytest.mark.asyncio
    async def test_multiline_message(self, mcp_client: Client, tui_queue: HITLQueue) -> None:
        """Test notification with multiline message."""
        result = await mcp_client.call_tool("hitl_notify", {"message": "Line 1\nLine 2\nLine 3"})
        assert result is not None
        assert result.data == {"acknowledged": True}
        assert not result.is_error

    @pytest.mark.asyncio
    async def test_message_with_special_formatting(self, mcp_client: Client, tui_queue: HITLQueue) -> None:
        """Test notification with special formatting characters."""
        result = await mcp_client.call_tool(
            "hitl_notify", {"message": "**Bold** _italic_ `code` [link](url) <tag>"}
        )
        assert result is not None
        assert result.data == {"acknowledged": True}
        assert not result.is_error
