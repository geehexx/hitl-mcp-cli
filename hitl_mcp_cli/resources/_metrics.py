"""``metrics://summary`` resource — aggregate performance metrics."""

from __future__ import annotations

import json
import time

from .._server_core import get_tui_app, get_tui_queue
from .._server_core import mcp as _mcp


@_mcp.resource("metrics://summary", mime_type="application/json")
def metrics_summary() -> str:
    """Return aggregate performance metrics across all sessions.

    Fields:
        - ``total_questions``: total HITL requests ever enqueued
        - ``avg_response_time_s``: mean seconds from creation to resolution
          (answered/cancelled only; null if none resolved yet)
        - ``active_sessions``: number of sessions seen by the TUI app
        - ``questions_by_type``: breakdown of request counts by tool name
    """
    queue = get_tui_queue()
    app = get_tui_app()

    if queue is None:
        return json.dumps(
            {
                "total_questions": 0,
                "avg_response_time_s": None,
                "active_sessions": 0,
                "questions_by_type": {},
                "warning": "TUI queue not configured",
            }
        )

    now = time.monotonic()
    total = len(queue.history)

    questions_by_type: dict[str, int] = {}
    response_times: list[float] = []

    for req in queue.history:
        questions_by_type[req.tool] = questions_by_type.get(req.tool, 0) + 1
        if req.status in ("answered", "cancelled"):
            resolved_at = getattr(req, "_resolved_at", None)
            elapsed = (resolved_at - req.created_at) if resolved_at is not None else (now - req.created_at)
            response_times.append(elapsed)

    avg_response_time = round(sum(response_times) / len(response_times), 3) if response_times else None

    active_sessions = len(getattr(app, "_sessions", {})) if app is not None else 0

    return json.dumps(
        {
            "total_questions": total,
            "avg_response_time_s": avg_response_time,
            "active_sessions": active_sessions,
            "questions_by_type": questions_by_type,
        },
        indent=2,
    )
