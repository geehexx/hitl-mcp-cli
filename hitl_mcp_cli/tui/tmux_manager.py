"""Optional tmux session management for HITL TUI."""

from __future__ import annotations

import logging
from typing import Any

try:
    import libtmux

    HAS_LIBTMUX = True
except ImportError:
    libtmux = None  # type: ignore[assignment]
    HAS_LIBTMUX = False

logger = logging.getLogger(__name__)


class TmuxManager:
    """Manage a tmux session for the HITL MCP server pane."""

    def __init__(self, session_name: str = "hitl-mcp") -> None:
        self._session_name = session_name
        self._server: Any = None
        if HAS_LIBTMUX:
            try:
                self._server = libtmux.Server()
            except Exception:
                logger.debug("tmux server not available")

    def _get_session(self) -> Any:
        """Find the named tmux session, or None."""
        if self._server is None:
            return None
        try:
            return self._server.sessions.get(session_name=self._session_name)
        except Exception:
            return None

    def is_server_alive(self) -> bool:
        """Check if the tmux session exists."""
        return self._get_session() is not None

    def restart_server(self, port: int = 5555) -> None:
        """Kill and recreate the server pane with hitl-mcp on the given port."""
        session = self._get_session()
        if session is None:
            logger.warning("No tmux session '%s' found", self._session_name)
            return
        pane = session.active_window.active_pane
        if pane is None:
            logger.warning("No active pane in session '%s'", self._session_name)
            return
        pane.send_keys("C-c", suppress_history=False)
        pane.send_keys(f"hitl-mcp --port {port}", enter=True)

    def ensure_server_pane(self) -> bool:
        """Ensure the session exists; return True if ready."""
        if not HAS_LIBTMUX or self._server is None:
            return False
        return self.is_server_alive()
