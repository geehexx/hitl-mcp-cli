"""``hitl_recommend`` tool primitive — pre-selected default with timed override.

The orchestrator can pre-select a recommended answer for time-sensitive
questions. The user has ``override_seconds`` (default 30) to pick a different
option; if they don't respond in time, the recommendation is auto-accepted.

Return value:
  - ``{"status": "auto_accepted", "value": <recommendation>, "elapsed_seconds": N}``
    when the timer expires without user input.
  - ``{"status": "user_selected", "value": <user_choice>}``
    when the user actively picks an option (including the recommendation).
  - ``{"status": "cancelled"}`` if the user explicitly cancels.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from .._server_core import Context, get_client_name, get_session_id, tui_enqueue
from .._server_core import mcp as _mcp
from ..interaction_log import log_interaction


@_mcp.tool()
async def hitl_recommend(
    message: str,
    recommendation: str,
    choices: list[str] | None = None,
    override_seconds: int = 30,
    notes: str | None = None,
    context: str | None = None,
    agent_name: str | None = None,
    project_id: str | None = None,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Present a pre-selected recommendation with a timed override window.

    The orchestrator pre-selects ``recommendation`` as the default answer.
    The user has ``override_seconds`` to pick a different option. If the timer
    expires, the recommendation is auto-accepted without user interaction.

    Args:
        message: Question or decision description.
        recommendation: The pre-selected default value.
        choices: Optional list of alternatives the user can pick instead.
            If omitted, the user can only accept or cancel.
        override_seconds: Seconds the user has to override. Default 30.
        notes: Freeform context shown below the prompt.
        context: Additional context shown above the prompt.
        agent_name: Calling agent identifier.
        project_id: Project identifier for session grouping.

    Returns:
        ``{"status": "auto_accepted"|"user_selected"|"cancelled", "value": ...}``
    """
    t0 = time.monotonic()
    client_name = get_client_name(ctx, agent_name)
    session_id = get_session_id(ctx)

    # Build choice list: recommendation first (pre-selected), then alternatives
    all_choices = [recommendation]
    if choices:
        for c in choices:
            if c != recommendation:
                all_choices.append(c)

    tui_params: dict[str, Any] = {
        "message": f"{message}\n[Auto-accepts '{recommendation}' in {override_seconds}s]",
        "choices": all_choices,
        "multiple": False,
        "fuzzy_search": False,
        "default": recommendation,
        "notes": notes,
        "context": context,
        "project_id": project_id,
        "step": None,
        "total_steps": None,
        "_recommendation": recommendation,
        "_override_seconds": override_seconds,
    }

    try:
        result = await asyncio.wait_for(
            tui_enqueue("hitl_choose", tui_params, client_name=client_name, session_id=session_id),
            timeout=float(override_seconds),
        )
        ms = int((time.monotonic() - t0) * 1000)
        log_interaction("hitl_recommend", ms, "value", message=message, result=str(result)[:80], notes=notes)
        return {"status": "user_selected", "value": result}
    except TimeoutError:
        elapsed = time.monotonic() - t0
        ms = int(elapsed * 1000)
        log_interaction(
            "hitl_recommend",
            ms,
            "timeout",
            message=message,
            result=f"auto_accepted:{recommendation}",
            notes=notes,
        )
        return {
            "status": "auto_accepted",
            "value": recommendation,
            "elapsed_seconds": round(elapsed, 1),
        }


__all__ = ["hitl_recommend"]
