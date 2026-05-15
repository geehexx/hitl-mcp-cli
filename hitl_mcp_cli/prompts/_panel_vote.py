"""``hitl_panel_vote_summary`` prompt — render a multi-agent panel vote."""

from __future__ import annotations

from fastmcp.prompts.prompt import Message
from mcp.types import PromptMessage

from .._server_core import mcp as _mcp


@_mcp.prompt(name="hitl_panel_vote_summary")
def panel_vote_summary(
    decision: str,
    votes: str,
    counter_arguments: str,
    quorum_outcome: str,
) -> list[PromptMessage]:
    """Template for surfacing a multi-agent panel vote to the user.

    Renders the structured output of a panel-of-experts review for user
    review and final adjudication. Use after dispatching a panel via
    ``.claude/skills/panel-review/`` and aggregating the votes.

    Args:
        decision: The decision under review (one sentence).
        votes: Markdown-formatted table or list of ``Agent: APPROVE/REJECT/ABSTAIN``
            with a short rationale for each.
        counter_arguments: Markdown-formatted summary of dissent. Surface
            the strongest REJECT cases verbatim — counter is mandatory.
        quorum_outcome: ``"APPROVED"`` / ``"REJECTED"`` / ``"NO_QUORUM"`` plus
            the threshold rule that fired (e.g. ``"unanimous required for
            destructive; 1 REJECT halted"``).
    """
    body = (
        f"## Panel vote summary\n\n"
        f"**Decision:** {decision}\n\n"
        f"### Votes\n\n{votes}\n\n"
        f"### Dissent / counter-arguments\n\n{counter_arguments}\n\n"
        f"### Quorum outcome\n\n{quorum_outcome}\n\n"
        f"---\n\n"
        f"Please ratify, override, or request more research. "
        f"Override requires a one-sentence rationale that will be recorded "
        f"alongside the vote in `data/basic-memory/panel-votes/`."
    )
    return [Message(role="user", content=body)]
