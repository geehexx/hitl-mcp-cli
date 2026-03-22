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
async def test_hitl_collect_keyboard_interrupt(mcp_client: Client) -> None:
    """Test text input handles Ctrl+C gracefully by returning cancel action."""
    with patch("hitl_mcp_cli.server.prompt_text", new_callable=AsyncMock) as mock:
        mock.side_effect = KeyboardInterrupt()

        result = await mcp_client.call_tool("hitl_collect", {"message": "Test:"})

        assert result is not None
        assert result.data == {"action": "cancel"}


@pytest.mark.asyncio
async def test_hitl_collect_generic_error(mcp_client: Client) -> None:
    """Test text input handles generic errors."""
    with patch("hitl_mcp_cli.server.prompt_text", new_callable=AsyncMock) as mock:
        mock.side_effect = ValueError("Invalid input")

        with pytest.raises(Exception) as exc_info:
            await mcp_client.call_tool("hitl_collect", {"message": "Test:"})

        assert "Input collection failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_hitl_choose_keyboard_interrupt(mcp_client: Client) -> None:
    """Test selection handles Ctrl+C gracefully by returning cancel action."""
    with patch("hitl_mcp_cli.server.prompt_select", new_callable=AsyncMock) as mock:
        mock.side_effect = KeyboardInterrupt()

        result = await mcp_client.call_tool("hitl_choose", {"message": "Choose:", "choices": ["A", "B"]})

        assert result is not None
        assert result.data == {"action": "cancel"}


@pytest.mark.asyncio
async def test_hitl_choose_generic_error(mcp_client: Client) -> None:
    """Test selection handles generic errors."""
    with patch("hitl_mcp_cli.server.prompt_select", new_callable=AsyncMock) as mock:
        mock.side_effect = RuntimeError("Selection failed")

        with pytest.raises(Exception) as exc_info:
            await mcp_client.call_tool("hitl_choose", {"message": "Choose:", "choices": ["A", "B"]})

        assert "Selection failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_hitl_confirm_keyboard_interrupt(mcp_client: Client) -> None:
    """Test confirmation handles Ctrl+C gracefully by returning cancel action."""
    with patch("hitl_mcp_cli.server.prompt_confirm", new_callable=AsyncMock) as mock:
        mock.side_effect = KeyboardInterrupt()

        result = await mcp_client.call_tool("hitl_confirm", {"message": "Proceed?"})

        assert result is not None
        assert result.data == {"action": "cancel"}


@pytest.mark.asyncio
async def test_hitl_confirm_generic_error(mcp_client: Client) -> None:
    """Test confirmation handles generic errors."""
    with patch("hitl_mcp_cli.server.prompt_confirm", new_callable=AsyncMock) as mock:
        mock.side_effect = OSError("Terminal error")

        with pytest.raises(Exception) as exc_info:
            await mcp_client.call_tool("hitl_confirm", {"message": "Proceed?"})

        assert "Confirmation failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_hitl_collect_path_keyboard_interrupt(mcp_client: Client) -> None:
    """Test path input handles Ctrl+C gracefully by returning cancel action."""
    with patch("hitl_mcp_cli.server.prompt_path", new_callable=AsyncMock) as mock:
        mock.side_effect = KeyboardInterrupt()

        result = await mcp_client.call_tool("hitl_collect", {"message": "Select path:", "input_type": "path"})

        assert result is not None
        assert result.data == {"action": "cancel"}


@pytest.mark.asyncio
async def test_hitl_collect_path_generic_error(mcp_client: Client) -> None:
    """Test path input handles generic errors."""
    with patch("hitl_mcp_cli.server.prompt_path", new_callable=AsyncMock) as mock:
        mock.side_effect = PermissionError("Access denied")

        with pytest.raises(Exception) as exc_info:
            await mcp_client.call_tool("hitl_collect", {"message": "Select path:", "input_type": "path"})

        assert "Input collection failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_hitl_notify_error(mcp_client: Client) -> None:
    """Test notification handles errors."""
    with patch("hitl_mcp_cli.server.display_notification") as mock:
        mock.side_effect = RuntimeError("Display error")

        with pytest.raises(Exception) as exc_info:
            await mcp_client.call_tool("hitl_notify", {"message": "Message"})

        assert "Notification display failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_hitl_choose_multiple_keyboard_interrupt(mcp_client: Client) -> None:
    """Test multiple selection handles Ctrl+C gracefully by returning cancel action."""
    with patch("hitl_mcp_cli.server.prompt_checkbox", new_callable=AsyncMock) as mock:
        mock.side_effect = KeyboardInterrupt()

        result = await mcp_client.call_tool(
            "hitl_choose",
            {"message": "Select:", "choices": ["A", "B"], "multiple": True},
        )

        assert result is not None
        assert result.data == {"action": "cancel"}
