"""E2E tests for HITLQueue: sequential drain, concurrency, future guards, cross-thread resolution."""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Generator
from typing import Any

import pytest

from hitl_mcp_cli.tui.queue import HITLQueue, HITLRequest


def _req(tool: str = "hitl_confirm", params: dict[str, Any] | None = None) -> HITLRequest:
    """Create a request with a future on the running loop."""
    loop = asyncio.get_running_loop()
    return HITLRequest(tool=tool, params=params or {"message": "test"}, future=loop.create_future())


class TestSequentialDrain:
    """3 requests queued, resolved FIFO, all futures resolve with correct values."""

    @pytest.mark.asyncio
    async def test_fifo_order(self) -> None:
        queue = HITLQueue()
        reqs = [_req(params={"message": f"msg-{i}"}) for i in range(3)]
        for r in reqs:
            await queue.put(r)

        results: list[str] = []
        for i in range(3):
            r = await queue.get()
            queue.resolve(r, f"result-{i}")
            results.append(f"result-{i}")

        for i, r in enumerate(reqs):
            assert r.future.done()
            assert r.future.result() == f"result-{i}"
        assert results == ["result-0", "result-1", "result-2"]

    @pytest.mark.asyncio
    async def test_queue_empty_after_drain(self) -> None:
        queue = HITLQueue()
        for _ in range(3):
            await queue.put(_req())
        for _ in range(3):
            r = await queue.get()
            queue.resolve(r, True)
        assert queue.size == 0

    @pytest.mark.asyncio
    async def test_priority_ordering(self) -> None:
        """Higher priority (lower number) dequeued first."""
        queue = HITLQueue()
        low = _req(params={"message": "low"})
        low.priority = 10
        high = _req(params={"message": "high"})
        high.priority = 1
        await queue.put(low)
        await queue.put(high)

        first = await queue.get()
        assert first.params["message"] == "high"
        second = await queue.get()
        assert second.params["message"] == "low"


class TestConcurrentRequests:
    """5 simultaneous requests via asyncio.gather, verify no future is dropped."""

    @pytest.mark.asyncio
    async def test_five_concurrent_no_drop(self) -> None:
        queue = HITLQueue()
        reqs = [_req(params={"message": f"c-{i}"}) for i in range(5)]

        async def enqueue_all() -> None:
            await asyncio.gather(*(queue.put(r) for r in reqs))

        await enqueue_all()
        assert queue.size == 5

        for i in range(5):
            r = await queue.get()
            queue.resolve(r, i)

        assert queue.size == 0
        resolved = sorted(r.future.result() for r in reqs)
        assert resolved == [0, 1, 2, 3, 4]

    @pytest.mark.asyncio
    async def test_concurrent_resolve_all_done(self) -> None:
        queue = HITLQueue()
        reqs = [_req() for _ in range(5)]
        for r in reqs:
            await queue.put(r)

        gotten = [await queue.get() for _ in range(5)]
        for i, g in enumerate(gotten):
            queue.resolve(g, f"v{i}")

        assert all(r.future.done() for r in reqs)


class TestFutureDoneGuard:
    """Calling resolve twice on same future doesn't raise."""

    @pytest.mark.asyncio
    async def test_double_resolve_no_error(self) -> None:
        queue = HITLQueue()
        req = _req()
        await queue.put(req)
        r = await queue.get()
        queue.resolve(r, "first")
        queue.resolve(r, "second")  # should not raise
        assert r.future.result() == "first"

    @pytest.mark.asyncio
    async def test_resolve_after_reject_no_error(self) -> None:
        queue = HITLQueue()
        req = _req()
        await queue.put(req)
        r = await queue.get()
        queue.reject(r, RuntimeError("fail"))
        queue.resolve(r, "late")  # should not raise
        with pytest.raises(RuntimeError, match="fail"):
            r.future.result()

    @pytest.mark.asyncio
    async def test_double_reject_no_error(self) -> None:
        queue = HITLQueue()
        req = _req()
        await queue.put(req)
        r = await queue.get()
        queue.reject(r, RuntimeError("first"))
        queue.reject(r, RuntimeError("second"))  # should not raise
        with pytest.raises(RuntimeError, match="first"):
            r.future.result()


