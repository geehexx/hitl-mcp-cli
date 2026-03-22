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
        assert mcp_client.initialize_result.serverInfo.name == "HITL MCP Server"
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
            "hitl_collect",
            "hitl_choose",
            "hitl_confirm",
            "hitl_notify",
            "hitl_approve_workflow",
        }

        # Verify each tool has required fields
        for tool in tools:
            assert tool.name is not None
            assert tool.description is not None
            assert tool.inputSchema is not None
            assert "properties" in tool.inputSchema


class TestToolExecution:
    """Test tool execution through MCP protocol."""

    @pytest.mark.asyncio
    async def test_hitl_collect_execution(self, mcp_client: Client) -> None:
        """Test hitl_collect tool executes and returns result."""
        with patch("hitl_mcp_cli.server.prompt_text", new_callable=AsyncMock) as mock_prompt:
            mock_prompt.return_value = "User Response"

            result = await mcp_client.call_tool(
                "hitl_collect",
                {"message": "Enter text:", "default": "default", "input_type": "text"},
            )

            assert result is not None
            assert result.data == "User Response"
            assert not result.is_error
            mock_prompt.assert_called_once_with("Enter text:", "default", False, None)

    @pytest.mark.asyncio
    async def test_hitl_collect_multiline(self, mcp_client: Client) -> None:
        """Test hitl_collect with multiline input_type."""
        with patch("hitl_mcp_cli.server.prompt_text", new_callable=AsyncMock) as mock_prompt:
            mock_prompt.return_value = "line1\nline2"

            result = await mcp_client.call_tool(
                "hitl_collect",
                {"message": "Enter text:", "input_type": "multiline"},
            )

            assert result is not None
            assert result.data == "line1\nline2"
            assert not result.is_error
            mock_prompt.assert_called_once_with("Enter text:", None, True, None)

    @pytest.mark.asyncio
    async def test_hitl_collect_path(self, mcp_client: Client) -> None:
        """Test hitl_collect with path input_type."""
        with patch("hitl_mcp_cli.server.prompt_path", new_callable=AsyncMock) as mock_path:
            mock_path.return_value = "/home/user/config.yaml"

            result = await mcp_client.call_tool(
                "hitl_collect",
                {"message": "Select file:", "input_type": "path"},
            )

            assert result is not None
            assert result.data == "/home/user/config.yaml"
            assert not result.is_error

    @pytest.mark.asyncio
    async def test_hitl_choose_single(self, mcp_client: Client) -> None:
        """Test hitl_choose with single choice."""
        with patch("hitl_mcp_cli.server.prompt_select", new_callable=AsyncMock) as mock_select:
            mock_select.return_value = "Choice B"

            result = await mcp_client.call_tool(
                "hitl_choose",
                {
                    "message": "Select one:",
                    "choices": ["Choice A", "Choice B", "Choice C"],
                    "default": "Choice A",
                    "multiple": False,
                },
            )

            assert result is not None
            assert result.data == "Choice B"
            assert not result.is_error

    @pytest.mark.asyncio
    async def test_hitl_choose_multiple(self, mcp_client: Client) -> None:
        """Test hitl_choose with multiple choices."""
        with patch("hitl_mcp_cli.server.prompt_checkbox", new_callable=AsyncMock) as mock_checkbox:
            mock_checkbox.return_value = ["Choice A", "Choice C"]

            result = await mcp_client.call_tool(
                "hitl_choose",
                {
                    "message": "Select multiple:",
                    "choices": ["Choice A", "Choice B", "Choice C"],
                    "multiple": True,
                },
            )

            assert result is not None
            assert result.data == ["Choice A", "Choice C"]
            assert not result.is_error

    @pytest.mark.asyncio
    async def test_hitl_choose_with_options(self, mcp_client: Client) -> None:
        """Test hitl_choose with rich options format."""
        with patch("hitl_mcp_cli.server.prompt_select", new_callable=AsyncMock) as mock_select:
            mock_select.return_value = "Fast: Quick but uses more memory"

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

            assert result is not None
            assert result.data == "fast"
            assert not result.is_error
            mock_select.assert_called_once()

    @pytest.mark.asyncio
    async def test_hitl_choose_options_without_description(self, mcp_client: Client) -> None:
        """Test hitl_choose with options that have no description."""
        with patch("hitl_mcp_cli.server.prompt_select", new_callable=AsyncMock) as mock_select:
            mock_select.return_value = "Fast"

            result = await mcp_client.call_tool(
                "hitl_choose",
                {
                    "message": "Select:",
                    "options": [
                        {"value": "fast", "label": "Fast"},
                        {"value": "safe", "label": "Safe"},
                    ],
                },
            )

            assert result is not None
            assert result.data == "fast"
            assert not result.is_error

    @pytest.mark.asyncio
    async def test_hitl_confirm_true(self, mcp_client: Client) -> None:
        """Test hitl_confirm returns accept action."""
        with patch("hitl_mcp_cli.server.prompt_confirm", new_callable=AsyncMock) as mock_confirm:
            mock_confirm.return_value = True

            result = await mcp_client.call_tool(
                "hitl_confirm", {"message": "Confirm action?", "default": False}
            )

            assert result is not None
            assert result.data == {"action": "accept"}
            assert not result.is_error

    @pytest.mark.asyncio
    async def test_hitl_confirm_false(self, mcp_client: Client) -> None:
        """Test hitl_confirm returns decline action."""
        with patch("hitl_mcp_cli.server.prompt_confirm", new_callable=AsyncMock) as mock_confirm:
            mock_confirm.return_value = False

            result = await mcp_client.call_tool(
                "hitl_confirm", {"message": "Confirm action?", "default": True}
            )

            assert result is not None
            assert result.data == {"action": "decline"}
            assert not result.is_error

    @pytest.mark.asyncio
    async def test_hitl_confirm_severity_high(self, mcp_client: Client) -> None:
        """Test hitl_confirm with severity=high requires typed yes."""
        with (
            patch("hitl_mcp_cli.server.prompt_text", new_callable=AsyncMock) as mock_text,
            patch("hitl_mcp_cli.server.display_notification"),
        ):
            mock_text.return_value = "yes"

            result = await mcp_client.call_tool(
                "hitl_confirm", {"message": "Delete everything?", "severity": "high"}
            )

            assert result is not None
            assert result.data == {"action": "accept"}
            assert not result.is_error

    @pytest.mark.asyncio
    async def test_hitl_confirm_severity_high_rejected(self, mcp_client: Client) -> None:
        """Test hitl_confirm with severity=high rejects non-yes input."""
        with (
            patch("hitl_mcp_cli.server.prompt_text", new_callable=AsyncMock) as mock_text,
            patch("hitl_mcp_cli.server.display_notification"),
        ):
            mock_text.return_value = "no"

            result = await mcp_client.call_tool(
                "hitl_confirm", {"message": "Delete everything?", "severity": "high"}
            )

            assert result is not None
            assert result.data == {"action": "decline"}
            assert not result.is_error

    @pytest.mark.asyncio
    async def test_hitl_confirm_severity_low(self, mcp_client: Client) -> None:
        """Test hitl_confirm with severity=low defaults to yes."""
        with patch("hitl_mcp_cli.server.prompt_confirm", new_callable=AsyncMock) as mock_confirm:
            mock_confirm.return_value = True

            result = await mcp_client.call_tool("hitl_confirm", {"message": "Continue?", "severity": "low"})

            assert result is not None
            assert result.data == {"action": "accept"}
            # severity=low should pass default=True
            mock_confirm.assert_called_once_with("Continue?", default=True)

    @pytest.mark.asyncio
    async def test_hitl_notify_execution(self, mcp_client: Client) -> None:
        """Test hitl_notify tool executes and returns acknowledgment."""
        with patch("hitl_mcp_cli.server.display_notification") as mock_notify:
            result = await mcp_client.call_tool(
                "hitl_notify",
                {"message": "Operation complete", "level": "success", "title": "Success"},
            )

            assert result is not None
            assert result.data == {"acknowledged": True}
            assert not result.is_error
            mock_notify.assert_called_once_with("Success", "Operation complete", "success")

    @pytest.mark.asyncio
    async def test_hitl_notify_default_title(self, mcp_client: Client) -> None:
        """Test hitl_notify uses level as title when no title provided."""
        with patch("hitl_mcp_cli.server.display_notification") as mock_notify:
            result = await mcp_client.call_tool(
                "hitl_notify",
                {"message": "Something happened"},
            )

            assert result is not None
            assert result.data == {"acknowledged": True}
            mock_notify.assert_called_once_with("Info", "Something happened", "info")

    @pytest.mark.asyncio
    async def test_hitl_approve_workflow_approved(self, mcp_client: Client) -> None:
        """Test hitl_approve_workflow returns approved."""
        with (
            patch("hitl_mcp_cli.server.prompt_select", new_callable=AsyncMock) as mock_select,
            patch("hitl_mcp_cli.server.display_notification"),
        ):
            mock_select.return_value = "Approve"

            result = await mcp_client.call_tool(
                "hitl_approve_workflow",
                {"message": "Deploy to production?", "timeout_seconds": 0},
            )

            assert result is not None
            assert result.data == {"approved": True, "choice": "Approve", "timed_out": False}

    @pytest.mark.asyncio
    async def test_hitl_approve_workflow_rejected(self, mcp_client: Client) -> None:
        """Test hitl_approve_workflow returns rejected."""
        with (
            patch("hitl_mcp_cli.server.prompt_select", new_callable=AsyncMock) as mock_select,
            patch("hitl_mcp_cli.server.display_notification"),
        ):
            mock_select.return_value = "Reject"

            result = await mcp_client.call_tool(
                "hitl_approve_workflow",
                {"message": "Deploy to production?", "timeout_seconds": 0},
            )

            assert result is not None
            assert result.data == {"approved": False, "choice": "Reject", "timed_out": False}

    @pytest.mark.asyncio
    async def test_hitl_approve_workflow_with_context(self, mcp_client: Client) -> None:
        """Test hitl_approve_workflow displays context."""
        with (
            patch("hitl_mcp_cli.server.prompt_select", new_callable=AsyncMock) as mock_select,
            patch("hitl_mcp_cli.server.display_notification") as mock_notify,
        ):
            mock_select.return_value = "Approve"

            result = await mcp_client.call_tool(
                "hitl_approve_workflow",
                {
                    "message": "Deploy?",
                    "context": "Version 2.0 to production",
                    "timeout_seconds": 0,
                },
            )

            assert result is not None
            assert result.data["approved"] is True
            # Should display context in notification
            call_args = mock_notify.call_args[0]
            assert "Version 2.0" in call_args[1]

    @pytest.mark.asyncio
    async def test_hitl_approve_workflow_custom_options(self, mcp_client: Client) -> None:
        """Test hitl_approve_workflow with custom options."""
        with (
            patch("hitl_mcp_cli.server.prompt_select", new_callable=AsyncMock) as mock_select,
            patch("hitl_mcp_cli.server.display_notification"),
        ):
            mock_select.return_value = "Deploy Now"

            result = await mcp_client.call_tool(
                "hitl_approve_workflow",
                {
                    "message": "When to deploy?",
                    "options": ["Deploy Now", "Schedule Later", "Cancel"],
                    "timeout_seconds": 0,
                },
            )

            assert result is not None
            assert result.data["approved"] is True
            assert result.data["choice"] == "Deploy Now"


