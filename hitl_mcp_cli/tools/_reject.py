"""``hitl_reject_question`` tool primitive — agent signals a malformed question.

When an agent determines that a question it received (e.g. via hitl_collect)
was malformed, ambiguous, or unanswerable, it can call this tool to return a
structured rejection back to the orchestrator rather than silently failing or
returning garbage.

The orchestrator should inspect the return value for
``{"status": "rejected_question", "reason": ...}`` and either reformulate the
question or escalate.
"""

from __future__ import annotations

import time

from .._server_core import Context, get_client_name
from .._server_core import mcp as _mcp
from ..interaction_log import log_interaction


@_mcp.tool()
async def hitl_reject_question(
    reason: str,
    question_id: str | None = None,
    original_message: str | None = None,
    agent_name: str | None = None,
    ctx: Context | None = None,
) -> dict[str, str]:
    """Signal that a question was malformed or unanswerable.

    Call this when you receive a question via ``hitl_collect`` / ``hitl_ask`` /
    ``hitl_choose`` / ``hitl_confirm`` that you cannot meaningfully answer —
    for example because it is ambiguous, missing required context, or outside
    your scope.

    Args:
        reason: Human-readable explanation of why the question is rejected.
        question_id: Optional ``question_id`` from the original tool call, for
            correlation.
        original_message: The original question text, for logging.
        agent_name: Calling agent identifier.

    Returns:
        ``{"status": "rejected_question", "reason": "<text>", "question_id": ...}``
    """
    t0 = time.monotonic()
    client_name = get_client_name(ctx, agent_name)
    ms = int((time.monotonic() - t0) * 1000)
    log_interaction(
        "hitl_reject_question",
        ms,
        "cancel",
        message=original_message or "(no message)",
        result=reason[:80],
        notes=f"agent={client_name}",
    )
    result: dict[str, str] = {"status": "rejected_question", "reason": reason}
    if question_id:
        result["question_id"] = question_id
    return result


__all__ = ["hitl_reject_question"]
