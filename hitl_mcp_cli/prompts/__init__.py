"""Prompt primitives — user-controlled reusable templates.

Per the MCP three-primitive idiom: PROMPTS are templates the user invokes
(typically via slash command in the host) to structure recurring agent
interactions. Unlike tools (model-controlled actions) and resources
(application-controlled data), prompts give the user a curated entry-point
to a specific agent workflow.

Public prompts registered here:
    - ``hitl_architectural_fork``      — present a fork between architectural choices
    - ``hitl_destructive_action``      — confirm a destructive irreversible action
    - ``hitl_scope_clarification``     — clarify ambiguous scope before proceeding
    - ``hitl_panel_vote_summary``      — summarise a multi-agent panel vote
"""

from __future__ import annotations

from . import _arch_fork, _destructive, _panel_vote, _scope_clarify  # noqa: F401

__all__: list[str] = []
