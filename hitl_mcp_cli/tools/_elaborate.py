"""``hitl_request_elaboration`` tool primitive — ask calling agent for more context.

When the user replies "elaborate" to a pending question, the server calls this
tool on behalf of the orchestrator to request additional context from the agent
that originally asked the question.

Flow:
  1. Agent calls ``hitl_collect(message="...")``
  2. User types "elaborate" in the TUI
  3. TUI resolves the future with ``{"action": "elaborate", "question_id": ...}``
  4. Agent receives that sentinel and calls ``hitl_request_elaboration(...)``
  5. Server re-queues the question with the elaboration appended
  6. User sees the enriched question and answers normally
"""

from __future__ import annotations

import time
from typing import cast

from .._server_core import Context, get_client_name, get_session_id, tui_enqueue
from .._server_core import mcp as _mcp
from ..interaction_log import log_interaction


@_mcp.tool()
async def hitl_request_elaboration(
    original_message: str,
    elaboration: str,
    question_id: str | None = None,
    agent_name: str | None = None,
    project_id: str | None = None,
    ctx: Context | None = None,
) -> str | dict[str, str]:
    """Re-ask a question with additional elaboration appended.

    Call this after receiving ``{"action": "elaborate", ...}`` from a previous
    ``hitl_collect`` / ``hitl_ask`` call. The enriched question is re-queued
    and blocks until the user responds.

    Args:
        original_message: The original question text.
        elaboration: Additional context or clarification to append.
        question_id: Optional original ``question_id`` for correlation.
        agent_name: Calling agent identifier.
        project_id: Project identifier for session grouping.

    Returns:
        The user's answer string, or a cancel/timeout sentinel dict.
    """
    t0 = time.monotonic()
    client_name = get_client_name(ctx, agent_name)
    session_id = get_session_id(ctx)

    enriched = f"{original_message}\n\n[Elaboration] {elaboration}"
    tui_params = {
        "message": enriched,
        "input_type": "text",
        "default": None,
        "validation_pattern": None,
        "validation_message": None,
        "notes": f"Elaboration of question {question_id}" if question_id else "Elaborated question",
        "context": None,
        "strip_whitespace": True,
        "required": False,
        "path_type": None,
        "project_id": project_id,
        "step": None,
        "total_steps": None,
        "_question_id": question_id,
        "_elaboration": True,
    }

    result = await tui_enqueue("hitl_collect", tui_params, client_name=client_name, session_id=session_id)
    ms = int((time.monotonic() - t0) * 1000)
    log_interaction(
        "hitl_request_elaboration",
        ms,
        "cancel" if isinstance(result, dict) else "value",
        message=enriched,
        result=str(result)[:80],
    )
    return cast("str | dict[str, str]", result)


__all__ = ["hitl_request_elaboration"]
