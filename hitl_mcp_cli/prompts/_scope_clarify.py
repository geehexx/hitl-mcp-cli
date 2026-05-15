"""``hitl_scope_clarification`` prompt — clarify ambiguous scope."""

from __future__ import annotations

from fastmcp.prompts.prompt import Message
from mcp.types import PromptMessage

from .._server_core import mcp as _mcp


@_mcp.prompt(name="hitl_scope_clarification")
def scope_clarification(
    task: str,
    ambiguity: str,
    interpretations: str,
) -> list[PromptMessage]:
    """Template for surfacing scope ambiguity before the agent commits.

    Args:
        task: One-sentence statement of the task as currently understood.
        ambiguity: What's specifically unclear (a phrase, a constraint, a target).
        interpretations: Markdown-formatted list of plausible readings of the
            ambiguous part. Each entry should include what the agent would
            do under that interpretation.
    """
    body = (
        f"## Scope clarification\n\n"
        f"**Task as understood:** {task}\n\n"
        f"**Ambiguous part:** {ambiguity}\n\n"
        f"### Plausible interpretations\n\n{interpretations}\n\n"
        f"Pick an interpretation, OR rephrase the task in your own words. "
        f"The agent will not proceed until scope is unambiguous."
    )
    return [Message(role="user", content=body)]
