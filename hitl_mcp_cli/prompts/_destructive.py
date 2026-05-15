"""``hitl_destructive_action`` prompt — confirm an irreversible action."""

from __future__ import annotations

from fastmcp.prompts.prompt import Message
from mcp.types import PromptMessage

from .._server_core import mcp as _mcp


@_mcp.prompt(name="hitl_destructive_action")
def destructive_action(
    action: str,
    blast_radius: str,
    rollback_path: str = "",
) -> list[PromptMessage]:
    """Template for asking the user to authorise a destructive irreversible action.

    Args:
        action: One-sentence statement of what will happen.
        blast_radius: What is affected (files / data / accounts / shared resources).
        rollback_path: Optional; how to recover if the user later regrets it.
            If omitted, the prompt warns ``"no rollback documented"``.
    """
    body = (
        f"## Destructive action — explicit authorisation required\n\n"
        f"**Action:** {action}\n\n"
        f"**Blast radius:** {blast_radius}\n\n"
        f"**Rollback path:** {rollback_path or '_no rollback documented_ — confirm carefully'}\n\n"
        f"Reply with one of:\n"
        f"- `proceed` — go ahead\n"
        f"- `abort` — stop and surface alternatives\n"
        f"- a question — the agent will pause and answer before re-asking"
    )
    return [Message(role="user", content=body)]
