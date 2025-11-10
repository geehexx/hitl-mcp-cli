"""Tests for UI components."""

from unittest.mock import patch

from hitl_mcp_cli.ui import display_banner
from hitl_mcp_cli.ui.feedback import show_error, show_info, show_success, show_warning


def test_display_banner() -> None:
    """Test banner displays correctly."""
    from io import StringIO

    from rich.console import Console

    output = StringIO()
    test_console = Console(file=output, force_terminal=True)

    with patch("hitl_mcp_cli.ui.banner.console", test_console):
        display_banner(host="localhost", port=8080)

    result = output.getvalue()
    assert "localhost" in result
    assert "8080" in result


def test_show_success() -> None:
    """Test success message display."""
    with patch("hitl_mcp_cli.ui.feedback.console") as mock_console:
        show_success("Operation completed")
        assert mock_console.print.called


def test_show_error() -> None:
    """Test error message display."""
    with patch("hitl_mcp_cli.ui.feedback.console") as mock_console:
        show_error("Operation failed")
        assert mock_console.print.called


def test_show_info() -> None:
    """Test info message display."""
    with patch("hitl_mcp_cli.ui.feedback.console") as mock_console:
        show_info("Information message")
        assert mock_console.print.called


def test_show_warning() -> None:
    """Test warning message display."""
    with patch("hitl_mcp_cli.ui.feedback.console") as mock_console:
        show_warning("Warning message")
        assert mock_console.print.called
