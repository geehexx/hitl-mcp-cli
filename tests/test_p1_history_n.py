"""RED tests for queue://history/{n} parameterized resource.

P1 spec: add queue://history/{n} resource that returns the N most-recent
history entries (default 10, max 50).
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest

from hitl_mcp_cli import _server_core
from hitl_mcp_cli.tui.queue import HITLQueue, HITLRequest


@pytest.fixture(autouse=True)
def _reset_tui_globals() -> None:
    _server_core._tui_queue = None
    _server_core._tui_app = None
    yield
    _server_core._tui_queue = None
    _server_core._tui_app = None


def _make_request(message: str = "msg", status: str = "answered") -> HITLRequest:
    loop = asyncio.new_event_loop()
    future: asyncio.Future[Any] = loop.create_future()
    loop.close()
    req = HITLRequest(tool="hitl_confirm", params={"message": message}, future=future)
    req.status = status
    return req


class TestQueueHistoryN:
    def test_history_n_resource_exists(self) -> None:
        """queue://history/{n} resource must be importable."""
        from hitl_mcp_cli.resources._history import queue_history_n  # noqa: F401

    def test_history_n_no_tui_returns_warning(self) -> None:
        from hitl_mcp_cli.resources._history import queue_history_n

        fn = queue_history_n.fn  # type: ignore[attr-defined]
        result = json.loads(fn(n=10))
        assert result["history"] == []
        assert "warning" in result

    def test_history_n_returns_n_entries(self) -> None:
        from hitl_mcp_cli.resources._history import queue_history_n

        fn = queue_history_n.fn  # type: ignore[attr-defined]
        queue = HITLQueue()
        _server_core._tui_queue = queue
        for i in range(20):
            req = _make_request(message=f"msg {i}")
            queue.history.append(req)
            queue._by_id[req.request_id] = req

        result = json.loads(fn(n=5))
        assert result["count"] == 5
        assert len(result["history"]) == 5

    def test_history_n_returns_newest_first(self) -> None:
        from hitl_mcp_cli.resources._history import queue_history_n

        fn = queue_history_n.fn  # type: ignore[attr-defined]
        queue = HITLQueue()
        _server_core._tui_queue = queue
        for i in range(5):
            req = _make_request(message=f"msg {i}")
            queue.history.append(req)
            queue._by_id[req.request_id] = req

        result = json.loads(fn(n=3))
        messages = [e["message"] for e in result["history"]]
        assert messages == ["msg 4", "msg 3", "msg 2"]

    def test_history_n_capped_at_50(self) -> None:
        from hitl_mcp_cli.resources._history import queue_history_n

        fn = queue_history_n.fn  # type: ignore[attr-defined]
        queue = HITLQueue()
        _server_core._tui_queue = queue
        for i in range(60):
            req = _make_request(message=f"msg {i}")
            queue.history.append(req)
            queue._by_id[req.request_id] = req

        result = json.loads(fn(n=100))
        assert result["count"] == 50

    def test_history_n_default_is_10(self) -> None:
        from hitl_mcp_cli.resources._history import queue_history_n

        fn = queue_history_n.fn  # type: ignore[attr-defined]
        queue = HITLQueue()
        _server_core._tui_queue = queue
        for i in range(20):
            req = _make_request(message=f"msg {i}")
            queue.history.append(req)
            queue._by_id[req.request_id] = req

        result = json.loads(fn(n=10))
        assert result["count"] == 10

    def test_history_n_fewer_than_n_returns_all(self) -> None:
        from hitl_mcp_cli.resources._history import queue_history_n

        fn = queue_history_n.fn  # type: ignore[attr-defined]
        queue = HITLQueue()
        _server_core._tui_queue = queue
        for i in range(3):
            req = _make_request(message=f"msg {i}")
            queue.history.append(req)
            queue._by_id[req.request_id] = req

        result = json.loads(fn(n=10))
        assert result["count"] == 3
