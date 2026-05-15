"""Tests for CLI functionality."""

import subprocess
import sys
from unittest.mock import MagicMock, patch


def test_cli_help() -> None:
    """Test CLI help message."""
    result = subprocess.run(
        [sys.executable, "-m", "hitl_mcp_cli.cli", "--help"],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0
    assert "Interactive MCP Server" in result.stdout
    assert "--port" in result.stdout
    assert "--host" in result.stdout
    assert "--no-banner" in result.stdout


def test_cli_no_tui_flag_removed() -> None:
    """Test --no-tui flag is no longer present."""
    result = subprocess.run(
        [sys.executable, "-m", "hitl_mcp_cli.cli", "--help"],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert "--no-tui" not in result.stdout


def test_cli_launches_tui() -> None:
    """Test CLI always launches TUI app."""
    from hitl_mcp_cli.cli import main

    with (
        patch("sys.argv", ["hitl-mcp"]),
        patch("hitl_mcp_cli.server.configure_tui_mode") as mock_configure,
        patch("hitl_mcp_cli.tui.HITLApp") as mock_app_cls,
        patch("hitl_mcp_cli.tui.queue.HITLQueue"),
        patch("hitl_mcp_cli.server.mcp") as mock_mcp,
    ):
        mock_mcp.http_app.return_value = MagicMock()
        mock_app_cls.return_value = MagicMock()
        main()
        mock_configure.assert_called_once()
        mock_app_cls.return_value.run.assert_called_once()
