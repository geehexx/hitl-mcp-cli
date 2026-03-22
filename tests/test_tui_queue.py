"""Tests for HITLQueue: ordering, priority, future resolution, sanitization."""

from __future__ import annotations

import asyncio

import pytest

from hitl_mcp_cli.tui.queue import HITLQueue, HITLRequest, _sanitize, _sanitize_params

# --- Sanitization ---


class TestSanitization:
    def test_sanitize_none(self) -> None:
        assert _sanitize(None) is None

    def test_sanitize_plain_text(self) -> None:
        assert _sanitize("hello world") == "hello world"

    def test_sanitize_rich_markup(self) -> None:
        result = _sanitize("[bold]danger[/bold]")
        assert "[bold]" not in result or result.startswith("\\")

    def test_sanitize_params_strings(self) -> None:
        params = {"message": "[red]alert[/red]", "count": 5, "flag": True}
        result = _sanitize_params(params)
        assert result["count"] == 5
        assert result["flag"] is True
        assert "[red]" not in result["message"] or result["message"].startswith("\\")


# --- HITLRequest ---


class TestHITLRequest:
    def test_request_creation(self) -> None:
        loop = asyncio.new_event_loop()
        future: asyncio.Future[str] = loop.create_future()
        req = HITLRequest(tool="confirm", params={"message": "ok?"}, future=future)
        assert req.tool == "confirm"
        assert req.priority == 5
        assert req.request_id  # non-empty uuid
        loop.close()

    def test_request_sanitizes_params(self) -> None:
        loop = asyncio.new_event_loop()
        future: asyncio.Future[str] = loop.create_future()
        req = HITLRequest(tool="confirm", params={"message": "[bold]hi[/bold]"}, future=future)
        assert "[bold]" not in req.params["message"] or req.params["message"].startswith("\\")
        loop.close()

    def test_request_ordering(self) -> None:
        loop = asyncio.new_event_loop()
        high = HITLRequest(
            tool="confirm",
            params={},
            future=loop.create_future(),
            priority=0,
        )
        low = HITLRequest(
            tool="confirm",
            params={},
            future=loop.create_future(),
            priority=10,
        )
        assert high < low
        assert not low < high
        loop.close()


# --- HITLQueue ---


class TestHITLQueue:
    @pytest.mark.asyncio
    async def test_put_get_fifo(self) -> None:
        queue = HITLQueue()
        loop = asyncio.get_event_loop()
        r1 = HITLRequest(tool="a", params={}, future=loop.create_future())
        r2 = HITLRequest(tool="b", params={}, future=loop.create_future())
        await queue.put(r1)
        await queue.put(r2)
        assert queue.size == 2
        got1 = await queue.get()
        assert got1.tool == "a"
        got2 = await queue.get()
        assert got2.tool == "b"
        assert queue.size == 0

    @pytest.mark.asyncio
    async def test_priority_ordering(self) -> None:
        queue = HITLQueue()
        loop = asyncio.get_event_loop()
        low = HITLRequest(tool="low", params={}, future=loop.create_future(), priority=10)
        high = HITLRequest(tool="high", params={}, future=loop.create_future(), priority=0)
        normal = HITLRequest(tool="normal", params={}, future=loop.create_future(), priority=5)
        # Insert in non-priority order
        await queue.put(low)
        await queue.put(high)
        await queue.put(normal)
        got1 = await queue.get()
        got2 = await queue.get()
        got3 = await queue.get()
        assert got1.tool == "high"
        assert got2.tool == "normal"
        assert got3.tool == "low"

    @pytest.mark.asyncio
    async def test_resolve_future(self) -> None:
        queue = HITLQueue()
        loop = asyncio.get_event_loop()
        future: asyncio.Future[dict[str, str]] = loop.create_future()
        req = HITLRequest(tool="confirm", params={}, future=future)
        await queue.put(req)
        got = await queue.get()
        queue.resolve(got, {"action": "accept"})
        assert future.done()
        assert future.result() == {"action": "accept"}

    @pytest.mark.asyncio
    async def test_reject_future(self) -> None:
        queue = HITLQueue()
        loop = asyncio.get_event_loop()
        future: asyncio.Future[dict[str, str]] = loop.create_future()
        req = HITLRequest(tool="confirm", params={}, future=future)
        await queue.put(req)
        got = await queue.get()
        queue.reject(got, TimeoutError("timed out"))
        assert future.done()
        with pytest.raises(TimeoutError, match="timed out"):
            future.result()

    @pytest.mark.asyncio
    async def test_resolve_already_done_is_noop(self) -> None:
        queue = HITLQueue()
        loop = asyncio.get_event_loop()
        future: asyncio.Future[str] = loop.create_future()
        future.set_result("first")
        req = HITLRequest(tool="confirm", params={}, future=future)
        # Should not raise
        queue.resolve(req, "second")
        assert future.result() == "first"

    @pytest.mark.asyncio
    async def test_size_property(self) -> None:
        queue = HITLQueue()
        assert queue.size == 0
        loop = asyncio.get_event_loop()
        await queue.put(HITLRequest(tool="a", params={}, future=loop.create_future()))
        assert queue.size == 1
        await queue.get()
        assert queue.size == 0

    @pytest.mark.asyncio
    async def test_concurrent_submits(self) -> None:
        """Multiple producers can enqueue concurrently."""
        queue = HITLQueue()
        loop = asyncio.get_event_loop()

        async def producer(name: str) -> None:
            req = HITLRequest(tool=name, params={}, future=loop.create_future())
            await queue.put(req)

        await asyncio.gather(producer("a"), producer("b"), producer("c"))
        assert queue.size == 3
