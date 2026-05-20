"""``hitl_poll`` tool — re-block on a previously timed-out question."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from .._server_core import (
    Context,
    get_client_name,
    get_session_id,
    get_tui_queue,
    tui_enqueue,
)
from .._server_core import mcp as _mcp
from ..interaction_log import log_interaction
from ..timeout_config import get_timeout_config


@_mcp.tool()
async def hitl_poll(
    question_id: str,
    wait_minutes: float = 5,
    agent_name: str | None = None,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Re-block on a previously timed-out HITL question.

    Args:
        question_id: The ``question_id`` returned by a prior timeout response.
        wait_minutes: How long to wait for a response (clamped to env limits).
        agent_name: Calling agent identifier.

    Returns:
        ``{"status": "answered", "answer": ...}`` if the user responds.
        ``{"status": "timeout", "question_id": ..., "retry_after": 60}`` if it times out again.
        ``{"status": "not_found", "question_id": ...}`` if the question_id is unknown.
    """
    queue = get_tui_queue()
    if queue is None:
        return {"status": "not_found", "question_id": question_id}

    req = queue.get_by_id(question_id)
    if req is None:
        # Also search by _question_id param (set by collect/choose/confirm)
        req = next(
            (r for r in queue.history if r.params.get("_question_id") == question_id),
            None,
        )
    if req is None:
        return {"status": "not_found", "question_id": question_id}

    # Already answered — return cached answer immediately
    if req.resolved_answer is not None:
        return {"status": "answered", "answer": req.resolved_answer}

    # Re-enqueue the same question and wait.
    # The original request's future may be cancelled (from a prior wait_for timeout).
    # We enqueue fresh params so the TUI gets a new request to display.
    cfg = get_timeout_config()
    wait_seconds = cfg.clamp(wait_minutes) * 60
    client_name = get_client_name(ctx, agent_name)
    session_id = get_session_id(ctx)

    # Carry the original question_id so callers can correlate across retries.
    poll_params = {**req.params, "_question_id": question_id}

    t0 = time.monotonic()
    try:
        result = await asyncio.wait_for(
            tui_enqueue(req.tool, poll_params, client_name=client_name, session_id=session_id),
            timeout=wait_seconds,
        )
        ms = int((time.monotonic() - t0) * 1000)
        log_interaction(
            "hitl_poll", ms, "value", message=req.params.get("message", ""), result=str(result)[:80]
        )
        return {"status": "answered", "answer": result}
    except TimeoutError:
        ms = int((time.monotonic() - t0) * 1000)
        log_interaction("hitl_poll", ms, "timeout", message=req.params.get("message", ""))
        return {"status": "timeout", "question_id": question_id, "retry_after": 60}


__all__ = ["hitl_poll"]
