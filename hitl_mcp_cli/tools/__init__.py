"""Tool primitives — model-controlled actions with side effects.

Per the MCP three-primitive idiom: TOOLS are invoked by the agent
autonomously to take action that has side effects (block on user, write
to log, dispatch to TUI). Each submodule registers tools via the
``@mcp.tool()`` decorator from ``_server_core``.

Public tools registered here:
    - ``hitl_collect`` / ``hitl_ask``  — collect a single value
    - ``hitl_choose``                  — present a list of options
    - ``hitl_confirm``                 — ask yes/no with severity
    - ``hitl_notify``                  — non-blocking status update (+ OS desktop notification)
    - ``hitl_poll``                    — re-block on a timed-out question
    - ``hitl_reject_question``         — signal a malformed/unanswerable question
    - ``hitl_request_elaboration``     — re-ask with additional context from agent
    - ``hitl_recommend``               — pre-selected default with timed override window
"""

from __future__ import annotations

from . import _collect, _confirm, _elaborate, _notify, _poll, _recommend, _reject  # noqa: F401

__all__: list[str] = []
