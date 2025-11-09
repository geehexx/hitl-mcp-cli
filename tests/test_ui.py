"""Tests for UI components."""

from unittest.mock import MagicMock, patch

import pytest

from hitl_mcp_cli.ui import display_banner
from hitl_mcp_cli.ui.feedback import show_error, show_info, show_success, show_warning


def test_display_banner_no_animation() -> None:
    """Test banner displays without animation."""
    with patch("hitl_mcp_cli.ui.banner.console") as mock_console:
        display_banner(host="localhost", port=8080, animate=False)
        assert mock_console.clear.called
        assert mock_console.print.called


def test_display_banner_with_animation() -> None:
    """Test banner displays with animation."""
    with patch("hitl_mcp_cli.ui.banner.console") as mock_console:
        with patch("hitl_mcp_cli.ui.banner.time.sleep"):
            display_banner(host="localhost", port=8080, animate=True)
            assert mock_console.clear.called
            assert mock_console.print.called


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
