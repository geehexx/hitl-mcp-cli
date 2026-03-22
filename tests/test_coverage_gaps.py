"""Targeted tests for uncovered lines in cli.py, ui/prompts.py, tui/app.py, tui/tmux_manager.py."""

from __future__ import annotations

import logging
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from hitl_mcp_cli.tui.app import HITLApp
from hitl_mcp_cli.tui.queue import HITLQueue

# --- ui/prompts.py line 76: re.error fallback ---


@pytest.mark.asyncio
async def test_prompt_text_invalid_regex_pattern() -> None:
    """Validator returns False when validate_pattern is an invalid regex."""
    captured_validator: list[Any] = []

    def fake_text(**kwargs: Any) -> MagicMock:
        # Capture and invoke the validator with the invalid pattern
        validate_fn = kwargs.get("validate")
        if validate_fn:
            captured_validator.append(validate_fn("anything"))
        mock_result = MagicMock()
        mock_result.execute.return_value = "anything"
        return mock_result

    with patch("hitl_mcp_cli.ui.prompts.inquirer.text", side_effect=fake_text):
        from hitl_mcp_cli.ui.prompts import prompt_text

        await prompt_text("Test:", validate_pattern="[invalid")

    assert captured_validator == [False]


# --- cli.py line 172: except Exception in main ---


def test_cli_main_server_exception() -> None:
    """main() re-raises non-KeyboardInterrupt exceptions."""
    from hitl_mcp_cli.cli import main

    with (
        patch("hitl_mcp_cli.cli.argparse.ArgumentParser.parse_args") as mock_args,
        patch("hitl_mcp_cli.cli.display_banner"),
        patch("hitl_mcp_cli.cli.mcp") as mock_mcp,
    ):
        mock_args.return_value = MagicMock(host="127.0.0.1", port=5555, no_banner=True, tui=False)
        mock_mcp.run.side_effect = RuntimeError("boom")

        with pytest.raises(RuntimeError, match="boom"):
            main()


def test_cli_main_keyboard_interrupt() -> None:
    """main() handles KeyboardInterrupt gracefully."""
    from hitl_mcp_cli.cli import main

    with (
        patch("hitl_mcp_cli.cli.argparse.ArgumentParser.parse_args") as mock_args,
        patch("hitl_mcp_cli.cli.display_banner"),
        patch("hitl_mcp_cli.cli.mcp") as mock_mcp,
    ):
        mock_args.return_value = MagicMock(host="127.0.0.1", port=5555, no_banner=True, tui=False)
        mock_mcp.run.side_effect = KeyboardInterrupt()
        main()  # should not raise


# --- cli.py --tui path (lines 82-88) ---


def test_cli_tui_mode() -> None:
    """--tui flag triggers TUI app launch."""
    from hitl_mcp_cli.cli import main

    with (
        patch("hitl_mcp_cli.cli.argparse.ArgumentParser.parse_args") as mock_args,
        patch("hitl_mcp_cli.server.configure_tui_mode") as mock_configure,
        patch("hitl_mcp_cli.tui.app.HITLApp.run") as mock_run,
        patch("hitl_mcp_cli.cli.mcp") as mock_mcp,
    ):
        mock_args.return_value = MagicMock(host="127.0.0.1", port=5555, no_banner=True, tui=True)
        mock_mcp.http_app.return_value = MagicMock()
        main()
        mock_configure.assert_called_once()
        mock_run.assert_called_once()


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


# --- tui/tmux_manager.py lines 12-14: libtmux import success path ---


def test_tmux_manager_init_with_libtmux() -> None:
    """TmuxManager.__init__ with libtmux available but no tmux server."""
    from hitl_mcp_cli.tui import tmux_manager

    mock_libtmux = MagicMock()
    mock_libtmux.Server.side_effect = Exception("no tmux")

    with (
        patch.object(tmux_manager, "HAS_LIBTMUX", True),
        patch.object(tmux_manager, "libtmux", mock_libtmux),
    ):
        mgr = tmux_manager.TmuxManager()
        assert mgr._server is None


# --- tui/tmux_manager.py lines 52-53: restart with no active pane ---


def test_tmux_restart_no_active_pane() -> None:
    """restart_server handles None active_pane gracefully."""
    from hitl_mcp_cli.tui import tmux_manager

    mgr = tmux_manager.TmuxManager.__new__(tmux_manager.TmuxManager)
    mgr._session_name = "hitl-mcp"
    mock_server = MagicMock()
    mgr._server = mock_server

    mock_session = MagicMock()
    mock_session.active_window.active_pane = None
    mock_server.sessions.get.return_value = mock_session

    mgr.restart_server()  # should not raise
