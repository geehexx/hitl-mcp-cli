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
async def test_hitl_collect_timeout_error(mcp_client: Client) -> None:
    """Test text input handles timeout errors gracefully."""
    with patch("hitl_mcp_cli.server.prompt_text", new_callable=AsyncMock) as mock:
        mock.side_effect = TimeoutError("Request timed out")

        with pytest.raises(Exception) as exc_info:
            await mcp_client.call_tool("hitl_collect", {"message": "Test:"})

        assert "Input collection failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_hitl_choose_timeout_error(mcp_client: Client) -> None:
    """Test selection handles timeout errors gracefully."""
    with patch("hitl_mcp_cli.server.prompt_select", new_callable=AsyncMock) as mock:
        mock.side_effect = TimeoutError("Request timed out")

        with pytest.raises(Exception) as exc_info:
            await mcp_client.call_tool("hitl_choose", {"message": "Choose:", "choices": ["A", "B"]})

        assert "Selection failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_hitl_confirm_timeout_error(mcp_client: Client) -> None:
    """Test confirmation handles timeout errors gracefully."""
    with patch("hitl_mcp_cli.server.prompt_confirm", new_callable=AsyncMock) as mock:
        mock.side_effect = TimeoutError("Request timed out")

        with pytest.raises(Exception) as exc_info:
            await mcp_client.call_tool("hitl_confirm", {"message": "Proceed?"})

        assert "Confirmation failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_hitl_collect_path_timeout_error(mcp_client: Client) -> None:
    """Test path input handles timeout errors gracefully."""
    with patch("hitl_mcp_cli.server.prompt_path", new_callable=AsyncMock) as mock:
        mock.side_effect = TimeoutError("Request timed out")

        with pytest.raises(Exception) as exc_info:
            await mcp_client.call_tool("hitl_collect", {"message": "Select path:", "input_type": "path"})

        assert "Input collection failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_hitl_collect_connection_error(mcp_client: Client) -> None:
    """Test text input handles connection errors gracefully."""
    with patch("hitl_mcp_cli.server.prompt_text", new_callable=AsyncMock) as mock:
        mock.side_effect = ConnectionError("Connection lost")

        with pytest.raises(Exception) as exc_info:
            await mcp_client.call_tool("hitl_collect", {"message": "Test:"})

        assert "Input collection failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_hitl_choose_connection_error(mcp_client: Client) -> None:
    """Test selection handles connection errors gracefully."""
    with patch("hitl_mcp_cli.server.prompt_select", new_callable=AsyncMock) as mock:
        mock.side_effect = ConnectionError("Connection lost")

        with pytest.raises(Exception) as exc_info:
            await mcp_client.call_tool("hitl_choose", {"message": "Choose:", "choices": ["A", "B"]})

        assert "Selection failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_long_running_operation_success(mcp_client: Client) -> None:
    """Test that long-running operations complete successfully."""
    with patch("hitl_mcp_cli.server.prompt_text", new_callable=AsyncMock) as mock:

        async def slow_response(*args: object, **kwargs: object) -> str:
            await asyncio.sleep(0.1)
            return "Slow response"

        mock.side_effect = slow_response

        result = await mcp_client.call_tool("hitl_collect", {"message": "Test:"})

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

        result1 = await mcp_client.call_tool("hitl_collect", {"message": "Name:"})
        result2 = await mcp_client.call_tool("hitl_choose", {"message": "Choose:", "choices": ["A", "B"]})
        result3 = await mcp_client.call_tool("hitl_confirm", {"message": "Proceed?"})

        assert result1.data == "Test Input"
        assert result2.data == "Option A"
        assert result3.data == {"action": "accept"}


@pytest.mark.asyncio
async def test_concurrent_tool_calls(mcp_client: Client) -> None:
    """Test that concurrent tool calls are handled properly."""
    with patch("hitl_mcp_cli.server.prompt_text", new_callable=AsyncMock) as mock:
        mock.return_value = "Concurrent response"

        tasks = [mcp_client.call_tool("hitl_collect", {"message": f"Test {i}:"}) for i in range(3)]

        results = await asyncio.gather(*tasks)

        assert len(results) == 3
        assert all(r.data == "Concurrent response" for r in results)


@pytest.mark.asyncio
async def test_error_recovery_after_failure(mcp_client: Client) -> None:
    """Test that server recovers after a tool call failure."""
    with patch("hitl_mcp_cli.server.prompt_text", new_callable=AsyncMock) as mock:
        mock.side_effect = [ValueError("First call failed"), "Second call success"]

        with pytest.raises(Exception):
            await mcp_client.call_tool("hitl_collect", {"message": "Test 1:"})

        result = await mcp_client.call_tool("hitl_collect", {"message": "Test 2:"})
        assert result.data == "Second call success"


@pytest.mark.asyncio
async def test_hitl_approve_workflow_timeout(mcp_client: Client) -> None:
    """Test approve_workflow returns timed_out when prompt exceeds timeout."""
    with patch("hitl_mcp_cli.server.display_notification"):
        with patch("hitl_mcp_cli.server.prompt_select", new_callable=AsyncMock) as mock:

            async def slow_prompt(*args: object, **kwargs: object) -> str:
                await asyncio.sleep(2)
                return "Approve"

            mock.side_effect = slow_prompt

            result = await mcp_client.call_tool(
                "hitl_approve_workflow",
                {"message": "Deploy?", "timeout_seconds": 1},
            )

            assert result is not None
            assert result.data == {"approved": False, "choice": "", "timed_out": True}


@pytest.mark.asyncio
async def test_hitl_approve_workflow_keyboard_interrupt(mcp_client: Client) -> None:
    """Test approve_workflow returns cancel on KeyboardInterrupt."""
    with patch("hitl_mcp_cli.server.display_notification"):
        with patch("hitl_mcp_cli.server.prompt_select", new_callable=AsyncMock) as mock:
            mock.side_effect = KeyboardInterrupt()

            result = await mcp_client.call_tool(
                "hitl_approve_workflow",
                {"message": "Deploy?", "timeout_seconds": 0},
            )

            assert result is not None
            assert result.data["action"] == "cancel"
            assert result.data["approved"] is False
            assert result.data["timed_out"] is False


@pytest.mark.asyncio
async def test_hitl_collect_keyboard_interrupt_cancel(mcp_client: Client) -> None:
    """Test hitl_collect returns cancel dict on KeyboardInterrupt."""
    with patch("hitl_mcp_cli.server.prompt_text", new_callable=AsyncMock) as mock:
        mock.side_effect = KeyboardInterrupt()

        result = await mcp_client.call_tool("hitl_collect", {"message": "Name:"})

        assert result is not None
        assert result.data == {"action": "cancel"}


@pytest.mark.asyncio
async def test_hitl_choose_keyboard_interrupt_cancel(mcp_client: Client) -> None:
    """Test hitl_choose returns cancel dict on KeyboardInterrupt."""
    with patch("hitl_mcp_cli.server.prompt_select", new_callable=AsyncMock) as mock:
        mock.side_effect = KeyboardInterrupt()

        result = await mcp_client.call_tool("hitl_choose", {"message": "Pick:", "choices": ["A", "B"]})

        assert result is not None
        assert result.data == {"action": "cancel"}
