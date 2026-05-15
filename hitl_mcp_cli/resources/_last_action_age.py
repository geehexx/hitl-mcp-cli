"""``session://last-user-action-age`` resource — seconds since last user reply."""

from __future__ import annotations

import json
import time

from .._server_core import get_tui_queue
from .._server_core import mcp as _mcp


@_mcp.resource("session://last-user-action-age", mime_type="application/json")
def last_user_action_age() -> str:
    """Return seconds elapsed since the user last responded to ANY HITL request.

    Useful for orchestrators deciding whether to wait for the user (recent
    activity) or proceed with a deferred-question strategy (idle for hours).

    Returns ``{"seconds": int | null, "last_request_id": str | null}``.
    ``seconds`` is ``null`` if no request has ever been answered.
    """
    queue = get_tui_queue()
    if queue is None:
        return json.dumps({"seconds": None, "warning": "TUI queue not configured"})

    now = time.monotonic()
    most_recent: float | None = None
    most_recent_id: str | None = None
    for req in queue.history:
        if req.status in ("answered", "cancelled"):
            ts = getattr(req, "_resolved_at", req.created_at)
            if most_recent is None or ts > most_recent:
                most_recent = ts
                most_recent_id = req.request_id
    if most_recent is None:
        return json.dumps({"seconds": None, "last_request_id": None})
    return json.dumps({"seconds": int(now - most_recent), "last_request_id": most_recent_id})
