"""Resource primitives — application-controlled read-only data.

Per the MCP three-primitive idiom: RESOURCES expose live state for the host
application to load as context. Unlike tools (which the agent invokes for
side-effecting actions), resources are read-only and queried by URI. The
client decides when to fetch; the server only describes available resources
and serves the bytes.

Public resources registered here:
    - ``queue://pending``                — pending HITL requests
    - ``queue://history``                — historical HITL request log
    - ``session://activity``             — per-session activity counters
    - ``session://last-user-action-age`` — seconds since last user action

NOTE: CC has closed MCP resource subscriptions as `not_planned`
(anthropics/claude-code#7252). Clients must POLL these resources rather than
subscribe — the server intentionally returns a fresh snapshot on each fetch.
"""

from __future__ import annotations

from . import _history, _last_action_age, _metrics, _pending, _session_activity  # noqa: F401

__all__: list[str] = []
