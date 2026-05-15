"""Tests for MCP resources: queue://pending, queue://history,
session://activity, session://last-user-action-age."""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any
from unittest.mock import MagicMock

import pytest

from hitl_mcp_cli import _server_core
from hitl_mcp_cli.resources._history import queue_history as _queue_history_resource
from hitl_mcp_cli.resources._last_action_age import last_user_action_age as _last_action_age_resource
from hitl_mcp_cli.resources._pending import queue_pending as _queue_pending_resource
from hitl_mcp_cli.resources._session_activity import session_activity as _session_activity_resource
from hitl_mcp_cli.tui.queue import HITLQueue, HITLRequest

# Access the underlying functions behind @mcp.resource() wrappers
queue_pending = _queue_pending_resource.fn  # type: ignore[attr-defined]
queue_history = _queue_history_resource.fn  # type: ignore[attr-defined]
session_activity = _session_activity_resource.fn  # type: ignore[attr-defined]
last_user_action_age = _last_action_age_resource.fn  # type: ignore[attr-defined]


@pytest.fixture(autouse=True)
def _reset_tui_globals() -> Any:
    """Reset TUI globals before/after each test."""
    _server_core._tui_queue = None
    _server_core._tui_app = None
    yield
    _server_core._tui_queue = None
    _server_core._tui_app = None


def _make_request(
    tool: str = "hitl_confirm",
    message: str = "Are you sure?",
    priority: int = 5,
    status: str = "pending",
) -> HITLRequest:
    loop = asyncio.new_event_loop()
    future: asyncio.Future[Any] = loop.create_future()
    loop.close()
    req = HITLRequest(tool=tool, params={"message": message}, future=future, priority=priority)
    req.status = status
    return req


# ---------------------------------------------------------------------------
# queue://pending
# ---------------------------------------------------------------------------


class TestQueuePending:
    def test_no_tui_returns_warning(self) -> None:
        result = json.loads(queue_pending())
        assert result["pending"] == []
        assert "warning" in result

    def test_empty_queue(self) -> None:
        queue = HITLQueue()
        _server_core._tui_queue = queue
        result = json.loads(queue_pending())
        assert result["pending"] == []
        assert result["count"] == 0

    def test_pending_request_appears(self) -> None:
        queue = HITLQueue()
        _server_core._tui_queue = queue
        req = _make_request(message="Deploy to prod?", priority=3)
        queue.history.append(req)
        queue._by_id[req.request_id] = req

        result = json.loads(queue_pending())
        assert result["count"] == 1
        entry = result["pending"][0]
        assert entry["tool"] == "hitl_confirm"
        assert entry["message"] == "Deploy to prod?"
        assert entry["priority"] == 3
        assert entry["request_id"] == req.request_id
        assert isinstance(entry["elapsed_seconds"], int)

    def test_answered_request_excluded(self) -> None:
        queue = HITLQueue()
        _server_core._tui_queue = queue
        req = _make_request(status="answered")
        queue.history.append(req)
        queue._by_id[req.request_id] = req

        result = json.loads(queue_pending())
        assert result["count"] == 0

    def test_long_message_truncated(self) -> None:
        queue = HITLQueue()
        _server_core._tui_queue = queue
        long_msg = "x" * 200
        req = _make_request(message=long_msg)
        queue.history.append(req)
        queue._by_id[req.request_id] = req

        result = json.loads(queue_pending())
        entry = result["pending"][0]
        assert entry["message"].endswith("...")
        assert len(entry["message"]) == 123  # 120 + "..."

    def test_short_message_not_truncated(self) -> None:
        queue = HITLQueue()
        _server_core._tui_queue = queue
        req = _make_request(message="Short msg")
        queue.history.append(req)
        queue._by_id[req.request_id] = req

        result = json.loads(queue_pending())
        assert result["pending"][0]["message"] == "Short msg"

    def test_multiple_statuses_only_pending_shown(self) -> None:
        queue = HITLQueue()
        _server_core._tui_queue = queue
        for status in ("pending", "answered", "cancelled", "minimized"):
            req = _make_request(status=status)
            queue.history.append(req)
            queue._by_id[req.request_id] = req

        result = json.loads(queue_pending())
        assert result["count"] == 1

    def test_client_name_and_project_id_included(self) -> None:
        queue = HITLQueue()
        _server_core._tui_queue = queue
        loop = asyncio.new_event_loop()
        future: asyncio.Future[Any] = loop.create_future()
        loop.close()
        req = HITLRequest(
            tool="hitl_confirm",
            params={"message": "ok?", "_client_name": "my-agent", "project_id": "proj-1"},
            future=future,
        )
        queue.history.append(req)
        queue._by_id[req.request_id] = req

        result = json.loads(queue_pending())
        entry = result["pending"][0]
        assert entry["client_name"] == "my-agent"
        assert entry["project_id"] == "proj-1"


