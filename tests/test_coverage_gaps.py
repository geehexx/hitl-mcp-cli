"""Targeted tests for uncovered lines in cli.py, tui/app.py."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest

from hitl_mcp_cli.tui.app import HITLApp
from hitl_mcp_cli.tui.queue import HITLQueue

# --- cli.py: except Exception in main ---


def test_cli_main_server_exception() -> None:
    """main() re-raises non-KeyboardInterrupt exceptions."""
    from hitl_mcp_cli.cli import main

    with (
        patch("hitl_mcp_cli.server.configure_tui_mode"),
        patch("hitl_mcp_cli.tui.HITLApp") as mock_app_cls,
        patch("hitl_mcp_cli.tui.queue.HITLQueue"),
        patch("hitl_mcp_cli.cli.mcp") as mock_mcp,
        patch("sys.argv", ["hitl-mcp"]),
    ):
        mock_mcp.http_app.return_value = MagicMock()
        mock_app_cls.return_value = MagicMock()
        mock_app_cls.return_value.run.side_effect = RuntimeError("boom")

        with pytest.raises(RuntimeError, match="boom"):
            main()


def test_cli_main_keyboard_interrupt() -> None:
    """main() handles KeyboardInterrupt gracefully."""
    from hitl_mcp_cli.cli import main

    with (
        patch("hitl_mcp_cli.server.configure_tui_mode"),
        patch("hitl_mcp_cli.tui.HITLApp") as mock_app_cls,
        patch("hitl_mcp_cli.tui.queue.HITLQueue"),
        patch("hitl_mcp_cli.cli.mcp") as mock_mcp,
        patch("sys.argv", ["hitl-mcp"]),
    ):
        mock_mcp.http_app.return_value = MagicMock()
        mock_app_cls.return_value = MagicMock()
        mock_app_cls.return_value.run.side_effect = KeyboardInterrupt()
        main()  # should not raise


# --- cli.py TUI path ---


def test_cli_tui_mode() -> None:
    """TUI app launch is the only path."""
    from hitl_mcp_cli.cli import main

    with (
        patch("hitl_mcp_cli.server.configure_tui_mode") as mock_configure,
        patch("hitl_mcp_cli.tui.HITLApp") as mock_app_cls,
        patch("hitl_mcp_cli.tui.queue.HITLQueue"),
        patch("hitl_mcp_cli.cli.mcp") as mock_mcp,
        patch("sys.argv", ["hitl-mcp"]),
    ):
        mock_mcp.http_app.return_value = MagicMock()
        mock_app_cls.return_value = MagicMock()
        main()
        mock_configure.assert_called_once()
        mock_app_cls.return_value.run.assert_called_once()


# --- tui/app.py line 100-101: _run_server exception ---


class _TestApp(HITLApp):
    CSS_PATH = ""  # type: ignore[assignment]

    def start_queue_worker(self) -> None:
        pass


def test_run_server_exception_logged(caplog: pytest.LogCaptureFixture) -> None:
    """_run_server logs exception when uvicorn fails."""
    queue = HITLQueue()
    app = _TestApp(hitl_queue=queue, mcp_app=MagicMock())

    with (
        patch("uvicorn.Config", side_effect=RuntimeError("port in use")),
        caplog.at_level(logging.ERROR, logger="hitl_mcp_cli.tui.app"),
    ):
        app._run_server()

    assert "Server thread error" in caplog.text