class TestPutThreadsafe:
    """Future created in one thread, resolved from another — result arrives correctly."""

    @pytest.mark.asyncio
    async def test_cross_thread_resolution(self) -> None:
        caller_loop = asyncio.get_running_loop()
        queue = HITLQueue()
        queue.set_caller_loop(caller_loop)

        req = HITLRequest(
            tool="hitl_notify",
            params={"message": "cross-thread"},
            future=caller_loop.create_future(),
        )
        await queue.put(req)
        r = await queue.get()

        # Resolve from a background thread via call_soon_threadsafe
        resolved = asyncio.Event()

        def _bg_resolve() -> None:
            queue.resolve(r, "from-thread")
            caller_loop.call_soon_threadsafe(resolved.set)

        t = threading.Thread(target=_bg_resolve, daemon=True)
        t.start()
        await asyncio.wait_for(resolved.wait(), timeout=2.0)
        t.join(timeout=1)

        assert req.future.done()
        assert req.future.result() == "from-thread"

    @pytest.mark.asyncio
    async def test_put_threadsafe_enqueues(self) -> None:
        """put_threadsafe from a foreign thread lands in the queue."""
        queue = HITLQueue()
        loop = asyncio.get_running_loop()
        queue.set_textual_loop(loop)

        req = HITLRequest(
            tool="hitl_confirm",
            params={"message": "threadsafe"},
            future=loop.create_future(),
        )

        enqueued = asyncio.Event()

        def _bg_put() -> None:
            queue.put_threadsafe(req)
            loop.call_soon_threadsafe(enqueued.set)

        t = threading.Thread(target=_bg_put, daemon=True)
        t.start()
        await asyncio.wait_for(enqueued.wait(), timeout=2.0)
        t.join(timeout=1)

        assert queue.size == 1
        r = await queue.get()
        assert r.tool == "hitl_confirm"


# ---------------------------------------------------------------------------
# TUI-mode server integration: configure_tui_mode + _tui_enqueue paths
# ---------------------------------------------------------------------------


