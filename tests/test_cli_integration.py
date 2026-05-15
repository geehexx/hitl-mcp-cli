"""Integration tests for CLI module."""

from unittest.mock import MagicMock, patch

import pytest


def test_cli_module_importable() -> None:
    """Test CLI module can be imported."""
    from hitl_mcp_cli import cli

    assert hasattr(cli, "main")


def test_cli_main_launches_tui() -> None:
    """Test CLI main always launches TUI."""
    from hitl_mcp_cli.cli import main

    with (
        patch("hitl_mcp_cli.server.configure_tui_mode"),
        patch("hitl_mcp_cli.tui.HITLApp") as mock_app_cls,
        patch("hitl_mcp_cli.tui.queue.HITLQueue"),
        patch("hitl_mcp_cli.server.mcp") as mock_mcp,
        patch("sys.argv", ["hitl-mcp"]),
    ):
        mock_mcp.http_app.return_value = MagicMock()
        mock_app_cls.return_value = MagicMock()
        main()
        mock_app_cls.return_value.run.assert_called_once()


def test_cli_main_with_custom_port() -> None:
    """Test CLI main function with custom port."""
    from hitl_mcp_cli.cli import main

    with (
        patch("hitl_mcp_cli.server.configure_tui_mode"),
        patch("hitl_mcp_cli.tui.HITLApp") as mock_app_cls,
        patch("hitl_mcp_cli.tui.queue.HITLQueue"),
        patch("hitl_mcp_cli.server.mcp") as mock_mcp,
        patch("sys.argv", ["hitl-mcp", "--port", "8080"]),
    ):
        mock_mcp.http_app.return_value = MagicMock()
        mock_app_cls.return_value = MagicMock()
        main()
        call_kwargs = mock_app_cls.call_args[1]
        assert call_kwargs["port"] == 8080


def test_cli_main_with_custom_host() -> None:
    """Test CLI main function with custom host."""
    from hitl_mcp_cli.cli import main

    with (
        patch("hitl_mcp_cli.server.configure_tui_mode"),
        patch("hitl_mcp_cli.tui.HITLApp") as mock_app_cls,
        patch("hitl_mcp_cli.tui.queue.HITLQueue"),
        patch("hitl_mcp_cli.server.mcp") as mock_mcp,
        patch("sys.argv", ["hitl-mcp", "--host", "0.0.0.0"]),
    ):
        mock_mcp.http_app.return_value = MagicMock()
        mock_app_cls.return_value = MagicMock()
        main()
        call_kwargs = mock_app_cls.call_args[1]
        assert call_kwargs["host"] == "0.0.0.0"


def test_cli_main_keyboard_interrupt() -> None:
    """Test CLI handles Ctrl+C gracefully."""
    from hitl_mcp_cli.cli import main

    with (
        patch("hitl_mcp_cli.server.configure_tui_mode"),
        patch("hitl_mcp_cli.tui.HITLApp") as mock_app_cls,
        patch("hitl_mcp_cli.tui.queue.HITLQueue"),
        patch("hitl_mcp_cli.server.mcp") as mock_mcp,
        patch("sys.argv", ["hitl-mcp"]),
    ):
        mock_mcp.http_app.return_value = MagicMock()
        mock_app_cls.return_value = MagicMock()
        mock_app_cls.return_value.run.side_effect = KeyboardInterrupt()
        main()  # should not raise


def test_cli_main_generic_exception() -> None:
    """Test CLI handles generic exceptions."""
    from hitl_mcp_cli.cli import main

    with (
        patch("hitl_mcp_cli.server.configure_tui_mode"),
        patch("hitl_mcp_cli.tui.HITLApp") as mock_app_cls,
        patch("hitl_mcp_cli.tui.queue.HITLQueue"),
        patch("hitl_mcp_cli.server.mcp") as mock_mcp,
        patch("sys.argv", ["hitl-mcp"]),
    ):
        mock_mcp.http_app.return_value = MagicMock()
        mock_app_cls.return_value = MagicMock()
        mock_app_cls.return_value.run.side_effect = RuntimeError("Test error")

        with pytest.raises(RuntimeError):
            main()