# ---------------------------------------------------------------------------
# queue://history
# ---------------------------------------------------------------------------


class TestQueueHistory:
    def test_no_tui_returns_warning(self) -> None:
        result = json.loads(queue_history())
        assert result["history"] == []
        assert "warning" in result

    def test_empty_history(self) -> None:
        queue = HITLQueue()
        _server_core._tui_queue = queue
        result = json.loads(queue_history())
        assert result["history"] == []
        assert result["count"] == 0

    def test_history_entry_fields(self) -> None:
        queue = HITLQueue()
        _server_core._tui_queue = queue
        req = _make_request(tool="hitl_collect", message="Your name?", status="answered")
        req.answer_preview = "Alice"
        queue.history.append(req)
        queue._by_id[req.request_id] = req

        result = json.loads(queue_history())
        assert result["count"] == 1
        entry = result["history"][0]
        assert entry["tool"] == "hitl_collect"
        assert entry["message"] == "Your name?"
        assert entry["status"] == "answered"
        assert entry["answer_preview"] == "Alice"
        assert isinstance(entry["elapsed_seconds"], int)

    def test_history_capped_at_50(self) -> None:
        queue = HITLQueue()
        _server_core._tui_queue = queue
        for i in range(60):
            req = _make_request(message=f"msg {i}")
            queue.history.append(req)
            queue._by_id[req.request_id] = req

        result = json.loads(queue_history())
        assert result["count"] == 50

    def test_history_returned_newest_first(self) -> None:
        queue = HITLQueue()
        _server_core._tui_queue = queue
        for i in range(3):
            req = _make_request(message=f"msg {i}")
            req.created_at = time.monotonic() + i
            queue.history.append(req)
            queue._by_id[req.request_id] = req

        result = json.loads(queue_history())
        messages = [e["message"] for e in result["history"]]
        assert messages == ["msg 2", "msg 1", "msg 0"]

    def test_long_message_truncated(self) -> None:
        queue = HITLQueue()
        _server_core._tui_queue = queue
        req = _make_request(message="y" * 200)
        queue.history.append(req)
        queue._by_id[req.request_id] = req

        result = json.loads(queue_history())
        assert result["history"][0]["message"].endswith("...")


# ---------------------------------------------------------------------------
# session://activity
# ---------------------------------------------------------------------------


