"""Tests for error handling across the application."""

from unittest.mock import AsyncMock, patch

import pytest
from fastmcp import Client

from hitl_mcp_cli.server import mcp


@pytest.fixture
async def mcp_client() -> Client:
    """Create MCP client for testing."""
    async with Client(mcp) as client:
        yield client


@pytest.mark.asyncio
async def test_request_text_input_keyboard_interrupt(mcp_client: Client) -> None:
    """Test text input handles Ctrl+C gracefully."""
    with patch("hitl_mcp_cli.server.prompt_text", new_callable=AsyncMock) as mock:
        mock.side_effect = KeyboardInterrupt()

        with pytest.raises(Exception) as exc_info:
            await mcp_client.call_tool("request_text_input", {"prompt": "Test:"})

        assert "User cancelled" in str(exc_info.value)


@pytest.mark.asyncio
async def test_request_text_input_generic_error(mcp_client: Client) -> None:
    """Test text input handles generic errors."""
    with patch("hitl_mcp_cli.server.prompt_text", new_callable=AsyncMock) as mock:
        mock.side_effect = ValueError("Invalid input")

        with pytest.raises(Exception) as exc_info:
            await mcp_client.call_tool("request_text_input", {"prompt": "Test:"})

        assert "Input collection failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_request_selection_keyboard_interrupt(mcp_client: Client) -> None:
    """Test selection handles Ctrl+C gracefully."""
    with patch("hitl_mcp_cli.server.prompt_select", new_callable=AsyncMock) as mock:
        mock.side_effect = KeyboardInterrupt()

        with pytest.raises(Exception) as exc_info:
            await mcp_client.call_tool("request_selection", {"prompt": "Choose:", "choices": ["A", "B"]})

        assert "User cancelled" in str(exc_info.value)


@pytest.mark.asyncio
async def test_request_selection_generic_error(mcp_client: Client) -> None:
    """Test selection handles generic errors."""
    with patch("hitl_mcp_cli.server.prompt_select", new_callable=AsyncMock) as mock:
        mock.side_effect = RuntimeError("Selection failed")

        with pytest.raises(Exception) as exc_info:
            await mcp_client.call_tool("request_selection", {"prompt": "Choose:", "choices": ["A", "B"]})

        assert "Selection failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_request_confirmation_keyboard_interrupt(mcp_client: Client) -> None:
    """Test confirmation handles Ctrl+C gracefully."""
    with patch("hitl_mcp_cli.server.prompt_confirm", new_callable=AsyncMock) as mock:
        mock.side_effect = KeyboardInterrupt()

        with pytest.raises(Exception) as exc_info:
            await mcp_client.call_tool("request_confirmation", {"prompt": "Proceed?"})

        assert "User cancelled" in str(exc_info.value)


@pytest.mark.asyncio
async def test_request_confirmation_generic_error(mcp_client: Client) -> None:
    """Test confirmation handles generic errors."""
    with patch("hitl_mcp_cli.server.prompt_confirm", new_callable=AsyncMock) as mock:
        mock.side_effect = OSError("Terminal error")

        with pytest.raises(Exception) as exc_info:
            await mcp_client.call_tool("request_confirmation", {"prompt": "Proceed?"})

        assert "Confirmation failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_request_path_input_keyboard_interrupt(mcp_client: Client) -> None:
    """Test path input handles Ctrl+C gracefully."""
    with patch("hitl_mcp_cli.server.prompt_path", new_callable=AsyncMock) as mock:
        mock.side_effect = KeyboardInterrupt()

        with pytest.raises(Exception) as exc_info:
            await mcp_client.call_tool("request_path_input", {"prompt": "Select path:"})

        assert "User cancelled" in str(exc_info.value)


@pytest.mark.asyncio
async def test_request_path_input_generic_error(mcp_client: Client) -> None:
    """Test path input handles generic errors."""
    with patch("hitl_mcp_cli.server.prompt_path", new_callable=AsyncMock) as mock:
        mock.side_effect = PermissionError("Access denied")

        with pytest.raises(Exception) as exc_info:
            await mcp_client.call_tool("request_path_input", {"prompt": "Select path:"})

        assert "Path input failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_notify_completion_error(mcp_client: Client) -> None:
    """Test notification handles errors."""
    with patch("hitl_mcp_cli.server.display_notification") as mock:
        mock.side_effect = RuntimeError("Display error")

        with pytest.raises(Exception) as exc_info:
            await mcp_client.call_tool("notify_completion", {"title": "Test", "message": "Message"})

        assert "Notification display failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_multiple_selection_keyboard_interrupt(mcp_client: Client) -> None:
    """Test multiple selection handles Ctrl+C gracefully."""
    with patch("hitl_mcp_cli.server.prompt_checkbox", new_callable=AsyncMock) as mock:
        mock.side_effect = KeyboardInterrupt()

        with pytest.raises(Exception) as exc_info:
            await mcp_client.call_tool(
                "request_selection",
                {"prompt": "Select:", "choices": ["A", "B"], "allow_multiple": True},
            )

        assert "User cancelled" in str(exc_info.value)
