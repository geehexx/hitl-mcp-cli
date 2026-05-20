"""Internal server primitives shared across tools/resources/prompts.

This module holds the FastMCP instance, TUI mode wiring, and helpers used by
the tool/resource/prompt submodules. End-users should NOT import from here
directly — register your primitives via the tools/, resources/, or prompts/
packages, which import from this internal module.
"""

from __future__ import annotations

import asyncio
import threading
from typing import TYPE_CHECKING, Any

from fastmcp import Context, FastMCP

from ._os_notify import send_os_notification

if TYPE_CHECKING:
    from .tui.app import HITLApp
    from .tui.queue import HITLQueue


mcp: FastMCP[Any] = FastMCP(
    name="HITL MCP Server",
    instructions=(
        "Human-in-the-Loop MCP server. Provides tools for AI agents to request human input, "
        "confirmation, and approval at critical decision points. Tools BLOCK until the user "
        "responds, ensuring human oversight of consequential actions. Resources expose live "
        "queue and session state. Prompts provide reusable HITL templates for common decision "
        "shapes (architectural fork, destructive action, scope clarification, panel-vote)."
    ),
)


_tui_queue: HITLQueue | None = None
_tui_app: HITLApp | None = None


def configure_tui_mode(queue: HITLQueue, app: HITLApp) -> None:
    """Wire the TUI queue + app into the server."""
    global _tui_queue, _tui_app
    _tui_queue, _tui_app = queue, app


def get_tui_queue() -> HITLQueue | None:
    """Return the wired TUI queue, or ``None`` if the server runs headless."""
    return _tui_queue


def get_tui_app() -> HITLApp | None:
    """Return the wired TUI app, or ``None`` if the server runs headless."""
    return _tui_app


def require_tui_queue() -> HITLQueue:
    """Return the wired TUI queue or raise ``RuntimeError`` if not configured."""
    if _tui_queue is None:
        raise RuntimeError("HITL server requires TUI mode. Run with hitl-mcp command.")
    return _tui_queue


def get_client_name(ctx: Context | None, agent_name: str | None = None) -> str | None:
    """Resolve a display client name from the per-call ``agent_name`` then ``ctx``."""
    if agent_name:
        return agent_name
    if ctx is None:
        return None
    try:
        session = ctx.session
        params = session.client_params
        if params and params.clientInfo:
            return params.clientInfo.name
    except Exception:
        return None
    return None


def get_session_id(ctx: Context | None) -> str:
    """Resolve a stable session id (MCP session id or thread fallback)."""
    if ctx is not None:
        try:
            return ctx.session_id
        except (RuntimeError, AttributeError):
            pass
    return f"thread-{threading.current_thread().ident}"


async def tui_enqueue(
    tool: str,
    params: dict[str, Any],
    *,
    client_name: str | None = None,
    session_id: str | None = None,
) -> Any:
    """Enqueue a request on the TUI queue and await the user's response."""
    from .tui.queue import HITLRequest

    queue = require_tui_queue()
    loop = asyncio.get_running_loop()
    if queue._caller_loop is None:
        queue.set_caller_loop(loop)
    future: asyncio.Future[Any] = loop.create_future()

    sid = session_id or f"thread-{threading.current_thread().ident}"
    params = {**params, "_session_id": sid, "_client_name": client_name or "unknown"}

    request = HITLRequest(tool=tool, params=params, future=future)
    queue.put_threadsafe(request)

    # Best-effort OS desktop notification so user knows a question is waiting
    _notif_title = f"HITL: {tool}"
    _notif_body = (params.get("message") or tool)[:120]
    _notif_task = asyncio.create_task(
        asyncio.to_thread(send_os_notification, _notif_title, _notif_body, "info")
    )
    _notif_task.add_done_callback(lambda t: t.exception() if not t.cancelled() else None)

    if _tui_app is not None:
        project_id = params.get("project_id")
        _tui_app.call_from_thread(_tui_app.record_session_activity, sid, tool, project_id, client_name)

    return await future


__all__ = [
    "Context",
    "configure_tui_mode",
    "get_client_name",
    "get_session_id",
    "get_tui_app",
    "get_tui_queue",
    "mcp",
    "require_tui_queue",
    "tui_enqueue",
]
