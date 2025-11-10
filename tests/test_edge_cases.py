"""Edge case tests for HITL MCP server.

Tests unusual inputs, boundary conditions, and error scenarios.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastmcp import Client

from hitl_mcp_cli.server import mcp


@pytest.fixture
async def mcp_client() -> Client:
    """Create MCP client connected to the server."""
    async with Client(mcp) as client:
        yield client


class TestInputEdgeCases:
    """Test edge cases for input handling."""

    @pytest.mark.asyncio
    async def test_empty_string_input(self, mcp_client: Client) -> None:
        """Test empty string input is accepted."""
        with patch("hitl_mcp_cli.server.prompt_text", new_callable=AsyncMock) as mock_prompt:
            mock_prompt.return_value = ""

            result = await mcp_client.call_tool("request_text_input", {"prompt": "Enter text:"})

            assert result is not None
            assert result.data == ""
            assert not result.is_error

    @pytest.mark.asyncio
    async def test_whitespace_only_input(self, mcp_client: Client) -> None:
        """Test whitespace-only input is accepted."""
        with patch("hitl_mcp_cli.server.prompt_text", new_callable=AsyncMock) as mock_prompt:
            mock_prompt.return_value = "   \t\n  "

            result = await mcp_client.call_tool("request_text_input", {"prompt": "Enter text:"})

            assert result is not None
            assert result.data == "   \t\n  "
            assert not result.is_error

    @pytest.mark.asyncio
    async def test_unicode_emoji_input(self, mcp_client: Client) -> None:
        """Test Unicode and emoji characters in input."""
        with patch("hitl_mcp_cli.server.prompt_text", new_callable=AsyncMock) as mock_prompt:
            mock_prompt.return_value = "Hello 世界 🌍 🚀 ñ é"

            result = await mcp_client.call_tool("request_text_input", {"prompt": "Enter text:"})

            assert result is not None
            assert result.data == "Hello 世界 🌍 🚀 ñ é"
            assert not result.is_error

    @pytest.mark.asyncio
    async def test_very_long_input(self, mcp_client: Client) -> None:
        """Test very long input (10KB+)."""
        with patch("hitl_mcp_cli.server.prompt_text", new_callable=AsyncMock) as mock_prompt:
            long_text = "A" * 10000
            mock_prompt.return_value = long_text

            result = await mcp_client.call_tool("request_text_input", {"prompt": "Enter text:"})

            assert result is not None
            assert result.data == long_text
            assert not result.is_error

    @pytest.mark.asyncio
    async def test_multiline_with_special_chars(self, mcp_client: Client) -> None:
        """Test multiline input with special characters."""
        with patch("hitl_mcp_cli.server.prompt_text", new_callable=AsyncMock) as mock_prompt:
            multiline_text = "Line 1\nLine 2\r\nLine 3\tTabbed\nLine 4 with \"quotes\" and 'apostrophes'"
            mock_prompt.return_value = multiline_text

            result = await mcp_client.call_tool(
                "request_text_input", {"prompt": "Enter text:", "multiline": True}
            )

            assert result is not None
            assert result.data == multiline_text
            assert not result.is_error

    @pytest.mark.asyncio
    async def test_special_characters_in_prompt(self, mcp_client: Client) -> None:
        """Test special characters in prompt text."""
        with patch("hitl_mcp_cli.server.prompt_text", new_callable=AsyncMock) as mock_prompt:
            mock_prompt.return_value = "response"

            result = await mcp_client.call_tool(
                "request_text_input", {"prompt": 'Enter <value> with "quotes" & special chars: $#@!'}
            )

            assert result is not None
            assert not result.is_error


class TestSelectionEdgeCases:
    """Test edge cases for selection tools."""

    @pytest.mark.asyncio
    async def test_single_choice_in_list(self, mcp_client: Client) -> None:
        """Test selection with only one choice."""
        with patch("hitl_mcp_cli.server.prompt_select", new_callable=AsyncMock) as mock_select:
            mock_select.return_value = "Only Option"

            result = await mcp_client.call_tool(
                "request_selection", {"prompt": "Select:", "choices": ["Only Option"]}
            )

            assert result is not None
            assert result.data == "Only Option"
            assert not result.is_error

    @pytest.mark.asyncio
    async def test_choices_with_special_characters(self, mcp_client: Client) -> None:
        """Test choices containing special characters."""
        with patch("hitl_mcp_cli.server.prompt_select", new_callable=AsyncMock) as mock_select:
            mock_select.return_value = 'Option with "quotes" & <tags>'

            result = await mcp_client.call_tool(
                "request_selection",
                {
                    "prompt": "Select:",
                    "choices": ['Option with "quotes" & <tags>', "Normal option"],
                },
            )

            assert result is not None
            assert result.data == 'Option with "quotes" & <tags>'
            assert not result.is_error

    @pytest.mark.asyncio
    async def test_very_long_choice_text(self, mcp_client: Client) -> None:
        """Test selection with very long choice text."""
        with patch("hitl_mcp_cli.server.prompt_select", new_callable=AsyncMock) as mock_select:
            long_choice = "A" * 500
            mock_select.return_value = long_choice

            result = await mcp_client.call_tool(
                "request_selection", {"prompt": "Select:", "choices": [long_choice, "Short"]}
            )

            assert result is not None
            assert result.data == long_choice
            assert not result.is_error

    @pytest.mark.asyncio
    async def test_many_choices(self, mcp_client: Client) -> None:
        """Test selection with many choices (100+)."""
        with patch("hitl_mcp_cli.server.prompt_select", new_callable=AsyncMock) as mock_select:
            choices = [f"Option {i}" for i in range(100)]
            mock_select.return_value = "Option 50"

            result = await mcp_client.call_tool(
                "request_selection", {"prompt": "Select:", "choices": choices}
            )

            assert result is not None
            assert result.data == "Option 50"
            assert not result.is_error

    @pytest.mark.asyncio
    async def test_empty_selection_multiple(self, mcp_client: Client) -> None:
        """Test multiple selection with no items selected."""
        with patch("hitl_mcp_cli.server.prompt_checkbox", new_callable=AsyncMock) as mock_checkbox:
            mock_checkbox.return_value = []

            result = await mcp_client.call_tool(
                "request_selection",
                {"prompt": "Select:", "choices": ["A", "B", "C"], "allow_multiple": True},
            )

            assert result is not None
            assert result.data == []
            assert not result.is_error

    @pytest.mark.asyncio
    async def test_all_items_selected_multiple(self, mcp_client: Client) -> None:
        """Test multiple selection with all items selected."""
        with patch("hitl_mcp_cli.server.prompt_checkbox", new_callable=AsyncMock) as mock_checkbox:
            mock_checkbox.return_value = ["A", "B", "C"]

            result = await mcp_client.call_tool(
                "request_selection",
                {"prompt": "Select:", "choices": ["A", "B", "C"], "allow_multiple": True},
            )

            assert result is not None
            assert result.data == ["A", "B", "C"]
            assert not result.is_error


class TestPathEdgeCases:
    """Test edge cases for path input."""

    @pytest.mark.asyncio
    async def test_path_with_spaces(self, mcp_client: Client) -> None:
        """Test path containing spaces."""
        with patch("hitl_mcp_cli.server.prompt_path", new_callable=AsyncMock) as mock_path:
            mock_path.return_value = "/home/user/My Documents/file.txt"

            result = await mcp_client.call_tool(
                "request_path_input", {"prompt": "Select file:", "path_type": "file"}
            )

            assert result is not None
            assert result.data == "/home/user/My Documents/file.txt"
            assert not result.is_error

    @pytest.mark.asyncio
    async def test_path_with_unicode(self, mcp_client: Client) -> None:
        """Test path containing Unicode characters."""
        with patch("hitl_mcp_cli.server.prompt_path", new_callable=AsyncMock) as mock_path:
            mock_path.return_value = "/home/user/文档/файл.txt"

            result = await mcp_client.call_tool(
                "request_path_input", {"prompt": "Select file:", "path_type": "file"}
            )

            assert result is not None
            assert result.data == "/home/user/文档/файл.txt"
            assert not result.is_error

    @pytest.mark.asyncio
    async def test_very_long_path(self, mcp_client: Client) -> None:
        """Test very long file path."""
        with patch("hitl_mcp_cli.server.prompt_path", new_callable=AsyncMock) as mock_path:
            long_path = "/home/" + "/".join(["dir" + str(i) for i in range(50)]) + "/file.txt"
            mock_path.return_value = long_path

            result = await mcp_client.call_tool(
                "request_path_input", {"prompt": "Select file:", "path_type": "file"}
            )

            assert result is not None
            assert result.data == long_path
            assert not result.is_error


class TestNotificationEdgeCases:
    """Test edge cases for notifications."""

    @pytest.mark.asyncio
    async def test_empty_message(self, mcp_client: Client) -> None:
        """Test notification with empty message."""
        with patch("hitl_mcp_cli.server.display_notification"):
            result = await mcp_client.call_tool("notify_completion", {"title": "Title", "message": ""})

            assert result is not None
            assert result.data == {"acknowledged": True}
            assert not result.is_error

    @pytest.mark.asyncio
    async def test_very_long_message(self, mcp_client: Client) -> None:
        """Test notification with very long message."""
        with patch("hitl_mcp_cli.server.display_notification"):
            long_message = "A" * 10000

            result = await mcp_client.call_tool(
                "notify_completion", {"title": "Title", "message": long_message}
            )

            assert result is not None
            assert result.data == {"acknowledged": True}
            assert not result.is_error

    @pytest.mark.asyncio
    async def test_multiline_message(self, mcp_client: Client) -> None:
        """Test notification with multiline message."""
        with patch("hitl_mcp_cli.server.display_notification"):
            multiline = "Line 1\nLine 2\nLine 3\n\nLine 5"

            result = await mcp_client.call_tool("notify_completion", {"title": "Title", "message": multiline})

            assert result is not None
            assert result.data == {"acknowledged": True}
            assert not result.is_error

    @pytest.mark.asyncio
    async def test_message_with_special_formatting(self, mcp_client: Client) -> None:
        """Test notification with special formatting characters."""
        with patch("hitl_mcp_cli.server.display_notification"):
            formatted = "**Bold** _italic_ `code` [link](url) <tag>"

            result = await mcp_client.call_tool("notify_completion", {"title": "Title", "message": formatted})

            assert result is not None
            assert result.data == {"acknowledged": True}
            assert not result.is_error
