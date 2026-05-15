"""``hitl_confirm`` tool primitive — yes/no with severity + timeout."""

from __future__ import annotations

import asyncio
import time
from typing import Any, Literal

from .._config import resolve_timeout
from .._server_core import (
    Context,
    get_client_name,
    get_session_id,
    get_tui_app,
    tui_enqueue,
)
from .._server_core import mcp as _mcp
from ..interaction_log import log_interaction


@_mcp.tool()
async def hitl_confirm(
    message: str,
    default: bool = False,
    severity: Literal["low", "medium", "high"] = "medium",
    context: str | None = None,
    timeout_seconds: int = 0,
    notes: str | None = None,
    agent_name: str | None = None,
    project_id: str | None = None,
    step: int | None = None,
    total_steps: int | None = None,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Ask the user to confirm or reject an action.

    Args:
        message: Clear yes/no question explaining the action.
        default: Default answer forwarded to the TUI; use ``False`` for destructive operations.
        severity: ``"low"`` (default yes), ``"medium"`` (standard),
            ``"high"`` (red warning, requires typed confirmation).
        context: Additional context displayed in a panel above the prompt.
        timeout_seconds: ``0`` for infinite wait, ``>0`` for timed confirmation.
        notes: Freeform context displayed as a dimmed line below the prompt.
        agent_name: Calling agent identifier.
        project_id: Project identifier for session grouping.
        step: Current step number.
        total_steps: Total steps in workflow.

    Returns:
        ``{"action": "accept" | "decline" | "cancel", "timed_out": bool}``.
        ``timed_out`` is True only when ``timeout_seconds > 0`` and the wait expired.
    """
    t0 = time.monotonic()
    client_name = get_client_name(ctx, agent_name)
    session_id = get_session_id(ctx)
    tui_app = get_tui_app()

    tui_params: dict[str, Any] = {
        "message": message,
        "default": default,
        "severity": severity,
        "context": context,
        "notes": notes,
        "project_id": project_id,
        "step": step,
        "total_steps": total_steps,
    }
    effective_timeout = resolve_timeout(timeout_seconds)
    try:
        if effective_timeout > 0:
            tui_result: dict[str, Any] = await asyncio.wait_for(
                tui_enqueue("hitl_confirm", tui_params, client_name=client_name, session_id=session_id),
                timeout=effective_timeout,
            )
            ms = int((time.monotonic() - t0) * 1000)
            log_interaction("hitl_confirm", ms, "value", message=message, result=str(tui_result), notes=notes)
            tui_result["timed_out"] = False
            return tui_result
        tui_result = await tui_enqueue(
            "hitl_confirm", tui_params, client_name=client_name, session_id=session_id
        )
        ms = int((time.monotonic() - t0) * 1000)
        log_interaction("hitl_confirm", ms, "value", message=message, result=str(tui_result), notes=notes)
        tui_result.setdefault("timed_out", False)
        return tui_result
    except TimeoutError:
        if tui_app is not None:
            tui_app.call_from_thread(tui_app.record_session_resolved, session_id)
        ms = int((time.monotonic() - t0) * 1000)
        log_interaction("hitl_confirm", ms, "timeout", message=message, notes=notes)
        return {"action": "decline", "timed_out": True}


__all__ = ["hitl_confirm"]
