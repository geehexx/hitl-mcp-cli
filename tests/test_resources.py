"""Unit tests for the four low-coverage MCP resource modules.

Covers the main logic paths in:
  - resources/_history.py      (queue://history)
  - resources/_pending.py      (queue://pending)
  - resources/_last_action_age.py  (session://last-user-action-age)
  - resources/_session_activity.py (session://activity)
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any
from unittest.mock import MagicMock

import pytest

from hitl_mcp_cli._server_core import configure_tui_mode
from hitl_mcp_cli.tui.queue import HITLQueue, HITLRequest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_req(
    tool: str = "hitl_confirm",
    params: dict[str, Any] | None = None,
    priority: int = 5,
) -> HITLRequest:
    loop = asyncio.new_event_loop()
    future: asyncio.Future[Any] = loop.create_future()
    return HITLRequest(tool=tool, params=params or {}, future=future, priority=priority)


def _call(resource: Any) -> Any:
    """Call the underlying function of a FastMCP FunctionResource."""
    return resource.fn()  # type: ignore[attr-defined]


@pytest.fixture(autouse=True)
def _reset_tui_mode() -> Any:
    """Ensure TUI mode is cleared after every test."""
    yield
    configure_tui_mode(None, None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# queue://history
# ---------------------------------------------------------------------------


class TestQueueHistory:
    def test_no_queue_returns_warning(self) -> None:
        configure_tui_mode(None, None)  # type: ignore[arg-type]
        from hitl_mcp_cli.resources._history import queue_history

        data = json.loads(_call(queue_history))
        assert data["history"] == []
        assert "warning" in data

    def test_empty_queue_returns_empty_history(self) -> None:
        queue = HITLQueue()
        configure_tui_mode(queue, None)  # type: ignore[arg-type]
        from hitl_mcp_cli.resources._history import queue_history

        data = json.loads(_call(queue_history))
        assert data["history"] == []
        assert data["count"] == 0

    def test_history_includes_registered_requests(self) -> None:
        queue = HITLQueue()
        configure_tui_mode(queue, None)  # type: ignore[arg-type]
        from hitl_mcp_cli.resources._history import queue_history

        req = _make_req("hitl_confirm", {"message": "Delete everything?"})
        queue._register(req)

        data = json.loads(_call(queue_history))
        assert data["count"] == 1
        row = data["history"][0]
        assert row["request_id"] == req.request_id
        assert row["tool"] == "hitl_confirm"
        assert row["status"] == "pending"
        assert "Delete everything?" in row["message"]

    def test_history_truncates_long_messages(self) -> None:
        queue = HITLQueue()
        configure_tui_mode(queue, None)  # type: ignore[arg-type]
        from hitl_mcp_cli.resources._history import queue_history

        long_msg = "x" * 200
        req = _make_req(params={"message": long_msg})
        queue._register(req)

        data = json.loads(_call(queue_history))
        assert data["history"][0]["message"].endswith("...")
        assert len(data["history"][0]["message"]) <= 124  # 120 + "..."

    def test_history_capped_at_50_most_recent(self) -> None:
        queue = HITLQueue()
        configure_tui_mode(queue, None)  # type: ignore[arg-type]
        from hitl_mcp_cli.resources._history import queue_history

        for i in range(60):
            queue._register(_make_req(params={"message": f"msg {i}"}))

        data = json.loads(_call(queue_history))
        assert data["count"] == 50

    def test_history_includes_answered_status(self) -> None:
        queue = HITLQueue()
        configure_tui_mode(queue, None)  # type: ignore[arg-type]
        from hitl_mcp_cli.resources._history import queue_history

        req = _make_req(params={"message": "Proceed?"})
        queue._register(req)
        queue.mark_answered(req.request_id, "yes")

        data = json.loads(_call(queue_history))
        row = data["history"][0]
        assert row["status"] == "answered"
        assert row["answer_preview"] == "yes"

    def test_history_includes_client_name_and_project_id(self) -> None:
        queue = HITLQueue()
        configure_tui_mode(queue, None)  # type: ignore[arg-type]
        from hitl_mcp_cli.resources._history import queue_history

        req = _make_req(params={"message": "hi", "_client_name": "agent-1", "project_id": "proj-42"})
        queue._register(req)

        data = json.loads(_call(queue_history))
        row = data["history"][0]
        assert row["client_name"] == "agent-1"
        assert row["project_id"] == "proj-42"

    def test_history_most_recent_first(self) -> None:
        queue = HITLQueue()
        configure_tui_mode(queue, None)  # type: ignore[arg-type]
        from hitl_mcp_cli.resources._history import queue_history

        for i in range(3):
            queue._register(_make_req(params={"message": f"msg {i}"}))

        data = json.loads(_call(queue_history))
        messages = [r["message"] for r in data["history"]]
        assert messages[0] == "msg 2"
        assert messages[-1] == "msg 0"


# ---------------------------------------------------------------------------
# queue://pending
# ---------------------------------------------------------------------------


class TestQueuePending:
    def test_no_queue_returns_warning(self) -> None:
        configure_tui_mode(None, None)  # type: ignore[arg-type]
        from hitl_mcp_cli.resources._pending import queue_pending

        data = json.loads(_call(queue_pending))
        assert data["pending"] == []
        assert "warning" in data

    def test_empty_queue_returns_empty_pending(self) -> None:
        queue = HITLQueue()
        configure_tui_mode(queue, None)  # type: ignore[arg-type]
        from hitl_mcp_cli.resources._pending import queue_pending

        data = json.loads(_call(queue_pending))
        assert data["pending"] == []
        assert data["count"] == 0

    def test_pending_includes_pending_requests(self) -> None:
        queue = HITLQueue()
        configure_tui_mode(queue, None)  # type: ignore[arg-type]
        from hitl_mcp_cli.resources._pending import queue_pending

        req = _make_req("hitl_confirm", {"message": "Are you sure?", "project_id": "p1"})
        queue._register(req)

        data = json.loads(_call(queue_pending))
        assert data["count"] == 1
        row = data["pending"][0]
        assert row["request_id"] == req.request_id
        assert row["tool"] == "hitl_confirm"
        assert row["project_id"] == "p1"
        assert row["elapsed_seconds"] >= 0

    def test_pending_excludes_answered_requests(self) -> None:
        queue = HITLQueue()
        configure_tui_mode(queue, None)  # type: ignore[arg-type]
        from hitl_mcp_cli.resources._pending import queue_pending

        req = _make_req(params={"message": "Done?"})
        queue._register(req)
        queue.mark_answered(req.request_id, "yes")

        data = json.loads(_call(queue_pending))
        assert data["count"] == 0

    def test_pending_excludes_cancelled_requests(self) -> None:
        queue = HITLQueue()
        configure_tui_mode(queue, None)  # type: ignore[arg-type]
        from hitl_mcp_cli.resources._pending import queue_pending

        req = _make_req(params={"message": "Cancel me"})
        queue._register(req)
        queue.mark_cancelled(req.request_id)

        data = json.loads(_call(queue_pending))
        assert data["count"] == 0

    def test_pending_truncates_long_messages(self) -> None:
        queue = HITLQueue()
        configure_tui_mode(queue, None)  # type: ignore[arg-type]
        from hitl_mcp_cli.resources._pending import queue_pending

        req = _make_req(params={"message": "y" * 200})
        queue._register(req)

        data = json.loads(_call(queue_pending))
        assert data["pending"][0]["message"].endswith("...")

    def test_pending_includes_priority(self) -> None:
        queue = HITLQueue()
        configure_tui_mode(queue, None)  # type: ignore[arg-type]
        from hitl_mcp_cli.resources._pending import queue_pending

        req = _make_req(priority=1, params={"message": "urgent"})
        queue._register(req)

        data = json.loads(_call(queue_pending))
        assert data["pending"][0]["priority"] == 1


# ---------------------------------------------------------------------------
# session://last-user-action-age
# ---------------------------------------------------------------------------


class TestLastUserActionAge:
    def test_no_queue_returns_warning(self) -> None:
        configure_tui_mode(None, None)  # type: ignore[arg-type]
        from hitl_mcp_cli.resources._last_action_age import last_user_action_age

        data = json.loads(_call(last_user_action_age))
        assert data["seconds"] is None
        assert "warning" in data

    def test_no_answered_requests_returns_null(self) -> None:
        queue = HITLQueue()
        configure_tui_mode(queue, None)  # type: ignore[arg-type]
        from hitl_mcp_cli.resources._last_action_age import last_user_action_age

        data = json.loads(_call(last_user_action_age))
        assert data["seconds"] is None
        assert data["last_request_id"] is None

    def test_answered_request_returns_seconds(self) -> None:
        queue = HITLQueue()
        configure_tui_mode(queue, None)  # type: ignore[arg-type]
        from hitl_mcp_cli.resources._last_action_age import last_user_action_age

        req = _make_req(params={"message": "Confirm?"})
        queue._register(req)
        queue.mark_answered(req.request_id, "yes")

        data = json.loads(_call(last_user_action_age))
        assert data["seconds"] is not None
        assert data["seconds"] >= 0
        assert data["last_request_id"] == req.request_id

    def test_cancelled_request_counts_as_resolved(self) -> None:
        queue = HITLQueue()
        configure_tui_mode(queue, None)  # type: ignore[arg-type]
        from hitl_mcp_cli.resources._last_action_age import last_user_action_age

        req = _make_req(params={"message": "Cancel?"})
        queue._register(req)
        queue.mark_cancelled(req.request_id)

        data = json.loads(_call(last_user_action_age))
        assert data["seconds"] is not None
        assert data["last_request_id"] == req.request_id

    def test_most_recent_resolved_request_is_used(self) -> None:
        queue = HITLQueue()
        configure_tui_mode(queue, None)  # type: ignore[arg-type]
        from hitl_mcp_cli.resources._last_action_age import last_user_action_age

        req1 = _make_req(params={"message": "First"})
        queue._register(req1)
        queue.mark_answered(req1.request_id, "yes")

        time.sleep(0.01)

        req2 = _make_req(params={"message": "Second"})
        queue._register(req2)
        queue.mark_answered(req2.request_id, "no")

        data = json.loads(_call(last_user_action_age))
        assert data["last_request_id"] == req2.request_id

    def test_pending_requests_are_ignored(self) -> None:
        queue = HITLQueue()
        configure_tui_mode(queue, None)  # type: ignore[arg-type]
        from hitl_mcp_cli.resources._last_action_age import last_user_action_age

        req = _make_req(params={"message": "Still waiting"})
        queue._register(req)

        data = json.loads(_call(last_user_action_age))
        assert data["seconds"] is None
        assert data["last_request_id"] is None


# ---------------------------------------------------------------------------
# session://activity
# ---------------------------------------------------------------------------


class TestSessionActivity:
    def test_no_app_returns_warning(self) -> None:
        configure_tui_mode(None, None)  # type: ignore[arg-type]
        from hitl_mcp_cli.resources._session_activity import session_activity

        data = json.loads(_call(session_activity))
        assert data["sessions"] == []
        assert "warning" in data

    def test_empty_sessions_returns_empty_list(self) -> None:
        app = MagicMock()
        app._sessions = {}
        configure_tui_mode(None, app)  # type: ignore[arg-type]
        from hitl_mcp_cli.resources._session_activity import session_activity

        data = json.loads(_call(session_activity))
        assert data["sessions"] == []
        assert data["count"] == 0

    def test_sessions_are_returned(self) -> None:
        app = MagicMock()
        now = time.monotonic()
        app._sessions = {
            "sess-1": {
                "client_name": "agent-alpha",
                "project_id": "proj-1",
                "call_count": 3,
                "pending_count": 1,
                "last_active_ts": now - 5,
            }
        }
        configure_tui_mode(None, app)  # type: ignore[arg-type]
        from hitl_mcp_cli.resources._session_activity import session_activity

        data = json.loads(_call(session_activity))
        assert data["count"] == 1
        row = data["sessions"][0]
        assert row["session_id"] == "sess-1"
        assert row["client_name"] == "agent-alpha"
        assert row["project_id"] == "proj-1"
        assert row["call_count"] == 3
        assert row["pending_count"] == 1
        assert row["last_active_seconds_ago"] >= 5

    def test_sessions_sorted_by_most_recent_first(self) -> None:
        app = MagicMock()
        now = time.monotonic()
        app._sessions = {
            "sess-old": {"last_active_ts": now - 100, "call_count": 1, "pending_count": 0},
            "sess-new": {"last_active_ts": now - 1, "call_count": 2, "pending_count": 0},
        }
        configure_tui_mode(None, app)  # type: ignore[arg-type]
        from hitl_mcp_cli.resources._session_activity import session_activity

        data = json.loads(_call(session_activity))
        ids = [r["session_id"] for r in data["sessions"]]
        assert ids[0] == "sess-new"
        assert ids[1] == "sess-old"

    def test_missing_last_active_ts_defaults_to_now(self) -> None:
        app = MagicMock()
        app._sessions = {
            "sess-no-ts": {"call_count": 0, "pending_count": 0},
        }
        configure_tui_mode(None, app)  # type: ignore[arg-type]
        from hitl_mcp_cli.resources._session_activity import session_activity

        data = json.loads(_call(session_activity))
        assert data["count"] == 1
        assert data["sessions"][0]["last_active_seconds_ago"] >= 0

    def test_app_without_sessions_attr(self) -> None:
        app = MagicMock(spec=[])  # no _sessions attribute
        configure_tui_mode(None, app)  # type: ignore[arg-type]
        from hitl_mcp_cli.resources._session_activity import session_activity

        data = json.loads(_call(session_activity))
        assert data["sessions"] == []
        assert data["count"] == 0
