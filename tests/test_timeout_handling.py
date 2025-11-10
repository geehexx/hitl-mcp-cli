"""Tests for timeout handling and retry scenarios."""

import asyncio
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
async def test_request_text_input_timeout_error(mcp_client: Client) -> None:
    """Test text input handles timeout errors gracefully."""
    with patch("hitl_mcp_cli.server.prompt_text", new_callable=AsyncMock) as mock:
        mock.side_effect = TimeoutError("Request timed out")

        with pytest.raises(Exception) as exc_info:
            await mcp_client.call_tool("request_text_input", {"prompt": "Test:"})

        assert "Input collection failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_request_selection_timeout_error(mcp_client: Client) -> None:
    """Test selection handles timeout errors gracefully."""
    with patch("hitl_mcp_cli.server.prompt_select", new_callable=AsyncMock) as mock:
        mock.side_effect = TimeoutError("Request timed out")

        with pytest.raises(Exception) as exc_info:
            await mcp_client.call_tool("request_selection", {"prompt": "Choose:", "choices": ["A", "B"]})

        assert "Selection failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_request_confirmation_timeout_error(mcp_client: Client) -> None:
    """Test confirmation handles timeout errors gracefully."""
    with patch("hitl_mcp_cli.server.prompt_confirm", new_callable=AsyncMock) as mock:
        mock.side_effect = TimeoutError("Request timed out")

        with pytest.raises(Exception) as exc_info:
            await mcp_client.call_tool("request_confirmation", {"prompt": "Proceed?"})

        assert "Confirmation failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_request_path_input_timeout_error(mcp_client: Client) -> None:
    """Test path input handles timeout errors gracefully."""
    with patch("hitl_mcp_cli.server.prompt_path", new_callable=AsyncMock) as mock:
        mock.side_effect = TimeoutError("Request timed out")

        with pytest.raises(Exception) as exc_info:
            await mcp_client.call_tool("request_path_input", {"prompt": "Select path:"})

        assert "Path input failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_request_text_input_connection_error(mcp_client: Client) -> None:
    """Test text input handles connection errors gracefully."""
    with patch("hitl_mcp_cli.server.prompt_text", new_callable=AsyncMock) as mock:
        mock.side_effect = ConnectionError("Connection lost")

        with pytest.raises(Exception) as exc_info:
            await mcp_client.call_tool("request_text_input", {"prompt": "Test:"})

        assert "Input collection failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_request_selection_connection_error(mcp_client: Client) -> None:
    """Test selection handles connection errors gracefully."""
    with patch("hitl_mcp_cli.server.prompt_select", new_callable=AsyncMock) as mock:
        mock.side_effect = ConnectionError("Connection lost")

        with pytest.raises(Exception) as exc_info:
            await mcp_client.call_tool("request_selection", {"prompt": "Choose:", "choices": ["A", "B"]})

        assert "Selection failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_long_running_operation_success(mcp_client: Client) -> None:
    """Test that long-running operations complete successfully."""
    with patch("hitl_mcp_cli.server.prompt_text", new_callable=AsyncMock) as mock:
        # Simulate a slow user response (5 seconds)
        async def slow_response(*args, **kwargs):
            await asyncio.sleep(0.1)  # Simulate delay
            return "Slow response"

        mock.side_effect = slow_response

        result = await mcp_client.call_tool("request_text_input", {"prompt": "Test:"})

        assert result is not None
        assert result.data == "Slow response"


@pytest.mark.asyncio
async def test_multiple_sequential_calls(mcp_client: Client) -> None:
    """Test multiple sequential tool calls work correctly."""
    with (
        patch("hitl_mcp_cli.server.prompt_text", new_callable=AsyncMock) as mock_text,
        patch("hitl_mcp_cli.server.prompt_select", new_callable=AsyncMock) as mock_select,
        patch("hitl_mcp_cli.server.prompt_confirm", new_callable=AsyncMock) as mock_confirm,
    ):
        mock_text.return_value = "Test Input"
        mock_select.return_value = "Option A"
        mock_confirm.return_value = True

        # Call multiple tools in sequence
        result1 = await mcp_client.call_tool("request_text_input", {"prompt": "Name:"})
        result2 = await mcp_client.call_tool(
            "request_selection", {"prompt": "Choose:", "choices": ["A", "B"]}
        )
        result3 = await mcp_client.call_tool("request_confirmation", {"prompt": "Proceed?"})

        assert result1.data == "Test Input"
        assert result2.data == "Option A"
        assert result3.data is True


@pytest.mark.asyncio
async def test_concurrent_tool_calls(mcp_client: Client) -> None:
    """Test that concurrent tool calls are handled properly."""
    with patch("hitl_mcp_cli.server.prompt_text", new_callable=AsyncMock) as mock:
        mock.return_value = "Concurrent response"

        # Note: In real usage, HITL tools should be called sequentially
        # This test verifies the server can handle concurrent requests
        tasks = [mcp_client.call_tool("request_text_input", {"prompt": f"Test {i}:"}) for i in range(3)]

        results = await asyncio.gather(*tasks)

        assert len(results) == 3
        assert all(r.data == "Concurrent response" for r in results)


@pytest.mark.asyncio
async def test_error_recovery_after_failure(mcp_client: Client) -> None:
    """Test that server recovers after a tool call failure."""
    with patch("hitl_mcp_cli.server.prompt_text", new_callable=AsyncMock) as mock:
        # First call fails
        mock.side_effect = [ValueError("First call failed"), "Second call success"]

        # First call should fail
        with pytest.raises(Exception):
            await mcp_client.call_tool("request_text_input", {"prompt": "Test 1:"})

        # Second call should succeed
        result = await mcp_client.call_tool("request_text_input", {"prompt": "Test 2:"})
        assert result.data == "Second call success"
