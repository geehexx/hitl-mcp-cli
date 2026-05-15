"""``queue://pending`` resource — current pending HITL requests."""

from __future__ import annotations

import json
import time
from typing import Any

from .._server_core import get_tui_queue
from .._server_core import mcp as _mcp


@_mcp.resource("queue://pending", mime_type="application/json")
def queue_pending() -> str:
    """Return JSON snapshot of HITL requests still awaiting a user response.

    Each entry contains: ``request_id``, ``tool``, ``message`` (truncated),
    ``elapsed_seconds``, ``priority``, ``client_name``, ``project_id``.

    Clients poll this resource — CC does not support subscriptions
    (`anthropics/claude-code#7252`).
    """
    queue = get_tui_queue()
    if queue is None:
        return json.dumps({"pending": [], "warning": "TUI queue not configured"})

    now = time.monotonic()
    pending: list[dict[str, Any]] = []
    for req in queue.history:
        if req.status != "pending":
            continue
        msg = req.params.get("message", "")
        pending.append(
            {
                "request_id": req.request_id,
                "tool": req.tool,
                "message": (msg[:120] + "...") if len(msg) > 120 else msg,
                "elapsed_seconds": int(now - req.created_at),
                "priority": req.priority,
                "client_name": req.params.get("_client_name"),
                "project_id": req.params.get("project_id"),
            }
        )
    return json.dumps({"pending": pending, "count": len(pending)}, indent=2)
