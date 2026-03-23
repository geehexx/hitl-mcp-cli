"""E2E scenario tests: realistic agent workflows through the MCP server."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastmcp import Client

from hitl_mcp_cli.server import mcp


@pytest.fixture
async def mcp_client() -> Client:
    async with Client(mcp) as client:
        yield client


class TestApprovalWorkflow:
    """hitl_notify → hitl_confirm → hitl_notify — full round trip."""

    @pytest.mark.asyncio
    async def test_notify_confirm_notify(self, mcp_client: Client) -> None:
        with (
            patch("hitl_mcp_cli.server.display_notification"),
            patch("hitl_mcp_cli.server.prompt_confirm", new_callable=AsyncMock) as mock_confirm,
        ):
            mock_confirm.return_value = True

            r1 = await mcp_client.call_tool(
                "hitl_notify", {"message": "Starting deploy", "level": "info", "title": "Agent"}
            )
            assert r1.data == {"acknowledged": True}

            r2 = await mcp_client.call_tool(
                "hitl_confirm", {"message": "Deploy to prod?", "severity": "medium"}
            )
            assert r2.data == {"action": "accept", "timed_out": False}

            r3 = await mcp_client.call_tool(
                "hitl_notify", {"message": "Deploy complete!", "level": "success", "title": "Agent"}
            )
            assert r3.data == {"acknowledged": True}

    @pytest.mark.asyncio
    async def test_approval_declined(self, mcp_client: Client) -> None:
        with (
            patch("hitl_mcp_cli.server.display_notification"),
            patch("hitl_mcp_cli.server.prompt_confirm", new_callable=AsyncMock) as mock_confirm,
        ):
            mock_confirm.return_value = False

            r1 = await mcp_client.call_tool(
                "hitl_notify", {"message": "Preparing destructive action", "level": "warning"}
            )
            assert r1.data == {"acknowledged": True}

            r2 = await mcp_client.call_tool(
                "hitl_confirm", {"message": "Delete all data?", "severity": "medium"}
            )
            assert r2.data == {"action": "decline", "timed_out": False}


class TestMultiStepCollection:
    """hitl_collect → hitl_choose — sequential, second waits for first."""

    @pytest.mark.asyncio
    async def test_collect_then_choose(self, mcp_client: Client) -> None:
        with (
            patch("hitl_mcp_cli.server.prompt_text", new_callable=AsyncMock) as mock_text,
            patch("hitl_mcp_cli.server.prompt_select", new_callable=AsyncMock) as mock_select,
        ):
            mock_text.return_value = "my-project"
            mock_select.return_value = "Python"

            r1 = await mcp_client.call_tool(
                "hitl_collect", {"message": "Project name:", "default": "untitled"}
            )
            assert r1.data == "my-project"

            r2 = await mcp_client.call_tool(
                "hitl_choose", {"message": "Language:", "choices": ["Python", "TypeScript", "Go"]}
            )
            assert r2.data == "Python"

    @pytest.mark.asyncio
    async def test_collect_multiline_then_choose_multiple(self, mcp_client: Client) -> None:
        with (
            patch("hitl_mcp_cli.server.prompt_text", new_callable=AsyncMock) as mock_text,
            patch("hitl_mcp_cli.server.prompt_checkbox", new_callable=AsyncMock) as mock_cb,
        ):
            mock_text.return_value = "line1\nline2\nline3"
            mock_cb.return_value = ["lint", "test"]

            r1 = await mcp_client.call_tool(
                "hitl_collect", {"message": "Description:", "input_type": "multiline"}
            )
            assert r1.data == "line1\nline2\nline3"

            r2 = await mcp_client.call_tool(
                "hitl_choose",
                {"message": "CI steps:", "choices": ["lint", "test", "deploy"], "multiple": True},
            )
            assert r2.data == ["lint", "test"]

    @pytest.mark.asyncio
    async def test_path_then_confirm(self, mcp_client: Client) -> None:
        with (
            patch("hitl_mcp_cli.server.prompt_path", new_callable=AsyncMock) as mock_path,
            patch("hitl_mcp_cli.server.prompt_confirm", new_callable=AsyncMock) as mock_confirm,
        ):
            mock_path.return_value = "/home/user/config.yaml"
            mock_confirm.return_value = True

            r1 = await mcp_client.call_tool("hitl_collect", {"message": "Config file:", "input_type": "path"})
            assert r1.data == "/home/user/config.yaml"

            r2 = await mcp_client.call_tool("hitl_confirm", {"message": "Apply this config?"})
            assert r2.data == {"action": "accept", "timed_out": False}


class TestTimeoutRecovery:
    """Tool times out → new tool call succeeds — server still healthy."""

    @pytest.mark.asyncio
    async def test_timeout_then_success(self, mcp_client: Client) -> None:
        # First call times out
        with patch("hitl_mcp_cli.server.prompt_confirm", new_callable=AsyncMock) as mock:

            async def _slow(*a: Any, **kw: Any) -> bool:
                await asyncio.sleep(3)
                return True

            mock.side_effect = _slow
            r1 = await mcp_client.call_tool("hitl_confirm", {"message": "Slow op?", "timeout_seconds": 1})
            assert r1.data["timed_out"] is True

        # Second call succeeds
        with patch("hitl_mcp_cli.server.prompt_text", new_callable=AsyncMock) as mock_text:
            mock_text.return_value = "recovered"
            r2 = await mcp_client.call_tool("hitl_collect", {"message": "Name:"})
            assert r2.data == "recovered"

    @pytest.mark.asyncio
    async def test_timeout_then_confirm_success(self, mcp_client: Client) -> None:
        # Timeout
        with patch("hitl_mcp_cli.server.prompt_confirm", new_callable=AsyncMock) as mock:

            async def _slow(*a: Any, **kw: Any) -> bool:
                await asyncio.sleep(3)
                return True

            mock.side_effect = _slow
            r1 = await mcp_client.call_tool("hitl_confirm", {"message": "Slow?", "timeout_seconds": 1})
            assert r1.data["timed_out"] is True

        # Same tool type succeeds after timeout
        with patch("hitl_mcp_cli.server.prompt_confirm", new_callable=AsyncMock) as mock:
            mock.return_value = False
            r2 = await mcp_client.call_tool("hitl_confirm", {"message": "Try again?", "timeout_seconds": 10})
            assert r2.data["action"] == "decline"
            assert r2.data["timed_out"] is False

    @pytest.mark.asyncio
    async def test_multiple_timeouts_then_success(self, mcp_client: Client) -> None:
        """Server survives multiple consecutive timeouts."""
        for _ in range(3):
            with patch("hitl_mcp_cli.server.prompt_confirm", new_callable=AsyncMock) as mock:

                async def _slow(*a: Any, **kw: Any) -> bool:
                    await asyncio.sleep(3)
                    return True

                mock.side_effect = _slow
                r = await mcp_client.call_tool("hitl_confirm", {"message": "Timeout?", "timeout_seconds": 1})
                assert r.data["timed_out"] is True

        # Still healthy
        with patch("hitl_mcp_cli.server.display_notification"):
            r = await mcp_client.call_tool("hitl_notify", {"message": "Still alive"})
            assert r.data == {"acknowledged": True}
