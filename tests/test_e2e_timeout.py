"""E2E tests for timeout, cancellation, and post-timeout health."""

from __future__ import annotations

import asyncio
import json

import pytest
from fastmcp import Client

from hitl_mcp_cli.interaction_log import LOG_FILE
from hitl_mcp_cli.server import mcp
from hitl_mcp_cli.tui.queue import HITLQueue, HITLRequest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _pin_timeout_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HITL_MIN_WAIT_MIN", "0")
    monkeypatch.setenv("HITL_DEFAULT_WAIT_MIN", "0.1")
    import hitl_mcp_cli.timeout_config as tc

    tc._config = None
    yield
    tc._config = None


@pytest.fixture
async def tui_queue() -> HITLQueue:
    """Create a TUI queue and configure the server to use it."""
    from hitl_mcp_cli.server import configure_tui_mode

    queue = HITLQueue()
    configure_tui_mode(queue, None)  # type: ignore[arg-type]
    yield queue
    configure_tui_mode(None, None)  # type: ignore[arg-type]


@pytest.fixture
async def mcp_client(tui_queue: HITLQueue) -> Client:
    async with Client(mcp) as client:
        yield client


# ---------------------------------------------------------------------------
# Timeout via MCP Client (TUI mode — exercises server.py timeout paths)
# ---------------------------------------------------------------------------


class TestConfirmTimeout:
    @pytest.mark.asyncio
    async def test_confirm_timeout_returns_decline(self, mcp_client: Client, tui_queue: HITLQueue) -> None:
        """hitl_confirm with timeout_seconds=1 and no resolution → timed_out: true."""
        # Don't resolve — let it time out
        result = await mcp_client.call_tool("hitl_confirm", {"message": "Deploy?", "max_wait_minutes": 0.02})
        assert result.data["status"] == "timeout"

    @pytest.mark.asyncio
    async def test_confirm_no_timeout_when_fast(self, mcp_client: Client, tui_queue: HITLQueue) -> None:
        """Fast response within timeout window → timed_out: false."""

        async def _resolve() -> None:
            req = await tui_queue.get()
            tui_queue.resolve(req, {"action": "accept"})

        task = asyncio.create_task(_resolve())
        result = await mcp_client.call_tool(
            "hitl_confirm", {"message": "Continue?", "max_wait_minutes": 0.020}
        )
        await task
        assert result.data["timed_out"] is False
        assert result.data["action"] == "accept"


class TestCollectTimeout:
    @pytest.mark.asyncio
    async def test_collect_slow_prompt_completes(self, mcp_client: Client, tui_queue: HITLQueue) -> None:
        """hitl_collect has no built-in timeout — resolves when queue resolves."""

        async def _resolve() -> None:
            req = await tui_queue.get()
            tui_queue.resolve(req, "delayed")

        task = asyncio.create_task(_resolve())
        result = await mcp_client.call_tool("hitl_collect", {"message": "Name:"})
        await task
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
    async def test_new_call_after_timeout(self, mcp_client: Client, tui_queue: HITLQueue) -> None:
        """After a timeout, server still accepts new tool calls."""
        r1 = await mcp_client.call_tool("hitl_confirm", {"message": "Slow?", "max_wait_minutes": 0.02})
        assert r1.data["status"] == "timeout"

        async def _resolve() -> None:
            req = await tui_queue.get()
            tui_queue.resolve(req, "healthy")

        task = asyncio.create_task(_resolve())
        r2 = await mcp_client.call_tool("hitl_collect", {"message": "Name:"})
        await task
        assert r2.data == "healthy"

    @pytest.mark.asyncio
    async def test_notify_after_timeout(self, mcp_client: Client, tui_queue: HITLQueue) -> None:
        """hitl_notify works after a confirm timeout."""
        await mcp_client.call_tool("hitl_confirm", {"message": "Slow?", "max_wait_minutes": 0.02})

        r = await mcp_client.call_tool("hitl_notify", {"message": "Still alive"})
        assert r.data == {"acknowledged": True}


# ---------------------------------------------------------------------------
# Interaction log on timeout
# ---------------------------------------------------------------------------


class TestInteractionLogOnTimeout:
    @pytest.mark.asyncio
    async def test_timeout_logged(self, mcp_client: Client, tui_queue: HITLQueue) -> None:
        """Verify result_type: timeout written to interaction log."""
        await mcp_client.call_tool("hitl_confirm", {"message": "Log timeout?", "max_wait_minutes": 0.02})

        # Read the last log entry (conftest redirects LOG_FILE to tmp)
        entries = [json.loads(line) for line in LOG_FILE.read_text().splitlines() if line.strip()]
        timeout_entries = [e for e in entries if e.get("result_type") == "timeout"]
        assert len(timeout_entries) >= 1
        assert timeout_entries[-1]["tool"] == "hitl_confirm"
