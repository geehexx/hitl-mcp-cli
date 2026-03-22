"""Tests for TUI mode integration in server.py."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hitl_mcp_cli import server
from hitl_mcp_cli.tui.queue import HITLQueue

# Access the underlying async functions behind @mcp.tool() wrappers
_hitl_collect = server.hitl_collect.fn  # type: ignore[attr-defined]
_hitl_ask = server.hitl_ask.fn  # type: ignore[attr-defined]
_hitl_choose = server.hitl_choose.fn  # type: ignore[attr-defined]
_hitl_confirm = server.hitl_confirm.fn  # type: ignore[attr-defined]
_hitl_notify = server.hitl_notify.fn  # type: ignore[attr-defined]


@pytest.fixture(autouse=True)
def _reset_tui_globals() -> Any:
    """Reset module-level TUI globals before/after each test."""
    server._tui_queue = None
    server._tui_app = None
    yield
    server._tui_queue = None
    server._tui_app = None


class TestConfigureTuiMode:
    def test_sets_globals(self) -> None:
        queue = MagicMock(spec=HITLQueue)
        app = MagicMock()
        server.configure_tui_mode(queue, app)
        assert server._tui_queue is queue
        assert server._tui_app is app


class TestTuiEnqueue:
    @pytest.mark.asyncio
    async def test_enqueues_and_awaits_future(self) -> None:
        queue = HITLQueue()
        server._tui_queue = queue

        async def resolve_next() -> None:
            req = await queue.get()
            assert req.tool == "hitl_confirm"
            assert req.params["message"] == "ok?"
            queue.resolve(req, {"action": "accept"})

        task = asyncio.create_task(resolve_next())
        result = await server._tui_enqueue("hitl_confirm", {"message": "ok?"})
        await task
        assert result == {"action": "accept"}


class TestHitlCollectTuiMode:
    @pytest.mark.asyncio
    async def test_collect_routes_to_tui_queue(self) -> None:
        queue = HITLQueue()
        server._tui_queue = queue

        async def resolve_next() -> None:
            req = await queue.get()
            assert req.tool == "hitl_collect"
            assert req.params["message"] == "Name?"
            queue.resolve(req, "Alice")

        task = asyncio.create_task(resolve_next())
        result = await _hitl_collect(message="Name?")
        await task
        assert result == "Alice"

    @pytest.mark.asyncio
    async def test_collect_falls_through_without_tui(self) -> None:
        with patch("hitl_mcp_cli.server._collect_input", new_callable=AsyncMock, return_value="Bob"):
            result = await _hitl_collect(message="Name?")
        assert result == "Bob"


class TestHitlConfirmTuiMode:
    @pytest.mark.asyncio
    async def test_confirm_routes_to_tui_queue(self) -> None:
        queue = HITLQueue()
        server._tui_queue = queue

        async def resolve_next() -> None:
            req = await queue.get()
            assert req.tool == "hitl_confirm"
            queue.resolve(req, {"action": "accept"})

        task = asyncio.create_task(resolve_next())
        result = await _hitl_confirm(message="Proceed?")
        await task
        assert result == {"action": "accept"}

    @pytest.mark.asyncio
    async def test_confirm_timeout_in_tui_mode(self) -> None:
        queue = HITLQueue()
        server._tui_queue = queue
        # Don't resolve — let it time out
        result = await _hitl_confirm(message="Proceed?", timeout_seconds=1)
        assert result == {"action": "decline", "timed_out": True}


class TestHitlChooseTuiMode:
    @pytest.mark.asyncio
    async def test_choose_routes_to_tui_queue(self) -> None:
        queue = HITLQueue()
        server._tui_queue = queue

        async def resolve_next() -> None:
            req = await queue.get()
            assert req.tool == "hitl_choose"
            queue.resolve(req, "Option A")

        task = asyncio.create_task(resolve_next())
        result = await _hitl_choose(message="Pick one", choices=["Option A", "Option B"])
        await task
        assert result == "Option A"


class TestHitlNotifyTuiMode:
    @pytest.mark.asyncio
    async def test_notify_streams_to_app(self) -> None:
        queue = MagicMock(spec=HITLQueue)
        app = MagicMock()
        server._tui_queue = queue
        server._tui_app = app

        result = await _hitl_notify(message="Done!", title="Build")
        assert result == {"acknowledged": True}
        assert app.call_from_thread.call_count == 2
        app.call_from_thread.assert_any_call(app.stream_output, "Build", "Done!", "info")

    @pytest.mark.asyncio
    async def test_notify_falls_through_without_tui(self) -> None:
        with patch("hitl_mcp_cli.server.display_notification"):
            result = await _hitl_notify(message="Hello")
        assert result == {"acknowledged": True}
