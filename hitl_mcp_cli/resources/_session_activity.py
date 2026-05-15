"""``session://activity`` resource — per-session activity counters."""

from __future__ import annotations

import json
import time
from typing import Any

from .._server_core import get_tui_app
from .._server_core import mcp as _mcp


@_mcp.resource("session://activity", mime_type="application/json")
def session_activity() -> str:
    """Return JSON snapshot of all known sessions and their activity.

    Each session row includes: ``client_name``, ``project_id``,
    ``call_count``, ``pending_count``, ``last_active_seconds_ago``.

    Sourced from the TUI app's session tracker (the same data the
    Sessions panel renders). Use this to find idle vs active agents
    when orchestrating multi-agent work.
    """
    app = get_tui_app()
    if app is None:
        return json.dumps({"sessions": [], "warning": "TUI app not configured"})

    now = time.monotonic()
    sessions: list[dict[str, Any]] = []
    for sid, info in getattr(app, "_sessions", {}).items():
        last_active = info.get("last_active_ts", now)
        sessions.append(
            {
                "session_id": sid,
                "client_name": info.get("client_name"),
                "project_id": info.get("project_id"),
                "call_count": info.get("call_count", 0),
                "pending_count": info.get("pending_count", 0),
                "last_active_seconds_ago": int(now - last_active),
            }
        )
    sessions.sort(key=lambda r: r["last_active_seconds_ago"])
    return json.dumps({"sessions": sessions, "count": len(sessions)}, indent=2)
