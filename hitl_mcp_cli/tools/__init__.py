"""Tool primitives — model-controlled actions with side effects.

Per the MCP three-primitive idiom: TOOLS are invoked by the agent
autonomously to take action that has side effects (block on user, write
to log, dispatch to TUI). Each submodule registers tools via the
``@mcp.tool()`` decorator from ``_server_core``.

Public tools registered here:
    - ``hitl_collect`` / ``hitl_ask``  — collect a single value
    - ``hitl_choose``                  — present a list of options
    - ``hitl_confirm``                 — ask yes/no with severity
    - ``hitl_notify``                  — non-blocking status update
"""

from __future__ import annotations

from . import _collect, _confirm, _notify, _poll  # noqa: F401  (registers tools)

__all__: list[str] = []