class TestErrorHandling:
    """Test error handling in MCP protocol."""

    @pytest.mark.asyncio
    async def test_keyboard_interrupt_handling(self, mcp_client: Client) -> None:
        """Test KeyboardInterrupt is converted to proper error."""
        with patch("hitl_mcp_cli.server.prompt_text", new_callable=AsyncMock) as mock_prompt:
            mock_prompt.side_effect = KeyboardInterrupt()

            result = await mcp_client.call_tool(
                "hitl_collect", {"message": "Enter text:"}, raise_on_error=False
            )

            assert result is not None
            assert result.is_error
            error_text = str(result.content[0].text if result.content else "")
            assert "cancelled" in error_text.lower() or "ctrl+c" in error_text.lower()

    @pytest.mark.asyncio
    async def test_generic_exception_handling(self, mcp_client: Client) -> None:
        """Test generic exceptions are converted to proper errors."""
        with patch("hitl_mcp_cli.server.prompt_text", new_callable=AsyncMock) as mock_prompt:
            mock_prompt.side_effect = RuntimeError("Test error")

            result = await mcp_client.call_tool(
                "hitl_collect", {"message": "Enter text:"}, raise_on_error=False
            )

            assert result is not None
            assert result.is_error
            error_text = str(result.content[0].text if result.content else "")
            assert "failed" in error_text.lower()

    @pytest.mark.asyncio
    async def test_missing_required_parameter(self, mcp_client: Client) -> None:
        """Test missing required parameter returns error."""
        result = await mcp_client.call_tool("hitl_collect", {}, raise_on_error=False)

        assert result is not None
        assert result.is_error

    @pytest.mark.asyncio
    async def test_hitl_choose_no_choices_or_options(self, mcp_client: Client) -> None:
        """Test hitl_choose fails when neither choices nor options provided."""
        result = await mcp_client.call_tool("hitl_choose", {"message": "Choose:"}, raise_on_error=False)

        assert result is not None
        assert result.is_error


