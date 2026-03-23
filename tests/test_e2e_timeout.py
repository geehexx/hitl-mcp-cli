"""E2E tests for timeout, cancellation, and post-timeout health."""

from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastmcp import Client

from hitl_mcp_cli.interaction_log import LOG_FILE
from hitl_mcp_cli.server import mcp
from hitl_mcp_cli.tui.queue import HITLQueue, HITLRequest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def mcp_client() -> Client:
    async with Client(mcp) as client:
        yield client


# ---------------------------------------------------------------------------
# Timeout via MCP Client (non-TUI mode — exercises server.py timeout paths)
# ---------------------------------------------------------------------------


class TestConfirmTimeout:
    @pytest.mark.asyncio
    async def test_confirm_timeout_returns_decline(self, mcp_client: Client) -> None:
        """hitl_confirm with timeout_seconds=1 and slow prompt → timed_out: true."""
        with patch("hitl_mcp_cli.server.prompt_confirm", new_callable=AsyncMock) as mock:

            async def _slow(*a: Any, **kw: Any) -> bool:
                await asyncio.sleep(3)
                return True

            mock.side_effect = _slow
            result = await mcp_client.call_tool("hitl_confirm", {"message": "Deploy?", "timeout_seconds": 1})
            assert result.data["timed_out"] is True
            assert result.data["action"] == "decline"

    @pytest.mark.asyncio
    async def test_confirm_no_timeout_when_fast(self, mcp_client: Client) -> None:
        """Fast response within timeout window → timed_out: false."""
        with patch("hitl_mcp_cli.server.prompt_confirm", new_callable=AsyncMock) as mock:
            mock.return_value = True
            result = await mcp_client.call_tool(
                "hitl_confirm", {"message": "Continue?", "timeout_seconds": 10}
            )
            assert result.data["timed_out"] is False
            assert result.data["action"] == "accept"


class TestCollectTimeout:
    @pytest.mark.asyncio
    async def test_collect_slow_prompt_completes(self, mcp_client: Client) -> None:
        """hitl_collect has no built-in timeout — slow prompt still returns."""
        with patch("hitl_mcp_cli.server.prompt_text", new_callable=AsyncMock) as mock:

            async def _slow(*a: Any, **kw: Any) -> str:
                await asyncio.sleep(0.1)
                return "delayed"

            mock.side_effect = _slow
            result = await mcp_client.call_tool("hitl_collect", {"message": "Name:"})
            assert result.data == "delayed"


# ---------------------------------------------------------------------------
# Cancellation cleanup at queue level
# ---------------------------------------------------------------------------


class TestCancellationCleanup:
    @pytest.mark.asyncio
    async def test_cancel_pending_future(self) -> None:
        """Cancel a pending future — verify cancelled, queue returns to 0."""
        queue = HITLQueue()
        loop = asyncio.get_running_loop()
        req = HITLRequest(
            tool="hitl_confirm",
            params={"message": "cancel me"},
            future=loop.create_future(),
        )
        await queue.put(req)
        assert queue.size == 1

        r = await queue.get()
        r.future.cancel()
        assert r.future.cancelled()
        assert queue.size == 0

    @pytest.mark.asyncio
    async def test_resolve_cancelled_future_no_error(self) -> None:
        """Resolving an already-cancelled future should not raise."""
        queue = HITLQueue()
        loop = asyncio.get_running_loop()
        req = HITLRequest(
            tool="hitl_confirm",
            params={"message": "cancel me"},
            future=loop.create_future(),
        )
        await queue.put(req)
        r = await queue.get()
        r.future.cancel()
        # resolve after cancel — done() guard should protect
        queue.resolve(r, "late")
        assert r.future.cancelled()


# ---------------------------------------------------------------------------
# Server health after timeout
# ---------------------------------------------------------------------------


class TestServerHealthAfterTimeout:
    @pytest.mark.asyncio
    async def test_new_call_after_timeout(self, mcp_client: Client) -> None:
        """After a timeout, server still accepts new tool calls."""
        with patch("hitl_mcp_cli.server.prompt_confirm", new_callable=AsyncMock) as mock_confirm:

            async def _slow(*a: Any, **kw: Any) -> bool:
                await asyncio.sleep(3)
                return True

            mock_confirm.side_effect = _slow
            r1 = await mcp_client.call_tool("hitl_confirm", {"message": "Slow?", "timeout_seconds": 1})
            assert r1.data["timed_out"] is True

        # New call should work fine
        with patch("hitl_mcp_cli.server.prompt_text", new_callable=AsyncMock) as mock_text:
            mock_text.return_value = "healthy"
            r2 = await mcp_client.call_tool("hitl_collect", {"message": "Name:"})
            assert r2.data == "healthy"

    @pytest.mark.asyncio
    async def test_notify_after_timeout(self, mcp_client: Client) -> None:
        """hitl_notify works after a confirm timeout."""
        with patch("hitl_mcp_cli.server.prompt_confirm", new_callable=AsyncMock) as mock:

            async def _slow(*a: Any, **kw: Any) -> bool:
                await asyncio.sleep(3)
                return True

            mock.side_effect = _slow
            await mcp_client.call_tool("hitl_confirm", {"message": "Slow?", "timeout_seconds": 1})

        with patch("hitl_mcp_cli.server.display_notification"):
            r = await mcp_client.call_tool("hitl_notify", {"message": "Still alive"})
            assert r.data == {"acknowledged": True}


# ---------------------------------------------------------------------------
# Interaction log on timeout
# ---------------------------------------------------------------------------


class TestInteractionLogOnTimeout:
    @pytest.mark.asyncio
    async def test_timeout_logged(self, mcp_client: Client) -> None:
        """Verify result_type: timeout written to interaction log."""
        with patch("hitl_mcp_cli.server.prompt_confirm", new_callable=AsyncMock) as mock:

            async def _slow(*a: Any, **kw: Any) -> bool:
                await asyncio.sleep(3)
                return True

            mock.side_effect = _slow
            await mcp_client.call_tool("hitl_confirm", {"message": "Log timeout?", "timeout_seconds": 1})

        # Read the last log entry (conftest redirects LOG_FILE to tmp)
        entries = [json.loads(line) for line in LOG_FILE.read_text().splitlines() if line.strip()]
        timeout_entries = [e for e in entries if e.get("result_type") == "timeout"]
        assert len(timeout_entries) >= 1
        assert timeout_entries[-1]["tool"] == "hitl_confirm"
