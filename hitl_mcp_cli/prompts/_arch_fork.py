"""``hitl_architectural_fork`` prompt — present an architectural fork to the user."""

from __future__ import annotations

from fastmcp.prompts.prompt import Message
from mcp.types import PromptMessage

from .._server_core import mcp as _mcp


@_mcp.prompt(name="hitl_architectural_fork")
def architectural_fork(
    decision: str,
    options: str,
    constraints: str = "",
    recommendation: str = "",
) -> list[PromptMessage]:
    """Template for surfacing an architectural fork to the user.

    Renders a structured Markdown prompt that asks the user to pick between
    architectural options. Use this prompt when the agent reaches a decision
    boundary that has multiple viable answers with different long-term
    implications.

    Args:
        decision: One-sentence statement of the decision needed.
        options: Markdown-formatted list of options. Each option should
            include a label, the tradeoff axis, and the implications.
        constraints: Optional; non-obvious constraints the user should weigh.
        recommendation: Optional; the agent's lean if asked.
    """
    body = f"## Architectural fork\n\n**Decision:** {decision}\n\n### Options\n\n{options}\n\n"
    if constraints:
        body += f"### Constraints\n\n{constraints}\n\n"
    if recommendation:
        body += f"### Agent recommendation (advisory)\n\n{recommendation}\n\n"
    body += (
        "Please pick an option and (optionally) explain why. "
        "If none of the options fit, say so and the agent will re-frame."
    )
    return [Message(role="user", content=body)]