class TestParameterHandling:
    """Test parameter validation and handling."""

    @pytest.mark.asyncio
    async def test_optional_parameters_omitted(self, mcp_client: Client) -> None:
        """Test tools work with only required parameters."""
        with patch("hitl_mcp_cli.server.prompt_text", new_callable=AsyncMock) as mock_prompt:
            mock_prompt.return_value = "Response"

            result = await mcp_client.call_tool("hitl_collect", {"message": "Enter text:"})

            assert result is not None
            assert not result.is_error
            mock_prompt.assert_called_once_with("Enter text:", None, False, None)

    @pytest.mark.asyncio
    async def test_all_parameters_provided(self, mcp_client: Client) -> None:
        """Test tools work with all parameters provided."""
        with patch("hitl_mcp_cli.server.prompt_text", new_callable=AsyncMock) as mock_prompt:
            mock_prompt.return_value = "Response"

            result = await mcp_client.call_tool(
                "hitl_collect",
                {
                    "message": "Enter text:",
                    "default": "default value",
                    "input_type": "multiline",
                    "validation_pattern": r"^\w+$",
                },
            )

            assert result is not None
            assert not result.is_error
            mock_prompt.assert_called_once_with("Enter text:", "default value", True, r"^\w+$")

    @pytest.mark.asyncio
    async def test_notification_level_values(self, mcp_client: Client) -> None:
        """Test level accepts valid literal values."""
        with patch("hitl_mcp_cli.server.display_notification"):
            for level in ["success", "info", "warning", "error"]:
                result = await mcp_client.call_tool(
                    "hitl_notify",
                    {"message": "Message", "level": level},
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
                result = await mcp_client.call_tool("hitl_collect", {"message": f"Prompt {i}:"})
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

            result1 = await mcp_client.call_tool("hitl_collect", {"message": "Enter text:"})
            assert result1 is not None
            assert not result1.is_error

            result2 = await mcp_client.call_tool("hitl_confirm", {"message": "Confirm?"})
            assert result2 is not None
            assert not result2.is_error

            result3 = await mcp_client.call_tool("hitl_notify", {"message": "Complete"})
            assert result3 is not None
            assert not result3.is_error
