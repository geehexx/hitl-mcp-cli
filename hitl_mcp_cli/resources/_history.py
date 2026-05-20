"""``queue://history`` resource — historical HITL request log."""

from __future__ import annotations

import json
import time
from typing import Any

from .._server_core import get_tui_queue
from .._server_core import mcp as _mcp


@_mcp.resource("queue://history", mime_type="application/json")
def queue_history() -> str:
    """Return JSON snapshot of recent HITL requests across all statuses.

    Returns up to 50 most-recent requests, each with ``request_id``,
    ``tool``, ``message``, ``status``, ``answer_preview``, and
    ``elapsed_seconds``. Use this to drive cross-session analytics or to
    let an agent self-audit its prior asks.
    """
    queue = get_tui_queue()
    if queue is None:
        return json.dumps({"history": [], "warning": "TUI queue not configured"})

    now = time.monotonic()
    rows: list[dict[str, Any]] = []
    for req in queue.history[-50:][::-1]:
        msg = req.params.get("message", "")
        rows.append(
            {
                "request_id": req.request_id,
                "tool": req.tool,
                "message": (msg[:120] + "...") if len(msg) > 120 else msg,
                "status": req.status,
                "answer_preview": req.answer_preview,
                "elapsed_seconds": int(now - req.created_at),
                "client_name": req.params.get("_client_name"),
                "project_id": req.params.get("project_id"),
            }
        )
    return json.dumps({"history": rows, "count": len(rows)}, indent=2)


@_mcp.resource("queue://history/{n}", mime_type="application/json")
def queue_history_n(n: int) -> str:
    """Return JSON snapshot of the N most-recent HITL requests (max 50).

    Args:
        n: Number of entries to return. Clamped to [1, 50].
    """
    queue = get_tui_queue()
    if queue is None:
        return json.dumps({"history": [], "warning": "TUI queue not configured"})

    limit = max(1, min(n, 50))
    now = time.monotonic()
    rows: list[dict[str, Any]] = []
    for req in queue.history[-limit:][::-1]:
        msg = req.params.get("message", "")
        rows.append(
            {
                "request_id": req.request_id,
                "tool": req.tool,
                "message": (msg[:120] + "...") if len(msg) > 120 else msg,
                "status": req.status,
                "answer_preview": req.answer_preview,
                "elapsed_seconds": int(now - req.created_at),
                "client_name": req.params.get("_client_name"),
                "project_id": req.params.get("project_id"),
            }
        )
    return json.dumps({"history": rows, "count": len(rows)}, indent=2)
