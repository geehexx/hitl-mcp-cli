"""Tests for TmuxManager with mocked libtmux."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from hitl_mcp_cli.tui import tmux_manager


class TestTmuxManagerWithoutLibtmux:
    def test_no_libtmux_returns_false(self) -> None:
        with patch.object(tmux_manager, "HAS_LIBTMUX", False):
            mgr = tmux_manager.TmuxManager()
            mgr._server = None
            assert mgr.is_server_alive() is False
            assert mgr.ensure_server_pane() is False


class TestTmuxManagerWithLibtmux:
    def _make_manager(self) -> tuple[tmux_manager.TmuxManager, MagicMock]:
        mock_server = MagicMock()
        mgr = tmux_manager.TmuxManager.__new__(tmux_manager.TmuxManager)
        mgr._session_name = "hitl-mcp"
        mgr._server = mock_server
        return mgr, mock_server

    def test_is_server_alive_true(self) -> None:
        mgr, mock_server = self._make_manager()
        mock_server.sessions.get.return_value = MagicMock()
        assert mgr.is_server_alive() is True

    def test_is_server_alive_false_on_exception(self) -> None:
        mgr, mock_server = self._make_manager()
        mock_server.sessions.get.side_effect = Exception("not found")
        assert mgr.is_server_alive() is False

    def test_restart_server_sends_keys(self) -> None:
        mgr, mock_server = self._make_manager()
        mock_session = MagicMock()
        mock_pane = MagicMock()
        mock_session.active_window.active_pane = mock_pane
        mock_server.sessions.get.return_value = mock_session

        mgr.restart_server(port=6666)
        mock_pane.send_keys.assert_any_call("C-c", suppress_history=False)
        mock_pane.send_keys.assert_any_call("hitl-mcp --port 6666", enter=True)

    def test_restart_server_no_session(self) -> None:
        mgr, mock_server = self._make_manager()
        mock_server.sessions.get.side_effect = Exception("nope")
        mgr.restart_server()  # should not raise

    def test_ensure_server_pane_true(self) -> None:
        mgr, mock_server = self._make_manager()
        mock_server.sessions.get.return_value = MagicMock()
        with patch.object(tmux_manager, "HAS_LIBTMUX", True):
            assert mgr.ensure_server_pane() is True

    def test_ensure_server_pane_no_libtmux(self) -> None:
        mgr, _ = self._make_manager()
        with patch.object(tmux_manager, "HAS_LIBTMUX", False):
            assert mgr.ensure_server_pane() is False
