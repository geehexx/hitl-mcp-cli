"""HITL MCP Server — thin entry-point that wires up the three primitive packages.

Per the MCP three-primitive idiom, the server is split into:
    - ``tools/``     — model-controlled actions (block on user, write log, dispatch to TUI)
    - ``resources/`` — application-controlled read-only data (queue / session state)
    - ``prompts/``   — user-controlled reusable templates (HITL workflow shapes)

The actual primitives live in those packages. This module re-exports the
FastMCP instance and the TUI-mode wiring so existing imports keep working.

For deep architecture, see ``docs/ARCHITECTURE.md``.
"""

from __future__ import annotations

# Register every primitive by side-effect import. Order does not matter — each
# submodule decorates its own primitives onto the shared FastMCP instance.
from . import prompts as _prompts  # noqa: F401
from . import resources as _resources  # noqa: F401
from . import tools as _tools  # noqa: F401

# Public surface — kept stable for back-compat with v0.x importers.
from ._server_core import (
    configure_tui_mode,
    mcp,
)
from ._server_core import (
    get_client_name as _get_client_name,
)
from ._server_core import (
    get_session_id as _get_session_id,
)
from ._server_core import (
    require_tui_queue as _require_tui_queue,
)
from ._server_core import (
    tui_enqueue as _tui_enqueue,
)

# Re-export tool functions at module top level — preserves
# ``from hitl_mcp_cli.server import hitl_collect`` callers.
from .tools._collect import hitl_ask, hitl_choose, hitl_collect
from .tools._confirm import hitl_confirm
from .tools._notify import hitl_notify
from .tools._poll import hitl_poll

__all__ = [
    "_get_client_name",
    "_get_session_id",
    "_require_tui_queue",
    "_tui_enqueue",
    "configure_tui_mode",
    "hitl_ask",
    "hitl_choose",
    "hitl_collect",
    "hitl_confirm",
    "hitl_notify",
    "hitl_poll",
    "mcp",
]


# ---- Back-compat shims for v0.x test reach-ins ----
# Some tests reach into ``server._tui_queue`` / ``server._tui_app`` directly.
# Forward those to the canonical ``_server_core`` attributes so the refactor
# does not break the public test surface.
import sys as _sys

from . import _server_core as _core


def __getattr__(name: str) -> object:
    """Forward private TUI-state reads to ``_server_core``."""
    if name in ("_tui_queue", "_tui_app"):
        return getattr(_core, name)
    raise AttributeError(name)


class _ServerModule(_sys.modules[__name__].__class__):  # type: ignore[misc]
    """Module subclass forwarding ``_tui_queue`` / ``_tui_app`` writes to ``_server_core``."""

    def __setattr__(self, name: str, value: object) -> None:
        if name in ("_tui_queue", "_tui_app"):
            setattr(_core, name, value)
            return
        super().__setattr__(name, value)


_sys.modules[__name__].__class__ = _ServerModule
