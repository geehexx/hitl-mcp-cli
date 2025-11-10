"""Integration tests for MCP protocol interaction.

These tests verify the full MCP request/response cycle with minimal mocking.
They test the actual HTTP transport and protocol handling.
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


class TestMCPProtocol:
    """Test MCP protocol compliance and behavior."""

    @pytest.mark.asyncio
    async def test_initialize_handshake(self, mcp_client: Client) -> None:
        """Test MCP initialization handshake completes successfully."""
        assert mcp_client.initialize_result is not None
        assert mcp_client.initialize_result.serverInfo is not None
        assert mcp_client.initialize_result.serverInfo.name == "Interactive Input Server"
        assert mcp_client.initialize_result.protocolVersion is not None

    @pytest.mark.asyncio
    async def test_server_capabilities(self, mcp_client: Client) -> None:
        """Test server advertises correct capabilities."""
        assert mcp_client.initialize_result is not None
        assert mcp_client.initialize_result.capabilities is not None
        assert mcp_client.initialize_result.capabilities.tools is not None

    @pytest.mark.asyncio
    async def test_tools_list_response(self, mcp_client: Client) -> None:
        """Test tools/list returns properly formatted tool definitions."""
        tools = await mcp_client.list_tools()

        assert len(tools) == 5
        tool_names = {tool.name for tool in tools}
        assert tool_names == {
            "request_text_input",
            "request_selection",
            "request_confirmation",
            "request_path_input",
            "notify_completion",
        }

        # Verify each tool has required fields
        for tool in tools:
            assert tool.name is not None
            assert tool.description is not None
            assert tool.inputSchema is not None
            assert "properties" in tool.inputSchema
            assert "required" in tool.inputSchema


class TestToolExecution:
    """Test tool execution through MCP protocol."""

    @pytest.mark.asyncio
    async def test_request_text_input_execution(self, mcp_client: Client) -> None:
        """Test request_text_input tool executes and returns result."""
        with patch("hitl_mcp_cli.server.prompt_text", new_callable=AsyncMock) as mock_prompt:
            mock_prompt.return_value = "User Response"

            result = await mcp_client.call_tool(
                "request_text_input",
                {"prompt": "Enter text:", "default": "default", "multiline": False, "validate_pattern": None},
            )

            assert result is not None
            assert result.data == "User Response"
            assert not result.is_error
            mock_prompt.assert_called_once_with("Enter text:", "default", False, None)

    @pytest.mark.asyncio
    async def test_request_selection_single_choice(self, mcp_client: Client) -> None:
        """Test request_selection with single choice."""
        with patch("hitl_mcp_cli.server.prompt_select", new_callable=AsyncMock) as mock_select:
            mock_select.return_value = "Choice B"

            result = await mcp_client.call_tool(
                "request_selection",
                {
                    "prompt": "Select one:",
                    "choices": ["Choice A", "Choice B", "Choice C"],
                    "default": "Choice A",
                    "allow_multiple": False,
                },
            )

            assert result is not None
            assert result.data == "Choice B"
            assert not result.is_error

    @pytest.mark.asyncio
    async def test_request_selection_multiple_choices(self, mcp_client: Client) -> None:
        """Test request_selection with multiple choices."""
        with patch("hitl_mcp_cli.server.prompt_checkbox", new_callable=AsyncMock) as mock_checkbox:
            mock_checkbox.return_value = ["Choice A", "Choice C"]

            result = await mcp_client.call_tool(
                "request_selection",
                {
                    "prompt": "Select multiple:",
                    "choices": ["Choice A", "Choice B", "Choice C"],
                    "allow_multiple": True,
                },
            )

            assert result is not None
            assert result.data == ["Choice A", "Choice C"]
            assert not result.is_error

    @pytest.mark.asyncio
    async def test_request_confirmation_true(self, mcp_client: Client) -> None:
        """Test request_confirmation returns True."""
        with patch("hitl_mcp_cli.server.prompt_confirm", new_callable=AsyncMock) as mock_confirm:
            mock_confirm.return_value = True

            result = await mcp_client.call_tool(
                "request_confirmation", {"prompt": "Confirm action?", "default": False}
            )

            assert result is not None
            assert result.data is True
            assert not result.is_error

    @pytest.mark.asyncio
    async def test_request_confirmation_false(self, mcp_client: Client) -> None:
        """Test request_confirmation returns False."""
        with patch("hitl_mcp_cli.server.prompt_confirm", new_callable=AsyncMock) as mock_confirm:
            mock_confirm.return_value = False

            result = await mcp_client.call_tool(
                "request_confirmation", {"prompt": "Confirm action?", "default": True}
            )

            assert result is not None
            assert result.data is False
            assert not result.is_error

    @pytest.mark.asyncio
    async def test_request_path_input_execution(self, mcp_client: Client) -> None:
        """Test request_path_input tool executes and returns path."""
        with patch("hitl_mcp_cli.server.prompt_path", new_callable=AsyncMock) as mock_path:
            mock_path.return_value = "/home/user/config.yaml"

            result = await mcp_client.call_tool(
                "request_path_input",
                {"prompt": "Select file:", "path_type": "file", "must_exist": False, "default": None},
            )

            assert result is not None
            assert result.data == "/home/user/config.yaml"
            assert not result.is_error

    @pytest.mark.asyncio
    async def test_notify_completion_execution(self, mcp_client: Client) -> None:
        """Test notify_completion tool executes and returns acknowledgment."""
        with patch("hitl_mcp_cli.server.display_notification") as mock_notify:
            result = await mcp_client.call_tool(
                "notify_completion",
                {"title": "Success", "message": "Operation complete", "notification_type": "success"},
            )

            assert result is not None
            assert result.data == {"acknowledged": True}
            assert not result.is_error
            mock_notify.assert_called_once_with("Success", "Operation complete", "success")


class TestErrorHandling:
    """Test error handling in MCP protocol."""

    @pytest.mark.asyncio
    async def test_keyboard_interrupt_handling(self, mcp_client: Client) -> None:
        """Test KeyboardInterrupt is converted to proper error."""
        with patch("hitl_mcp_cli.server.prompt_text", new_callable=AsyncMock) as mock_prompt:
            mock_prompt.side_effect = KeyboardInterrupt()

            result = await mcp_client.call_tool(
                "request_text_input", {"prompt": "Enter text:"}, raise_on_error=False
            )

            assert result is not None
            assert result.is_error
            # Error message should mention user cancellation
            error_text = str(result.content[0].text if result.content else "")
            assert "cancelled" in error_text.lower() or "ctrl+c" in error_text.lower()

    @pytest.mark.asyncio
    async def test_generic_exception_handling(self, mcp_client: Client) -> None:
        """Test generic exceptions are converted to proper errors."""
        with patch("hitl_mcp_cli.server.prompt_text", new_callable=AsyncMock) as mock_prompt:
            mock_prompt.side_effect = RuntimeError("Test error")

            result = await mcp_client.call_tool(
                "request_text_input", {"prompt": "Enter text:"}, raise_on_error=False
            )

            assert result is not None
            assert result.is_error
            error_text = str(result.content[0].text if result.content else "")
            assert "failed" in error_text.lower()

    @pytest.mark.asyncio
    async def test_missing_required_parameter(self, mcp_client: Client) -> None:
        """Test missing required parameter returns error."""
        result = await mcp_client.call_tool("request_text_input", {}, raise_on_error=False)

        assert result is not None
        assert result.is_error


class TestParameterHandling:
    """Test parameter validation and handling."""

    @pytest.mark.asyncio
    async def test_optional_parameters_omitted(self, mcp_client: Client) -> None:
        """Test tools work with only required parameters."""
        with patch("hitl_mcp_cli.server.prompt_text", new_callable=AsyncMock) as mock_prompt:
            mock_prompt.return_value = "Response"

            result = await mcp_client.call_tool("request_text_input", {"prompt": "Enter text:"})

            assert result is not None
            assert not result.is_error
            # Verify defaults were used
            mock_prompt.assert_called_once_with("Enter text:", None, False, None)

    @pytest.mark.asyncio
    async def test_all_parameters_provided(self, mcp_client: Client) -> None:
        """Test tools work with all parameters provided."""
        with patch("hitl_mcp_cli.server.prompt_text", new_callable=AsyncMock) as mock_prompt:
            mock_prompt.return_value = "Response"

            result = await mcp_client.call_tool(
                "request_text_input",
                {
                    "prompt": "Enter text:",
                    "default": "default value",
                    "multiline": True,
                    "validate_pattern": r"^\w+$",
                },
            )

            assert result is not None
            assert not result.is_error
            mock_prompt.assert_called_once_with("Enter text:", "default value", True, r"^\w+$")

    @pytest.mark.asyncio
    async def test_path_type_literal_values(self, mcp_client: Client) -> None:
        """Test path_type accepts valid literal values."""
        with patch("hitl_mcp_cli.server.prompt_path", new_callable=AsyncMock) as mock_path:
            mock_path.return_value = "/path/to/file"

            for path_type in ["file", "directory", "any"]:
                result = await mcp_client.call_tool(
                    "request_path_input", {"prompt": "Select path:", "path_type": path_type}
                )

                assert result is not None
                assert not result.is_error

    @pytest.mark.asyncio
    async def test_notification_type_literal_values(self, mcp_client: Client) -> None:
        """Test notification_type accepts valid literal values."""
        with patch("hitl_mcp_cli.server.display_notification"):
            for notif_type in ["success", "info", "warning", "error"]:
                result = await mcp_client.call_tool(
                    "notify_completion",
                    {"title": "Test", "message": "Message", "notification_type": notif_type},
                )

                assert result is not None
                assert not result.is_error


class TestConcurrentRequests:
    """Test handling of concurrent tool calls."""

    @pytest.mark.asyncio
    async def test_multiple_sequential_calls(self, mcp_client: Client) -> None:
        """Test multiple sequential tool calls work correctly."""
        with patch("hitl_mcp_cli.server.prompt_text", new_callable=AsyncMock) as mock_prompt:
            mock_prompt.side_effect = ["Response 1", "Response 2", "Response 3"]

            for i in range(3):
                result = await mcp_client.call_tool("request_text_input", {"prompt": f"Prompt {i}:"})
                assert result is not None
                assert not result.is_error
                assert result.data == f"Response {i + 1}"

    @pytest.mark.asyncio
    async def test_different_tools_sequential(self, mcp_client: Client) -> None:
        """Test calling different tools sequentially."""
        with (
            patch("hitl_mcp_cli.server.prompt_text", new_callable=AsyncMock) as mock_text,
            patch("hitl_mcp_cli.server.prompt_confirm", new_callable=AsyncMock) as mock_confirm,
            patch("hitl_mcp_cli.server.display_notification"),
        ):
            mock_text.return_value = "Text response"
            mock_confirm.return_value = True

            # Call text input
            result1 = await mcp_client.call_tool("request_text_input", {"prompt": "Enter text:"})
            assert result1 is not None
            assert not result1.is_error

            # Call confirmation
            result2 = await mcp_client.call_tool("request_confirmation", {"prompt": "Confirm?"})
            assert result2 is not None
            assert not result2.is_error

            # Call notification
            result3 = await mcp_client.call_tool(
                "notify_completion", {"title": "Done", "message": "Complete"}
            )
            assert result3 is not None
            assert not result3.is_error