class TestSessionActivity:
    def test_no_tui_returns_warning(self) -> None:
        result = json.loads(session_activity())
        assert result["sessions"] == []
        assert "warning" in result

    def test_no_sessions(self) -> None:
        app = MagicMock()
        app._sessions = {}
        _server_core._tui_app = app
        result = json.loads(session_activity())
        assert result["sessions"] == []
        assert result["count"] == 0

    def test_session_fields(self) -> None:
        app = MagicMock()
        now = time.monotonic()
        app._sessions = {
            "sess-1": {
                "client_name": "agent-a",
                "project_id": "proj-x",
                "call_count": 5,
                "pending_count": 2,
                "last_active_ts": now - 30,
            }
        }
        _server_core._tui_app = app
        result = json.loads(session_activity())
        assert result["count"] == 1
        s = result["sessions"][0]
        assert s["session_id"] == "sess-1"
        assert s["client_name"] == "agent-a"
        assert s["project_id"] == "proj-x"
        assert s["call_count"] == 5
        assert s["pending_count"] == 2
        assert s["last_active_seconds_ago"] == 30

    def test_sessions_sorted_by_recency(self) -> None:
        app = MagicMock()
        now = time.monotonic()
        app._sessions = {
            "old": {
                "last_active_ts": now - 100,
                "client_name": "old",
                "project_id": None,
                "call_count": 0,
                "pending_count": 0,
            },
            "recent": {
                "last_active_ts": now - 5,
                "client_name": "recent",
                "project_id": None,
                "call_count": 0,
                "pending_count": 0,
            },
        }
        _server_core._tui_app = app
        result = json.loads(session_activity())
        names = [s["client_name"] for s in result["sessions"]]
        assert names == ["recent", "old"]

    def test_missing_last_active_ts_defaults_to_now(self) -> None:
        app = MagicMock()
        app._sessions = {
            "sess-no-ts": {"client_name": "x", "project_id": None, "call_count": 1, "pending_count": 0}
        }
        _server_core._tui_app = app
        result = json.loads(session_activity())
        assert result["count"] == 1
        # last_active_ts defaults to now, so elapsed should be ~0
        assert result["sessions"][0]["last_active_seconds_ago"] <= 1

    def test_app_without_sessions_attr(self) -> None:
        app = MagicMock(spec=[])  # no _sessions attribute
        _server_core._tui_app = app
        result = json.loads(session_activity())
        assert result["sessions"] == []
        assert result["count"] == 0


# ---------------------------------------------------------------------------
# session://last-user-action-age
# ---------------------------------------------------------------------------


class TestLastUserActionAge:
    def test_no_tui_returns_warning(self) -> None:
        result = json.loads(last_user_action_age())
        assert result["seconds"] is None
        assert "warning" in result

    def test_no_answered_requests(self) -> None:
        queue = HITLQueue()
        _server_core._tui_queue = queue
        result = json.loads(last_user_action_age())
        assert result["seconds"] is None
        assert result["last_request_id"] is None

    def test_answered_request_age(self) -> None:
        queue = HITLQueue()
        _server_core._tui_queue = queue
        req = _make_request(status="answered")
        req._resolved_at = time.monotonic() - 42  # type: ignore[attr-defined]
        queue.history.append(req)
        queue._by_id[req.request_id] = req

        result = json.loads(last_user_action_age())
        assert result["seconds"] == 42
        assert result["last_request_id"] == req.request_id

    def test_cancelled_request_counts(self) -> None:
        queue = HITLQueue()
        _server_core._tui_queue = queue
        req = _make_request(status="cancelled")
        req._resolved_at = time.monotonic() - 10  # type: ignore[attr-defined]
        queue.history.append(req)
        queue._by_id[req.request_id] = req

        result = json.loads(last_user_action_age())
        assert result["seconds"] == 10

    def test_pending_request_excluded(self) -> None:
        queue = HITLQueue()
        _server_core._tui_queue = queue
        req = _make_request(status="pending")
        queue.history.append(req)
        queue._by_id[req.request_id] = req

        result = json.loads(last_user_action_age())
        assert result["seconds"] is None

    def test_most_recent_answered_wins(self) -> None:
        queue = HITLQueue()
        _server_core._tui_queue = queue
        now = time.monotonic()

        old_req = _make_request(status="answered")
        old_req._resolved_at = now - 100  # type: ignore[attr-defined]
        queue.history.append(old_req)
        queue._by_id[old_req.request_id] = old_req

        new_req = _make_request(status="answered")
        new_req._resolved_at = now - 5  # type: ignore[attr-defined]
        queue.history.append(new_req)
        queue._by_id[new_req.request_id] = new_req

        result = json.loads(last_user_action_age())
        assert result["seconds"] == 5
        assert result["last_request_id"] == new_req.request_id

    def test_falls_back_to_created_at_when_no_resolved_at(self) -> None:
        queue = HITLQueue()
        _server_core._tui_queue = queue
        req = _make_request(status="answered")
        # No _resolved_at set — should fall back to created_at
        queue.history.append(req)
        queue._by_id[req.request_id] = req

        result = json.loads(last_user_action_age())
        assert result["seconds"] is not None
        assert result["seconds"] >= 0
