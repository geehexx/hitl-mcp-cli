"""``hitl_notify`` tool primitive — non-blocking status update to TUI."""

from __future__ import annotations

import asyncio
import time
from typing import Literal

from .._os_notify import send_os_notification
from .._server_core import (
    Context,
    get_client_name,
    get_session_id,
    get_tui_app,
    require_tui_queue,
)
from .._server_core import mcp as _mcp
from ..interaction_log import log_interaction


@_mcp.tool()
async def hitl_notify(
    message: str,
    level: Literal["success", "info", "warning", "error"] = "info",
    title: str | None = None,
    notes: str | None = None,
    agent_name: str | None = None,
    project_id: str | None = None,
    step: int | None = None,
    total_steps: int | None = None,
    ctx: Context | None = None,
) -> dict[str, bool]:
    """Display a styled notification to the user. Non-blocking.

    Args:
        message: Detailed message (supports multi-line via newlines).
        level: ``"success"`` (green), ``"info"`` (blue), ``"warning"`` (yellow), ``"error"`` (red).
        title: Optional short title.
        notes: Optional freeform context.
        agent_name: Calling agent identifier.
        project_id: Project identifier for session grouping.
        step: Current step number.
        total_steps: Total steps in workflow.

    Returns:
        ``{"acknowledged": True}`` once the notification has been queued.
    """
    t0 = time.monotonic()
    client_name = get_client_name(ctx, agent_name)
    session_id = get_session_id(ctx)
    tui_app = get_tui_app()

    queue = require_tui_queue()
    if tui_app is not None:
        tui_app.call_from_thread(tui_app.stream_output, title or "agent", message, level)
        tui_app.call_from_thread(
            tui_app.record_session_activity, session_id, "hitl_notify", project_id, client_name
        )
        short_msg = message[:40] + "..." if len(message) > 40 else message
        tui_app.call_from_thread(
            tui_app.stream_output,
            "queue",
            f"▶ [bold]hitl_notify[/bold] \\[{client_name or 'unknown'}] — {short_msg}",
            "info",
        )
        tui_app.call_from_thread(tui_app.record_session_resolved, session_id)
    _ = queue  # queue presence checked by require_tui_queue()
    ms = int((time.monotonic() - t0) * 1000)
    log_interaction("hitl_notify", ms, "value", message=message, notes=notes)
    _notif_task = asyncio.create_task(
        asyncio.to_thread(send_os_notification, title or "HITL Notification", message[:120], level)
    )
    _notif_task.add_done_callback(lambda t: t.exception() if not t.cancelled() else None)
    return {"acknowledged": True}


__all__ = ["hitl_notify"]