class TestTuiModeEnqueue:
    """Tests that exercise server.py TUI-mode paths (configure_tui_mode + _tui_enqueue)."""

    @pytest.fixture(autouse=True)
    def _reset_tui_mode(self) -> Generator[None, None, None]:
        """Reset TUI mode globals after each test."""
        import hitl_mcp_cli.server as srv

        old_queue, old_app = srv._tui_queue, srv._tui_app
        yield
        srv._tui_queue, srv._tui_app = old_queue, old_app

    @pytest.mark.asyncio
    async def test_tui_notify_resolves_immediately(self) -> None:
        """hitl_notify in TUI mode calls app.stream_output, returns acknowledged."""
        from unittest.mock import MagicMock

        from fastmcp import Client

        import hitl_mcp_cli.server as srv
        from hitl_mcp_cli.tui.queue import HITLQueue

        queue = HITLQueue()
        mock_app = MagicMock()
        srv._tui_queue = queue
        srv._tui_app = mock_app

        async with Client(srv.mcp) as client:
            result = await client.call_tool(
                "hitl_notify", {"message": "TUI notify", "level": "info", "title": "Agent"}
            )
        assert result.data == {"acknowledged": True}
        mock_app.call_from_thread.assert_called()

    @pytest.mark.asyncio
    async def test_tui_confirm_enqueue_and_resolve(self) -> None:
        """hitl_confirm in TUI mode enqueues and resolves via queue."""
        from unittest.mock import MagicMock

        from fastmcp import Client

        import hitl_mcp_cli.server as srv
        from hitl_mcp_cli.tui.queue import HITLQueue

        queue = HITLQueue()
        loop = asyncio.get_running_loop()
        queue.set_caller_loop(loop)
        mock_app = MagicMock()
        srv._tui_queue = queue
        srv._tui_app = mock_app

        async def _resolve_worker() -> None:
            """Background task that resolves the enqueued request."""
            r = await queue.get()
            queue.resolve(r, {"action": "accept"})

        worker = asyncio.create_task(_resolve_worker())

        async with Client(srv.mcp) as client:
            result = await client.call_tool("hitl_confirm", {"message": "TUI confirm?", "severity": "medium"})
        await worker
        assert result.data == {"action": "accept", "timed_out": False}

    @pytest.mark.asyncio
    async def test_tui_confirm_timeout_path(self) -> None:
        """hitl_confirm with timeout in TUI mode returns timed_out when queue never resolves."""
        from unittest.mock import MagicMock

        from fastmcp import Client

        import hitl_mcp_cli.server as srv
        from hitl_mcp_cli.tui.queue import HITLQueue

        queue = HITLQueue()
        loop = asyncio.get_running_loop()
        queue.set_caller_loop(loop)
        mock_app = MagicMock()
        srv._tui_queue = queue
        srv._tui_app = mock_app

        async with Client(srv.mcp) as client:
            result = await client.call_tool("hitl_confirm", {"message": "TUI timeout?", "timeout_seconds": 1})
        assert result.data["timed_out"] is True
        assert result.data["action"] == "decline"

    @pytest.mark.asyncio
    async def test_tui_collect_enqueue_and_resolve(self) -> None:
        """hitl_collect in TUI mode enqueues and resolves via queue."""
        from unittest.mock import MagicMock

        from fastmcp import Client

        import hitl_mcp_cli.server as srv
        from hitl_mcp_cli.tui.queue import HITLQueue

        queue = HITLQueue()
        loop = asyncio.get_running_loop()
        queue.set_caller_loop(loop)
        mock_app = MagicMock()
        srv._tui_queue = queue
        srv._tui_app = mock_app

        async def _resolve_worker() -> None:
            r = await queue.get()
            queue.resolve(r, "tui-input")

        worker = asyncio.create_task(_resolve_worker())

        async with Client(srv.mcp) as client:
            result = await client.call_tool("hitl_collect", {"message": "TUI collect:", "input_type": "text"})
        await worker
        assert result.data == "tui-input"

    @pytest.mark.asyncio
    async def test_tui_choose_enqueue_and_resolve(self) -> None:
        """hitl_choose in TUI mode enqueues and resolves via queue."""
        from unittest.mock import MagicMock

        from fastmcp import Client

        import hitl_mcp_cli.server as srv
        from hitl_mcp_cli.tui.queue import HITLQueue

        queue = HITLQueue()
        loop = asyncio.get_running_loop()
        queue.set_caller_loop(loop)
        mock_app = MagicMock()
        srv._tui_queue = queue
        srv._tui_app = mock_app

        async def _resolve_worker() -> None:
            r = await queue.get()
            queue.resolve(r, "Option B")

        worker = asyncio.create_task(_resolve_worker())

        async with Client(srv.mcp) as client:
            result = await client.call_tool(
                "hitl_choose", {"message": "Pick:", "choices": ["Option A", "Option B"]}
            )
        await worker
        assert result.data == "Option B"

    @pytest.mark.asyncio
    async def test_tui_ask_enqueue_and_resolve(self) -> None:
        """hitl_ask (alias) in TUI mode enqueues and resolves via queue."""
        from unittest.mock import MagicMock

        from fastmcp import Client

        import hitl_mcp_cli.server as srv
        from hitl_mcp_cli.tui.queue import HITLQueue

        queue = HITLQueue()
        loop = asyncio.get_running_loop()
        queue.set_caller_loop(loop)
        mock_app = MagicMock()
        srv._tui_queue = queue
        srv._tui_app = mock_app

        async def _resolve_worker() -> None:
            r = await queue.get()
            queue.resolve(r, "ask-response")

        worker = asyncio.create_task(_resolve_worker())

        async with Client(srv.mcp) as client:
            result = await client.call_tool("hitl_ask", {"message": "TUI ask:"})
        await worker
        assert result.data == "ask-response"

    @pytest.mark.asyncio
    async def test_tui_confirm_no_timeout_resolves(self) -> None:
        """hitl_confirm with timeout_seconds>0 in TUI mode, resolved before timeout."""
        from unittest.mock import MagicMock

        from fastmcp import Client

        import hitl_mcp_cli.server as srv
        from hitl_mcp_cli.tui.queue import HITLQueue

        queue = HITLQueue()
        loop = asyncio.get_running_loop()
        queue.set_caller_loop(loop)
        mock_app = MagicMock()
        srv._tui_queue = queue
        srv._tui_app = mock_app

        async def _resolve_worker() -> None:
            r = await queue.get()
            queue.resolve(r, {"action": "accept"})

        worker = asyncio.create_task(_resolve_worker())

        async with Client(srv.mcp) as client:
            result = await client.call_tool("hitl_confirm", {"message": "Fast?", "timeout_seconds": 10})
        await worker
        assert result.data["timed_out"] is False
        assert result.data["action"] == "accept"
